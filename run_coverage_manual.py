"""
Automatizované měření code coverage (RQ2).

Spustí server s coverage, provede testy, zastaví server,
vygeneruje coverage JSON a zredukuje ho — vše v jednom příkazu.

Použití:
    # Jeden soubor:
    python run_coverage_manual.py outputs/test_generated_...__L0__run1__t0_4.py

    # Všechny testy v outputs/:
    python run_coverage_manual.py outputs/

    # Glob pattern:
    python run_coverage_manual.py "outputs/test_generated_*__L0__*.py"

    # Jen slim (bez spouštění testů):
    python run_coverage_manual.py --slim coverage_full.json coverage_slim.json

Předpokládá strukturu:
    ../bookstore-api/       — server s app.main:app
    ./outputs/              — vygenerované testy
    ./coverage_results/     — výstupní coverage JSONy (vytvoří se)
"""

import sys
import os
import glob
import json
import time
import signal
import subprocess
import re
from pathlib import Path

# ── Konfigurace ──────────────────────────────────────────────
BOOKSTORE_DIR = Path(__file__).resolve().parent.parent / "bookstore-api"
RESULTS_DIR = Path(__file__).resolve().parent / "coverage_results"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_STARTUP_TIMEOUT = 15  # sekund
SERVER_SHUTDOWN_WAIT = 3     # sekund po SIGINT


# ── Pomocné funkce ───────────────────────────────────────────

def tag_from_filename(test_file: str) -> str:
    """Extrahuje tag z názvu testovacího souboru pro pojmenování výstupu.

    test_generated_gemini-3_1-flash-lite-preview__bookstore__L0__run1__t0_4.py
    → gemini-3_1-flash-lite-preview__L0__run1
    """
    name = Path(test_file).stem  # bez .py
    # Odstraň prefix "test_generated_"
    name = re.sub(r"^test_generated_", "", name)
    # Parsuj části oddělené "__"
    parts = name.split("__")
    # parts: [model, bookstore, level, run, temp]
    if len(parts) >= 4:
        model, _, level, run = parts[0], parts[1], parts[2], parts[3]
        return f"{model}__{level}__{run}"
    return name


def wait_for_server(timeout: int = SERVER_STARTUP_TIMEOUT) -> bool:
    """Čeká až server odpoví na /health."""
    import urllib.request
    import urllib.error

    url = f"http://{SERVER_HOST}:{SERVER_PORT}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = urllib.request.urlopen(url, timeout=2)
            if r.status == 200:
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.5)
    return False


def reset_database():
    """Resetuje databázi přes /reset endpoint."""
    import urllib.request
    import urllib.error

    url = f"http://{SERVER_HOST}:{SERVER_PORT}/reset"
    try:
        req = urllib.request.Request(url, method="POST")
        r = urllib.request.urlopen(req, timeout=5)
        if r.status == 200:
            print("  ✅ Databáze resetována")
        else:
            print(f"  ⚠️  Reset vrátil {r.status}")
    except Exception as e:
        print(f"  ⚠️  Reset selhal ({e})")


def slim_coverage(input_path: str, output_path: str):
    """Zredukuje coverage JSON na per-function summary."""
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

        if filepath.endswith(("crud.py", "main.py")):
            funcs = {}
            for fname, finfo in fdata.get("functions", {}).items():
                if fname == "":
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
    print(f"  ✅ Slim: {orig:,} B → {new:,} B ({new/orig*100:.0f}%)")


# ── Hlavní logika ────────────────────────────────────────────

