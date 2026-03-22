"""
Fáze 6: Diagnostika — data pro obhajobu.

Neměří kvalitu testů (to dělá phase5_metrics.py).
Měří PROČ jsou výsledky takové jaké jsou.

Sbírá se po každém runu a ukládá do results JSON vedle metrics.

Diagnostiky:
  1. context_size        — kolik textu/tokenů model dostal per level
  2. plan_analysis       — které endpointy model vybral a proč (distribuce)
  3. helper_snapshot     — jak vypadá create_* helper (default hodnoty, parametry)
  4. prompt_budget       — poměr kontext vs instrukce vs prostor pro odpověď
  5. instruction_compliance — dodržel model framework_rules?
  6. repair_trajectory   — co se změnilo per iterace (počty, typy oprav)
  7. failure_taxonomy    — automatická klasifikace selhání do kategorií
  8. code_patterns       — jaké HTTP patterny a struktury model použil
  9. plan_vs_code_drift  — jak se liší plán od skutečně vygenerovaného kódu
 10. context_utilization — které části kontextu model skutečně použil
"""
import ast
import json
import os
import re
import yaml


# ═══════════════════════════════════════════════════════════
#  1. Context Size — kolik kontextu model dostal
# ═══════════════════════════════════════════════════════════

def measure_context_size(context: str) -> dict:
    """Změří velikost kontextového stringu per sekce.

    Obhajoba: "L2 mělo 45k znaků kontextu, L0 jen 8k.
    Model musel zpracovat 5.6× více textu."
    """
    chars = len(context)
    lines = context.count('\n') + 1
    est_tokens = chars // 3

    # Rozděl na sekce a změř každou
    sections = {}
    current_section = "preamble"
    current_lines = []

    for line in context.split('\n'):
        m = re.match(r'^---\s+(.+?)\s+---$', line)
        if m:
            if current_lines:
                text = '\n'.join(current_lines)
                sections[current_section] = {
                    "chars": len(text),
                    "lines": len(current_lines),
                    "est_tokens": len(text) // 3,
                }
            current_section = m.group(1)
            current_lines = []
        else:
            current_lines.append(line)

    # Poslední sekce
    if current_lines:
        text = '\n'.join(current_lines)
        sections[current_section] = {
            "chars": len(text),
            "lines": len(current_lines),
            "est_tokens": len(text) // 3,
        }

    return {
        "total_chars": chars,
        "total_lines": lines,
        "total_est_tokens": est_tokens,
        "section_count": len(sections),
        "sections": sections,
    }


# ═══════════════════════════════════════════════════════════
#  2. Plan Analysis — co model vybral k testování
# ═══════════════════════════════════════════════════════════

def analyze_plan(test_plan: dict, openapi_path: str) -> dict:
    """Analyzuje strategii výběru endpointů v plánu.

    Obhajoba: "L2 alokoval 23/30 testů na error handling,
    protože viděl raise HTTPException ve zdrojovém kódu."
    """
    api_endpoints = set()
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f) if openapi_path.endswith(('.yaml', '.yml')) else json.load(f)
        methods = {'get', 'post', 'put', 'delete', 'patch'}
        api_endpoints = {
            f"{m.upper()} {p}"
            for p, ms in spec.get('paths', {}).items()
            for m in ms if m.lower() in methods
        }
    except Exception:
        pass

    ep_test_counts = {}
    ep_type_dist = {}
    total_tests = 0

    for ep in test_plan.get("test_plan", []):
        key = f"{ep.get('method', '').upper()} {ep.get('endpoint', '')}"
        cases = ep.get("test_cases", [])
        ep_test_counts[key] = len(cases)
        total_tests += len(cases)

        type_dist = {}
        for tc in cases:
            t = tc.get("type", "other")
            type_dist[t] = type_dist.get(t, 0) + 1
        ep_type_dist[key] = type_dist

    sorted_eps = sorted(ep_test_counts.items(), key=lambda x: -x[1])

    # Endpoint s nejvíce error testy
    error_focus = {}
    for ep, dist in ep_type_dist.items():
        err = dist.get("error", 0) + dist.get("edge_case", 0)
        if err > 0:
            error_focus[ep] = err

    # Concentration: kolik % testů pokrývá top 3 endpointy
    top3_tests = sum(c for _, c in sorted_eps[:3])
    concentration = round(top3_tests / total_tests * 100, 1) if total_tests else 0

    # Resource mapping: kolik testů per "domain"
    domains = {
        "authors": 0, "categories": 0, "books": 0,
        "reviews": 0, "tags": 0, "orders": 0, "other": 0,
    }
    for ep_key, count in ep_test_counts.items():
        matched = False
        for domain in domains:
            if domain != "other" and domain in ep_key.lower():
                domains[domain] += count
                matched = True
                break
        if not matched:
            domains["other"] += count

    return {
        "total_planned_tests": total_tests,
        "unique_endpoints_in_plan": len(ep_test_counts),
        "total_api_endpoints": len(api_endpoints),
        "tests_per_endpoint": ep_test_counts,
        "type_per_endpoint": ep_type_dist,
        "top_tested": sorted_eps[:5],
        "error_focused_endpoints": dict(sorted(error_focus.items(), key=lambda x: -x[1])),
        "top3_concentration_pct": concentration,
        "skipped_endpoints": sorted(api_endpoints - set(ep_test_counts.keys())),
        "domain_distribution": {k: v for k, v in domains.items() if v > 0},
    }


