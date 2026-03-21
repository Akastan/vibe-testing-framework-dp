"""
Fáze 5: Automatické metriky (součást pipeline).

  1. Test Validity Rate      – % prošlých testů
  2. Endpoint Coverage       – % pokrytých endpointů (z plánu vs OpenAPI)
  3. Assertion Depth         – průměr asercí na test
  4. Response Validation     – % testů co ověřují response body (ne jen status kód)
  5. Test Type Distribution  – poměr happy_path / error / edge_case v plánu
  6. Status Code Diversity   – kolik různých status kódů testy ověřují
  7. Empty Test Detection    – testy s 0 asercemi
  8. Avg Test Length         – průměrný počet řádků na test
  9. HTTP Method Coverage    – distribuce GET/POST/PUT/DELETE/PATCH v plánu
 10. Plan Adherence          – kolik testů z plánu se skutečně vygenerovalo

Ruční metriky (coverage, mutation) viz run_coverage_manual.py.
"""
import ast
import json
import yaml
import re
import os


# ═══════════════════════════════════════════════════════════
#  1. Test Validity Rate
# ═══════════════════════════════════════════════════════════

def parse_test_validity_rate(pytest_output: str) -> dict:
    passed = failed = errors = 0

    m = re.search(r'(\d+)\s+passed', pytest_output)
    if m: passed = int(m.group(1))
    m = re.search(r'(\d+)\s+failed', pytest_output)
    if m: failed = int(m.group(1))
    m = re.search(r'(\d+)\s+error', pytest_output)
    if m: errors = int(m.group(1))

    if passed == 0 and failed == 0 and errors == 0:
        passed = len(re.findall(r' PASSED', pytest_output))
        failed = len(re.findall(r' FAILED', pytest_output))
        failed += len(re.findall(r'Timeout', pytest_output))

    total = passed + failed + errors
    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_errors": errors,
        "total_executed": total,
        "validity_rate_pct": round(passed / total * 100, 2) if total else 0.0,
    }


# ═══════════════════════════════════════════════════════════
#  2. Endpoint Coverage
# ═══════════════════════════════════════════════════════════

def calculate_endpoint_coverage(openapi_path: str, test_plan: dict) -> dict:
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f) if openapi_path.endswith(('.yaml', '.yml')) else json.load(f)

        methods = {'get', 'post', 'put', 'delete', 'patch'}
        api_eps = {f"{m.upper()} {p}" for p, ms in spec.get('paths', {}).items()
                   for m in ms if m.lower() in methods}

        plan_eps = set()
        for ep in test_plan.get('test_plan', []):
            p, m = ep.get('endpoint', ''), ep.get('method', '').upper()
            if p and m:
                plan_eps.add(f"{m} {p}")

        covered = len(api_eps & plan_eps)
        total = len(api_eps)
        return {
            "total_api_endpoints": total,
            "covered_endpoints": covered,
            "uncovered_endpoints": sorted(api_eps - plan_eps),
            "endpoint_coverage_pct": round(covered / total * 100, 2) if total else 0.0,
        }
    except Exception as e:
        return {"error": str(e), "total_api_endpoints": 0,
                "covered_endpoints": 0, "endpoint_coverage_pct": 0.0}


# ═══════════════════════════════════════════════════════════
#  3. Assertion Depth
# ═══════════════════════════════════════════════════════════

