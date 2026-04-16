"""
Fáze 3: Generování a oprava pytest testů (v5 — stale refresh + helper retry).

Změny oproti v4:
  - StaleTracker.refresh_with_current_errors(): odblokuje testy jejichž chyba se změnila
  - Nová alternační logika: helper retry pokud helper změnil chybu (progres)
  - repair_failing_tests() vrací "errors_changed" v repair_info

Flow alternace:
  - previous == None nebo isolated → helper (pokud root cause) nebo isolated
  - previous == isolated → helper
  - previous == helper + chyba se změnila → ZNOVU helper (progres!)
  - previous == helper + chyba stejná → isolated (a pravděpodobně stale)
"""
import ast
import json
import re
import textwrap
import time

from pipeline.prompt_templates import PromptBuilder

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
        return match.group(1).strip()[-2000:]
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
    return error.strip()


# ═══════════════════════════════════════════════════════════
#  Stale Detection (v5 — s refresh logikou)
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

    v5: refresh_with_current_errors() odblokuje testy jejichž chyba
    se mezitím změnila (např. helper repair opravil root cause ale
    zavedl nový bug → jiná chyba = progres, ne stale).
    """

    def __init__(self):
        self._entries: dict[str, _StaleEntry] = {}
        self._stale: set[str] = set()

    def update(self, repair_type: str, pytest_log: str,
               failing_names: list[str],
               attempted_names: list[str],
               code_changed: bool = False):
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

        # ÚPLNĚ ODSTRANĚNO: if code_changed: return ...
        # Díky refresh_with_current_errors můžeme vyhodnocovat limity okamžitě.

        for name, entry in self._entries.items():
            iso_count = len(entry.isolated_errors)
            help_count = len(entry.helper_errors)

            # Nový striktní limit: stačí 1x isolated a 1x helper
            if iso_count >= 1 and help_count >= 1:
                last_isolated = entry.isolated_errors[-1]
                last_helper = entry.helper_errors[-1]

                # Pokud obě strategie skončily na naprosto stejné chybě -> STALE
                if last_isolated == last_helper:
                    if name not in self._stale:
                        print(f"      🔒 {name} je stale "
                              f"(isolated i helper selhaly na identické chybě)")
                    self._stale.add(name)

    def refresh_with_current_errors(self, pytest_log: str,
                                     failing_names: list[str]) -> list[str]:
        """Zkontroluje aktuální chyby stale testů. Pokud se chyba změnila,
        odblokuje test (smaže historii) → dostane novou šanci na opravu.

        Returns:
            Seznam odblokovaných testů.
        """
        unstaled = []
        for name in list(self._stale):
            if name not in failing_names:
                # Test prošel! Odstraň ze stale i entries.
                self._stale.discard(name)
                self._entries.pop(name, None)
                unstaled.append(name)
                continue

            current_error = _extract_error_for_test(pytest_log, name)
            current_norm = _normalize_error(current_error)

            entry = self._entries.get(name)
            if not entry:
                continue

            # Porovnej s poslední známou chybou (z obou seznamů)
            last_known = set()
            if entry.isolated_errors:
                last_known.add(entry.isolated_errors[-1])
            if entry.helper_errors:
                last_known.add(entry.helper_errors[-1])

            if last_known and current_norm not in last_known:
                # Chyba se změnila! → odblokuj, resetuj historii
                self._stale.discard(name)
                entry.isolated_errors.clear()
                entry.helper_errors.clear()
                unstaled.append(name)

        if unstaled:
            print(f"      🔓 {len(unstaled)} testů odblokováno (chyba se změnila): "
                  f"{', '.join(unstaled[:5])}{'...' if len(unstaled) > 5 else ''}")

        return unstaled

    def detect_errors_changed(self, pytest_log: str,
                               failing_names: list[str]) -> bool:
        """Zjistí zda se chyby failing testů změnily oproti poslední iteraci.

        Používá se pro rozhodnutí: opakovat helper repair (progres)
        nebo přepnout na isolated (žádný progres).
        """
        changed = 0
        total = 0
        for name in failing_names:
            entry = self._entries.get(name)
            if not entry:
                continue

            current_error = _extract_error_for_test(pytest_log, name)
            current_norm = _normalize_error(current_error)

            # Porovnej s poslední známou chybou
            last_known = None
            if entry.helper_errors:
                last_known = entry.helper_errors[-1]
            elif entry.isolated_errors:
                last_known = entry.isolated_errors[-1]

            if last_known is not None:
                total += 1
                if current_norm != last_known:
                    changed += 1

        if total == 0:
            return False

        # Pokud ≥50% testů má jinou chybu, považuj za "errors changed"
        ratio = changed / total
        if ratio >= 0.5:
            print(f"      🔄 Chyby se změnily u {changed}/{total} testů ({ratio:.0%})")
            return True
        return False

    def get_stale(self) -> list[str]:
        return sorted(self._stale)

    def filter_repairable(self, failing_names: list[str]) -> list[str]:
        return [n for n in failing_names if n not in self._stale]



# ═══════════════════════════════════════════════════════════
#  Import Sanitizer
# ═══════════════════════════════════════════════════════════

# Knihovny které NEJSOU dostupné v test prostředí
_BANNED_IMPORTS = {
    "PIL", "pillow", "numpy", "pandas", "matplotlib",
    "scipy", "sklearn", "flask", "django", "fastapi",
    "sqlalchemy", "pydantic", "httpx", "aiohttp",
}

# Mapování: pokud se v kódu vyskytne daný pattern → potřebuje tento import
_AUTO_IMPORTS = {
    "datetime.now":       "from datetime import datetime",
    "datetime.utcnow":    "from datetime import datetime",
    "datetime(":          "from datetime import datetime",
    "timezone.utc":       "from datetime import timezone",
    "timedelta(":         "from datetime import timedelta",
    "json.dumps":         "import json",
    "json.loads":         "import json",
    "base64.b64encode":   "import base64",
    "base64.b64decode":   "import base64",
    "os.path":            "import os",
    "os.environ":         "import os",
    "re.search":          "import re",
    "re.match":           "import re",
    "re.findall":         "import re",
    "copy.deepcopy":      "import copy",
    "random.randint":     "import random",
    "random.choice":      "import random",
    "string.ascii":       "import string",
    "math.ceil":          "import math",
    "math.floor":         "import math",
    "pytest":             "import pytest",
    "@pytest":            "import pytest",
    "pytest.":            "import pytest",
    "requests.get":       "import requests",
    "requests.post":      "import requests",
    "requests.put":       "import requests",
    "requests.patch":     "import requests",
    "requests.delete":    "import requests",
    "requests.request":   "import requests",
    "uuid.uuid4":         "import uuid",
    "uuid4(":             "import uuid",
    "time.sleep":         "import time",
    "time.time":          "import time",
}


def _fix_imports(code: str) -> str:
    """Opraví importy ve vygenerovaném kódu:
    1. Odstraní importy nedostupných knihoven (PIL, numpy, ...)
    2. Přidá chybějící importy standardní knihovny (datetime, json, ...)

    Returns:
        Opravený kód.
    """
    lines = code.split('\n')
    changes_made = False

    # ── 1) Odstranění banned importů ─────────────────────
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()

        # "from PIL import ..." nebo "import PIL"
        is_banned = False
        if stripped.startswith("from "):
            module = stripped.split()[1].split(".")[0]
            if module in _BANNED_IMPORTS:
                is_banned = True
        elif stripped.startswith("import "):
            # "import numpy" nebo "import numpy as np"
            modules = stripped[7:].split(",")
            for m in modules:
                mod_name = m.strip().split()[0].split(".")[0]
                if mod_name in _BANNED_IMPORTS:
                    is_banned = True
                    break

        if is_banned:
            print(f"    [ImportFix] ❌ Odstraněn nedostupný import: {stripped}")
            changes_made = True
            continue

        cleaned_lines.append(line)

    # ── 2) Detekce chybějících importů ───────────────────
    code_body = '\n'.join(cleaned_lines)
    existing_imports = set()
    for line in cleaned_lines:
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            existing_imports.add(stripped)

    missing_imports = []
    for pattern, import_stmt in _AUTO_IMPORTS.items():
        if pattern in code_body and import_stmt not in existing_imports:
            # Ověř že import ještě není přítomen v jiné formě
            # např. "from datetime import datetime, timezone" pokrývá oba
            module_name = import_stmt.split()[-1]  # "datetime", "json", etc.

            already_imported = False
            for existing in existing_imports:
                if module_name in existing:
                    already_imported = True
                    break

            if not already_imported:
                missing_imports.append(import_stmt)
                existing_imports.add(import_stmt)  # Prevent duplicates

    if missing_imports:
        # Deduplikace
        missing_imports = list(dict.fromkeys(missing_imports))
        print(f"    [ImportFix] ➕ Přidávám chybějící importy: {missing_imports}")
        changes_made = True

        # Najdi pozici pro vložení (za poslední existující import)
        last_import_idx = -1
        for i, line in enumerate(cleaned_lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import_idx = i

        insert_pos = last_import_idx + 1 if last_import_idx >= 0 else 0
        for imp in reversed(missing_imports):
            cleaned_lines.insert(insert_pos, imp)

    if changes_made:
        result = '\n'.join(cleaned_lines)
        # Ověř že výsledek je validní Python
        try:
            ast.parse(result)
            return result
        except SyntaxError:
            print(f"    [ImportFix] ⚠️ Oprava importů způsobila syntax error, vracím originál")
            return code

    return code

def _is_truncated(code: str) -> bool:
    """Detekuje zda byl kód oříznut (nevalidní AST)."""
    try:
        ast.parse(code)
        return False
    except SyntaxError:
        return True


def _salvage_truncated_code(code: str) -> str:
    """Pokusí se zachránit oříznutý kód — ořízne na poslední kompletní funkci.

    Strategie: odebírej řádky od konce dokud AST neprojde.
    Optimalizace: skáče po blocích, pak jemně.
    """
    lines = code.split('\n')

    # Rychlý pokus: najdi poslední 'def test_' a ořízni před ním
    last_test_start = None
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('def test_'):
            last_test_start = i
            break

    if last_test_start is not None:
        # Ořízni nekompletní poslední test
        candidate = '\n'.join(lines[:last_test_start]).rstrip()
        if not _is_truncated(candidate) and count_test_functions(candidate) > 0:
            salvaged_count = count_test_functions(candidate)
            print(f"    [Salvage] Oříznutý kód zachráněn: {salvaged_count} kompletních testů")
            return candidate

    # Fallback: ořezávej řádky od konce po blocích
    for cut in range(1, min(200, len(lines))):
        candidate = '\n'.join(lines[:-cut]).rstrip()
        if not _is_truncated(candidate) and count_test_functions(candidate) > 0:
            salvaged_count = count_test_functions(candidate)
            print(f"    [Salvage] Fallback: {salvaged_count} kompletních testů (ořízl {cut} řádků)")
            return candidate

    print(f"    [Salvage] ⚠️ Nepodařilo se zachránit kód")
    return code

# ═══════════════════════════════════════════════════════════
#  LLM Response Cleanup
# ═══════════════════════════════════════════════════════════

def _clean_llm_response(raw: str) -> str:
    """Odstraní prose, markdown bloky a další obal kolem Python kódu.

    Mistral (a jiné modely) často ignorují instrukci 'NO MARKDOWN, NO PROSE'
    a odpověď obalí do prose textu + ```python bloků. Naivní startswith()
    to nechytí pokud je prose PŘED markdown blokem.
    """
    clean = raw.strip()

    # 1) Najdi ```python blok a vezmi jen jeho obsah
    match = re.search(r'```python\s*\n(.*?)(?:```|$)', clean, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2) Obecný ``` blok
    match = re.search(r'```\s*\n(.*?)(?:```|$)', clean, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3) Prose před kódem — najdi první import/def/komentář
    first_code = re.search(r'^(import |from |def |#)', clean, re.MULTILINE)
    if first_code and first_code.start() > 0:
        clean = clean[first_code.start():]

    # 4) Fallback: stávající strip (pro případ že ``` je na začátku)
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]

    return clean.strip()


