"""
Fáze 3: Generování a oprava pytest testů (v2 — unified prompt framework).

Změny oproti v1:
- Všechny prompty přes PromptBuilder (žádné hardcoded API pravidla)
- Stale detection: testy se stejnou chybou ≥2× po sobě se přeskakují
- PromptBuilder se předává jako parametr (vytvořen v main.py z api_cfg)

Klíčové principy (beze změny):
- Počáteční generování: LLM vygeneruje celý soubor z plánu
- Validace počtu: AST kontrola + ořezání přebytečných testů
- Izolovaná oprava: mikro-prompty pro jednotlivé failing testy
- Helper detekce: společná root cause → oprava helperů
- Počet testů se nikdy nemění
"""
import ast
import json
import re
import textwrap
import time

from prompts.prompt_templates import PromptBuilder

MAX_INDIVIDUAL_REPAIRS = 10


# ═══════════════════════════════════════════════════════════
#  AST Utility (beze změny)
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


# ═══════════════════════════════════════════════════════════
#  Pytest Log Parsing (beze změny)
# ═══════════════════════════════════════════════════════════

def _parse_failing_test_names(pytest_log: str) -> list[str]:
    names = re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)
    return list(dict.fromkeys(names))


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
    if len(failing_names) < 4:
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

    def normalize(line):
        line = re.sub(r'\d+', 'N', line)
        line = re.sub(r'["\'].*?["\']', 'STR', line)
        return line.strip()

    normalized = [normalize(e) for e in first_errors]
    most_common = max(set(normalized), key=normalized.count)
    ratio = normalized.count(most_common) / len(normalized)
    return ratio >= 0.7


# ═══════════════════════════════════════════════════════════
#  Stale Detection
# ═══════════════════════════════════════════════════════════

class StaleTracker:
    """Sleduje opakující se chyby testů napříč iteracemi.

    Test je "stale" pokud má stejnou normalizovanou chybu ≥ threshold
    po sobě jdoucích iterací KDE BYL POKUS O OPRAVU.
    Testy přeskočené kvůli capu nenabírají stale historii.
    """

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        # {test_name: [normalized_error_iter1, normalized_error_iter2, ...]}
        self._history: dict[str, list[str]] = {}
        self._stale: set[str] = set()

    def update(self, pytest_log: str, failing_names: list[str],
               attempted_names: list[str] | None = None):
        """Aktualizuj historii po každé iteraci.

        Args:
            pytest_log: výstup z pytestu
            failing_names: všechny failing testy
            attempted_names: testy které byly skutečně pokuseny o opravu.
                Pokud None, všechny failing se považují za attempted.
                Testy v failing ale NE v attempted nenabírají stale historii.
        """
        if attempted_names is None:
            attempted_names = failing_names

        attempted_set = set(attempted_names)

        current_errors: dict[str, str] = {}
        for name in failing_names:
            error = _extract_error_for_test(pytest_log, name)
            current_errors[name] = self._normalize(error)

        # Aktualizuj historii JEN pro attempted testy
        for name, norm_err in current_errors.items():
            if name in attempted_set:
                # Test dostal šanci → nabírá historii
                if name not in self._history:
                    self._history[name] = []
                self._history[name].append(norm_err)
            # Testy které nedostaly šanci: neinkrement (historii neměníme)

        # Vyčisti testy co prošly (už nejsou failing)
        passed = set(self._history.keys()) - set(failing_names)
        for name in passed:
            self._history.pop(name, None)
            self._stale.discard(name)

        # Detekuj stale
        for name, history in self._history.items():
            if len(history) >= self.threshold:
                last_n = history[-self.threshold:]
                if len(set(last_n)) == 1:  # Všechny stejné
                    if name not in self._stale:
                        print(f"      🔒 {name} je stale (stejná chyba {self.threshold}×)")
                    self._stale.add(name)

    def get_stale(self) -> list[str]:
        """Vrátí seznam stale testů."""
        return sorted(self._stale)

    def filter_repairable(self, failing_names: list[str]) -> list[str]:
        """Vrátí jen testy které NEJSOU stale (opravitelné)."""
        return [n for n in failing_names if n not in self._stale]

    @staticmethod
    def _normalize(error: str) -> str:
        """Normalizuje chybovou hlášku pro porovnání."""
        error = re.sub(r'\d+', 'N', error)
        error = re.sub(r'["\'].*?["\']', 'STR', error)
        error = re.sub(r'0x[0-9a-fA-F]+', 'ADDR', error)
        return error.strip()[:500]


