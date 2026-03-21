
"""
Vibe Testing Framework – Experiment Runner.
Čte experiment.yaml a spouští všechny kombinace: LLM × API × Level × Run.

Použití:
    1. Uprav experiment.yaml (LLM modely, API, úrovně, počet runů)
    2. Nastav API klíče v .env (GEMINI_API_KEY, OPENAI_API_KEY, ...)
    3. Ujisti se, že na portu 8000 NEBĚŽÍ žádný server (framework si ho spouští sám)
    4. Spusť:
         taskkill /IM python.exe /F          # Windows: zabij staré procesy
         .venv\\Scripts\\Activate.ps1
         python main.py

    Server se spustí automaticky a zůstává běžet napříč iteracemi i úrovněmi.
    Po dokončení všech úrovní pro dané API se server automaticky zastaví.

Výstupy:
    outputs/test_generated_{llm}__{api}__{level}__run{N}.py   – vygenerované testy
    outputs/test_plan_{llm}__{api}__{level}__run{N}.json      – testovací plán
    outputs/..._log.txt                                        – pytest log
    results/experiment_{name}_{timestamp}.json                 – souhrnné metriky
"""
import os
import sys
import json
import time
import yaml
from datetime import datetime
from dotenv import load_dotenv

from llm_provider import create_llm
from prompts.phase1_context import analyze_context
from prompts.phase2_planning import generate_test_plan
from prompts.phase3_generation import generate_test_code, repair_failing_tests, validate_test_count, count_test_functions
from prompts.phase4_validation import run_tests_and_validate, stop_managed_server
from prompts.phase5_metrics import calculate_all_metrics, parse_test_validity_rate

OUTPUTS_DIR = "outputs"
RESULTS_DIR = "results"

CONTEXT_LEVELS = {
    "L0": "OpenAPI specifikace",
    "L1": "OpenAPI + dokumentace",
    "L2": "L1 + zdrojový kód",
    "L3": "L2 + DB schéma",
    "L4": "L3 + existující testy",
}