# ═══════════════════════════════════════════════════════════
#  3. Helper Snapshot — jak vypadají helper funkce
# ═══════════════════════════════════════════════════════════

def snapshot_helpers(code: str) -> dict:
    """Extrahuje klíčové info z helper funkcí.

    Obhajoba: "L0 helper nemá stock parametr, L1+ ano.
    Proto L0 order testy kaskádově selhávají."
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "syntax_error", "helpers": {}, "helper_count": 0}

    helpers = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            args = []
            defaults_offset = len(node.args.args) - len(node.args.defaults)
            for i, arg in enumerate(node.args.args):
                default_idx = i - defaults_offset
                if default_idx >= 0:
                    d = node.args.defaults[default_idx]
                    if isinstance(d, ast.Constant):
                        args.append(f"{arg.arg}={repr(d.value)}")
                    else:
                        args.append(f"{arg.arg}=<expr>")
                else:
                    args.append(arg.arg)

            lines = code.split('\n')
            start = node.lineno - 1
            end = node.end_lineno
            body_text = '\n'.join(lines[start:end])

            payload_keys = re.findall(r'"(\w+)":', body_text)

            helpers[node.name] = {
                "signature": f"{node.name}({', '.join(args)})",
                "lines": end - start,
                "has_stock_field": '"stock"' in body_text or "'stock'" in body_text,
                "uses_unique_names": 'unique(' in body_text or 'uuid' in body_text,
                "has_assertion": 'assert' in body_text,
                "payload_keys": list(dict.fromkeys(payload_keys)),
                "default_published_year": _extract_default_year(body_text),
            }

    return {"helpers": helpers, "helper_count": len(helpers)}


def _extract_default_year(body: str) -> int | None:
    """Najde default published_year v helper kódu.
    Matchuje: published_year=2020, year=2020, "published_year": 2020
    """
    patterns = [
        r'published_year["\']?\s*[:=]\s*(\d{4})',
        r'\byear\s*=\s*(\d{4})',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            return int(m.group(1))
    return None


# ═══════════════════════════════════════════════════════════
#  4. Prompt Budget — kolik z kontextového okna se využije
# ═══════════════════════════════════════════════════════════

def estimate_prompt_budget(context: str, plan_json: str,
                           model_context_window: int = 128000) -> dict:
    """Odhadne využití kontextového okna.

    Obhajoba: "L4 prompt zabral 62% kontextového okna,
    zbývalo méně prostoru pro generovaný kód."
    """
    ctx_tokens = len(context) // 3
    plan_tokens = len(plan_json) // 3
    instruction_overhead = 800

    total_prompt = ctx_tokens + plan_tokens + instruction_overhead
    remaining = model_context_window - total_prompt

    return {
        "context_tokens_est": ctx_tokens,
        "plan_tokens_est": plan_tokens,
        "instruction_tokens_est": instruction_overhead,
        "total_prompt_tokens_est": total_prompt,
        "remaining_for_output_est": remaining,
        "prompt_budget_pct": round(total_prompt / model_context_window * 100, 1),
        "model_context_window": model_context_window,
    }


# ═══════════════════════════════════════════════════════════
#  5. Instruction Compliance — dodržel model instrukce?
# ═══════════════════════════════════════════════════════════

def check_instruction_compliance(code: str) -> dict:
    """Kontroluje jestli model dodržel framework_rules.

    Obhajoba: "Model v 3 testech nepoužil timeout=30.
    To není chyba frameworku ale non-compliance modelu."
    """
    http_calls = re.findall(r'requests\.(get|post|put|patch|delete)\(', code)
    timeout_calls = re.findall(r'timeout\s*=\s*\d+', code)
    missing_timeout = max(0, len(http_calls) - len(timeout_calls))

    uses_unique = 'unique(' in code
    calls_reset = bool(re.search(r'/reset', code))
    uses_fixtures = bool(re.search(
        r'@pytest\.fixture|conftest|setup_module|setup_function', code
    ))
    json_after_204 = bool(re.search(r'\.json\(\).*== 204|== 204.*\.json\(\)', code))

    # Helper umístěný mezi testy (špatná struktura)
    helper_between_tests = _detect_helper_between_tests(code)

    score = 100
    if missing_timeout > 0:
        score -= min(missing_timeout * 5, 20)
    if not uses_unique:
        score -= 20
    if calls_reset:
        score -= 15
    if uses_fixtures:
        score -= 10
    if json_after_204:
        score -= 10

    return {
        "total_http_calls": len(http_calls),
        "missing_timeout": missing_timeout,
        "uses_unique_helper": uses_unique,
        "calls_reset_endpoint": calls_reset,
        "uses_fixtures": uses_fixtures,
        "json_after_204_risk": json_after_204,
        "helper_between_tests": helper_between_tests,
        "compliance_score": max(score, 0),
    }


def _detect_helper_between_tests(code: str) -> list[str]:
    """Najde helper funkce umístěné MEZI test_ funkcemi."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            funcs.append((node.lineno, node.name))

    misplaced = []
    seen_test = False
    for _, name in sorted(funcs):
        if name.startswith("test_"):
            seen_test = True
        elif seen_test:
            misplaced.append(name)

    return misplaced


