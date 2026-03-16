"""
Fáze 5: Automatické metriky (součást pipeline).

  1. Test Validity Rate – % prošlých testů
  2. Endpoint Coverage – % pokrytých endpointů
  3. Assertion Depth – průměr asercí na test
  4. Iteration Delta – rozdíl mezi 1. a poslední iterací

Ruční metriky (coverage, mutation) viz run_coverage_manual.py a run_mutation_manual.py.
"""
import ast
import json
import yaml
import re
import os


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
            "total_api_endpoints": total, "covered_endpoints": covered,
            "uncovered_endpoints": sorted(api_eps - plan_eps),
            "endpoint_coverage_pct": round(covered / total * 100, 2) if total else 0.0,
        }
    except Exception as e:
        return {"error": str(e), "total_api_endpoints": 0,
                "covered_endpoints": 0, "endpoint_coverage_pct": 0.0}


def parse_test_validity_rate(pytest_output: str) -> dict:
    passed = failed = errors = 0

    m = re.search(r'(\d+)\s+passed', pytest_output)
    if m: passed = int(m.group(1))
    m = re.search(r'(\d+)\s+failed', pytest_output)
    if m: failed = int(m.group(1))
    m = re.search(r'(\d+)\s+error', pytest_output)
    if m: errors = int(m.group(1))

    # Fallback: summary chybí (timeout zabil session)
    if passed == 0 and failed == 0 and errors == 0:
        passed = len(re.findall(r' PASSED', pytest_output))
        failed = len(re.findall(r' FAILED', pytest_output))
        failed += len(re.findall(r'Timeout', pytest_output))

    total = passed + failed + errors
    return {
        "tests_passed": passed, "tests_failed": failed, "tests_errors": errors,
        "total_executed": total,
        "validity_rate_pct": round(passed / total * 100, 2) if total else 0.0,
    }


class IterationTracker:
    def __init__(self):
        self.first_iteration = None
        self.last_iteration = None
        self.iteration_count = 0

    def record_iteration(self, num: int, pytest_output: str, test_file: str):
        self.iteration_count = num
        snap = {
            "iteration": num,
            "validity": parse_test_validity_rate(pytest_output),
            "assertions": calculate_assertion_depth(test_file),
        }
        if num == 1:
            self.first_iteration = snap
        self.last_iteration = snap

    def get_delta(self) -> dict:
        if not self.first_iteration or not self.last_iteration:
            return {"error": "Nedostatek dat."}
        if self.first_iteration["iteration"] == self.last_iteration["iteration"]:
            return {"note": "1 iterace.", "iterations_total": 1,
                    "first_iteration": self.first_iteration,
                    "last_iteration": self.last_iteration, "delta": {}}

        fv, lv = self.first_iteration["validity"], self.last_iteration["validity"]
        fa, la = self.first_iteration["assertions"], self.last_iteration["assertions"]
        return {
            "iterations_total": self.iteration_count,
            "first_iteration": self.first_iteration,
            "last_iteration": self.last_iteration,
            "delta": {
                "validity_rate_delta": round(lv["validity_rate_pct"] - fv["validity_rate_pct"], 2),
                "tests_passed_delta": lv["tests_passed"] - fv["tests_passed"],
                "tests_failed_delta": lv["tests_failed"] - fv["tests_failed"],
                "assertion_depth_delta": round(la.get("assertion_depth", 0) - fa.get("assertion_depth", 0), 2),
                "total_tests_delta": la.get("total_test_functions", 0) - fa.get("total_test_functions", 0),
            },
        }