# ═══════════════════════════════════════════════════════════
#  Počáteční generování
# ═══════════════════════════════════════════════════════════

def generate_test_code(test_plan: dict, context_data: str, llm,
                       prompt_builder: PromptBuilder,
                       base_url: str = "http://localhost:8000") -> str:
    """Vygeneruje kompletní testovací soubor z plánu."""
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
    """Zajistí přesně expected testů: ořízne přebytečné, doplní chybějící."""
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
#  Oprava failing testů (s PromptBuilder + stale detection)
# ═══════════════════════════════════════════════════════════

def _repair_single_test(test_name, test_code, error_msg, helpers, llm,
                         prompt_builder: PromptBuilder, base_url: str,
                         stale_tests: list[str] | None = None):
    """Mikro-prompt: opraví jeden konkrétní selhávající test."""
    prompt = prompt_builder.repair_single_prompt(
        test_name, test_code, error_msg, helpers, base_url, stale_tests
    )

    try:
        raw = llm.generate_text(prompt)
    except Exception as e:
        print(f"      ⚠️ LLM chyba: {str(e)[:100]}")
        return None

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = textwrap.dedent(clean).strip()

    try:
        tree = ast.parse(clean)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                lines = clean.split('\n')
                start = node.lineno - 1
                end = node.end_lineno - 1
                return '\n'.join(lines[start:end + 1])
    except SyntaxError:
        pass

    if f"def {test_name}" in clean or "def test_" in clean:
        return clean
    return None


