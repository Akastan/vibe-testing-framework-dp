"""
Fáze 6: Diagnostika — data pro obhajobu.

Neměří kvalitu testů (to dělá phase5_metrics.py).
Měří PROČ jsou výsledky takové jaké jsou.

Mapování na výzkumné otázky:
  RQ1 (validity):   context_size, helper_snapshot, instruction_compliance,
                     repair_trajectory, prompt_budget
  RQ2 (coverage):   plan_analysis (distribuce testů per endpoint/domain)
  RQ3 (selhání):    failure_taxonomy, code_patterns (summary),
                     plan_code_drift, context_utilization
"""
import ast, json, os, re, yaml


# ─── 1. Context Size (RQ1 — opponent: "přetížili jste model?") ──

def measure_context_size(context: str) -> dict:
    chars = len(context)
    sections = {}
    current_section = "preamble"
    current_lines = []

    for line in context.split('\n'):
        m = re.match(r'^---\s+(.+?)\s+---$', line)
        if m:
            if current_lines:
                text = '\n'.join(current_lines)
                sections[current_section] = {
                    "chars": len(text), "lines": len(current_lines),
                    "est_tokens": len(text) // 3,
                }
            current_section = m.group(1)
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        text = '\n'.join(current_lines)
        sections[current_section] = {
            "chars": len(text), "lines": len(current_lines),
            "est_tokens": len(text) // 3,
        }

    return {
        "total_chars": chars,
        "total_lines": context.count('\n') + 1,
        "total_est_tokens": chars // 3,
        "section_count": len(sections),
        "sections": sections,
    }


# ─── 2. Plan Analysis (RQ2 — distribuce testů) ──────────

def analyze_plan(test_plan: dict, openapi_path: str) -> dict:
    api_endpoints = set()
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f) if openapi_path.endswith(('.yaml', '.yml')) else json.load(f)
        methods = {'get', 'post', 'put', 'delete', 'patch'}
        api_endpoints = {f"{m.upper()} {p}"
                         for p, ms in spec.get('paths', {}).items()
                         for m in ms if m.lower() in methods}
    except Exception:
        pass

    ep_test_counts = {}
    total_tests = 0
    error_focus = {}
    domains = {"authors": 0, "categories": 0, "books": 0,
               "reviews": 0, "tags": 0, "orders": 0, "other": 0}

    for ep in test_plan.get("test_plan", []):
        key = f"{ep.get('method', '').upper()} {ep.get('endpoint', '')}"
        cases = ep.get("test_cases", [])
        ep_test_counts[key] = len(cases)
        total_tests += len(cases)

        err = sum(1 for tc in cases if tc.get("type") in ("error", "edge_case"))
        if err > 0:
            error_focus[key] = err

        matched = False
        for domain in domains:
            if domain != "other" and domain in key.lower():
                domains[domain] += len(cases)
                matched = True
                break
        if not matched:
            domains["other"] += len(cases)

    sorted_eps = sorted(ep_test_counts.items(), key=lambda x: -x[1])
    top3 = sum(c for _, c in sorted_eps[:3])

    return {
        "total_planned_tests": total_tests,
        "unique_endpoints_in_plan": len(ep_test_counts),
        "total_api_endpoints": len(api_endpoints),
        "top3_concentration_pct": round(top3 / total_tests * 100, 1) if total_tests else 0,
        "error_focused_endpoints": len(error_focus),
        "skipped_endpoints": sorted(api_endpoints - set(ep_test_counts.keys())),
        "domain_distribution": {k: v for k, v in domains.items() if v > 0},
    }


# ─── 3. Helper Snapshot (RQ1/RQ3 — proč L0 selhává) ─────

def snapshot_helpers(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "syntax_error", "helpers": {}, "helper_count": 0}

    helpers = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            args = []
            off = len(node.args.args) - len(node.args.defaults)
            for i, arg in enumerate(node.args.args):
                di = i - off
                if di >= 0:
                    d = node.args.defaults[di]
                    if isinstance(d, ast.Constant):
                        args.append(f"{arg.arg}={repr(d.value)}")
                    else:
                        args.append(f"{arg.arg}=<expr>")
                else:
                    args.append(arg.arg)

            lines = code.split('\n')
            body = '\n'.join(lines[node.lineno - 1:node.end_lineno])

            helpers[node.name] = {
                "signature": f"{node.name}({', '.join(args)})",
                "lines": node.end_lineno - node.lineno + 1,
                "has_stock_field": '"stock"' in body or "'stock'" in body,
                "has_assertion": 'assert' in body,
                "default_published_year": _extract_default_year(body),
            }

    return {"helpers": helpers, "helper_count": len(helpers)}


