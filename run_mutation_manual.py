"""
Ruční měření mutation score.

Použití:
    1. Spusť server v jiném terminálu:
       cd C:\\Projects\\bookstore-api
       .venv\\Scripts\\Activate.ps1
       python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

    2. Spusť tento skript:
       python run_mutation_manual.py outputs\\test_generated_L0_run1.py

Tento skript nepoužívá mutmut (ten potřebuje restartovat server pro
každého mutanta). Místo toho implementuje jednoduchý vlastní mutation
testing přímo v Pythonu.

Postup:
  - Načte crud.py, vytvoří mutanty (změní operátory, konstanty, podmínky)
  - Pro každého mutanta: přepíše crud.py, restartuje server, pustí testy
  - Pokud testy PROJDOU s mutantem = mutant přežil (špatné)
  - Pokud testy SELŽOU = mutant zabit (dobré)
  - Na konci obnoví originální crud.py
"""
import sys
import os
import re
import time
import shutil
import subprocess
import json

# Konfigurace
API_DIR = os.path.join("..", "bookstore-api")
CRUD_PATH = os.path.join(API_DIR, "app", "crud.py")
API_PYTHON = os.path.join(API_DIR, ".venv", "Scripts", "python.exe")
SERVER_CMD = ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
STARTUP_WAIT = 3.0


# ── Mutace ───────────────────────────────────────────────

MUTATIONS = [
    # (pattern, replacement, description)
    (r"status_code=404", "status_code=500", "404 → 500"),
    (r"status_code=409", "status_code=500", "409 → 500"),
    (r"status_code=400", "status_code=500", "400 → 500"),
    (r"if book_count > 0:", "if book_count > 999:", "delete guard: >0 → >999"),
    (r"if new_stock < 0:", "if new_stock < -999:", "stock check: <0 → <-999"),
    (r"if current_year - book\.published_year < 1:", "if False:", "discount year check disabled"),
    (r"round\(book\.price \* \(1 - data\.discount_percent / 100\), 2\)",
     "round(book.price * (1 + data.discount_percent / 100), 2)",
     "discount: subtract → add"),
    (r"\.ilike\(f\"%\{search\}%\"\)", '.ilike(f"NOMATCH{search}NOMATCH")', "search: break LIKE"),
    (r"avg = sum\(r\.rating for r in reviews\) / len\(reviews\)",
     "avg = 0.0", "rating: always return 0"),
    (r"book\.stock \+ quantity", "book.stock - quantity", "stock: add → subtract"),
]


def create_mutant(original: str, pattern: str, replacement: str) -> str | None:
    """Aplikuje jednu mutaci na zdrojový kód. Vrátí None pokud pattern nenalezen."""
    mutated, count = re.subn(pattern, replacement, original)
    if count == 0:
        return None
    return mutated


# ── Server management ────────────────────────────────────

