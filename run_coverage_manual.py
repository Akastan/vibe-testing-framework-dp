"""
Ruční měření code coverage (RQ2).

Použití:
    1. Terminál 1 (bookstore-api):
       coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    2. Terminál 2 (vibe-testing-framework):
       python run_coverage_manual.py outputs/test_generated_L0_run1.py
    3. Terminál 1: Ctrl+C, pak:
       coverage json -o coverage_full.json
    4. Terminál 2 (zredukuje JSON):
       python run_coverage_manual.py --slim ../bookstore-api/coverage_full.json coverage_L0_run1.json
"""
import sys, os, subprocess, json


def slim_coverage(input_path: str, output_path: str):
    """Zredukuje coverage JSON na per-function summary pro RQ2.

    Původní: ~3000+ řádků (per-line executed_lines, missing_lines, classes...)
    Výstup:  ~100 řádků (per-function % pro crud.py + main.py, totals)
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    slim = {
        "meta": {
            "timestamp": data.get("meta", {}).get("timestamp"),
            "version": data.get("meta", {}).get("version"),
        },
        "files": {},
        "totals": data.get("totals", {}),
    }

    for filepath, fdata in data.get("files", {}).items():
        file_summary = {
            "covered_lines": fdata["summary"]["covered_lines"],
            "num_statements": fdata["summary"]["num_statements"],
            "percent_covered": round(fdata["summary"]["percent_covered"], 2),
        }

        # Per-function coverage jen pro crud.py a main.py (tam je business logika)
        if filepath.endswith(("crud.py", "main.py")):
            funcs = {}
            for fname, finfo in fdata.get("functions", {}).items():
                if fname == "":  # module-level code
                    continue
                funcs[fname] = {
                    "covered": finfo["summary"]["covered_lines"],
                    "total": finfo["summary"]["num_statements"],
                    "pct": round(finfo["summary"]["percent_covered"], 1),
                }
            file_summary["functions"] = funcs

        slim["files"][filepath] = file_summary

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(slim, f, indent=2, ensure_ascii=False)

    orig = os.path.getsize(input_path)
    new = os.path.getsize(output_path)
    print(f"✅ {input_path} ({orig:,} B) → {output_path} ({new:,} B) — {new/orig*100:.0f}% velikosti")


def run_tests(test_file: str):
    """Spustí testy proti běžícímu serveru s coverage."""
    import requests

    try:
        r = requests.get("http://localhost:8000/health", timeout=2)
        if r.status_code != 200:
            raise Exception()
        print("✅ Server běží na localhost:8000")
    except Exception:
        print("❌ Server neběží! Spusť ho v jiném terminálu:")
        print("   cd ../bookstore-api")
        print("   coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)

    print("🔄 Resetuji databázi...")
    try:
        r = requests.post("http://localhost:8000/reset", timeout=5)
        if r.status_code == 200:
            print("✅ Databáze resetována")
        else:
            print(f"⚠️  Reset vrátil {r.status_code}")
    except Exception as e:
        print(f"⚠️  Reset selhal ({e})")

    print(f"\n▶ Spouštím testy: {test_file}")
    subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "--disable-warnings"],
        text=True,
    )

    print(f"\n{'=' * 50}")
    print("HOTOVO! V terminálu se serverem:")
    print("  1. Ctrl+C (zastaví server)")
    print("  2. coverage json -o coverage_full.json")
    print(f"  3. python run_coverage_manual.py --slim ../bookstore-api/coverage_full.json coverage_TAG.json")
    print(f"{'=' * 50}")


def main():
    if len(sys.argv) < 2:
        print("Použití:")
        print("  python run_coverage_manual.py <test_file>          — spustí testy")
        print("  python run_coverage_manual.py --slim <in> <out>    — zredukuje coverage JSON")
        sys.exit(1)

    if sys.argv[1] == "--slim":
        if len(sys.argv) < 4:
            print("Použití: python run_coverage_manual.py --slim <input.json> <output.json>")
            sys.exit(1)
        slim_coverage(sys.argv[2], sys.argv[3])
    else:
        test_file = sys.argv[1]
        if not os.path.exists(test_file):
            print(f"❌ Soubor {test_file} nenalezen.")
            sys.exit(1)
        run_tests(test_file)


if __name__ == "__main__":
    main()