def _extract_default_year(body: str) -> int | None:
    for p in [r'published_year["\']?\s*[:=]\s*(\d{4})', r'\byear\s*=\s*(\d{4})']:
        m = re.search(p, body)
        if m:
            return int(m.group(1))
    return None


# ─── 4. Prompt Budget (RQ1 — opponent) ───────────────────

def estimate_prompt_budget(context: str, plan_json: str,
                           model_context_window: int = 128000) -> dict:
    ctx_tok = len(context) // 3
    plan_tok = len(plan_json) // 3
    overhead = 800
    total = ctx_tok + plan_tok + overhead
    return {
        "context_tokens_est": ctx_tok,
        "plan_tokens_est": plan_tok,
        "total_prompt_tokens_est": total,
        "remaining_for_output_est": model_context_window - total,
        "prompt_budget_pct": round(total / model_context_window * 100, 1),
    }


# ─── 5. Instruction Compliance (RQ1 — in-context learning) ──

def check_instruction_compliance(code: str) -> dict:
    http_calls = re.findall(r'requests\.(get|post|put|patch|delete)\(', code)
    timeout_calls = re.findall(r'timeout\s*=\s*\d+', code)
    missing_timeout = max(0, len(http_calls) - len(timeout_calls))

    uses_unique = 'unique(' in code
    calls_reset = bool(re.search(r'/reset', code))
    uses_fixtures = bool(re.search(
        r'@pytest\.fixture|conftest|setup_module|setup_function', code))

    score = 100
    if missing_timeout > 0: score -= min(missing_timeout * 5, 20)
    if not uses_unique: score -= 20
    if calls_reset: score -= 15
    if uses_fixtures: score -= 10

    return {
        "total_http_calls": len(http_calls),
        "missing_timeout": missing_timeout,
        "uses_unique_helper": uses_unique,
        "calls_reset_endpoint": calls_reset,
        "uses_fixtures": uses_fixtures,
        "compliance_score": max(score, 0),
    }


# ─── 6. Repair Trajectory (RQ1/RQ3) ─────────────────────

class RepairTracker:
    def __init__(self):
        self._iterations: list[dict] = []

    def record_iteration(self, iteration: int, pytest_log: str,
                         repair_type: str | None = None,
                         repaired_count: int = 0, stale_count: int = 0):
        passed = failed = 0
        m = re.search(r'(\d+)\s+passed', pytest_log)
        if m: passed = int(m.group(1))
        m = re.search(r'(\d+)\s+failed', pytest_log)
        if m: failed = int(m.group(1))

        failing_names = list(dict.fromkeys(
            re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)))

        # Failure details jen pro první iteraci (čerstvé tracebacky pro taxonomy)
        failure_details = {}
        if iteration == 1:
            for name in failing_names:
                error = _extract_error_block(pytest_log, name)
                cat = _classify_single_failure(error, name, "")
                failure_details[name] = {
                    "category": cat,
                    "error_summary": _summarize_error(error),
                }

        entry = {
            "iteration": iteration,
            "passed": passed,
            "failed": failed,
            "failing_tests": failing_names,
            "repair_type": repair_type,
            "repaired_count": repaired_count,
            "stale_skipped": stale_count,
        }
        if failure_details:
            entry["failure_details"] = failure_details

        self._iterations.append(entry)

    def annotate_last(self, repair_type: str | None = None,
                      repaired_count: int = 0, stale_skipped: int = 0):
        if self._iterations:
            self._iterations[-1]["repair_type"] = repair_type
            self._iterations[-1]["repaired_count"] = repaired_count
            self._iterations[-1]["stale_skipped"] = stale_skipped

    def get_trajectory(self) -> dict:
        if not self._iterations:
            return {"iterations": [], "convergence_iteration": 0}

        # Konvergence
        convergence = len(self._iterations)
        for i in range(1, len(self._iterations)):
            if self._iterations[i]["failed"] == self._iterations[i - 1]["failed"]:
                convergence = i
                break

        first_failing = set(self._iterations[0].get("failing_tests", []))
        last_failing = set(self._iterations[-1].get("failing_tests", []))

        # Failure categories z první iterace
        all_categories = {}
        first = self._iterations[0].get("failure_details", {})
        for name, info in first.items():
            all_categories[name] = info["category"]

        # Slim iterations — jen čísla, bez failing_tests listů (kromě iter 1)
        slim_iters = []
        for it in self._iterations:
            entry = {
                "iteration": it["iteration"],
                "passed": it["passed"],
                "failed": it["failed"],
                "repair_type": it.get("repair_type"),
                "repaired_count": it.get("repaired_count", 0),
                "stale_skipped": it.get("stale_skipped", 0),
            }
            slim_iters.append(entry)

        return {
            "iterations": slim_iters,
            "convergence_iteration": convergence + 1,
            "never_fixed_tests": sorted(first_failing & last_failing),
            "fixed_tests": sorted(first_failing - last_failing),
            "failure_categories": all_categories,
        }


