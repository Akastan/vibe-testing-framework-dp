import ast
import json
import yaml
import re
import os


def calculate_assertion_depth(file_path: str) -> dict:
    """Metrika: Assertion Depth (Hloubka asercí)"""
    if not os.path.exists(file_path):
        return {"error": "Soubor s testy neexistuje."}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)

        # Hledáme všechny funkce začínající na 'test_'
        test_funcs = [node for node in ast.walk(tree) if
                      isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]

        total_asserts = 0
        for func in test_funcs:
            # Počet explicitních klíčových slov 'assert'
            asserts = [node for node in ast.walk(func) if isinstance(node, ast.Assert)]
            total_asserts += len(asserts)

            # Pokud model používá custom helper metody začínající na "assert" (např. assert_response)
            calls = [node for node in ast.walk(func) if isinstance(node, ast.Call)]
            for call in calls:
                if isinstance(call.func, ast.Name) and "assert" in call.func.id.lower():
                    total_asserts += 1

        total_tests = len(test_funcs)
        depth = (total_asserts / total_tests) if total_tests > 0 else 0.0

        return {
            "total_test_functions": total_tests,
            "total_assertions": total_asserts,
            "assertion_depth": round(depth, 2)
        }
    except SyntaxError:
        return {"error": "Vygenerovaný kód má syntaktickou chybu (nelze parsovat AST).", "assertion_depth": 0.0}
    except Exception as e:
        return {"error": str(e)}


def calculate_endpoint_coverage(openapi_path: str, test_plan: dict) -> dict:
    """Metrika: Endpoint Coverage (Pokrytí endpointů)"""
    try:
        with open(openapi_path, 'r', encoding='utf-8') as file:
            spec = yaml.safe_load(file) if openapi_path.endswith(('.yaml', '.yml')) else json.load(file)

        # Zjistíme všechny endpointy v API
        api_endpoints = set()
        if 'paths' in spec:
            for path, methods in spec['paths'].items():
                for method in methods.keys():
                    if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                        api_endpoints.add(f"{method.upper()} {path}")

        # Zjistíme, co pokryl LLM testovací plán
        planned_endpoints = set()
        if isinstance(test_plan, dict) and 'test_plan' in test_plan:
            for endpoint_def in test_plan['test_plan']:
                path = endpoint_def.get('endpoint', '')
                method = endpoint_def.get('method', '').upper()
                planned_endpoints.add(f"{method} {path}")

        total_api = len(api_endpoints)
        covered = len(api_endpoints.intersection(planned_endpoints))
        coverage_pct = (covered / total_api * 100) if total_api > 0 else 0.0

        return {
            "total_api_endpoints": total_api,
            "covered_endpoints": covered,
            "endpoint_coverage_pct": round(coverage_pct, 2)
        }
    except Exception as e:
        return {"error": str(e)}


def parse_test_validity_rate(pytest_output: str) -> dict:
    """Metrika: Test Validity Rate (Míra validity testů)"""
    passed, failed, errors = 0, 0, 0

    # Hledáme běžný výstup pytestu (např. "== 4 passed, 2 failed in 1.12s ==")
    passed_match = re.search(r'(\d+)\s+passed', pytest_output)
    if passed_match: passed = int(passed_match.group(1))

    failed_match = re.search(r'(\d+)\s+failed', pytest_output)
    if failed_match: failed = int(failed_match.group(1))

    error_match = re.search(r'(\d+)\s+error', pytest_output)
    if error_match: errors = int(error_match.group(1))

    total_executed = passed + failed + errors
    validity_rate = (passed / total_executed * 100) if total_executed > 0 else 0.0

    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_errors": errors,
        "total_executed": total_executed,
        "validity_rate_pct": round(validity_rate, 2)
    }