"""
Samostatné spuštění metrik na existujících vygenerovaných testech.

Použití:
    python run_metrics_only.py --file outputs/test_generated_X.py --plan outputs/test_plan_X.json
    python run_metrics_only.py --tag "gemini-2.5-flash__bookstore__L0__run1"
"""
import os
import json
import subprocess
import argparse

from prompts.phase5_metrics import (
    calculate_assertion_depth,
    calculate_endpoint_coverage,
    parse_test_validity_rate,
)

OUTPUTS_DIR = "outputs"


def find_openapi_for_tag(tag: str) -> str:
    """Zkusí najít správný openapi soubor podle tagu."""
    # Default
    default = os.path.join("inputs", "openapi.yaml")
    if os.path.exists(default):
        return default
    return None


def run_metrics(test_file: str, plan_file: str = None, openapi_path: str = None):
    if not os.path.exists(test_file):
        print(f"❌ Soubor {test_file} nenalezen.")
        return

    print(f"📄 Testy:  {test_file}")
    if plan_file:
        print(f"📋 Plán:   {plan_file}")

    # 1. Spuštění pytestu (server musí běžet!)
    print("\n🧪 Spouštím pytest...")
    result = subprocess.run(
        ["pytest", test_file, "-v", "--tb=short", "--disable-warnings"],
        capture_output=True, text=True, timeout=300,
    )
    output_log = result.stdout + "\n" + result.stderr

    # Uložit log
    log_path = test_file.replace(".py", "_rerun_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(output_log)
    print(f"📝 Log:    {log_path}")

    # 2. Metriky
    print(f"\n{'=' * 50}")
    print(f"  METRIKY")
    print(f"{'=' * 50}")

    tv = parse_test_validity_rate(output_log)
    print(f"  Test Validity:    {tv['validity_rate_pct']}% "
          f"({tv['tests_passed']} passed, {tv['tests_failed']} failed, "
          f"{tv['tests_errors']} errors / {tv['total_executed']} total)")

    ad = calculate_assertion_depth(test_file)
    print(f"  Assertion Depth:  {ad['assertion_depth']} avg "
          f"({ad['total_assertions']} asserts in {ad['total_test_functions']} tests)")

    if plan_file and os.path.exists(plan_file) and openapi_path and os.path.exists(openapi_path):
        with open(plan_file, "r", encoding="utf-8") as f:
            test_plan = json.load(f)
        ec = calculate_endpoint_coverage(openapi_path, test_plan)
        print(f"  Endpoint Cov:     {ec['endpoint_coverage_pct']}% "
              f"({ec['covered_endpoints']}/{ec['total_api_endpoints']})")
        if ec.get("uncovered_endpoints"):
            uncov = ec["uncovered_endpoints"][:5]
            print(f"    Nepokryté: {', '.join(uncov)}{'...' if len(ec['uncovered_endpoints']) > 5 else ''}")
    else:
        print(f"  Endpoint Cov:     ⏭️  (chybí plán nebo openapi)")

    # 3. Výpis selhávajících testů
    failed_lines = [l.strip() for l in output_log.split("\n")
                    if "FAILED" in l and "::" in l]
    if failed_lines:
        print(f"\n  ❌ Selhávající testy ({len(failed_lines)}):")
        for fl in failed_lines:
            print(f"    {fl}")

    print(f"{'=' * 50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metriky na existujících testech")
    parser.add_argument("--file", default=None, help="Cesta k test souboru")
    parser.add_argument("--plan", default=None, help="Cesta k JSON plánu")
    parser.add_argument("--openapi", default=None, help="Cesta k OpenAPI spec")
    parser.add_argument("--tag", default=None,
                        help='Tag ve formátu "llm__api__level__runN"')
    args = parser.parse_args()

    if args.file:
        test_f = args.file
        plan_f = args.plan
        openapi_f = args.openapi or os.path.join("inputs", "openapi.yaml")
    elif args.tag:
        test_f = os.path.join(OUTPUTS_DIR, f"test_generated_{args.tag}.py")
        plan_f = os.path.join(OUTPUTS_DIR, f"test_plan_{args.tag}.json")
        openapi_f = args.openapi or os.path.join("inputs", "openapi.yaml")
    else:
        # Najdi poslední vygenerovaný soubor
        files = sorted([f for f in os.listdir(OUTPUTS_DIR)
                        if f.startswith("test_generated_") and f.endswith(".py")])
        if not files:
            print("❌ Žádné test soubory v outputs/")
            exit(1)
        test_f = os.path.join(OUTPUTS_DIR, files[-1])
        plan_f = os.path.join(OUTPUTS_DIR, files[-1].replace("test_generated_", "test_plan_").replace(".py", ".json"))
        openapi_f = os.path.join("inputs", "openapi.yaml")
        print(f"ℹ️  Automaticky vybráno: {files[-1]}")

    run_metrics(test_f, plan_f, openapi_f)