def calculate_assertion_depth(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"error": "Soubor neexistuje.", "total_test_functions": 0,
                "total_assertions": 0, "assertion_depth": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        total = 0
        per_test = {}
        for func in test_funcs:
            count = sum(1 for n in ast.walk(func) if isinstance(n, ast.Assert))
            for n in ast.walk(func):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    if "assert" in n.func.id.lower():
                        count += 1
            per_test[func.name] = count
            total += count

        depth = round(total / len(test_funcs), 2) if test_funcs else 0.0
        return {"total_test_functions": len(test_funcs), "total_assertions": total,
                "assertion_depth": depth, "per_test_assertions": per_test}
    except SyntaxError:
        return {"error": "Syntax error.", "total_test_functions": 0,
                "total_assertions": 0, "assertion_depth": 0.0}
    except Exception as e:
        return {"error": str(e), "total_test_functions": 0,
                "total_assertions": 0, "assertion_depth": 0.0}


# ═══════════════════════════════════════════════════════════
#  4. Response Validation Rate
# ═══════════════════════════════════════════════════════════

def calculate_response_validation(file_path: str) -> dict:
    """
    Kolik testů ověřuje response body (ne jen status kód).
    Hledá přístupy k r.json(), response body klíčům, len() atd.
    """
    if not os.path.exists(file_path):
        return {"error": "Soubor neexistuje.", "tests_with_body_check": 0,
                "total_test_functions": 0, "response_validation_pct": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            tree = ast.parse(source)

        lines = source.split('\n')
        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]

        body_check_patterns = [
            r'\.json\(\)\[',        # r.json()["key"]
            r'\.json\(\)\s*==',     # r.json() == {...}
            r'data\[',              # data["key"]
            r'"id"\s+in',           # "id" in r.json()
            r'"detail"\s+in',       # "detail" in r.json()
            r'len\(',              # len(r.json())
            r'\["status"\]',       # ["status"]
            r'\["name"\]',         # ["name"]
            r'\["total',           # ["total_price"], ["total"]
            r'\["items"\]',        # ["items"]
            r'assert.*\.json\(',   # assert something about json
        ]
        pattern = re.compile('|'.join(body_check_patterns))

        with_body = 0
        per_test = {}
        for func in test_funcs:
            start = func.lineno - 1
            end = func.end_lineno
            func_lines = '\n'.join(lines[start:end])

            # Odečti helper asserty (assert r.status_code) a hledej body checky
            has_body = bool(pattern.search(func_lines))
            per_test[func.name] = has_body
            if has_body:
                with_body += 1

        total = len(test_funcs)
        return {
            "tests_with_body_check": with_body,
            "tests_status_only": total - with_body,
            "total_test_functions": total,
            "response_validation_pct": round(with_body / total * 100, 2) if total else 0.0,
            "per_test_body_check": per_test,
        }
    except Exception as e:
        return {"error": str(e), "tests_with_body_check": 0,
                "total_test_functions": 0, "response_validation_pct": 0.0}


# ═══════════════════════════════════════════════════════════
#  5. Test Type Distribution (z plánu)
# ═══════════════════════════════════════════════════════════

def calculate_test_type_distribution(test_plan: dict) -> dict:
    """Poměr happy_path / error / edge_case v plánu."""
    types = {"happy_path": 0, "error": 0, "edge_case": 0, "other": 0}

    for ep in test_plan.get("test_plan", []):
        for tc in ep.get("test_cases", []):
            t = tc.get("type", "other")
            if t in types:
                types[t] += 1
            else:
                types["other"] += 1

    total = sum(types.values())
    dist = {}
    for k, v in types.items():
        if v > 0:
            dist[k] = {"count": v, "pct": round(v / total * 100, 2) if total else 0.0}

    return {"total_planned": total, "distribution": dist}


# ═══════════════════════════════════════════════════════════
#  6. Status Code Diversity
# ═══════════════════════════════════════════════════════════

def calculate_status_code_diversity(file_path: str) -> dict:
    """Kolik různých HTTP status kódů testy ověřují."""
    if not os.path.exists(file_path):
        return {"error": "Soubor neexistuje.", "unique_status_codes": [],
                "diversity_count": 0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Hledej assert r.status_code == NNN nebo assert resp.status_code == NNN
        codes = re.findall(r'status_code\s*==\s*(\d{3})', source)
        unique = sorted(set(int(c) for c in codes))

        # Distribuce
        code_counts = {}
        for c in codes:
            c = int(c)
            code_counts[c] = code_counts.get(c, 0) + 1

        return {
            "unique_status_codes": unique,
            "diversity_count": len(unique),
            "code_distribution": dict(sorted(code_counts.items())),
        }
    except Exception as e:
        return {"error": str(e), "unique_status_codes": [], "diversity_count": 0}


# ═══════════════════════════════════════════════════════════
#  7. Empty Test Detection
# ═══════════════════════════════════════════════════════════

def detect_empty_tests(file_path: str) -> dict:
    """Najde testy s 0 asercemi (projdou vždy, ale nic netestují)."""
    ad = calculate_assertion_depth(file_path)
    if "error" in ad:
        return {"error": ad["error"], "empty_tests": [], "empty_count": 0}

    per_test = ad.get("per_test_assertions", {})
    empty = [name for name, count in per_test.items() if count == 0]

    return {
        "empty_tests": empty,
        "empty_count": len(empty),
        "total_test_functions": ad["total_test_functions"],
    }


# ═══════════════════════════════════════════════════════════
#  8. Average Test Length
# ═══════════════════════════════════════════════════════════

def calculate_avg_test_length(file_path: str) -> dict:
    """Průměrný počet řádků na test funkci."""
    if not os.path.exists(file_path):
        return {"error": "Soubor neexistuje.", "avg_lines": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]

        if not test_funcs:
            return {"avg_lines": 0.0, "total_test_functions": 0, "per_test_lines": {}}

        per_test = {}
        total_lines = 0
        for func in test_funcs:
            length = func.end_lineno - func.lineno + 1
            per_test[func.name] = length
            total_lines += length

        return {
            "avg_lines": round(total_lines / len(test_funcs), 2),
            "min_lines": min(per_test.values()),
            "max_lines": max(per_test.values()),
            "total_test_functions": len(test_funcs),
            "per_test_lines": per_test,
        }
    except Exception as e:
        return {"error": str(e), "avg_lines": 0.0}


# ═══════════════════════════════════════════════════════════
#  9. HTTP Method Coverage (z plánu)
# ═══════════════════════════════════════════════════════════

def calculate_method_coverage(test_plan: dict) -> dict:
    """Distribuce HTTP metod v plánu."""
    methods = {}
    for ep in test_plan.get("test_plan", []):
        m = ep.get("method", "").upper()
        test_count = len(ep.get("test_cases", []))
        if m:
            methods[m] = methods.get(m, 0) + test_count

    total = sum(methods.values())
    dist = {}
    for k, v in sorted(methods.items()):
        dist[k] = {"count": v, "pct": round(v / total * 100, 2) if total else 0.0}

    return {"total_planned": total, "method_distribution": dist}


# ═══════════════════════════════════════════════════════════
#  10. Plan Adherence
# ═══════════════════════════════════════════════════════════

def calculate_plan_adherence(file_path: str, test_plan: dict) -> dict:
    """Kolik testů z plánu se skutečně vygenerovalo (podle názvu)."""
    if not os.path.exists(file_path):
        return {"error": "Soubor neexistuje.", "adherence_pct": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        actual_names = {n.name for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}

        planned_names = set()
        for ep in test_plan.get("test_plan", []):
            for tc in ep.get("test_cases", []):
                name = tc.get("name", "")
                if name:
                    planned_names.add(f"test_{name}")

        if not planned_names:
            return {"planned": 0, "found_in_code": 0, "adherence_pct": 0.0}

        found = len(planned_names & actual_names)
        return {
            "planned": len(planned_names),
            "found_in_code": found,
            "extra_in_code": len(actual_names - planned_names),
            "missing_from_code": sorted(planned_names - actual_names),
            "adherence_pct": round(found / len(planned_names) * 100, 2),
        }
    except Exception as e:
        return {"error": str(e), "adherence_pct": 0.0}


# ═══════════════════════════════════════════════════════════
#  Souhrn všech metrik
# ═══════════════════════════════════════════════════════════

def calculate_all_metrics(
    file_path: str,
    pytest_output: str,
    openapi_path: str,
    test_plan: dict,
) -> dict:
    """Spočítá všechny metriky najednou. Volej z main.py."""
    return {
        "test_validity": parse_test_validity_rate(pytest_output),
        "endpoint_coverage": calculate_endpoint_coverage(openapi_path, test_plan),
        "assertion_depth": calculate_assertion_depth(file_path),
        "response_validation": calculate_response_validation(file_path),
        "test_type_distribution": calculate_test_type_distribution(test_plan),
        "status_code_diversity": calculate_status_code_diversity(file_path),
        "empty_tests": detect_empty_tests(file_path),
        "avg_test_length": calculate_avg_test_length(file_path),
        "method_coverage": calculate_method_coverage(test_plan),
        "plan_adherence": calculate_plan_adherence(file_path, test_plan),
    }