# ─── 7. Failure Taxonomy (RQ3) ───────────────────────────

def classify_failures(pytest_log: str, code: str) -> dict:
    failing_names = list(dict.fromkeys(
        re.findall(r'FAILED\s+\S+::(\w+)', pytest_log)))
    if not failing_names:
        return {"total_failures": 0, "categories": {}, "per_test": {}}

    cats = {}
    per_test = {}
    for name in failing_names:
        error = _extract_error_block(pytest_log, name)
        cat = _classify_single_failure(error, name, code)
        cats[cat] = cats.get(cat, 0) + 1
        per_test[name] = {
            "category": cat,
            "error_summary": _summarize_error(error),
        }

    total = len(failing_names)
    return {
        "total_failures": total,
        "categories": cats,
        "category_pct": {k: round(v / total * 100, 1) for k, v in cats.items()},
        "per_test": per_test,
    }


def _extract_error_block(pytest_log: str, test_name: str) -> str:
    # Strategie 1: FAILURES blok
    pattern = (
        rf'_{2,}\s+\S*{re.escape(test_name)}\s+_{2,}'
        rf'(.*?)'
        rf'(?=_{2,}\s+\S*\w+\s+_{2,}|={2,}\s+short test summary|$)'
    )
    m = re.search(pattern, pytest_log, re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()[:2000]

    # Strategie 2: short test summary
    m2 = re.search(
        rf'FAILED\s+\S+::{re.escape(test_name)}\s*(?:[-–]\s*(.+))?$',
        pytest_log, re.MULTILINE)
    if m2 and m2.group(1):
        return m2.group(1).strip()[:500]

    # Strategie 3: E-řádky v traceback bloku
    m3 = re.search(
        rf'in {re.escape(test_name)}\b.*?\n(.*?)(?=\n\S|\nFAILED|\n={2,}|\Z)',
        pytest_log, re.DOTALL)
    if m3:
        e_lines = [l.strip() for l in m3.group(1).splitlines()
                    if l.strip().startswith('E ')]
        if e_lines:
            return '\n'.join(e_lines)[:500]
        if m3.group(1).strip():
            return m3.group(1).strip()[:500]

    # Strategie 4: řádek s test_name + assert/E
    for line in pytest_log.splitlines():
        if test_name in line and ('E ' in line or 'assert' in line.lower()):
            return line.strip()[:500]

    # Strategie 5: E-řádky za řádkem s test_name
    lines = pytest_log.splitlines()
    for i, line in enumerate(lines):
        if test_name in line:
            for j in range(i + 1, min(i + 11, len(lines))):
                s = lines[j].strip()
                if s.startswith('E ') and len(s) > 4:
                    return s[2:].strip()[:500]

    return ""


def _classify_single_failure(error: str, test_name: str, code: str) -> str:
    if not error:
        return "unknown_no_error_captured"

    if re.search(r'status_code\s*==\s*\d{3}', error):
        return "wrong_status_code"
    if re.search(r'assert\s+\d{3}\s*[=!]=\s*\d{3}', error):
        return "wrong_status_code"
    if re.search(r'\d{3}\s*[!=]=\s*\d{3}', error):
        return "wrong_status_code"
    if re.search(r'in create_\w+|in unique\b', error):
        return "helper_cascade"
    if 'KeyError' in error:
        return "key_error"
    if 'AttributeError' in error:
        return "attribute_error"
    if re.search(r'ConnectionError|ConnectionRefused|RemoteDisconnected', error, re.I):
        return "connection_error"
    if re.search(r'Timeout|timed?\s*out', error, re.I):
        return "timeout"
    if 'TypeError' in error:
        return "type_error"
    if 'JSONDecodeError' in error:
        return "json_decode_error"
    if re.search(r'assert\s+\S+\s*==\s*\S+', error) and 'status_code' not in error:
        return "assertion_value_mismatch"
    return "other"


def _summarize_error(error: str) -> str:
    for line in error.splitlines():
        s = line.strip()
        if s.startswith("E ") and len(s) > 4:
            return s[2:].strip()[:120]
    for line in error.splitlines():
        s = line.strip()
        if s and not s.startswith("_"):
            return s[:120]
    return ""


# ─── 8. Code Patterns — jen summary (RQ1/RQ3) ───────────

def analyze_code_patterns(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "syntax_error"}

    test_funcs = [n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    lines = code.split('\n')

    http_counts, setup_counts = [], []
    side_effect, chaining = [], []

    for func in test_funcs:
        body = '\n'.join(lines[func.lineno - 1:func.end_lineno])
        http = len(re.findall(r'requests\.(get|post|put|patch|delete)\(', body))
        helpers = len(re.findall(r'create_\w+\(', body))
        methods = re.findall(r'requests\.(get|post|put|patch|delete)', body)

        http_counts.append(http)
        setup_counts.append(helpers)
        side_effect.append(
            'get' in methods and any(m in methods for m in ('post', 'put', 'patch', 'delete'))
        )
        chaining.append(bool(re.search(r'\.json\(\)\[', body)))

    n = len(test_funcs) or 1
    return {
        "total_tests": len(test_funcs),
        "avg_http_calls": round(sum(http_counts) / n, 2),
        "avg_helper_calls": round(sum(setup_counts) / n, 2),
        "pct_side_effect_checks": round(sum(side_effect) / n * 100, 1),
        "pct_chaining": round(sum(chaining) / n * 100, 1),
    }


# ─── 9. Plan vs Code Drift (RQ3) ────────────────────────

def analyze_plan_code_drift(test_plan: dict, code: str) -> dict:
    planned = {}
    for ep in test_plan.get("test_plan", []):
        for tc in ep.get("test_cases", []):
            name = f"test_{tc.get('name', '')}"
            planned[name] = tc.get("expected_status", 0)

    actual_names = set()
    try:
        tree = ast.parse(code)
        actual_names = {n.name for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    except SyntaxError:
        pass

    planned_set = set(planned.keys())

    # Status code drift
    drift_count = 0
    for name, expected in planned.items():
        if name in actual_names and expected:
            func_code = _extract_func_body(code, name)
            if func_code:
                actual = [int(s) for s in re.findall(r'status_code\s*==\s*(\d{3})', func_code)]
                if expected not in actual:
                    drift_count += 1

    return {
        "planned_count": len(planned),
        "actual_count": len(actual_names),
        "matched": len(planned_set & actual_names),
        "only_in_plan_count": len(planned_set - actual_names),
        "only_in_code_count": len(actual_names - planned_set),
        "status_code_drift_count": drift_count,
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


# ─── 10. Context Utilization (RQ3) ───────────────────────

def analyze_context_utilization(context: str, code: str, test_plan: dict) -> dict:
    ctx_statuses = set(re.findall(r'\b([2-5]\d{2})\b', context))
    code_statuses = set(re.findall(r'status_code\s*==\s*(\d{3})', code))

    plan_endpoints = {ep.get("endpoint", "") for ep in test_plan.get("test_plan", [])}
    context_endpoints = set(re.findall(r'(/\w[\w/{}_]*)', context))

    return {
        "context_endpoints_found": len(context_endpoints),
        "plan_endpoints_used": len(plan_endpoints),
        "status_codes_from_context": sorted(ctx_statuses & code_statuses),
        "status_codes_hallucinated": sorted(code_statuses - ctx_statuses),
    }


# ─── Souhrn ───────────────────────────────────────────────

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
    if not plan_json_str:
        plan_json_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    # Failure taxonomy: preferuj první iteraci RepairTrackeru
    failure_tax = {"total_failures": 0, "categories": {}, "per_test": {}}
    if repair_tracker and repair_tracker._iterations:
        first = repair_tracker._iterations[0]
        details = first.get("failure_details", {})
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
    if failure_tax["total_failures"] == 0:
        failure_tax = classify_failures(pytest_log, code)

    diag = {
        "context_size": measure_context_size(context),
        "plan_analysis": analyze_plan(test_plan, openapi_path),
        "helper_snapshot": snapshot_helpers(code),
        "prompt_budget": estimate_prompt_budget(
            context, plan_json_str, model_context_window),
        "instruction_compliance": check_instruction_compliance(code),
        "failure_taxonomy": failure_tax,
        "code_patterns": analyze_code_patterns(code),
        "plan_code_drift": analyze_plan_code_drift(test_plan, code),
        "context_utilization": analyze_context_utilization(context, code, test_plan),
    }

    if repair_tracker:
        diag["repair_trajectory"] = repair_tracker.get_trajectory()

    return diag