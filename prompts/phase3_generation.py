"""
Fáze 3: Generování a oprava pytest testů.

Klíčové principy:
- Počáteční generování: LLM vygeneruje celý soubor z plánu
- Validace počtu: AST kontrola + ořezání přebytečných testů
- Izolovaná oprava: mikro-prompty pro jednotlivé failing testy
- Helper detekce: společná root cause → oprava helperů
- Framework je orchestrátor, LLM je worker
"""
import ast
import json
import re
import textwrap
import time

# Nad tímto limitem failing testů → oprava helperů místo izolované opravy
MAX_INDIVIDUAL_REPAIRS = 10


# ═══════════════════════════════════════════════════════════
#  AST Utility
# ═══════════════════════════════════════════════════════════

def count_test_functions(code: str) -> int:
    """Spočítá test_ funkce v kódu přes AST."""
    try:
        tree = ast.parse(code)
        return sum(1 for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    except SyntaxError:
        return 0


def _get_test_function_names(code: str) -> list[str]:
    """Vrátí seznam test_ funkcí v pořadí jak jsou v kódu."""
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
    """Vrátí (start, end) řádky funkce (0-indexed, inclusive). None pokud nenalezena."""
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
    """Extrahuje kód jedné funkce jako string."""
    rng = _get_function_range(code, func_name)
    if not rng:
        return None
    start, end = rng
    lines = code.split('\n')
    return '\n'.join(lines[start:end + 1])


def _replace_function_code(code: str, func_name: str, new_func: str) -> str:
    """Nahradí kód jedné funkce novým kódem."""
    rng = _get_function_range(code, func_name)
    if not rng:
        return code
    start, end = rng
    lines = code.split('\n')
    new_func = textwrap.dedent(new_func).strip()
    new_lines = lines[:start] + new_func.split('\n') + lines[end + 1:]
    return '\n'.join(new_lines)


def _extract_helpers_code(code: str) -> str:
    """Extrahuje vše nad prvním test_ (importy, konstanty, helper funkce)."""
    test_names = _get_test_function_names(code)
    if not test_names:
        return code

    first_rng = _get_function_range(code, test_names[0])
    if not first_rng:
        return ""

    lines = code.split('\n')
    return '\n'.join(lines[:first_rng[0]]).strip()


def _replace_helpers(code: str, new_helpers: str) -> str:
    """Nahradí helper část kódu (vše nad prvním testem)."""
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
    """Odstraní posledních N test funkcí z kódu."""
    test_names = _get_test_function_names(code)
    if n <= 0 or n > len(test_names):
        return code

    to_remove = test_names[-n:]
    for name in reversed(to_remove):
        rng = _get_function_range(code, name)
        if rng:
            start, end = rng
            lines = code.split('\n')
            # Odstraň i prázdné řádky za funkcí
            while end + 1 < len(lines) and lines[end + 1].strip() == '':
                end += 1
            code = '\n'.join(lines[:start] + lines[end + 1:])
    return code


# ═══════════════════════════════════════════════════════════
#  Pytest Log Parsing
# ═══════════════════════════════════════════════════════════

def _parse_failing_test_names(pytest_log: str) -> list[str]:
    """Extrahuje názvy failing testů z pytest výstupu (deduplikované)."""
    names = re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)
    return list(dict.fromkeys(names))


def _extract_error_for_test(pytest_log: str, test_name: str) -> str:
    """Extrahuje traceback/error pro konkrétní test z FAILURES sekce."""
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
    """Zjistí, zda většina selhání má stejnou root cause (= bug v helperu).

    Bere pouze PRVNÍ E-řádek per test, aby se vyhnul zdvojení
    (každý assert produkuje i '+ where ...' řádek).
    """
    if len(failing_names) < 4:
        return False

    # Extrahuj první E-řádek z každého failing testu
    first_errors = []
    for name in failing_names:
        error_block = _extract_error_for_test(pytest_log, name)
        if not error_block:
            continue
        # První řádek začínající "E " v bloku daného testu
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
#  Počáteční generování (beze změny)
# ═══════════════════════════════════════════════════════════

