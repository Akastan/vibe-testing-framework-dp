import os
import subprocess
from prompts.phase5_metrics import calculate_assertion_depth, parse_test_validity_rate


def run_just_metrics():
    # Cesta k tvému opravenému souboru s testy
    # (pokud ho máš v kořenové složce, nech to takto, jinak uprav na "outputs/test_generated.py")
    #test_file = "outputs/test_generated.py"
    #test_file = "outputs/test_generated_L0.py"
    test_file = "outputs/test_generated_L1.py"

    if not os.path.exists(test_file):
        print(f"❌ Soubor {test_file} nebyl nalezen.")
        return

    print(f"Spouštím existující testy ze souboru {test_file} a počítám metriky...")

    # 1. Spuštění pytestu pro získání logu (Test Validity Rate)
    # Parametr --disable-warnings skryje zbytečný spam a nechá čisté výsledky
    result = subprocess.run(
        ["pytest", test_file, "-v", "--tb=short", "--disable-warnings"],
        capture_output=True,
        text=True
    )

    output_log = result.stdout + "\n" + result.stderr
    print("\n--- Výstup z Pytestu ---")
    print(output_log)
    print("------------------------\n")

    # 2. Výpočet metrik
    print("=== [VÝSLEDKY EXPERIMENTU A METRIKY] ===")

    # Metrika: Assertion Depth
    assertion_metrics = calculate_assertion_depth(test_file)
    print(f"1. Assertion Depth: {assertion_metrics.get('assertion_depth', 0.0)} asercí na test "
          f"(Zjištěno {assertion_metrics.get('total_assertions', 0)} asercí v {assertion_metrics.get('total_test_functions', 0)} testech)")
    if "error" in assertion_metrics:
        print(f"   -> Varování: {assertion_metrics['error']}")

    # Metrika: Test Validity Rate
    validity_metrics = parse_test_validity_rate(output_log)
    print(f"2. Test Validity Rate: {validity_metrics.get('validity_rate_pct', 0)}% "
          f"({validity_metrics.get('tests_passed', 0)} prošlo z celkových {validity_metrics.get('total_executed', 0)} spuštěných testů)")


if __name__ == "__main__":
    run_just_metrics()