def load_experiment_config(path: str = "experiment.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)



def _sanitize_tag(name: str) -> str:
    """Nahradí tečky a jiné problematické znaky v názvu souboru."""
    return name.replace(".", "_").replace(" ", "_")

def run_pipeline(
    llm, llm_name: str, api_cfg: dict, level: str,
    run_id: int, test_count: int, max_iterations: int,
) -> dict:
    """Spustí jednu kombinaci: 1 LLM × 1 API × 1 Level × 1 Run."""
    api_name = api_cfg["name"]
    tag = f"{_sanitize_tag(llm_name)}__{api_name}__{level}__run{run_id}"
    output_filename = f"test_generated_{tag}.py"
    plan_filename = f"test_plan_{tag}.json"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    inputs = api_cfg["inputs"]

    print(f"\n{'=' * 65}")
    print(f"  {llm_name} | {api_name} | {level} | Běh {run_id}")
    print(f"{'=' * 65}")

    start_time = time.time()

    # ── FÁZE 1: Kontext ──────────────────────────────────
    context = analyze_context(
        openapi_path=inputs["openapi"],
        doc_path=inputs.get("documentation"),
        level=level,
        source_code_path=inputs.get("source_code"),
        db_schema_path=inputs.get("db_schema"),
        existing_tests_path=inputs.get("existing_tests"),
    )

    # ── FÁZE 2: Plánování ────────────────────────────────
    print(f"  [Fáze 2] Generování plánu ({test_count} testů)...")
    test_plan = generate_test_plan(context, llm, level=level, test_count=test_count)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(os.path.join(OUTPUTS_DIR, plan_filename), "w", encoding="utf-8") as f:
        json.dump(test_plan, f, indent=2, ensure_ascii=False)

    plan_test_count = sum(
        len(ep.get("test_cases", []))
        for ep in test_plan.get("test_plan", [])
    )
    print(f"  Plán: {plan_test_count} testů")

    # ── FÁZE 3 + 4: Generování + Feedback loop ──────────
    print(f"  [Fáze 3+4] Generování kódu (max {max_iterations} iterací)...")
    test_code = generate_test_code(
        test_plan, context, llm,
        base_url=api_cfg["base_url"],
    )

    actual_count = count_test_functions(test_code)
    if plan_test_count > 0:
        test_code = validate_test_count(
            test_code, plan_test_count, llm=llm,
            base_url=api_cfg["base_url"], context=context,
        )
        actual_count = count_test_functions(test_code)
    print(f"  Testů v kódu: {actual_count} (plán: {plan_test_count})")

    iteration = 0
    success = False
    output_log = ""

    while iteration < max_iterations and not success:
        iteration += 1
        print(f"\n  --- Iterace {iteration}/{max_iterations} ---")

        success, output_log = run_tests_and_validate(
            test_code,
            output_filename=output_filename,
            api_cfg=api_cfg,
            iteration=iteration,
        )

        if success:
            print("  ✅ Všechny testy prošly!")
        elif iteration < max_iterations:
            print("  ❌ Testy selhaly. Opravuji...")
            test_code = repair_failing_tests(
                test_code, output_log, context, llm,
                base_url=api_cfg["base_url"],
            )
        else:
            print(f"  ⚠️ Max iterací dosaženo.")

    elapsed = round(time.time() - start_time, 2)

    # ── FÁZE 5: Metriky ─────────────────────────────────
    tv = parse_test_validity_rate(output_log)
    metrics = calculate_all_metrics(
        file_path=output_path,
        pytest_output=output_log,
        openapi_path=inputs["openapi"],
        test_plan=test_plan,
    )

    ec = metrics["endpoint_coverage"]
    ad = metrics["assertion_depth"]
    rv = metrics["response_validation"]
    et = metrics["empty_tests"]

    print(f"\n  {'─' * 50}")
    print(f"  Validity:   {tv['validity_rate_pct']}% ({tv['tests_passed']}/{tv['total_executed']})")
    print(f"  Endpoint:   {ec['endpoint_coverage_pct']}% ({ec['covered_endpoints']}/{ec['total_api_endpoints']})")
    print(f"  Assert:     {ad['assertion_depth']} avg ({ad['total_assertions']} total)")
    print(
        f"  Body check: {rv['response_validation_pct']}% ({rv['tests_with_body_check']}/{rv['total_test_functions']})")
    print(f"  Status codes: {metrics['status_code_diversity']['diversity_count']} unique")
    print(f"  Empty tests: {et['empty_count']}")
    print(f"  Čas:        {elapsed}s | Iterací: {iteration}")

    return {
        "timestamp": datetime.now().isoformat(),
        "llm": llm_name,
        "api": api_name,
        "level": level,
        "run_id": run_id,
        "iterations_used": iteration,
        "all_tests_passed": success,
        "elapsed_seconds": elapsed,
        "plan_test_count": plan_test_count,
        "output_filename": output_filename,
        "plan_filename": plan_filename,
        "metrics": metrics,
    }


def main():
    load_dotenv()

    cfg = load_experiment_config()
    exp = cfg["experiment"]
    levels = exp["levels"]
    max_iter = exp["max_iterations"]
    runs = exp["runs_per_combination"]
    test_count = exp["test_count"]

    # Celkový počet kombinací
    total = len(cfg["llms"]) * len(cfg["apis"]) * len(levels) * runs
    print(f"\n🔬 EXPERIMENT: {exp['name']}")
    print(f"   {len(cfg['llms'])} LLMs × {len(cfg['apis'])} APIs × {len(levels)} levels × {runs} runs = {total} běhů")
    print(f"   Max iterací: {max_iter} | Testů na plán: {test_count}\n")

    all_results = []
    done = 0

    for llm_cfg in cfg["llms"]:
        api_key = os.environ.get(llm_cfg["api_key_env"])
        if not api_key:
            print(f"⚠️ {llm_cfg['api_key_env']} nenalezen, přeskakuji {llm_cfg['name']}")
            continue

        llm = create_llm(llm_cfg["provider"], api_key, llm_cfg["model"])
        print(f"\n🤖 LLM: {llm_cfg['name']}")

        for api_cfg in cfg["apis"]:
            print(f"\n📦 API: {api_cfg['name']}")

            for level in levels:
                for run_id in range(1, runs + 1):
                    done += 1
                    print(f"\n[{done}/{total}] ", end="")

                    try:
                        result = run_pipeline(
                            llm=llm,
                            llm_name=llm_cfg["name"],
                            api_cfg=api_cfg,
                            level=level,
                            run_id=run_id,
                            test_count=test_count,
                            max_iterations=max_iter,
                        )
                        all_results.append(result)
                    except Exception as e:
                        print(f"  ❌ CHYBA: {e}")
                        all_results.append({
                            "llm": llm_cfg["name"],
                            "api": api_cfg["name"],
                            "level": level,
                            "run_id": run_id,
                            "error": str(e),
                        })

            # Zastavit server po dokončení všech úrovní pro toto API
            stop_managed_server(api_cfg)

    # Uložit výsledky
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"experiment_{exp['name']}_{timestamp}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Shrnutí
    print(f"\n\n{'=' * 65}")
    print(f"  EXPERIMENT DOKONČEN | {len(all_results)} běhů | Výsledky: {path}")
    print(f"{'=' * 65}")

    ok = sum(1 for r in all_results if r.get("all_tests_passed"))
    err = sum(1 for r in all_results if "error" in r)
    print(f"  ✅ Passed: {ok} | ❌ Failed: {len(all_results) - ok - err} | 💥 Error: {err}")


if __name__ == "__main__":
    main()