def generate_test_code(test_plan: dict, context_data: str, llm,
                       base_url: str = "http://localhost:8000") -> str:
    """Vygeneruje kompletní testovací soubor z plánu."""
    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    prompt = f"""Napiš pytest testy v Pythonu (requests knihovna) pro toto REST API.
BASE_URL = "{base_url}"

PLÁN:
{plan_str}

KONTEXT:
{context_data}

TECHNICKÉ POŽADAVKY (aby testy šly spustit):
- import pytest, requests, uuid na začátku
- Každý test začíná test_, používá timeout=30 na každém HTTP volání
- Nepoužívej fixtures, conftest, setup_module, setup_function ani žádné pytest hooks.
- Databáze se resetuje automaticky PŘED spuštěním testů (framework to zajistí).
  Negeneruj test na reset databáze a NEVOLEJ /reset endpoint nikde v kódu.
- Každý test musí být self-contained – vytvoří si vlastní data přes helper funkce.

UNIKÁTNÍ NÁZVY (povinné, jinak testy kolidují):
- Pro unikátní názvy použij uuid4 suffix:
    def unique(prefix="test"):
        return f"{{prefix}}_{{uuid.uuid4().hex[:8]}}"
- V KAŽDÉM helper volání generuj unikátní názvy:
    def create_author(name=None):
        name = name or unique("Author")
        r = requests.post(f"{{BASE_URL}}/authors", json={{"name": name}}, timeout=30)
        assert r.status_code == 201
        return r.json()

KVALITA ASERCÍ (důležité pro kvalitu testů):
- Nekontroluj POUZE status kód. Každý test by měl ověřit i odpověď:
  - Happy path (201/200): ověř klíče v response body (assert "id" in data, assert data["name"] == ...)
  - Error (400/404/409/422): ověř assert "detail" in r.json()
  - GET seznam: ověř strukturu (assert "items" in data nebo assert isinstance(data, list))
  - Side effects: po vytvoření objednávky ověř snížení skladu, po smazání ověř 404 na GET
- Příklad dobrého testu:
    def test_create_author_valid():
        name = unique("Author")
        r = requests.post(f"{{BASE_URL}}/authors", json={{"name": name}}, timeout=30)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == name
        assert "id" in data

SPECIFIKA TOHOTO API (bez tohoto testy spadnou):
- DELETE endpointy vracejí 204 s PRÁZDNÝM tělem. Nevolej .json() na 204 odpovědích.
- DELETE /books/{{id}}/tags používá REQUEST BODY: requests.delete(..., json={{"tag_ids": [...]}})
- PATCH /books/{{id}}/stock používá QUERY parametr: params={{"quantity": N}}, ne JSON body.
- Neověřuj přesný text chybových hlášek, ověřuj jen přítomnost klíče "detail".

Vrať POUZE Python kód, žádný markdown.
"""

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

    # Méně testů → doplnit přes LLM
    if not llm:
        print(f"    [Validace] ⚠️ {actual} testů (očekáváno {expected}), LLM nedostupný")
        return code

    missing = expected - actual
    print(f"    [Validace] {actual} testů → doplňuji {missing}...")

    helpers = _extract_helpers_code(code)
    existing_names = _get_test_function_names(code)

    fill_prompt = f"""Vygeneruj PŘESNĚ {missing} nových pytest testů pro toto REST API.
BASE_URL = "{base_url}"

DOSTUPNÉ HELPERY (použi je, nevymýšlej nové):
{helpers}

EXISTUJÍCÍ TESTY (tyto názvy NEPOUŽÍVEJ):
{', '.join(existing_names)}

KONTEXT API:
{context[:3000]}

PRAVIDLA:
- Vrať POUZE {missing} nových test funkcí (def test_...(): ...).
- Žádné importy, žádné helpery, žádný markdown.
- Každý test musí být self-contained, používat timeout=30, unique() helper.
- Zaměř se na scénáře které existující testy nepokrývají (edge cases, error handling).
- Nekontroluj jen status kód — ověřuj i response body (klíče, hodnoty, strukturu).
- DELETE endpointy → 204, prázdné tělo.
- PATCH /books/{{id}}/stock → params={{"quantity": N}}.
- DELETE /books/{{id}}/tags → json={{"tag_ids": [...]}}.
"""

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

    # Připoj nové testy na konec souboru
    new_code = code.rstrip() + "\n\n\n" + clean

    # Validace: musí být parsovatelný
    try:
        ast.parse(new_code)
    except SyntaxError:
        print(f"    [Validace] ⚠️ Doplněné testy mají syntax error, ponechávám původní")
        return code

    new_actual = count_test_functions(new_code)
    if new_actual > expected:
        # Doplnilo příliš → ořízni
        excess = new_actual - expected
        new_code = _remove_last_n_tests(new_code, excess)
        new_actual = count_test_functions(new_code)

    print(f"    [Validace] ✅ {new_actual} testů (cíl {expected})")
    return new_code


# ═══════════════════════════════════════════════════════════
#  Izolovaná oprava failing testů
# ═══════════════════════════════════════════════════════════

def _repair_single_test(test_name, test_code, error_msg, helpers, llm, base_url):
    """Mikro-prompt: opraví jeden konkrétní selhávající test."""
    prompt = f"""Oprav POUZE tuto jednu testovací funkci. Vrať POUZE opravenou funkci.

BASE_URL = "{base_url}"

DOSTUPNÉ HELPERY:
{helpers}

SELHÁVAJÍCÍ TEST:
{test_code}

CHYBA:
{error_msg}

PRAVIDLA:
- Vrať POUZE opravenou funkci (def test_...(): ...), žádné importy ani helpery.
- Neměň název funkce.
- Zachovej timeout=30 na HTTP voláních.
- Používej existující helper funkce, nevymýšlej nové.
- DELETE endpointy → 204, prázdné tělo, nevolej .json().
- PATCH /books/{{id}}/stock → params={{"quantity": N}}.
- DELETE /books/{{id}}/tags → json={{"tag_ids": [...]}}.
- Pokud test ověřuje jen status kód, přidej i kontrolu response body (assert "id" in data apod.).
"""

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

    # Extrahuj jen funkci (LLM může vrátit víc)
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

    # Fallback
    if f"def {test_name}" in clean or "def test_" in clean:
        return clean

    return None