def _repair_helpers(master_code, pytest_log, helpers, failing_names, llm,
                     prompt_builder: PromptBuilder, base_url: str):
    """Opraví helper funkce při detekci společné root cause."""
    sample_errors = []
    for name in failing_names[:3]:
        err = _extract_error_for_test(pytest_log, name)
        if err:
            sample_errors.append(f"Test {name}:\n{err[:500]}")

    prompt = prompt_builder.repair_helpers_prompt(
        helpers, sample_errors, len(failing_names), base_url
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

    result = _replace_helpers(master_code, clean)

    try:
        ast.parse(result)
    except SyntaxError:
        print(f"    [Repair] ⚠️ Výsledný soubor má syntax error, ponechávám původní")
        return master_code

    return result


def repair_failing_tests(master_code: str, pytest_log: str,
                         context: str, llm,
                         prompt_builder: PromptBuilder,
                         base_url: str,
                         stale_tracker: StaleTracker | None = None,
                         previous_repair_type: str | None = None,
                         ) -> tuple[str, dict]:
    """
    Izolovaně opraví selhávající testy s podporou stale detection.

    Vrací: (opravený_kód, repair_info)
    repair_info = {"repair_type": str|None, "repaired_count": int, "stale_skipped": int}

    previous_repair_type: typ opravy z předchozí iterace.
      Pokud byl "helper_root_cause" nebo "helper_fallback" a nepomohl,
      přeskočíme helper strategie a jdeme rovnou na izolovaný repair.
    """
    repair_info = {"repair_type": None, "repaired_count": 0, "stale_skipped": 0}

    failing = _parse_failing_test_names(pytest_log)
    if not failing:
        return master_code, repair_info

    # Stale detection
    stale_tests = []
    repairable = failing
    if stale_tracker:
        stale_tests = stale_tracker.get_stale()
        repairable = stale_tracker.filter_repairable(failing)
        repair_info["stale_skipped"] = len(stale_tests)

        if stale_tests:
            print(f"    [Repair] {len(stale_tests)} stale testů přeskočeno: "
                  f"{', '.join(stale_tests[:3])}{'...' if len(stale_tests) > 3 else ''}")

        if not repairable:
            print(f"    [Repair] Všechny failing testy jsou stale, přeskakuji opravu.")
            repair_info["repair_type"] = "skipped_all_stale"
            return master_code, repair_info

    helpers = _extract_helpers_code(master_code)
    backup = master_code

    # Rozhodnutí: smíme použít helper repair?
    # Pokud předchozí iterace už zkoušela helper repair a nepomohlo,
    # přeskočíme a jdeme rovnou na izolovaný repair.
    helper_already_tried = previous_repair_type in ("helper_root_cause", "helper_fallback")

    if helper_already_tried:
        print(f"    [Repair] Předchozí helper repair nepomohl → přepínám na izolovaný repair.")

    # Společná root cause → oprava helperů (jen pokud helper ještě nebyl zkoušen)
    if not helper_already_tried and _detect_helper_root_cause(pytest_log, failing):
        print(f"    [Repair] Společná root cause ({len(failing)} testů). Opravuji helpery...")
        repair_info["repair_type"] = "helper_root_cause"
        master_code = _repair_helpers(
            master_code, pytest_log, helpers, failing, llm, prompt_builder, base_url
        )
        repair_info["repaired_count"] = len(failing)
        return master_code, repair_info

    # Příliš mnoho repairable → fallback na opravu helperů (jen pokud helper ještě nebyl zkoušen)
    if not helper_already_tried and len(repairable) > MAX_INDIVIDUAL_REPAIRS:
        print(f"    [Repair] {len(repairable)} repairable testů (limit {MAX_INDIVIDUAL_REPAIRS}). "
              f"Opravuji helpery...")
        repair_info["repair_type"] = "helper_fallback"
        master_code = _repair_helpers(
            master_code, pytest_log, helpers, repairable, llm, prompt_builder, base_url
        )
        repair_info["repaired_count"] = len(repairable)
        return master_code, repair_info

    # Izolovaná oprava jednotlivých testů (capped na MAX_INDIVIDUAL_REPAIRS)
    to_repair = repairable[:MAX_INDIVIDUAL_REPAIRS]
    skipped_excess = len(repairable) - len(to_repair)

    if skipped_excess > 0:
        print(f"    [Repair] Izolovaná oprava {len(to_repair)}/{len(repairable)} testů"
              f" (+ {len(stale_tests)} stale, {skipped_excess} odloženo na další iteraci)...")
    else:
        print(f"    [Repair] Izolovaná oprava {len(to_repair)} testů"
              f" (+ {len(stale_tests)} stale přeskočeno)...")

    repair_info["repair_type"] = "isolated"
    repaired = 0

    for i, test_name in enumerate(to_repair, 1):
        if i > 1:
            time.sleep(5)

        test_code = _extract_function_code(master_code, test_name)
        if not test_code:
            print(f"      ⚠️ {test_name} nenalezen v kódu")
            continue

        error_msg = _extract_error_for_test(pytest_log, test_name)
        print(f"      ({i}/{len(to_repair)}) {test_name}...")

        fixed = _repair_single_test(
            test_name, test_code, error_msg, helpers, llm,
            prompt_builder, base_url, stale_tests
        )

        if fixed:
            new_code = _replace_function_code(master_code, test_name, fixed)
            try:
                ast.parse(new_code)
                master_code = new_code
                repaired += 1
            except SyntaxError:
                print(f"      ⚠️ {test_name} oprava způsobila syntax error, přeskakuji")
        else:
            print(f"      ⚠️ {test_name} oprava selhala")

    repair_info["repaired_count"] = repaired
    print(f"    [Repair] ✅ Opraveno {repaired}/{len(to_repair)}")

    if stale_tracker:
        if repair_info["repair_type"] in ("helper_root_cause", "helper_fallback"):
            # Helper repair = pokus o opravu VŠECH failing
            stale_tracker.update(pytest_log, failing, attempted_names=failing)
        elif repair_info["repair_type"] == "isolated":
            # Izolovaný = jen to_repair (capped seznam)
            stale_tracker.update(pytest_log, failing, attempted_names=to_repair)
        elif repair_info["repair_type"] == "skipped_all_stale":
            # Nikdo nebyl attempted, ale stale testy stále failují
            stale_tracker.update(pytest_log, failing, attempted_names=[])

    # Bezpečnostní kontrola: počet testů se nesmí změnit
    before = count_test_functions(backup)
    after = count_test_functions(master_code)
    if before != after:
        print(f"    [Repair] ⚠️ Počet testů se změnil ({before} → {after}), revertuji")
        master_code = backup

    return master_code, repair_info