def start_server():
    proc = subprocess.Popen(
        [API_PYTHON] + SERVER_CMD,
        cwd=os.path.abspath(API_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    time.sleep(STARTUP_WAIT)
    if proc.poll() is not None:
        return None
    # Ověř health
    try:
        import requests
        r = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if r.status_code == 200:
            return proc
    except Exception:
        pass
    proc.kill()
    return None


def stop_server(proc):
    if proc and proc.poll() is None:
        if os.name == "nt":
            proc.kill()
        else:
            proc.terminate()
        proc.wait(timeout=10)


def run_tests(test_file: str) -> tuple[bool, int]:
    """
    Spustí testy a vrátí (was_killed, num_passed).
    Mutant je killed pokud počet passing testů KLESNE oproti baseline.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file,
         "-v", "--tb=no", "--disable-warnings"],
        capture_output=True, text=True, timeout=600,
    )
    output = result.stdout + "\n" + result.stderr
    num_passed = len(re.findall(r' PASSED', output))
    return num_passed


# ── Main ─────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Použití: python run_mutation_manual.py <cesta_k_testům>")
        sys.exit(1)

    test_file = os.path.abspath(sys.argv[1])
    if not os.path.exists(test_file):
        print(f"❌ {test_file} nenalezen.")
        sys.exit(1)

    if not os.path.exists(CRUD_PATH):
        print(f"❌ {CRUD_PATH} nenalezen.")
        sys.exit(1)

    # Nejdřív ověř, že testy prochází BEZ mutací
    print("\n🔍 Ověřuji baseline (testy bez mutací)...")
    print("   Spouštím server s originálním kódem...")
    baseline_proc = start_server()
    if baseline_proc is None:
        print("❌ Server se nespustil. Konec.")
        sys.exit(1)

    try:
        baseline_result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file,
             "-v", "--tb=short", "--disable-warnings"],
            capture_output=True, text=True, timeout=600,
        )
        baseline_output = baseline_result.stdout + "\n" + baseline_result.stderr

        # Spočítej passing testy
        baseline_passed = len(re.findall(r' PASSED', baseline_output))
        baseline_failed = len(re.findall(r' FAILED', baseline_output))
        baseline_timeout = len(re.findall(r'Timeout', baseline_output))
        baseline_total = baseline_passed + baseline_failed + baseline_timeout

        print(f"   Baseline: {baseline_passed} passed, {baseline_failed} failed, "
              f"{baseline_timeout} timeout z {baseline_total}")

        if baseline_passed == 0:
            print("❌ Žádný test neprošel. Mutation testing nemá smysl.")
            sys.exit(1)

        if baseline_failed > 0 or baseline_timeout > 0:
            print(f"   ⚠️  {baseline_failed + baseline_timeout} testů selhává i bez mutací!")
            print(f"   Mutation testing poběží, ale bude porovnávat počet PASSING testů,")
            print(f"   ne jen returncode. Mutant je killed jen pokud SNÍŽÍ počet passing testů.")
    finally:
        stop_server(baseline_proc)
        time.sleep(1)

    # Záloha originálu
    backup_path = CRUD_PATH + ".bak"
    shutil.copy2(CRUD_PATH, backup_path)
    print(f"✅ Záloha: {backup_path}")

    with open(CRUD_PATH, "r", encoding="utf-8") as f:
        original_code = f.read()

    killed = 0
    survived = 0
    skipped = 0
    results = []

    try:
        for i, (pattern, replacement, desc) in enumerate(MUTATIONS):
            mutated = create_mutant(original_code, pattern, replacement)
            if mutated is None:
                print(f"  [{i+1}/{len(MUTATIONS)}] ⏭️  SKIP  {desc} (pattern nenalezen)")
                skipped += 1
                results.append({"mutation": desc, "result": "skipped"})
                continue

            # Zapiš mutanta
            with open(CRUD_PATH, "w", encoding="utf-8") as f:
                f.write(mutated)

            # Spusť server s mutantem
            proc = start_server()
            if proc is None:
                print(f"  [{i+1}/{len(MUTATIONS)}] ⚠️  ERROR {desc} (server nenaběhl)")
                results.append({"mutation": desc, "result": "error"})
                # Obnov originál pro další mutanta
                with open(CRUD_PATH, "w", encoding="utf-8") as f:
                    f.write(original_code)
                continue

            try:
                mutant_passed = run_tests(test_file)
                if mutant_passed < baseline_passed:
                    killed += 1
                    print(f"  [{i+1}/{len(MUTATIONS)}] ✅ KILLED {desc} "
                          f"({mutant_passed}/{baseline_passed} passed)")
                    results.append({"mutation": desc, "result": "killed",
                                    "passed": mutant_passed})
                else:
                    survived += 1
                    print(f"  [{i+1}/{len(MUTATIONS)}] ❌ SURVIVED {desc} "
                          f"({mutant_passed}/{baseline_passed} passed)")
                    results.append({"mutation": desc, "result": "survived",
                                    "passed": mutant_passed})
            except subprocess.TimeoutExpired:
                killed += 1
                print(f"  [{i+1}/{len(MUTATIONS)}] ⏱️  TIMEOUT {desc} (počítáno jako killed)")
                results.append({"mutation": desc, "result": "timeout"})
            finally:
                stop_server(proc)

            # Obnov originál
            with open(CRUD_PATH, "w", encoding="utf-8") as f:
                f.write(original_code)
            time.sleep(1)  # Pauza mezi mutanty

    finally:
        # Vždy obnov originál
        shutil.copy2(backup_path, CRUD_PATH)
        os.remove(backup_path)
        print(f"\n✅ Originální crud.py obnoven.")

    # Výsledky
    total = killed + survived
    score = round(killed / total * 100, 2) if total > 0 else 0.0

    print(f"\n{'=' * 50}")
    print(f"  MUTATION SCORE")
    print(f"{'=' * 50}")
    print(f"  Killed:   {killed}")
    print(f"  Survived: {survived}")
    print(f"  Skipped:  {skipped}")
    print(f"  Score:    {score}% ({killed}/{total})")
    print(f"{'=' * 50}")

    # Uložit do JSON
    output = {
        "mutation_score_pct": score,
        "mutants_killed": killed,
        "mutants_survived": survived,
        "mutants_skipped": skipped,
        "total_mutants": total,
        "baseline_passed": baseline_passed,
        "baseline_total": baseline_total,
        "details": results,
    }
    out_path = os.path.join("results", "mutation_score.json")
    os.makedirs("results", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n📊 Výsledky: {out_path}")


if __name__ == "__main__":
    main()