def _repair_helpers(master_code, pytest_log, helpers, failing_names, llm, base_url):
    """Opraví helper funkce při detekci společné root cause."""
    sample_errors = []
    for name in failing_names[:3]:
        err = _extract_error_for_test(pytest_log, name)
        if err:
            sample_errors.append(f"Test {name}:\n{err[:500]}")

    prompt = f"""Většina testů padá kvůli bugu v helper funkcích. Oprav helpery.

BASE_URL = "{base_url}"

AKTUÁLNÍ HELPERY:
{helpers}

UKÁZKY CHYB ({len(failing_names)} testů celkem padá):
{chr(10).join(sample_errors)}

PRAVIDLA:
- Vrať POUZE opravené helpery a importy (vše co je nad test funkcemi).
- Zachovej signatury helperů kompatibilní s existujícími testy.
- Zajisti unikátní názvy přes uuid4 (unique() helper).
- Žádný markdown, jen Python kód.
"""

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

    # Validace: nové helpery musí být parsovatelné
    try:
        ast.parse(clean)
    except SyntaxError:
        print(f"    [Repair] ⚠️ Opravené helpery mají syntax error, ponechávám původní")
        return master_code

    result = _replace_helpers(master_code, clean)

    # Validace: celý soubor musí být parsovatelný
    try:
        ast.parse(result)
    except SyntaxError:
        print(f"    [Repair] ⚠️ Výsledný soubor má syntax error, ponechávám původní")
        return master_code

    return result


def repair_failing_tests(master_code: str, pytest_log: str,
                         context: str, llm, base_url: str) -> str:
    """
    Izolovaně opraví selhávající testy. Počet testů zůstane zachován.

    Strategie:
    1. Parsuj failing testy z pytest logu
    2. Pokud je společná root cause → oprav helpery
    3. Pokud je příliš mnoho failing → oprav helpery jako fallback
    4. Jinak → mikro-prompt pro každý failing test zvlášť
    """
    failing = _parse_failing_test_names(pytest_log)
    if not failing:
        return master_code

    helpers = _extract_helpers_code(master_code)
    backup = master_code

    # Společná root cause → oprava helperů
    if _detect_helper_root_cause(pytest_log, failing):
        print(f"    [Repair] Společná root cause ({len(failing)} testů). Opravuji helpery...")
        master_code = _repair_helpers(
            master_code, pytest_log, helpers, failing, llm, base_url
        )
        return master_code

    # Příliš mnoho failing → fallback na opravu helperů
    if len(failing) > MAX_INDIVIDUAL_REPAIRS:
        print(f"    [Repair] {len(failing)} failing testů (limit {MAX_INDIVIDUAL_REPAIRS}). "
              f"Opravuji helpery jako fallback...")
        master_code = _repair_helpers(
            master_code, pytest_log, helpers, failing, llm, base_url
        )
        return master_code

    # Izolovaná oprava jednotlivých testů
    print(f"    [Repair] Izolovaná oprava {len(failing)} testů...")
    repaired = 0

    for i, test_name in enumerate(failing, 1):
        # Rate limit: pauza mezi LLM cally (Gemini free tier = 15 RPM)
        if i > 1:
            time.sleep(5)
        test_code = _extract_function_code(master_code, test_name)
        if not test_code:
            print(f"      ⚠️ {test_name} nenalezen v kódu")
            continue

        error_msg = _extract_error_for_test(pytest_log, test_name)
        print(f"      ({i}/{len(failing)}) {test_name}...")

        fixed = _repair_single_test(
            test_name, test_code, error_msg, helpers, llm, base_url
        )

        if fixed:
            new_code = _replace_function_code(master_code, test_name, fixed)
            # Validace: celý soubor musí zůstat parsovatelný
            try:
                ast.parse(new_code)
                master_code = new_code
                repaired += 1
            except SyntaxError:
                print(f"      ⚠️ {test_name} oprava způsobila syntax error, přeskakuji")
        else:
            print(f"      ⚠️ {test_name} oprava selhala")

    print(f"    [Repair] ✅ Opraveno {repaired}/{len(failing)}")

    # Bezpečnostní kontrola: počet testů se nesmí změnit
    before = count_test_functions(backup)
    after = count_test_functions(master_code)
    if before != after:
        print(f"    [Repair] ⚠️ Počet testů se změnil ({before} → {after}), revertuji")
        master_code = backup

    return master_code