# ═══════════════════════════════════════════════════════════
#  Počáteční generování
# ═══════════════════════════════════════════════════════════

def generate_test_code(test_plan: dict, context_data: str, llm,
                       prompt_builder: PromptBuilder,
                       base_url: str = "http://localhost:8000") -> str:
    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)
    prompt = prompt_builder.generation_prompt(plan_str, context_data, base_url)

    raw = llm.generate_text(prompt)

    # ── Robustní cleanup (prose + markdown) ──────────
    clean = _clean_llm_response(raw)
    clean = _fix_imports(clean)

    # ── Truncation detection ─────────────────────────
    if _is_truncated(clean):
        print(f"    ⚠️ TRUNCATION DETECTED — kód je syntakticky nevalidní (pravděpodobně max_tokens limit)")
        original_lines = len(clean.split('\n'))
        clean = _salvage_truncated_code(clean)
        salvaged_lines = len(clean.split('\n'))
        print(f"    [Salvage] {original_lines} → {salvaged_lines} řádků")

    # ── Okamžitý trim pokud model přestřelil ────────
    expected = sum(
        len(ep.get("test_cases", []))
        for ep in test_plan.get("test_plan", [])
    )
    actual = count_test_functions(clean)
    if actual > expected:
        excess = actual - expected
        print(f"    [Gen] ⚠️ Model vygeneroval {actual} testů místo {expected} — ořezávám {excess}")
        clean = _remove_last_n_tests(clean, excess)

    return clean


