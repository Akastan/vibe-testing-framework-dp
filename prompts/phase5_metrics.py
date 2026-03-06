"""
Fáze 5: Výpočet metrik kvality vygenerovaných testů.

Metriky:
  1. Assertion Depth – průměrný počet asercí na test
  2. Endpoint Coverage – % pokrytých endpointů z OpenAPI specifikace
  3. Test Validity Rate – % úspěšně prošlých testů
"""
import ast
import json
import yaml
import re
import os


def calculate_assertion_depth(file_path: str) -> dict:
    """
    Spočítá průměrný počet asercí na testovací funkci.
    Hledá jak `assert` statementy, tak volání funkcí obsahujících 'assert' v názvu.
    """
    if not os.path.exists(file_path):
        return {"error": "Soubor s testy neexistuje.", "total_test_functions": 0,
                "total_assertions": 0, "assertion_depth": 0.0}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)

        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]

        total_asserts = 0
        for func in test_funcs:
            # Explicitní assert statementy
            asserts = sum(1 for n in ast.walk(func) if isinstance(n, ast.Assert))
            total_asserts += asserts

            # Volání helper funkcí s 'assert' v názvu (např. assert_response)
            for n in ast.walk(func):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    if "assert" in n.func.id.lower():
                        total_asserts += 1

        total_tests = len(test_funcs)
        depth = round(total_asserts / total_tests, 2) if total_tests > 0 else 0.0

        return {
            "total_test_functions": total_tests,
            "total_assertions": total_asserts,
            "assertion_depth": depth
        }
    except SyntaxError:
        return {"error": "Syntaktická chyba v kódu (nelze parsovat AST).",
                "total_test_functions": 0, "total_assertions": 0, "assertion_depth": 0.0}
    except Exception as e:
        return {"error": str(e), "total_test_functions": 0,
                "total_assertions": 0, "assertion_depth": 0.0}


def calculate_endpoint_coverage(openapi_path: str, test_plan: dict) -> dict:
    """
    Porovná endpointy v OpenAPI specifikaci s endpointy v testovacím plánu.
    """
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            if openapi_path.endswith(('.yaml', '.yml')):
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)

        # Všechny endpointy v API
        http_methods = {'get', 'post', 'put', 'delete', 'patch'}
        api_endpoints = set()
        for path, methods in spec.get('paths', {}).items():
            for method in methods:
                if method.lower() in http_methods:
                    api_endpoints.add(f"{method.upper()} {path}")

        # Endpointy pokryté testovacím plánem
        planned_endpoints = set()
        if isinstance(test_plan, dict) and 'test_plan' in test_plan:
            for ep in test_plan['test_plan']:
                path = ep.get('endpoint', '')
                method = ep.get('method', '').upper()
                if path and method:
                    planned_endpoints.add(f"{method} {path}")

        total = len(api_endpoints)
        covered = len(api_endpoints & planned_endpoints)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "total_api_endpoints": total,
            "covered_endpoints": covered,
            "uncovered_endpoints": sorted(api_endpoints - planned_endpoints),
            "endpoint_coverage_pct": pct
        }
    except Exception as e:
        return {"error": str(e), "total_api_endpoints": 0,
                "covered_endpoints": 0, "endpoint_coverage_pct": 0.0}


def parse_test_validity_rate(pytest_output: str) -> dict:
    """
    Parsuje výstup pytestu a spočítá míru validity testů.
    """
    passed = failed = errors = 0

    m = re.search(r'(\d+)\s+passed', pytest_output)
    if m:
        passed = int(m.group(1))

    m = re.search(r'(\d+)\s+failed', pytest_output)
    if m:
        failed = int(m.group(1))

    m = re.search(r'(\d+)\s+error', pytest_output)
    if m:
        errors = int(m.group(1))

    total = passed + failed + errors
    rate = round(passed / total * 100, 2) if total > 0 else 0.0

    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_errors": errors,
        "total_executed": total,
        "validity_rate_pct": rate
    }