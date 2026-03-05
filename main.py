import os
import json
from dotenv import load_dotenv

from llm_provider import GeminiProvider
from prompts.phase1_context import analyze_context
from prompts.phase2_planning import generate_test_plan
from prompts.phase3_generation import generate_test_code
from prompts.phase4_validation import run_tests_and_validate
from prompts.phase5_metrics import calculate_assertion_depth, calculate_endpoint_coverage, parse_test_validity_rate

MAX_ITERATIONS = 5


def run_vibe_testing_pipeline(llm, level="L0", output_filename="test_generated_L0.py",
                              plan_filename="test_plan_L0.json"):
    print(f"\n=======================================================")
    print(f"=== Spouštím Vibe Testing Framework | Úroveň: {level} ===")
    print(f"=======================================================\n")

    openapi_path = "inputs/openapi.yaml"
    doc_path = "inputs/documentation.md"

    # 1. Analýza kontextu
    print(f"[FÁZE 1] Načítání kontextu (Úroveň {level})...")
    context = analyze_context(openapi_path, doc_path, level=level)

    # 2. Vytvoření testovacího plánu
    print("\n[FÁZE 2] Generování testovacího plánu (Reasoning)...")
    test_plan = generate_test_plan(context, llm)

    # Uložení plánu do souboru pro případnou analýzu v diplomce
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{plan_filename}", "w", encoding="utf-8") as f:
        json.dump(test_plan, f, indent=2, ensure_ascii=False)

    # 3. Generování kódu
    print("\n[FÁZE 3] Generování spustitelných Python testů...")
    test_code = generate_test_code(test_plan, context, llm)

    # 4. Exekuce a sebereflexní smyčka
    print("\n[FÁZE 4] Validace a iterace (Feedback loop)...")
    iteration = 0
    success = False
    output_log = ""

    while iteration < MAX_ITERATIONS and not success:
        iteration += 1
        print(f"\n--- Iterace {iteration}/{MAX_ITERATIONS} ---")

        # Validace s dynamickým názvem souboru pro danou úroveň
        success, output_log = run_tests_and_validate(test_code, output_filename=output_filename)

        if success:
            print("✅ Všechny testy prošly úspěšně!")
        else:
            print("❌ Testy selhaly. Spouštím sebereflexi LLM...")
            test_code = generate_test_code(test_plan, context, llm, feedback=output_log)

    if not success:
        print(f"\n⚠️ Dosažen maximální počet iterací ({MAX_ITERATIONS}). Testy nejsou plně funkční.")

    # --- VÝPOČET METRIK ---
    print(f"\n=== [VÝSLEDKY EXPERIMENTU A METRIKY - ÚROVEŇ {level}] ===")

    coverage_metrics = calculate_endpoint_coverage(openapi_path, test_plan)
    print(f"1. Endpoint Coverage: {coverage_metrics.get('endpoint_coverage_pct', 0)}% "
          f"({coverage_metrics.get('covered_endpoints', 0)} z {coverage_metrics.get('total_api_endpoints', 0)} endpointů)")

    file_path = f"outputs/{output_filename}"
    assertion_metrics = calculate_assertion_depth(file_path)
    print(f"2. Assertion Depth: {assertion_metrics.get('assertion_depth', 0.0)} asercí na test "
          f"(Zjištěno {assertion_metrics.get('total_assertions', 0)} asercí v {assertion_metrics.get('total_test_functions', 0)} testech)")
    if "error" in assertion_metrics:
        print(f"   -> Varování: {assertion_metrics['error']}")

    validity_metrics = parse_test_validity_rate(output_log)
    # Opravené klíče pro správný výpis
    passed = validity_metrics.get('passed', 0)
    failed = validity_metrics.get('failed', 0)
    total = validity_metrics.get('total', passed + failed)  # Pokud by total chyběl, spočítá ho

    print(f"3. Test Validity Rate: {validity_metrics.get('validity_rate_pct', 0)}% "
          f"({passed} úspěšných z {total} celkem)")


if __name__ == "__main__":
    # Načtení klíčů z .env
    load_dotenv()

    # 1. Konfigurace modelu přes našeho Providera
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY nenalezen v prostředí (nebo .env souboru).")

    # Použij model, který ti fungoval (např. 2.5 flash)
    #llm_provider = GeminiProvider(api_key=gemini_key, model_name='gemini-2.5-flash')
    llm_provider = GeminiProvider(api_key=gemini_key, model_name='gemini-3.1-flash-lite-preview')

    # --- AUTOMATIZOVANÝ EXPERIMENT PRO DIPLOMKU ---

    # BĚH 1: Úroveň L0 (Pouze specifikace)
    run_vibe_testing_pipeline(
        llm=llm_provider,
        level="L0",
        output_filename="test_generated_L0.py",
        plan_filename="test_plan_L0.json"
    )

    print("\n\n" + "*" * 70)
    print("⏳ PŘEPÍNÁM KONTEXT NA ÚROVEŇ L1 (OPENAPI + BYZNYS DOKUMENTACE) ⏳")
    print("*" * 70 + "\n\n")

    # BĚH 2: Úroveň L1 (Specifikace + Dokumentace)
    run_vibe_testing_pipeline(
        llm=llm_provider,
        level="L1",
        output_filename="test_generated_L1.py",
        plan_filename="test_plan_L1.json"
    )