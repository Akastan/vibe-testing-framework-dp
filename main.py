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
    OUTPUTS_DIR, RESULTS_DIR, CONTEXT_LEVELS
)
from llm_provider import GeminiProvider
from prompts.phase1_context import analyze_context
from prompts.phase2_planning import generate_test_plan
from prompts.phase3_generation import generate_test_code
from prompts.phase4_validation import run_tests_and_validate
from prompts.phase5_metrics import (
    calculate_assertion_depth,
    calculate_endpoint_coverage,
    parse_test_validity_rate
)


def run_pipeline(llm, level: str = "L0", run_id: int = 1) -> dict:
    """
    Spustí jednu kompletní iteraci pipeline pro danou úroveň a vrátí metriky.

    Returns:
        dict s výsledky experimentu
    """
    # Dynamické názvy souborů
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
        # Pro budoucí L2–L4: přidat cesty k source_code, db_schema, existing_tests
    )

    # ── FÁZE 2: Plánování ────────────────────────────────
    print("\n[FÁZE 2] Generování testovacího plánu...")
    test_plan = generate_test_plan(context, llm, level=level)

    # Uložení plánu
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

    iteration = 0
    success = False
    output_log = ""

    while iteration < MAX_ITERATIONS and not success:
        iteration += 1
        print(f"\n  --- Iterace {iteration}/{MAX_ITERATIONS} ---")

        success, output_log = run_tests_and_validate(test_code, output_filename=output_filename)

        if success:
            print("  ✅ Všechny testy prošly!")
        else:
            if iteration < MAX_ITERATIONS:
                print("  ❌ Testy selhaly. Spouštím sebereflexi LLM...")
                test_code = generate_test_code(test_plan, context, llm, feedback=output_log)
            else:
                print(f"  ⚠️ Dosažen max. počet iterací ({MAX_ITERATIONS}).")

    elapsed = round(time.time() - start_time, 2)

    # ── FÁZE 5: Metriky ─────────────────────────────────
    print(f"\n[FÁZE 5] Výpočet metrik...")

    coverage = calculate_endpoint_coverage(OPENAPI_PATH, test_plan)
    assertions = calculate_assertion_depth(output_path)
    validity = parse_test_validity_rate(output_log)

    # Výpis
    print(f"\n{'─' * 50}")
    print(f"  VÝSLEDKY | {level} | Běh {run_id}")
    print(f"{'─' * 50}")
    print(f"  Endpoint Coverage:   {coverage['endpoint_coverage_pct']}% "
          f"({coverage['covered_endpoints']}/{coverage['total_api_endpoints']})")
    print(f"  Assertion Depth:     {assertions['assertion_depth']} asercí/test "
          f"({assertions['total_assertions']} v {assertions['total_test_functions']} testech)")
    print(f"  Test Validity Rate:  {validity['validity_rate_pct']}% "
          f"({validity['tests_passed']} prošlo z {validity['total_executed']})")
    print(f"  Feedback iterací:    {iteration}")
    print(f"  Celkový čas:         {elapsed}s")

    if "error" in assertions:
        print(f"  ⚠️ Assertion warning: {assertions['error']}")

    # Sestavení výsledku pro export
    result = {
        "timestamp": datetime.now().isoformat(),
        "model": llm.__class__.__name__,
        "model_name": getattr(llm, 'model_name', 'unknown'),
        "level": level,
        "run_id": run_id,
        "iterations_used": iteration,
        "all_tests_passed": success,
        "elapsed_seconds": elapsed,
        "metrics": {
            "endpoint_coverage": coverage,
            "assertion_depth": assertions,
            "test_validity": validity,
        },
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

    # Konfigurace modelu
    llm = GeminiProvider(api_key=gemini_key, model_name='gemini-3.1-flash-lite-preview')

    # === EXPERIMENT ===
    # Definuj, které úrovně chceš spustit a kolik běhů na každou
    levels_to_run = ["L0", "L1"]
    runs_per_level = 1  # Pro diplomku nastavíš na 3–5

    all_results = []

    for level in levels_to_run:
        for run_id in range(1, runs_per_level + 1):
            result = run_pipeline(llm=llm, level=level, run_id=run_id)
            all_results.append(result)

    # Uložení souhrnných výsledků
    save_results(all_results)

    print("\n" + "=" * 60)
    print("  EXPERIMENT DOKONČEN")
    print("=" * 60)