# ═══════════════════════════════════════════════════════════
#  6. Repair Trajectory — co se změnilo per iterace
# ═══════════════════════════════════════════════════════════

class RepairTracker:
    """Sleduje trajektorii oprav napříč iteracemi.

    Obhajoba: "Iterace 1→2 opravila 15 testů přes helper repair.
    Iterace 2→3 neopravila nic — všech 6 failing je stale."
    """

    def __init__(self):
        self._iterations: list[dict] = []

    def record_iteration(self, iteration: int, pytest_log: str,
                         repair_type: str | None = None,
                         repaired_count: int = 0,
                         stale_count: int = 0):
        passed = failed = 0
        m = re.search(r'(\d+)\s+passed', pytest_log)
        if m: passed = int(m.group(1))
        m = re.search(r'(\d+)\s+failed', pytest_log)
        if m: failed = int(m.group(1))

        failing_names = re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)

        # Per-iteration failure taxonomy (ne jen z poslední iterace)
        per_test_errors = {}
        for name in dict.fromkeys(failing_names):
            error = _extract_error_block(pytest_log, name)
            category = _classify_single_failure(error, name, "")
            per_test_errors[name] = {
                "category": category,
                "error_summary": _summarize_error(error),
            }

        self._iterations.append({
            "iteration": iteration,
            "passed": passed,
            "failed": failed,
            "failing_tests": list(dict.fromkeys(failing_names)),
            "repair_type": repair_type,
            "repaired_count": repaired_count,
            "stale_skipped": stale_count,
            "failure_details": per_test_errors,
        })

    def annotate_last(self, repair_type: str | None = None,
                      repaired_count: int = 0, stale_skipped: int = 0):
        """Doplní repair metadata k poslední zaznamenané iteraci.
        Volá se po repair_failing_tests() v main.py.
        """
        if self._iterations:
            self._iterations[-1]["repair_type"] = repair_type
            self._iterations[-1]["repaired_count"] = repaired_count
            self._iterations[-1]["stale_skipped"] = stale_skipped

    def get_trajectory(self) -> dict:
        if not self._iterations:
            return {"iterations": [], "convergence_iteration": 0}

        # Konvergence: první iterace kde se failing stabilizoval
        convergence = len(self._iterations)
        for i in range(1, len(self._iterations)):
            if self._iterations[i]["failed"] == self._iterations[i - 1]["failed"]:
                convergence = i
                break

        deltas = []
        for i in range(1, len(self._iterations)):
            prev = self._iterations[i - 1]["failed"]
            curr = self._iterations[i]["failed"]
            deltas.append({
                "from_iter": i,
                "to_iter": i + 1,
                "delta": prev - curr,
                "repair_type": self._iterations[i].get("repair_type"),
            })

        first_failing = set(self._iterations[0]["failing_tests"])
        last_failing = set(self._iterations[-1]["failing_tests"])

        # Aggregate failure categories across all iterations
        all_categories = {}
        for it in self._iterations:
            for name, info in it.get("failure_details", {}).items():
                if name not in all_categories:
                    all_categories[name] = info["category"]

        return {
            "iterations": self._iterations,
            "convergence_iteration": convergence + 1,
            "deltas": deltas,
            "never_fixed_tests": sorted(first_failing & last_failing),
            "fixed_tests": sorted(first_failing - last_failing),
            "total_repair_calls": sum(
                it.get("repaired_count", 0) for it in self._iterations
            ),
            "total_stale_skipped": sum(
                it.get("stale_skipped", 0) for it in self._iterations
            ),
            "failure_categories": all_categories,
        }