# ═══════════════════════════════════════════════════════════
#  Validace počtu testů
# ═══════════════════════════════════════════════════════════

def validate_test_count(code: str, expected: int, llm=None,
                        prompt_builder: PromptBuilder = None,
                        base_url: str = "http://localhost:8000",
                        context: str = "") -> str:
    # ── NOVÉ: Pokud kód stále není validní AST, pokus o salvage ──
    if _is_truncated(code):
        print(f"    [Validace] ⚠️ Kód je stále truncated, zkouším salvage...")
        code = _salvage_truncated_code(code)

    actual = count_test_functions(code)

    # ── NOVÉ: Pokud AST vrátí 0 ale kód není prázdný → problém ──
    if actual == 0 and len(code.strip()) > 100:
        print(f"    [Validace] ⚠️ 0 testů detekováno ale kód není prázdný "
              f"({len(code)} znaků) — pravděpodobně stále broken")
        return code

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

    clean = _clean_llm_response(raw)

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
    """Ověří že nové helpery neztratily funkce oproti starým.
    (Chybějící importy už jen logujeme, protože se o ně stará Sanitizer)
    """
    old_imports = _get_import_names(old_helpers)
    new_imports = _get_import_names(new_helpers)
    missing_imports = old_imports - new_imports
    if missing_imports:
        # Změna: Už nevracíme False! LLM pravděpodobně jen smazalo nepoužitý import.
        # Sanitizer by ho vrátil, kdyby byl potřeba.
        print(
            f"    [HelperValidation] ℹ️ LLM odebralo importy: {missing_imports} (pokud jsou potřeba, Sanitizer je doplní)")

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
            sample_errors.append(f"Test {name}:\n{err}")

    prompt = prompt_builder.repair_helpers_prompt(
        helpers, sample_errors, len(failing_names), context, base_url
    )

    try:
        raw = llm.generate_text(prompt)
    except Exception as e:
        print(f"    [Repair] ⚠️ LLM chyba při opravě helperů: {e}")
        return master_code

    clean = _clean_llm_response(raw)

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
    """
    Pokus o textový merge starých importů a nových (nekompletních) helperů
    je nebezpečný a vedl by ke smazání funkcí, na které LLM zapomnělo.
    Jelikož předchozí validace selhala, vracíme None a bezpečně tuto
    vadnou opravu zahazujeme.
    """
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
    clean = _clean_llm_response(raw)

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
#  Hlavní repair funkce (v5)
# ═══════════════════════════════════════════════════════════

