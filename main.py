"""
Vibe Testing Framework – Hlavní pipeline.
Spouští celý experiment: kontext → plán → kód → validace → metriky.
"""
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

from config import (
    MAX_ITERATIONS, OPENAPI_PATH, DOC_PATH,
    SOURCE_CODE_PATH, DB_SCHEMA_PATH, EXISTING_TESTS_PATH,
    OUTPUTS_DIR, RESULTS_DIR, CONTEXT_LEVELS, API_BASE_URL,
    API_SOURCE_DIR, API_PYTHON, API_SERVER_CMD,
    API_SOURCE_MODULE, MUTATION_TARGET, API_STARTUP_WAIT,
    RUN_CODE_COVERAGE, RUN_MUTATION_SCORE,
)
from llm_provider import GeminiProvider
from prompts.phase1_context import analyze_context
from prompts.phase2_planning import generate_test_plan
from prompts.phase3_generation import generate_test_code
from prompts.phase4_validation import run_tests_and_validate
from prompts.phase5_metrics import (
    calculate_all_metrics,
    IterationTracker,
)


def run_pipeline(llm, level: str = "L0", run_id: int = 1) -> dict:
    """Spustí jednu kompletní iteraci pipeline pro danou úroveň."""
    output_filename = f"test_generated_{level}_run{run_id}.py"
    plan_filename = f"test_plan_{level}_run{run_id}.json"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE | Model: {llm.__class__.__name__} | Úroveň: {level} | Běh: {run_id}")
    print(f"  Popis: {CONTEXT_LEVELS.get(level, 'Neznámá úroveň')}")
    print(f"{'=' * 60}")

    start_time = time.time()

    # ── FÁZE 1: Kontext ──────────────────────────────────
    print("\n[FÁZE 1] Načítání kontextu...")
    context = analyze_context(
        openapi_path=OPENAPI_PATH,
        doc_path=DOC_PATH,
        level=level,
        source_code_path=SOURCE_CODE_PATH,
        db_schema_path=DB_SCHEMA_PATH,
        existing_tests_path=EXISTING_TESTS_PATH,
    )

    # ── FÁZE 2: Plánování ────────────────────────────────
    print("\n[FÁZE 2] Generování testovacího plánu...")
    test_plan = generate_test_plan(context, llm, level=level)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(os.path.join(OUTPUTS_DIR, plan_filename), "w", encoding="utf-8") as f:
        json.dump(test_plan, f, indent=2, ensure_ascii=False)

    plan_test_count = sum(
        len(ep.get("test_cases", []))
        for ep in test_plan.get("test_plan", [])
    )
    print(f"  Plán obsahuje {plan_test_count} testovacích případů.")

    # ── FÁZE 3 + 4: Generování kódu + Feedback loop ─────
    print("\n[FÁZE 3+4] Generování kódu a iterativní validace...")
    test_code = generate_test_code(test_plan, context, llm)

    tracker = IterationTracker()
    iteration = 0
    success = False
    output_log = ""

    while iteration < MAX_ITERATIONS and not success:
        iteration += 1
        print(f"\n  --- Iterace {iteration}/{MAX_ITERATIONS} ---")

        success, output_log = run_tests_and_validate(
            test_code, output_filename=output_filename
        )

        # Zaznamenej metriky této iterace
        tracker.record_iteration(iteration, output_log, output_path)

        if success:
            print("  ✅ Všechny testy prošly!")
        else:
            if iteration < MAX_ITERATIONS:
                print("  ❌ Testy selhaly. Spouštím sebereflexi LLM...")
                test_code = generate_test_code(
                    test_plan, context, llm, feedback=output_log
                )
            else:
                print(f"  ⚠️ Dosažen max. počet iterací ({MAX_ITERATIONS}).")

    elapsed = round(time.time() - start_time, 2)

    # ── FÁZE 5: Metriky ─────────────────────────────────
    print(f"\n[FÁZE 5] Výpočet metrik...")

    api_dir = os.path.abspath(API_SOURCE_DIR) if os.path.isdir(API_SOURCE_DIR) else None
    if not api_dir and (RUN_CODE_COVERAGE or RUN_MUTATION_SCORE):
        print(f"  ⚠️ API adresář ({API_SOURCE_DIR}) nenalezen.")
        print(f"     Code coverage a mutation score budou přeskočeny.")

    metrics = calculate_all_metrics(
        test_file=output_path,
        openapi_path=OPENAPI_PATH,
        test_plan=test_plan,
        pytest_output=output_log,
        api_source_dir=api_dir,
        api_python=API_PYTHON,
        server_cmd=API_SERVER_CMD,
        source_module=API_SOURCE_MODULE,
        run_coverage=RUN_CODE_COVERAGE and api_dir is not None,
        run_mutation=RUN_MUTATION_SCORE and api_dir is not None,
        mutation_paths=MUTATION_TARGET,
        startup_wait=API_STARTUP_WAIT,
        iteration_tracker=tracker,
    )

    # ── Výpis ────────────────────────────────────────────
    cov = metrics["endpoint_coverage"]
    ad = metrics["assertion_depth"]
    tv = metrics["test_validity"]
    cc = metrics.get("code_coverage", {})
    ms = metrics.get("mutation_score", {})
    delta = metrics.get("iteration_delta", {})

    print(f"\n{'─' * 55}")
    print(f"  VÝSLEDKY | {level} | Běh {run_id}")
    print(f"{'─' * 55}")
    print(f"  Test Validity Rate:  {tv['validity_rate_pct']}% "
          f"({tv['tests_passed']} prošlo z {tv['total_executed']})")
    print(f"  Endpoint Coverage:   {cov['endpoint_coverage_pct']}% "
          f"({cov['covered_endpoints']}/{cov['total_api_endpoints']})")
    print(f"  Assertion Depth:     {ad['assertion_depth']} asercí/test "
          f"({ad['total_assertions']} v {ad['total_test_functions']} testech)")

    if not cc.get("skipped"):
        if "error" in cc:
            print(f"  Code Coverage:       ❌ {cc['error']}")
        else:
            print(f"  Code Coverage:       {cc.get('line_coverage_pct', 'N/A')}% "
                  f"({cc.get('covered_lines', '?')}/{cc.get('total_statements', '?')} řádků)")
    else:
        print(f"  Code Coverage:       přeskočeno")

    if not ms.get("skipped"):
        if "error" in ms:
            print(f"  Mutation Score:      ❌ {ms['error']}")
        else:
            print(f"  Mutation Score:      {ms.get('mutation_score_pct', 'N/A')}% "
                  f"({ms.get('mutants_killed', '?')}/{ms.get('total_mutants', '?')} zabitých)")
    else:
        print(f"  Mutation Score:      přeskočeno")

    d = delta.get("delta", {})
    if d:
        print(f"\n  --- Iteration Delta (iter 1 → {delta.get('iterations_total', '?')}) ---")
        print(f"  Validity Rate:  {d.get('validity_rate_delta', 0):+.2f} pp")
        print(f"  Tests Passed:   {d.get('tests_passed_delta', 0):+d}")
        print(f"  Tests Failed:   {d.get('tests_failed_delta', 0):+d}")
        print(f"  Assert. Depth:  {d.get('assertion_depth_delta', 0):+.2f}")
    elif delta.get("note"):
        print(f"\n  Iteration Delta: {delta['note']}")

    print(f"\n  Feedback iterací:    {iteration}")
    print(f"  Celkový čas:         {elapsed}s")

    result = {
        "timestamp": datetime.now().isoformat(),
        "model": llm.__class__.__name__,
        "model_name": getattr(llm, 'model_name', 'unknown'),
        "level": level,
        "run_id": run_id,
        "iterations_used": iteration,
        "all_tests_passed": success,
        "elapsed_seconds": elapsed,
        "metrics": metrics,
        "plan_test_count": plan_test_count,
        "output_filename": output_filename,
        "plan_filename": plan_filename,
    }

    return result


def save_results(results: list[dict]):
    """Uloží všechny výsledky experimentu do JSON souboru."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"experiment_{timestamp}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Výsledky uloženy do: {path}")


if __name__ == "__main__":
    load_dotenv()

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY nenalezen v .env souboru.")

    llm = GeminiProvider(api_key=gemini_key, model_name='gemini-3.1-flash-lite-preview')

    # === EXPERIMENT ===
    levels_to_run = ["L0"]  # Pro testování metrik; pro experiment ["L0","L1","L2","L3","L4"]
    runs_per_level = 1

    all_results = []

    for level in levels_to_run:
        for run_id in range(1, runs_per_level + 1):
            result = run_pipeline(llm=llm, level=level, run_id=run_id)
            all_results.append(result)

    save_results(all_results)

    print("\n" + "=" * 60)
    print("  EXPERIMENT DOKONČEN")
    print("=" * 60)