# ═══════════════════════════════════════════════════════════
#  7. Failure Taxonomy — automatická klasifikace selhání
# ═══════════════════════════════════════════════════════════

def classify_failures(pytest_log: str, code: str) -> dict:
    """Automaticky klasifikuje selhání do kategorií.

    Obhajoba: "60% selhání je typ 'wrong_status_code',
    20% je 'helper_cascade'. To není náhoda — L0 model
    bez kontextu systematicky hádá špatné kódy."
    """
    failing_names = re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)
    if not failing_names:
        return {"total_failures": 0, "categories": {}, "per_test": {}}

    categories = {
        "wrong_status_code": [],
        "helper_cascade": [],
        "assertion_value_mismatch": [],
        "key_error": [],
        "attribute_error": [],
        "connection_error": [],
        "timeout": [],
        "other": [],
    }
    per_test = {}

    for name in dict.fromkeys(failing_names):
        error = _extract_error_block(pytest_log, name)
        category = _classify_single_failure(error, name, code)
        categories[category].append(name)
        per_test[name] = {
            "category": category,
            "error_summary": _summarize_error(error),
        }

    # Filtruj prázdné kategorie
    active = {k: v for k, v in categories.items() if v}

    return {
        "total_failures": len(dict.fromkeys(failing_names)),
        "categories": {k: len(v) for k, v in active.items()},
        "category_pct": {
            k: round(len(v) / len(dict.fromkeys(failing_names)) * 100, 1)
            for k, v in active.items()
        },
        "per_test": per_test,
        "category_details": {k: v for k, v in active.items()},
    }