def run_single(test_file: str):
    """Spustí celý coverage cyklus pro jeden testovací soubor."""
    test_path = Path(test_file).resolve()
    tag = tag_from_filename(test_file)

    print(f"\n{'━' * 60}")
    print(f"📋 {tag}")
    print(f"   Soubor: {test_path.name}")
    print(f"{'━' * 60}")

    # 1. Vyčistit předchozí coverage data
    coverage_datafile = BOOKSTORE_DIR / ".coverage"
    if coverage_datafile.exists():
        coverage_datafile.unlink()

    # 2. Spustit server s coverage
    print("  🚀 Spouštím server s coverage...")
    popen_kwargs = {}
    if os.name != "nt":
        # Unix: nová session, aby SIGINT nešel na náš skript
        popen_kwargs["preexec_fn"] = os.setsid

    server_proc = subprocess.Popen(
        [
            sys.executable, "-m", "coverage", "run",
            "--source", "app",
            "-m", "uvicorn", "app.main:app",
            "--host", SERVER_HOST,
            "--port", str(SERVER_PORT),
        ],
        cwd=BOOKSTORE_DIR,
        **popen_kwargs,
    )

    try:
        # 3. Počkat na server
        if not wait_for_server():
            print("  ❌ Server nenaběhl! Kontroluj bookstore-api.")
            server_proc.kill()
            return None

        print("  ✅ Server běží")

        # 4. Reset databáze
        reset_database()

        # 5. Spustit testy
        print(f"  ▶ Spouštím testy...")
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v", "--tb=short", "--disable-warnings",
            ],
            capture_output=True,
            text=True,
        )

        # Výsledek testů
        passed = result.stdout.count(" PASSED")
        failed = result.stdout.count(" FAILED")
        errors = result.stdout.count(" ERROR")
        print(f"  📊 Testy: {passed} passed, {failed} failed, {errors} errors")

        if result.returncode != 0 and passed == 0:
            print("  ⚠️  Žádný test neprošel, coverage bude prázdné")
            # Detail chyby
            for line in result.stdout.splitlines()[-10:]:
                print(f"     {line}")

    finally:
        # 6. Zastavit server — graceful shutdown aby coverage uložil data
        print("  🛑 Zastavuji server...")
        if os.name != "nt":
            os.killpg(os.getpgid(server_proc.pid), signal.SIGINT)
        else:
            # Windows: pošleme CTRL_C_EVENT (graceful), ale náš skript
            # si ho dočasně ignoruje, aby se nezabil sám
            original_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.kill(server_proc.pid, signal.CTRL_C_EVENT)

        try:
            server_proc.wait(timeout=SERVER_SHUTDOWN_WAIT)
        except subprocess.TimeoutExpired:
            print("  ⚠️  Server se nezastavil včas, zabíjím...")
            server_proc.kill()
            server_proc.wait()
        finally:
            if os.name == "nt":
                # Obnovit původní SIGINT handler
                signal.signal(signal.SIGINT, original_handler)

    # 7. Vygenerovat coverage JSON
    coverage_full = BOOKSTORE_DIR / "coverage_full.json"
    print("  📄 Generuji coverage JSON...")
    gen_result = subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", str(coverage_full)],
        cwd=BOOKSTORE_DIR,
        capture_output=True,
        text=True,
    )

    if gen_result.returncode != 0 or not coverage_full.exists():
        print(f"  ❌ Coverage JSON se nevygeneroval!")
        print(f"     {gen_result.stderr.strip()}")
        return None

    # 8. Slim + uložit do results
    RESULTS_DIR.mkdir(exist_ok=True)
    output_file = RESULTS_DIR / f"coverage_{tag}.json"
    slim_coverage(str(coverage_full), str(output_file))

    # Přečíst total coverage pro summary
    with open(output_file, "r") as f:
        slim_data = json.load(f)
    total_pct = slim_data.get("totals", {}).get("percent_covered", 0)

    print(f"  🎯 Celkové pokrytí: {total_pct:.1f}%")
    print(f"  💾 Uloženo: {output_file.relative_to(Path.cwd())}")

    return {"tag": tag, "file": test_path.name, "coverage": total_pct, "passed": passed, "failed": failed}


def collect_test_files(path_arg: str) -> list[str]:
    """Rozpozná vstup — soubor, adresář, nebo glob pattern."""
    # Glob pattern
    if "*" in path_arg or "?" in path_arg:
        files = sorted(glob.glob(path_arg))
        return [f for f in files if f.endswith(".py")]

    p = Path(path_arg)

    # Jeden soubor
    if p.is_file():
        return [str(p)]

    # Adresář — najdi všechny test_generated_*.py
    if p.is_dir():
        files = sorted(p.glob("test_generated_*.py"))
        return [str(f) for f in files]

    print(f"❌ '{path_arg}' není soubor, adresář ani glob pattern.")
    sys.exit(1)


def print_summary(results: list[dict]):
    """Vytiskne souhrnnou tabulku."""
    if not results:
        return

    print(f"\n{'═' * 70}")
    print("📊 SOUHRNNÉ VÝSLEDKY")
    print(f"{'═' * 70}")
    print(f"{'Tag':<45} {'Cov%':>6} {'Pass':>5} {'Fail':>5}")
    print(f"{'─' * 45} {'─' * 6} {'─' * 5} {'─' * 5}")
    for r in results:
        print(f"{r['tag']:<45} {r['coverage']:>5.1f}% {r['passed']:>5} {r['failed']:>5}")
    print(f"{'─' * 45} {'─' * 6} {'─' * 5} {'─' * 5}")

    avg_cov = sum(r["coverage"] for r in results) / len(results)
    print(f"{'Průměr':<45} {avg_cov:>5.1f}%")
    print()


# ── CLI ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # --slim mód (zpětná kompatibilita)
    if sys.argv[1] == "--slim":
        if len(sys.argv) < 4:
            print("Použití: python run_coverage_manual.py --slim <input.json> <output.json>")
            sys.exit(1)
        slim_coverage(sys.argv[2], sys.argv[3])
        return

    # Sesbírat testovací soubory
    test_files = collect_test_files(sys.argv[1])

    if not test_files:
        print("❌ Žádné testovací soubory nenalezeny.")
        sys.exit(1)

    print(f"🔍 Nalezeno {len(test_files)} testovacích souborů")
    for f in test_files:
        print(f"   • {Path(f).name}")

    # Spustit postupně
    results = []
    for i, tf in enumerate(test_files, 1):
        print(f"\n[{i}/{len(test_files)}]", end="")
        r = run_single(tf)
        if r:
            results.append(r)

    # Souhrnná tabulka
    print_summary(results)

    # Uložit summary JSON
    if results:
        summary_path = RESULTS_DIR / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Summary uloženo: {summary_path.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()