def repair_failing_tests(master_code: str, pytest_log: str,
                         context: str, llm,
                         prompt_builder: PromptBuilder,
                         base_url: str,
                         stale_tracker: StaleTracker | None = None,
                         previous_repair_type: str | None = None,
                         ) -> tuple[str, dict]:
    """
    Opraví selhávající testy. Alternuje: isolated → helper → ...

    v5 změny:
      - refresh_with_current_errors(): odblokuje testy jejichž chyba se změnila
      - Helper retry: pokud předchozí helper změnil chybu (progres), opakuj helper
      - repair_info obsahuje "errors_changed" flag

    Alternační logika:
      - previous == None → isolated
      - previous == "isolated" → helper
      - previous == helper + errors_changed → HELPER ZNOVU (progres!)
      - previous == helper + errors_same → isolated

    Returns:
        (opravený_kód, repair_info)
    """
    repair_info = {
        "repair_type": None,
        "repaired_count": 0,
        "stale_skipped": 0,
        "regression_rollback": False,
        "errors_changed": False,
        "code_changed": False,
    }

    failing = _parse_failing_test_names(pytest_log)
    if not failing:
        return master_code, repair_info

    passing_before = _parse_passing_count(pytest_log)

    # ── Stale filtrování (s refresh logikou) ─────────────
    stale_tests = []
    repairable = failing
    errors_changed = False

    if stale_tracker:
        # NOVÉ v5: Zjisti zda se chyby změnily oproti minulé iteraci
        errors_changed = stale_tracker.detect_errors_changed(pytest_log, failing)
        repair_info["errors_changed"] = errors_changed

        # NOVÉ v5: Odblokuj stale testy jejichž chyba se změnila
        unstaled = stale_tracker.refresh_with_current_errors(pytest_log, failing)

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
    # v5: Nová logika s helper retry při progresu
    is_prev_helper = previous_repair_type in (
        "helper_root_cause", "helper_fallback",
    )

    if previous_repair_type is None:
        # První iterace → standardně isolated, ale pokud je 10+ failů, jdi rovnou na helper
        if len(repairable) >= 10:
            print(f"    [Repair] 🚨 Detekováno {len(repairable)} selhání! Vynucuji helper repair v 1. iteraci.")
            use_helper = True
        else:
            use_helper = False
    elif previous_repair_type == "isolated":
        # Po isolated → helper
        use_helper = True
    elif is_prev_helper and errors_changed:
        # Po helper + chyby se změnily → ZNOVU HELPER (progres!)
        print(f"    [Repair] 🔄 Helper repair udělal progres (chyby se změnily). "
              f"Opakuji helper repair...")
        use_helper = True
    elif is_prev_helper and not errors_changed:
        # Po helper + chyby stejné → přepni na isolated
        use_helper = False
    else:
        # Fallback: alternuj
        use_helper = (previous_repair_type == "isolated")

    if use_helper:
        # ── HELPER REPAIR ────────────────────────────────
        master_code, repair_type = _do_helper_repair(
            master_code, pytest_log, repairable, helpers,
            llm, prompt_builder, base_url, context,
        )
        repair_info["repair_type"] = repair_type
        repair_info["repaired_count"] = len(repairable)

        code_changed = (master_code != backup)
        if stale_tracker:
            stale_tracker.update(
                repair_type, pytest_log, failing,
                attempted_names=repairable,
                code_changed=code_changed,
            )

    else:
        # ── ISOLATED REPAIR ──────────────────────────────
        master_code, repaired, attempted = _do_isolated_repairs(
            master_code, pytest_log, repairable, helpers,
            llm, prompt_builder, base_url, context, stale_tests,
        )
        repair_info["repair_type"] = "isolated"
        repair_info["repaired_count"] = repaired

        code_changed = (master_code != backup)
        if stale_tracker:
            stale_tracker.update(
                "isolated", pytest_log, failing,
                attempted_names=attempted,
                code_changed=code_changed,
            )

    # ── Bezpečnostní kontrola: počet testů se nesmí změnit ──
    before = count_test_functions(backup)
    after = count_test_functions(master_code)
    if before != after:
        print(f"    [Repair] ⚠️ Počet testů se změnil ({before} → {after}), revertuji")
        master_code = backup
        repair_info["regression_rollback"] = True

    repair_info["code_changed"] = (master_code != backup)

    return master_code, repair_info