def _extract_error_block(pytest_log: str, test_name: str) -> str:
    """Extrahuje chybový blok pro test. Tři strategie:
    1. FAILURES sekce (plný traceback) — matchuje test_name kdekoliv v header řádku
    2. Fallback: short test summary řádek (s nebo bez error message)
    3. Jakýkoli řádek s E-prefixem nebo assert poblíž test_name
    """
    # Strategie 1: FAILURES blok — test_name může být prefix::test_name v headeru
    # Pytest header: "_______ file::test_name _______" nebo "_______ test_name _______"
    pattern = (
        rf'_{2,}\s+\S*{re.escape(test_name)}\s+_{2,}'
        rf'(.*?)'
        rf'(?=_{2,}\s+\S*\w+\s+_{2,}|={2,}\s+short test summary|$)'
    )
    m = re.search(pattern, pytest_log, re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()[:2000]

    # Strategie 2: short test summary — s nebo bez error message za dashem
    # Format A: "FAILED file::test_name - ErrorType: message"
    # Format B: "FAILED file::test_name"  (bez error message)
    summary_pattern = rf'FAILED\s+\S+::{re.escape(test_name)}\s*(?:[-–]\s*(.+))?$'
    m2 = re.search(summary_pattern, pytest_log, re.MULTILINE)
    if m2:
        if m2.group(1):
            return m2.group(1).strip()[:500]
        # Nemáme error message z summary, zkusíme najít E-řádky poblíž
        # Hledej v okolí tohoto FAILED řádku (pytest --tb=short dává traceback NAD summary)

    # Strategie 3: najdi E-řádky (chybové) které jsou v bloku pro tento test
    # --tb=short formát: "test_file.py:LINE: in test_name\n    code\nE   error"
    tb_pattern = rf'in {re.escape(test_name)}\b.*?\n(.*?)(?=\n\S|\nFAILED|\n={2,}|\Z)'
    m3 = re.search(tb_pattern, pytest_log, re.DOTALL)
    if m3:
        block = m3.group(1).strip()
        # Extrahuj jen E-řádky
        e_lines = [l.strip() for l in block.splitlines() if l.strip().startswith('E ')]
        if e_lines:
            return '\n'.join(e_lines)[:500]
        if block:
            return block[:500]

    # Strategie 4: jakýkoli řádek obsahující test_name + "E " nebo "assert"
    for line in pytest_log.splitlines():
        if test_name in line and ('E ' in line or 'assert' in line.lower()):
            return line.strip()[:500]

    # Strategie 5: hledej AssertionError/assert řádky bezprostředně za řádkem s test_name
    lines = pytest_log.splitlines()
    for i, line in enumerate(lines):
        if test_name in line:
            # Prohledej následujících 10 řádků
            for j in range(i + 1, min(i + 11, len(lines))):
                s = lines[j].strip()
                if s.startswith('E ') and len(s) > 4:
                    return s[2:].strip()[:500]
                if 'AssertionError' in s or 'assert' in s.lower():
                    return s[:500]

    return ""


def _classify_single_failure(error: str, test_name: str, code: str) -> str:
    """Klasifikuje jeden failing test."""
    if not error:
        return "unknown_no_error_captured"

    # Status code mismatch: "assert 404 == 422" nebo "404 != 422"
    if re.search(r'assert\s+\d{3}\s*[=!]=\s*\d{3}', error):
        return "wrong_status_code"
    # Varianta z short summary: "assert 404 == 200"
    if re.search(r'\d{3}\s*==\s*\d{3}', error):
        return "wrong_status_code"

    if re.search(r'status_code\s*==\s*\d{3}', error):
        return "wrong_status_code"

    # Helper cascade: chyba je v helperu, ne v testu
    if re.search(r'in create_\w+|in unique\b', error):
        return "helper_cascade"

    # KeyError
    if 'KeyError' in error:
        return "key_error"

    # AttributeError
    if 'AttributeError' in error:
        return "attribute_error"

    # Value mismatch: "assert 15 == 5", "assert None == 'test'"
    if re.search(r'assert\s+\S+\s*==\s*\S+', error) and 'status_code' not in error:
        return "assertion_value_mismatch"

    # Connection errors
    if re.search(r'ConnectionError|ConnectionRefused|Timeout', error, re.I):
        return "connection_error"

    if 'Timeout' in error:
        return "timeout"

    return "other"


def _summarize_error(error: str) -> str:
    """Krátké shrnutí chyby pro JSON."""
    # Najdi hlavní E-řádek
    for line in error.splitlines():
        s = line.strip()
        if s.startswith("E ") and len(s) > 4:
            return s[2:].strip()[:120]
    # Fallback: první neprázdný řádek
    for line in error.splitlines():
        s = line.strip()
        if s and not s.startswith("_"):
            return s[:120]
    return ""


# ═══════════════════════════════════════════════════════════
#  8. Code Patterns — jaké patterny model použil
# ═══════════════════════════════════════════════════════════

def analyze_code_patterns(code: str) -> dict:
    """Analyzuje strukturu a patterny vygenerovaného kódu.

    Obhajoba: "L4 model generuje testy s průměrně 3.2 HTTP
    volání na test (multi-step), L0 jen 1.4 (single-call).
    Proto L4 má lepší code coverage i přes menší EP coverage."
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "syntax_error"}

    test_funcs = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    lines = code.split('\n')

    results = {
        "total_tests": len(test_funcs),
        "per_test": {},
    }

    http_counts = []
    assert_counts = []
    setup_counts = []
    has_side_effect_check = []
    has_chaining = []

    for func in test_funcs:
        start = func.lineno - 1
        end = func.end_lineno
        body = '\n'.join(lines[start:end])

        # HTTP volání v testu
        http = len(re.findall(r'requests\.(get|post|put|patch|delete)\(', body))
        # Volání helperů (create_*)
        helper_calls = len(re.findall(r'create_\w+\(', body))
        # Asserty
        asserts = sum(1 for n in ast.walk(func) if isinstance(n, ast.Assert))
        # Side-effect check: test volá GET po POST/DELETE/PATCH
        methods_used = re.findall(r'requests\.(get|post|put|patch|delete)', body)
        side_effect = (
            'get' in methods_used and
            any(m in methods_used for m in ('post', 'put', 'patch', 'delete'))
        )
        # Chaining: výsledek jednoho callu se používá v dalším
        chain = bool(re.search(r'\.json\(\)\[', body))

        http_counts.append(http)
        assert_counts.append(asserts)
        setup_counts.append(helper_calls)
        has_side_effect_check.append(side_effect)
        has_chaining.append(chain)

        results["per_test"][func.name] = {
            "http_calls": http,
            "helper_calls": helper_calls,
            "total_calls": http + helper_calls,
            "asserts": asserts,
            "side_effect_check": side_effect,
            "uses_chaining": chain,
            "lines": end - start,
        }

    n = len(test_funcs) or 1
    results["summary"] = {
        "avg_http_calls": round(sum(http_counts) / n, 2),
        "avg_helper_calls": round(sum(setup_counts) / n, 2),
        "avg_total_calls": round(sum(c + h for c, h in zip(http_counts, setup_counts)) / n, 2),
        "avg_asserts": round(sum(assert_counts) / n, 2),
        "pct_side_effect_checks": round(sum(has_side_effect_check) / n * 100, 1),
        "pct_chaining": round(sum(has_chaining) / n * 100, 1),
        "single_call_tests": sum(1 for c in http_counts if c <= 1),
        "multi_step_tests": sum(1 for c in http_counts if c >= 3),
    }

    return results


# ═══════════════════════════════════════════════════════════
#  9. Plan vs Code Drift — jak se liší plán od kódu
# ═══════════════════════════════════════════════════════════

def analyze_plan_code_drift(test_plan: dict, code: str) -> dict:
    """Srovná plánované a skutečné testy.

    Obhajoba: "Model plánoval 3 error testy na /orders ale
    vygeneroval 5 — přidal 2 navíc protože viděl ve zdrojovém
    kódu validační logiku."
    """
    # Plánované testy
    planned = {}
    for ep in test_plan.get("test_plan", []):
        for tc in ep.get("test_cases", []):
            name = f"test_{tc.get('name', '')}"
            planned[name] = {
                "endpoint": ep.get("endpoint", ""),
                "method": ep.get("method", ""),
                "type": tc.get("type", ""),
                "expected_status": tc.get("expected_status", 0),
            }

    # Skutečné testy v kódu
    actual_names = set()
    try:
        tree = ast.parse(code)
        actual_names = {
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
        }
    except SyntaxError:
        pass

    planned_set = set(planned.keys())

    # Zjisti jaké status kódy test skutečně assertuje
    actual_statuses = {}
    for name in actual_names:
        func_code = _extract_func_body(code, name)
        if func_code:
            statuses = re.findall(r'status_code\s*==\s*(\d{3})', func_code)
            actual_statuses[name] = [int(s) for s in statuses]

    # Drift: plánovaný vs skutečný status
    status_drift = {}
    for name, info in planned.items():
        if name in actual_statuses and info["expected_status"]:
            actual = actual_statuses[name]
            if info["expected_status"] not in actual:
                status_drift[name] = {
                    "planned": info["expected_status"],
                    "actual_in_code": actual,
                }

    return {
        "planned_count": len(planned),
        "actual_count": len(actual_names),
        "matched": len(planned_set & actual_names),
        "only_in_plan": sorted(planned_set - actual_names),
        "only_in_code": sorted(actual_names - planned_set),
        "status_code_drift": status_drift,
        "drift_count": len(status_drift),
    }


def _extract_func_body(code: str, func_name: str) -> str | None:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                lines = code.split('\n')
                return '\n'.join(lines[node.lineno - 1:node.end_lineno])
    except SyntaxError:
        pass
    return None


# ═══════════════════════════════════════════════════════════
#  10. Context Utilization — které části kontextu model použil
# ═══════════════════════════════════════════════════════════

def analyze_context_utilization(context: str, code: str, test_plan: dict) -> dict:
    """Odhadne které části kontextu model skutečně využil.

    Obhajoba: "L2 model použil 8/12 endpointů z OpenAPI,
    ale z 340 řádků zdrojového kódu referencoval patterny
    jen ze 45 řádků (13%). Většina source_code byla noise."
    """
    # Endpointy zmíněné v kontextu vs použité v plánu
    context_endpoints = set(re.findall(r'(/\w[\w/{}_]*)', context))
    plan_endpoints = set()
    for ep in test_plan.get("test_plan", []):
        plan_endpoints.add(ep.get("endpoint", ""))

    # Stringy z kontextu co se objevují v kódu
    # (názvy polí, status kódy, URL cesty)
    context_field_names = set(re.findall(r'"(\w+)"', context))
    code_field_names = set(re.findall(r'"(\w+)"', code))
    shared_fields = context_field_names & code_field_names
    # Odstraň triviální (id, name, status, type, ...)
    trivial = {'id', 'name', 'status', 'type', 'description', 'items',
               'detail', 'message', 'error', 'total', 'page', 'data'}
    nontrivial_shared = shared_fields - trivial

    # Status kódy z kontextu vs z kódu
    ctx_statuses = set(re.findall(r'\b([2-5]\d{2})\b', context))
    code_statuses = set(re.findall(r'status_code\s*==\s*(\d{3})', code))

    return {
        "context_endpoints_found": len(context_endpoints),
        "plan_endpoints_used": len(plan_endpoints),
        "endpoint_utilization_pct": round(
            len(plan_endpoints & context_endpoints) /
            max(len(context_endpoints), 1) * 100, 1
        ),
        "context_field_names": len(context_field_names),
        "code_field_names": len(code_field_names),
        "shared_nontrivial_fields": sorted(nontrivial_shared),
        "context_status_codes": sorted(ctx_statuses),
        "code_status_codes": sorted(code_statuses),
        "status_codes_from_context": sorted(ctx_statuses & code_statuses),
        "status_codes_hallucinated": sorted(code_statuses - ctx_statuses),
    }


# ═══════════════════════════════════════════════════════════
#  Souhrn všech diagnostik
# ═══════════════════════════════════════════════════════════

def collect_all_diagnostics(
    context: str,
    test_plan: dict,
    code: str,
    pytest_log: str,
    openapi_path: str,
    plan_json_str: str = "",
    repair_tracker: "RepairTracker | None" = None,
    model_context_window: int = 128000,
) -> dict:
    """Sbírá všechny diagnostiky najednou. Volej z main.py."""

    if not plan_json_str:
        plan_json_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    # Failure taxonomy: preferuj data z první iterace RepairTrackeru
    # (tam jsou čerstvé tracebacky, ne stale opakování)
    failure_tax = {"total_failures": 0, "categories": {}, "per_test": {}}
    if repair_tracker and repair_tracker._iterations:
        first_iter = repair_tracker._iterations[0]
        details = first_iter.get("failure_details", {})
        if details:
            cats = {}
            for name, info in details.items():
                c = info["category"]
                cats[c] = cats.get(c, 0) + 1
            total = len(details)
            failure_tax = {
                "total_failures": total,
                "categories": cats,
                "category_pct": {
                    k: round(v / total * 100, 1) for k, v in cats.items()
                } if total else {},
                "per_test": details,
            }
    # Fallback: parsuj z posledního pytest logu
    if failure_tax["total_failures"] == 0:
        failure_tax = classify_failures(pytest_log, code)

    diag = {
        "context_size": measure_context_size(context),
        "plan_analysis": analyze_plan(test_plan, openapi_path),
        "helper_snapshot": snapshot_helpers(code),
        "prompt_budget": estimate_prompt_budget(
            context, plan_json_str, model_context_window
        ),
        "instruction_compliance": check_instruction_compliance(code),
        "failure_taxonomy": failure_tax,
        "code_patterns": analyze_code_patterns(code),
        "plan_code_drift": analyze_plan_code_drift(test_plan, code),
        "context_utilization": analyze_context_utilization(
            context, code, test_plan
        ),
    }

    if repair_tracker:
        diag["repair_trajectory"] = repair_tracker.get_trajectory()

    return diag