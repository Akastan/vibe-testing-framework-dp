"""
Samostatné spuštění metrik na již existujících vygenerovaných testech.
Užitečné pro re-evaluaci bez nutnosti znovu volat LLM.

Použití:
    python run_metrics_only.py                          # default: L0, run1
    python run_metrics_only.py --level L1 --run 2       # konkrétní soubor
    python run_metrics_only.py --file outputs/custom.py --plan outputs/custom_plan.json
"""
import os
import json
import subprocess
import argparse

from config import OPENAPI_PATH, OUTPUTS_DIR
from prompts.phase5_metrics import (
    calculate_assertion_depth,
    calculate_endpoint_coverage,
    parse_test_validity_rate
)


def run_metrics(test_file: str, plan_file: str = None):
    """Spustí pytest a vypočte všechny metriky."""
    if not os.path.exists(test_file):
        print(f"❌ Soubor {test_file} nebyl nalezen.")
        return

    print(f"Spouštím testy: {test_file}")
    if plan_file:
        print(f"Testovací plán: {plan_file}")

    # 1. Spuštění pytestu
    result = subprocess.run(
        ["pytest", test_file, "-v", "--tb=short", "--disable-warnings"],
        capture_output=True,
        text=True,
        timeout=120
    )

    output_log = result.stdout + "\n" + result.stderr
    print("\n--- Výstup pytestu ---")
    print(output_log)
    print("─" * 50)

    # 2. Metriky
    print("\n=== METRIKY ===\n")

    # Assertion Depth
    ad = calculate_assertion_depth(test_file)
    print(f"1. Assertion Depth:    {ad['assertion_depth']} asercí/test "
          f"({ad['total_assertions']} asercí v {ad['total_test_functions']} testech)")
    if "error" in ad:
        print(f"   ⚠️ {ad['error']}")

    # Test Validity Rate
    tv = parse_test_validity_rate(output_log)
    print(f"2. Test Validity Rate: {tv['validity_rate_pct']}% "
          f"({tv['tests_passed']} prošlo, {tv['tests_failed']} selhalo, "
          f"{tv['tests_errors']} chyb z {tv['total_executed']} celkem)")

    # Endpoint Coverage (potřebuje test plan JSON)
    if plan_file and os.path.exists(plan_file):
        with open(plan_file, "r", encoding="utf-8") as f:
            test_plan = json.load(f)
        ec = calculate_endpoint_coverage(OPENAPI_PATH, test_plan)
        print(f"3. Endpoint Coverage:  {ec['endpoint_coverage_pct']}% "
              f"({ec['covered_endpoints']}/{ec['total_api_endpoints']})")
        if ec.get("uncovered_endpoints"):
            print(f"   Nepokryté: {', '.join(ec['uncovered_endpoints'][:5])}...")
    else:
        print("3. Endpoint Coverage:  ⚠️ Nebyl nalezen testovací plán (JSON), přeskakuji.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spuštění metrik na existujících testech")
    parser.add_argument("--level", default="L0", help="Úroveň kontextu (L0, L1, ...)")
    parser.add_argument("--run", type=int, default=1, help="Číslo běhu")
    parser.add_argument("--file", default=None, help="Přímá cesta k test souboru")
    parser.add_argument("--plan", default=None, help="Přímá cesta k JSON plánu")
    args = parser.parse_args()

    if args.file:
        test_f = args.file
        plan_f = args.plan
    else:
        test_f = os.path.join(OUTPUTS_DIR, f"test_generated_{args.level}_run{args.run}.py")
        plan_f = os.path.join(OUTPUTS_DIR, f"test_plan_{args.level}_run{args.run}.json")

    run_metrics(test_f, plan_f)