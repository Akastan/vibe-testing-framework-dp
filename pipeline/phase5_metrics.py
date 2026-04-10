"""
Fáze 5: Automatické metriky (součást pipeline).

Měří kvalitu vygenerovaných testů pro výzkumné otázky:
  RQ1 (validity):  test_validity, assertion_depth, response_validation,
                   test_type_distribution, instruction compliance (→ phase6)
  RQ2 (coverage):  endpoint_coverage, (code coverage = manuální)
  RQ3 (selhání):   failure_taxonomy (→ phase6), status_code_diversity

Ruční metriky (code coverage, mutation) viz run_coverage_manual.py.
"""
import ast, json, yaml, re, os


# ─── 1. Test Validity Rate (RQ1) ─────────────────────────

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


# ─── 2. Endpoint Coverage (RQ2) ──────────────────────────

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


# ─── 3. Assertion Depth (RQ1 kvalita) ────────────────────

def calculate_assertion_depth(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"error": "File not found", "assertion_depth": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        total = 0
        for func in test_funcs:
            count = sum(1 for n in ast.walk(func) if isinstance(n, ast.Assert))
            for n in ast.walk(func):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    if "assert" in n.func.id.lower():
                        count += 1
            total += count

        depth = round(total / len(test_funcs), 2) if test_funcs else 0.0
        return {
            "total_test_functions": len(test_funcs),
            "total_assertions": total,
            "assertion_depth": depth,
        }
    except Exception as e:
        return {"error": str(e), "assertion_depth": 0.0}


# ─── 4. Response Validation (RQ1 kvalita) ────────────────

def calculate_response_validation(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"error": "File not found", "response_validation_pct": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            tree = ast.parse(source)

        lines = source.split('\n')
        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]

        pattern = re.compile(
            r'\.json\(\)\[|\.json\(\)\s*==|data\[|"id"\s+in|"detail"\s+in'
            r'|len\(|\["status"\]|\["name"\]|\["total|\["items"\]|assert.*\.json\('
        )

        with_body = sum(
            1 for func in test_funcs
            if pattern.search('\n'.join(lines[func.lineno - 1:func.end_lineno]))
        )
        total = len(test_funcs)
        return {
            "tests_with_body_check": with_body,
            "total_test_functions": total,
            "response_validation_pct": round(with_body / total * 100, 2) if total else 0.0,
        }
    except Exception as e:
        return {"error": str(e), "response_validation_pct": 0.0}


# ─── 5. Test Type Distribution (RQ1/RQ3) ─────────────────

def calculate_test_type_distribution(test_plan: dict) -> dict:
    types = {"happy_path": 0, "error": 0, "edge_case": 0}
    for ep in test_plan.get("test_plan", []):
        for tc in ep.get("test_cases", []):
            t = tc.get("type", "other")
            if t in types:
                types[t] += 1
            else:
                types.setdefault("other", 0)
                types["other"] += 1

    total = sum(types.values())
    return {
        "total_planned": total,
        "distribution": {
            k: {"count": v, "pct": round(v / total * 100, 2) if total else 0.0}
            for k, v in types.items() if v > 0
        },
    }


# ─── 6. Status Code Diversity (RQ3) ──────────────────────

def calculate_status_code_diversity(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"error": "File not found", "diversity_count": 0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        codes = re.findall(r'status_code\s*==\s*(\d{3})', source)
        code_counts = {}
        for c in codes:
            c = int(c)
            code_counts[c] = code_counts.get(c, 0) + 1

        return {
            "unique_status_codes": sorted(code_counts.keys()),
            "diversity_count": len(code_counts),
            "code_distribution": dict(sorted(code_counts.items())),
        }
    except Exception as e:
        return {"error": str(e), "diversity_count": 0}


# ─── 7. Empty Test Detection ─────────────────────────────

def detect_empty_tests(file_path: str) -> dict:
    ad = calculate_assertion_depth(file_path)
    if "error" in ad:
        return {"empty_count": 0}

    # Potřebujeme per-test pro detekci — ale neukládáme do JSON
    if not os.path.exists(file_path):
        return {"empty_count": 0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        empty = []
        for func in test_funcs:
            count = sum(1 for n in ast.walk(func) if isinstance(n, ast.Assert))
            if count == 0:
                empty.append(func.name)
        return {"empty_tests": empty, "empty_count": len(empty)}
    except Exception:
        return {"empty_count": 0}


# ─── 8. Avg Test Length ───────────────────────────────────

def calculate_avg_test_length(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"avg_lines": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        test_funcs = [n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        if not test_funcs:
            return {"avg_lines": 0.0, "total_test_functions": 0}

        lengths = [f.end_lineno - f.lineno + 1 for f in test_funcs]
        return {
            "avg_lines": round(sum(lengths) / len(lengths), 2),
            "total_test_functions": len(test_funcs),
        }
    except Exception:
        return {"avg_lines": 0.0}


# ─── 9. Plan Adherence ───────────────────────────────────

def calculate_plan_adherence(file_path: str, test_plan: dict) -> dict:
    if not os.path.exists(file_path):
        return {"adherence_pct": 0.0}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        actual = {n.name for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
        planned = set()
        for ep in test_plan.get("test_plan", []):
            for tc in ep.get("test_cases", []):
                name = tc.get("name", "")
                if name:
                    planned.add(f"test_{name}")
        if not planned:
            return {"planned": 0, "found_in_code": 0, "adherence_pct": 0.0}
        found = len(planned & actual)
        return {
            "planned": len(planned),
            "found_in_code": found,
            "extra_in_code": len(actual - planned),
            "adherence_pct": round(found / len(planned) * 100, 2),
        }
    except Exception:
        return {"adherence_pct": 0.0}


# ─── Souhrn ───────────────────────────────────────────────

def calculate_all_metrics(
    file_path: str,
    pytest_output: str,
    openapi_path: str,
    test_plan: dict,
) -> dict:
    return {
        "test_validity": parse_test_validity_rate(pytest_output),
        "endpoint_coverage": calculate_endpoint_coverage(openapi_path, test_plan),
        "assertion_depth": calculate_assertion_depth(file_path),
        "response_validation": calculate_response_validation(file_path),
        "test_type_distribution": calculate_test_type_distribution(test_plan),
        "status_code_diversity": calculate_status_code_diversity(file_path),
        "empty_tests": detect_empty_tests(file_path),
        "avg_test_length": calculate_avg_test_length(file_path),
        "plan_adherence": calculate_plan_adherence(file_path, test_plan),
    }