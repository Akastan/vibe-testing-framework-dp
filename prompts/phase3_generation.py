"""
Fáze 3: Generování a oprava pytest testů (v4 — context-aware repair + regression guard).

Změny oproti v3:
  - Repair prompty dostávají API kontext → LLM ví CO opravuje
  - Regression guard: po opravě se porovná počet passing testů, rollback při regresi
  - Helper repair: validace že nové helpery obsahují všechny importy + funkce z originálu
  - repair_failing_tests() má nový parametr context

Flow:
  Iterace 1: isolated repair (per-test prompty)
  Iterace 2: helper repair (pokud root cause, jinak isolated znovu)
  Iterace 3: isolated (pro ne-stale testy)
  Iterace 4: helper
  ...dokud nejsou všechny stale nebo max_iterations
"""
import ast
import json
import re
import textwrap
import time

from prompts.prompt_templates import PromptBuilder

MAX_INDIVIDUAL_REPAIRS = 10


# ═══════════════════════════════════════════════════════════
#  AST Utility
# ═══════════════════════════════════════════════════════════

def count_test_functions(code: str) -> int:
    try:
        tree = ast.parse(code)
        return sum(1 for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    except SyntaxError:
        return 0


def _get_test_function_names(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
        funcs = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                funcs.append((node.lineno, node.name))
        return [name for _, name in sorted(funcs)]
    except SyntaxError:
        return []


def _get_function_range(code: str, func_name: str):
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                start = node.lineno - 1
                if node.decorator_list:
                    start = node.decorator_list[0].lineno - 1
                end = node.end_lineno - 1
                return start, end
    except SyntaxError:
        pass
    return None


def _extract_function_code(code: str, func_name: str):
    rng = _get_function_range(code, func_name)
    if not rng:
        return None
    start, end = rng
    lines = code.split('\n')
    return '\n'.join(lines[start:end + 1])


def _replace_function_code(code: str, func_name: str, new_func: str) -> str:
    rng = _get_function_range(code, func_name)
    if not rng:
        return code
    start, end = rng
    lines = code.split('\n')
    new_func = textwrap.dedent(new_func).strip()
    new_lines = lines[:start] + new_func.split('\n') + lines[end + 1:]
    return '\n'.join(new_lines)


def _extract_helpers_code(code: str) -> str:
    test_names = _get_test_function_names(code)
    if not test_names:
        return code
    first_rng = _get_function_range(code, test_names[0])
    if not first_rng:
        return ""
    lines = code.split('\n')
    return '\n'.join(lines[:first_rng[0]]).strip()


def _replace_helpers(code: str, new_helpers: str) -> str:
    test_names = _get_test_function_names(code)
    if not test_names:
        return code
    first_rng = _get_function_range(code, test_names[0])
    if not first_rng:
        return code
    lines = code.split('\n')
    tests_part = '\n'.join(lines[first_rng[0]:])
    return new_helpers.strip() + '\n\n\n' + tests_part


def _remove_last_n_tests(code: str, n: int) -> str:
    test_names = _get_test_function_names(code)
    if n <= 0 or n > len(test_names):
        return code
    to_remove = test_names[-n:]
    for name in reversed(to_remove):
        rng = _get_function_range(code, name)
        if rng:
            start, end = rng
            lines = code.split('\n')
            while end + 1 < len(lines) and lines[end + 1].strip() == '':
                end += 1
            code = '\n'.join(lines[:start] + lines[end + 1:])
    return code


def _get_all_function_names(code: str) -> list[str]:
    """Vrátí názvy VŠECH funkcí (ne jen test_) v kódu."""
    try:
        tree = ast.parse(code)
        return [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    except SyntaxError:
        return []


def _get_import_names(code: str) -> set[str]:
    """Vrátí set importovaných modulů/jmen."""
    try:
        tree = ast.parse(code)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
        return names
    except SyntaxError:
        return set()


# ═══════════════════════════════════════════════════════════
#  Pytest Log Parsing
# ═══════════════════════════════════════════════════════════

def _parse_failing_test_names(pytest_log: str) -> list[str]:
    names = re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)
    return list(dict.fromkeys(names))


def _parse_passing_count(pytest_log: str) -> int:
    """Extrahuje počet passing testů z pytest výstupu."""
    match = re.search(r'(\d+)\s+passed', pytest_log)
    return int(match.group(1)) if match else 0


def _extract_error_for_test(pytest_log: str, test_name: str) -> str:
    pattern = (
        rf'_{2,}\s+{re.escape(test_name)}\s+_{2,}'
        rf'(.*?)'
        rf'(?=_{2,}\s+\w+\s+_{2,}|={2,}\s+short test summary|$)'
    )
    match = re.search(pattern, pytest_log, re.DOTALL)
    if match:
        return match.group(1).strip()[:1500]
    return ""


def _detect_helper_root_cause(pytest_log: str, failing_names: list[str]) -> bool:
    if len(failing_names) < 3:
        return False

    first_errors = []
    for name in failing_names:
        error_block = _extract_error_for_test(pytest_log, name)
        if not error_block:
            continue
        for line in error_block.splitlines():
            stripped = line.strip()
            if stripped.startswith("E "):
                first_errors.append(stripped)
                break

    if len(first_errors) < 3:
        return False

    normalized = [_normalize_error(e) for e in first_errors]
    most_common = max(set(normalized), key=normalized.count)
    ratio = normalized.count(most_common) / len(normalized)
    return ratio >= 0.7


def _normalize_error(error: str) -> str:
    error = re.sub(r'\d+', 'N', error)
    error = re.sub(r'["\'].*?["\']', 'STR', error)
    error = re.sub(r'0x[0-9a-fA-F]+', 'ADDR', error)
    return error.strip()[:500]


# ═══════════════════════════════════════════════════════════
#  Stale Detection (v3)
# ═══════════════════════════════════════════════════════════

class _StaleEntry:
    __slots__ = ("isolated_errors", "helper_errors")

    def __init__(self):
        self.isolated_errors: list[str] = []
        self.helper_errors: list[str] = []


class StaleTracker:
    """Sleduje opakující se chyby testů napříč iteracemi.

    Test je "stale" pokud:
      1. Má alespoň 1 pokus o izolovanou opravu
      2. Má alespoň 1 pokus o helper opravu
      3. Poslední chyba z obou typů je stejná (normalizovaná)
    """

    def __init__(self):
        self._entries: dict[str, _StaleEntry] = {}
        self._stale: set[str] = set()

    def update(self, repair_type: str, pytest_log: str,
               failing_names: list[str],
               attempted_names: list[str]):
        attempted_set = set(attempted_names)
        is_helper = repair_type in ("helper_root_cause", "helper_fallback")

        for name in failing_names:
            if name not in attempted_set:
                continue
            error = _extract_error_for_test(pytest_log, name)
            norm = _normalize_error(error)
            entry = self._entries.setdefault(name, _StaleEntry())
            if is_helper:
                entry.helper_errors.append(norm)
            else:
                entry.isolated_errors.append(norm)

        passed = set(self._entries.keys()) - set(failing_names)
        for name in passed:
            self._entries.pop(name, None)
            self._stale.discard(name)

        for name, entry in self._entries.items():
            if not entry.isolated_errors or not entry.helper_errors:
                continue
            last_isolated = entry.isolated_errors[-1]
            last_helper = entry.helper_errors[-1]
            if last_isolated == last_helper:
                if name not in self._stale:
                    print(f"      🔒 {name} je stale "
                          f"(isolated {len(entry.isolated_errors)}× + "
                          f"helper {len(entry.helper_errors)}×, stejná chyba)")
                self._stale.add(name)

    def get_stale(self) -> list[str]:
        return sorted(self._stale)

    def filter_repairable(self, failing_names: list[str]) -> list[str]:
        return [n for n in failing_names if n not in self._stale]


# ═══════════════════════════════════════════════════════════
#  Počáteční generování
# ═══════════════════════════════════════════════════════════

def generate_test_code(test_plan: dict, context_data: str, llm,
                       prompt_builder: PromptBuilder,
                       base_url: str = "http://localhost:8000") -> str:
    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)
    prompt = prompt_builder.generation_prompt(plan_str, context_data, base_url)

    raw = llm.generate_text(prompt)

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]

    return clean.strip()


