"""
Ruční měření code coverage na Windows.
Spouští server pod coverage v aktuálním procesu,
takže atexit handler coverage spolehlivě zapíše data.

Použití:
    1. Otevři DVA terminály
    2. V prvním: cd C:\Projects\bookstore-api && .venv\Scripts\Activate.ps1
                 coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    3. V druhém: cd C:\Projects\vibe-testing-framework && .venv\Scripts\Activate.ps1
                 python run_coverage_manual.py outputs\test_generated_L0_run1.py
    4. V prvním terminálu stiskni Ctrl+C (zastaví server a zapíše coverage)
    5. V prvním: coverage json -o coverage.json
                 coverage report

Tento skript automatizuje krok 3 a pak vypíše instrukce.
"""
import sys
import os
import subprocess
import json


def main():
    if len(sys.argv) < 2:
        print("Použití: python run_coverage_manual.py <cesta_k_testům>")
        print("Příklad: python run_coverage_manual.py outputs\\test_generated_L0_run1.py")
        sys.exit(1)

    test_file = sys.argv[1]
    if not os.path.exists(test_file):
        print(f"❌ Soubor {test_file} nenalezen.")
        sys.exit(1)

    # Ověř, že server běží
    try:
        import requests
        r = requests.get("http://localhost:8000/health", timeout=2)
        if r.status_code != 200:
            raise Exception()
        print("✅ Server běží na localhost:8000")
    except Exception:
        print("❌ Server neběží! Spusť ho v jiném terminálu:")
        print("   cd C:\\Projects\\bookstore-api")
        print("   .venv\\Scripts\\Activate.ps1")
        print("   coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)

    # Spusť testy
    print(f"\nSpouštím testy: {test_file}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "--timeout=10"],
        text=True,
    )

    print(f"\n{'=' * 50}")
    print("HOTOVO! Teď v terminálu se serverem:")
    print("  1. Stiskni Ctrl+C (zastaví server, coverage zapíše data)")
    print("  2. Spusť: coverage json -o coverage.json")
    print("  3. Spusť: coverage report")
    print(f"{'=' * 50}")

    # Pokud coverage.json už existuje, zobraz výsledky
    api_dir = os.path.join("..", "bookstore-api")
    cov_json = os.path.join(api_dir, "coverage.json")
    if os.path.exists(cov_json):
        with open(cov_json, "r") as f:
            data = json.load(f)
        totals = data.get("totals", {})
        print(f"\n📊 Předchozí coverage výsledky:")
        print(f"   Line Coverage: {totals.get('percent_covered', 0):.1f}%")
        print(f"   Řádky: {totals.get('covered_lines', 0)}/{totals.get('num_statements', 0)}")


if __name__ == "__main__":
    main()