# ═══════════════════════════════════════════════════════════
#  Validace počtu testů
# ═══════════════════════════════════════════════════════════

def validate_test_count(code: str, expected: int, llm=None,
                        prompt_builder: PromptBuilder = None,
                        base_url: str = "http://localhost:8000",
                        context: str = "") -> str:
    actual = count_test_functions(code)
    if actual == expected:
        return code

    if actual > expected:
        excess = actual - expected
        print(f"    [Validace] {actual} testů → ořezávám na {expected} (-{excess})")
        return _remove_last_n_tests(code, excess)

    if not llm or not prompt_builder:
        print(f"    [Validace] ⚠️ {actual} testů (očekáváno {expected}), LLM nedostupný")
        return code

    missing = expected - actual
    print(f"    [Validace] {actual} testů → doplňuji {missing}...")

    helpers = _extract_helpers_code(code)
    existing_names = _get_test_function_names(code)

    fill_prompt = prompt_builder.fill_tests_prompt(
        missing, helpers, existing_names, context, base_url
    )

    try:
        raw = llm.generate_text(fill_prompt)
    except Exception as e:
        print(f"    [Validace] ⚠️ LLM chyba: {e}")
        return code

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    if not clean:
        return code

    new_code = code.rstrip() + "\n\n\n" + clean

    try:
        ast.parse(new_code)
    except SyntaxError:
        print(f"    [Validace] ⚠️ Doplněné testy mají syntax error, ponechávám původní")
        return code

    new_actual = count_test_functions(new_code)
    if new_actual > expected:
        excess = new_actual - expected
        new_code = _remove_last_n_tests(new_code, excess)
        new_actual = count_test_functions(new_code)

    print(f"    [Validace] ✅ {new_actual} testů (cíl {expected})")
    return new_code


# ═══════════════════════════════════════════════════════════
#  Helper repair — safety validation
# ═══════════════════════════════════════════════════════════

def _validate_helpers_safe(old_helpers: str, new_helpers: str) -> tuple[bool, str]:
    """Ověří že nové helpery neztratily importy ani funkce oproti starým.

    Returns:
        (is_safe, reason)
    """
    old_imports = _get_import_names(old_helpers)
    new_imports = _get_import_names(new_helpers)
    missing_imports = old_imports - new_imports
    if missing_imports:
        return False, f"Chybějící importy: {missing_imports}"

    old_funcs = set(_get_all_function_names(old_helpers))
    new_funcs = set(_get_all_function_names(new_helpers))
    # Odfiltruj test_ funkce (neměly by být v helperech)
    old_helpers_only = {f for f in old_funcs if not f.startswith("test_")}
    new_helpers_only = {f for f in new_funcs if not f.startswith("test_")}
    missing_funcs = old_helpers_only - new_helpers_only
    if missing_funcs:
        return False, f"Chybějící helper funkce: {missing_funcs}"

    return True, "OK"


# ═══════════════════════════════════════════════════════════
#  Repair — interní funkce
# ═══════════════════════════════════════════════════════════

def _repair_helpers(master_code, pytest_log, helpers, failing_names, llm,
                     prompt_builder: PromptBuilder, base_url: str, context: str):
    sample_errors = []
    for name in failing_names[:3]:
        err = _extract_error_for_test(pytest_log, name)
        if err:
            sample_errors.append(f"Test {name}:\n{err[:500]}")

    prompt = prompt_builder.repair_helpers_prompt(
        helpers, sample_errors, len(failing_names), context, base_url
    )

    try:
        raw = llm.generate_text(prompt)
    except Exception as e:
        print(f"    [Repair] ⚠️ LLM chyba při opravě helperů: {e}")
        return master_code

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    if not clean:
        return master_code

    try:
        ast.parse(clean)
    except SyntaxError:
        print(f"    [Repair] ⚠️ Opravené helpery mají syntax error, ponechávám původní")
        return master_code

    # ── Safety check: nové helpery nesmí ztratit importy/funkce ──
    is_safe, reason = _validate_helpers_safe(helpers, clean)
    if not is_safe:
        print(f"    [Repair] ⚠️ Nové helpery nejsou bezpečné: {reason}")
        print(f"    [Repair] ⚠️ Zkouším merge: zachovám staré importy + přidám opravené funkce")
        clean = _merge_helpers(helpers, clean)
        if not clean:
            print(f"    [Repair] ⚠️ Merge selhal, ponechávám původní helpery")
            return master_code

    result = _replace_helpers(master_code, clean)

    try:
        ast.parse(result)
    except SyntaxError:
        print(f"    [Repair] ⚠️ Výsledný soubor má syntax error, ponechávám původní")
        return master_code

    return result


def _merge_helpers(old_helpers: str, new_helpers: str) -> str | None:
    """Pokusí se mergovat staré a nové helpery — zachová staré importy,
    použije nové funkce."""
    try:
        # Extrahuj importy z obou
        old_lines = old_helpers.split('\n')
        new_lines = new_helpers.split('\n')

        # Najdi import řádky ze starých helperů
        old_import_lines = []
        old_rest_lines = []
        for line in old_lines:
            stripped = line.strip()
            if (stripped.startswith("import ") or stripped.startswith("from ")
                    or stripped == "" and not old_rest_lines):
                old_import_lines.append(line)
            else:
                old_rest_lines.append(line)

        # Najdi ne-import řádky z nových helperů (opravené funkce)
        new_func_lines = []
        in_imports = True
        for line in new_lines:
            stripped = line.strip()
            if in_imports and (stripped.startswith("import ") or stripped.startswith("from ")
                               or stripped == ""):
                continue  # Přeskočíme importy z nových — použijeme staré
            else:
                in_imports = False
                new_func_lines.append(line)

        merged = '\n'.join(old_import_lines) + '\n\n' + '\n'.join(new_func_lines)

        # Ověř syntax
        ast.parse(merged)
        return merged.strip()
    except SyntaxError:
        return None


def _do_isolated_repairs(master_code, pytest_log, repairable, helpers, llm,
                          prompt_builder, base_url, context, stale_tests):
    """Hromadná izolovaná oprava — 1 prompt pro všechny failing testy."""
    to_repair = repairable[:MAX_INDIVIDUAL_REPAIRS]
    skipped_excess = len(repairable) - len(to_repair)

    if skipped_excess > 0:
        print(f"    [Repair:Isolated] Opravuji {len(to_repair)}/{len(repairable)} testů"
              f" v 1 promptu ({skipped_excess} odloženo)...")
    else:
        print(f"    [Repair:Isolated] Opravuji {len(to_repair)} testů v 1 promptu...")

    test_entries = []
    for name in to_repair:
        code = _extract_function_code(master_code, name)
        if not code:
            print(f"      ⚠️ {name} nenalezen v kódu")
            continue
        error = _extract_error_for_test(pytest_log, name)
        test_entries.append((name, code, error))

    if not test_entries:
        return master_code, 0, to_repair

    prompt = prompt_builder.repair_batch_prompt(
        test_entries, helpers, context, base_url, stale_tests
    )

    try:
        raw = llm.generate_text(prompt)
    except Exception as e:
        print(f"    [Repair:Isolated] ⚠️ LLM chyba: {str(e)[:120]}")
        return master_code, 0, to_repair

    fixed_functions = _parse_batch_repair_response(raw)
    print(f"    [Repair:Isolated] LLM vrátil {len(fixed_functions)} opravených funkcí")

    repaired = 0
    for name, fixed_code in fixed_functions.items():
        if name not in {e[0] for e in test_entries}:
            continue

        new_code = _replace_function_code(master_code, name, fixed_code)
        try:
            ast.parse(new_code)
            master_code = new_code
            repaired += 1
        except SyntaxError:
            print(f"      ⚠️ {name} oprava způsobila syntax error, přeskakuji")

    print(f"    [Repair:Isolated] ✅ Opraveno {repaired}/{len(test_entries)}")
    return master_code, repaired, to_repair


def _parse_batch_repair_response(raw: str) -> dict[str, str]:
    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    if not clean:
        return {}

    try:
        tree = ast.parse(clean)
    except SyntaxError:
        return _extract_functions_regex(clean)

    functions = {}
    lines = clean.split('\n')
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            start = node.lineno - 1
            if node.decorator_list:
                start = node.decorator_list[0].lineno - 1
            end = node.end_lineno - 1
            func_code = '\n'.join(lines[start:end + 1])
            functions[node.name] = func_code

    return functions


def _extract_functions_regex(raw: str) -> dict[str, str]:
    functions = {}
    pattern = r'(def (test_\w+)\(.*?\):.*?)(?=\ndef |\Z)'
    for match in re.finditer(pattern, raw, re.DOTALL):
        func_code = match.group(1).rstrip()
        func_name = match.group(2)
        try:
            ast.parse(func_code)
            functions[func_name] = func_code
        except SyntaxError:
            continue
    return functions


def _do_helper_repair(master_code, pytest_log, repairable, helpers, llm,
                       prompt_builder, base_url, context):
    is_root_cause = _detect_helper_root_cause(pytest_log, repairable)

    if is_root_cause:
        print(f"    [Repair:Helper] Root cause detekována ({len(repairable)} testů). "
              f"Opravuji helpery...")
        repair_type = "helper_root_cause"
    else:
        print(f"    [Repair:Helper] {len(repairable)} testů stále selhává po izolované opravě. "
              f"Zkouším helpery...")
        repair_type = "helper_fallback"

    new_code = _repair_helpers(
        master_code, pytest_log, helpers, repairable, llm, prompt_builder,
        base_url, context
    )
    return new_code, repair_type


# ═══════════════════════════════════════════════════════════
#  Hlavní repair funkce (v4)
# ═══════════════════════════════════════════════════════════

def repair_failing_tests(master_code: str, pytest_log: str,
                         context: str, llm,
                         prompt_builder: PromptBuilder,
                         base_url: str,
                         stale_tracker: StaleTracker | None = None,
                         previous_repair_type: str | None = None,
                         ) -> tuple[str, dict]:
    """
    Opraví selhávající testy. Alternuje: isolated → helper → isolated → ...

    Nově:
      - Předává API kontext do repair promptů → LLM ví co opravuje
      - Regression guard: po opravě porovná passing count, rollback při regresi

    Returns:
        (opravený_kód, repair_info)
    """
    repair_info = {
        "repair_type": None,
        "repaired_count": 0,
        "stale_skipped": 0,
        "regression_rollback": False,
    }

    failing = _parse_failing_test_names(pytest_log)
    if not failing:
        return master_code, repair_info

    passing_before = _parse_passing_count(pytest_log)

    # ── Stale filtrování ─────────────────────────────────
    stale_tests = []
    repairable = failing

    if stale_tracker:
        stale_tests = stale_tracker.get_stale()
        repairable = stale_tracker.filter_repairable(failing)
        repair_info["stale_skipped"] = len(stale_tests)

        if stale_tests:
            print(f"    [Repair] {len(stale_tests)} stale testů přeskočeno: "
                  f"{', '.join(stale_tests[:5])}{'...' if len(stale_tests) > 5 else ''}")

        if not repairable:
            print(f"    [Repair] ⛔ Všechny failing testy ({len(failing)}) jsou stale. "
                  f"Další iterace nemají smysl.")
            repair_info["repair_type"] = "all_stale_early_stop"
            return master_code, repair_info

    helpers = _extract_helpers_code(master_code)
    backup = master_code

    # ── Rozhodnutí: isolated nebo helper? ────────────────
    use_helper = (previous_repair_type == "isolated")

    if use_helper:
        # ── HELPER REPAIR ────────────────────────────────
        master_code, repair_type = _do_helper_repair(
            master_code, pytest_log, repairable, helpers,
            llm, prompt_builder, base_url, context,
        )
        repair_info["repair_type"] = repair_type
        repair_info["repaired_count"] = len(repairable)

        if stale_tracker:
            stale_tracker.update(
                repair_type, pytest_log, failing,
                attempted_names=repairable,
            )

    else:
        # ── ISOLATED REPAIR ──────────────────────────────
        master_code, repaired, attempted = _do_isolated_repairs(
            master_code, pytest_log, repairable, helpers,
            llm, prompt_builder, base_url, context, stale_tests,
        )
        repair_info["repair_type"] = "isolated"
        repair_info["repaired_count"] = repaired

        if stale_tracker:
            stale_tracker.update(
                "isolated", pytest_log, failing,
                attempted_names=attempted,
            )

    # ── Bezpečnostní kontrola: počet testů se nesmí změnit ──
    before = count_test_functions(backup)
    after = count_test_functions(master_code)
    if before != after:
        print(f"    [Repair] ⚠️ Počet testů se změnil ({before} → {after}), revertuji")
        master_code = backup
        repair_info["regression_rollback"] = True

    return master_code, repair_info