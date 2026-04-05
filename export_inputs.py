"""
Centrální export vstupních dat pro vibe-testing-framework.

Stahuje kontext (L0-L4) z externích lokálních repozitářů
a ukládá do složky inputs/ uvnitř frameworku.

OBĚ API běží na portu 8000 — exportuj je PO JEDNOM:
    python export_inputs.py bookstore      # bookstore musí běžet na :8000
    python export_inputs.py astroops       # astroops musí běžet na :8000
    python export_inputs.py all            # exportuj jen soubory (bez OpenAPI)
    python export_inputs.py                # interaktivní výběr
"""

import os
import sys
import shutil
import requests
import yaml

APIS = [
    {
        "id": "api1_bookstore",
        "short": "bookstore",
        "server_url": "http://localhost:8000",
        "repo_path": "../bookstore-api",
        "files": {
            "l1_docs": "docs/documentation.md",
            "l2_source": [
                "app/main.py",
                "app/crud.py",
                "app/schemas.py",
                "app/models.py",
            ],
            "l3_schema": "db_schema.sql",
            "l4_tests": "tests/test_existing.py",
        }
    },
    {
        "id": "api2_astroops",
        "short": "astroops",
        "server_url": "http://localhost:8000",
        "repo_path": "../astroops-api",
        "files": {
            "l1_docs": "docs/documentation.md",
            "l2_source": [
                "app/main.py",
                "app/crud.py",
                "app/schemas.py",
                "app/models.py",
            ],
            "l3_schema": "db_schema.sql",
            "l4_tests": "tests/test_existing.py",
        }
    }
]

FRAMEWORK_INPUTS = "inputs"


def export_openapi(api_cfg, output_dir):
    """L0: Stáhne OpenAPI spec z běžícího serveru."""
    url = f"{api_cfg['server_url']}/openapi.json"
    path = os.path.join(output_dir, "openapi.yaml")

    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        spec = r.json()

        # Ověř že to je správné API
        title = spec.get("info", {}).get("title", "")
        print(f"  ℹ️  API title: {title}")

        path_count = len(spec.get("paths", {}))
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
        print(f"  ✅ L0: OpenAPI spec ({path_count} cest) → {path}")

    except requests.exceptions.RequestException as e:
        print(f"  ❌ L0: Nelze stáhnout OpenAPI z {url}. Běží server? (Chyba: {e})")


def export_file(api_cfg, file_key, output_name, output_dir, step_name):
    """L1, L3, L4: Zkopíruje jeden soubor z repozitáře."""
    src = os.path.join(api_cfg["repo_path"], api_cfg["files"][file_key])
    dst = os.path.join(output_dir, output_name)

    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  ✅ {step_name}: Zkopírováno ({size:,} B) → {dst}")
    else:
        print(f"  ⚠️  {step_name}: Nenalezeno v {src} — přeskakuji")


def export_source_code(api_cfg, output_dir):
    """L2: Spojí specifikované zdrojové kódy do jednoho souboru."""
    dst = os.path.join(output_dir, "source_code.py")
    total_lines = 0
    files_processed = 0

    with open(dst, "w", encoding="utf-8") as out:
        for rel_path in api_cfg["files"]["l2_source"]:
            fpath = os.path.join(api_cfg["repo_path"], rel_path)

            if not os.path.exists(fpath):
                print(f"  ⚠️  L2: Soubor {fpath} neexistuje — přeskakuji")
                continue

            out.write(f"\n# ═══ FILE: {rel_path} ═══\n\n")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                out.write(content)
                total_lines += content.count("\n")
            out.write("\n")
            files_processed += 1

    if files_processed > 0:
        print(f"  ✅ L2: Zdrojový kód ({files_processed} souborů, ~{total_lines} řádků) → {dst}")
    else:
        print(f"  ❌ L2: Žádné zdrojové soubory nenalezeny pro {api_cfg['id']}.")


def export_db_schema(api_cfg, output_dir):
    """L3: Zkopíruje DB schéma. Pokud neexistuje, pokusí se vygenerovat z SQLite."""
    src = os.path.join(api_cfg["repo_path"], api_cfg["files"]["l3_schema"])
    dst = os.path.join(output_dir, "db_schema.sql")

    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  ✅ L3: DB schéma ({size:,} B) → {dst}")
        return

    import glob
    import sqlite3

    db_files = glob.glob(os.path.join(api_cfg["repo_path"], "*.db"))
    if not db_files:
        print(f"  ⚠️  L3: Nenalezeno {src} ani žádný .db soubor — přeskakuji")
        return

    db_path = db_files[0]
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name")
        schemas = [row[0] for row in cursor.fetchall()]
        conn.close()

        with open(dst, "w", encoding="utf-8") as f:
            f.write(f"-- Auto-exported from {os.path.basename(db_path)}\n\n")
            for s in schemas:
                f.write(f"{s};\n\n")
        print(f"  ✅ L3: DB schéma vygenerováno z {os.path.basename(db_path)} ({len(schemas)} tabulek) → {dst}")
    except Exception as e:
        print(f"  ❌ L3: Chyba při exportu schématu z {db_path}: {e}")


def process_api(api, skip_openapi=False):
    """Exportuje vstupy pro jedno API."""
    api_id = api["id"]
    print(f"\n🚀 Zpracovávám: {api_id}")

    output_dir = os.path.join(FRAMEWORK_INPUTS, api_id)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(api["repo_path"]):
        print(f"  ❌ Složka repozitáře {api['repo_path']} nenalezena! Přeskakuji.\n")
        return

    if not skip_openapi:
        export_openapi(api, output_dir)
    else:
        print(f"  ⏭️  L0: OpenAPI přeskočeno (server neběží)")

    export_file(api, "l1_docs", "documentation.md", output_dir, "L1")
    export_source_code(api, output_dir)
    export_db_schema(api, output_dir)
    export_file(api, "l4_tests", "existing_tests.py", output_dir, "L4")

    print(f"{'─' * 40}")


def print_structure():
    """Vypíše strukturu výstupních souborů."""
    print(f"\nVýstupní struktura:")
    for api in APIS:
        d = os.path.join(FRAMEWORK_INPUTS, api["id"])
        if os.path.exists(d):
            files = os.listdir(d)
            print(f"  {d}/")
            for f in sorted(files):
                size = os.path.getsize(os.path.join(d, f))
                print(f"    {f} ({size:,} B)")


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None

    print(f"\n📦 Export vstupů do '{FRAMEWORK_INPUTS}/'\n")

    if arg in ("bookstore", "astroops"):
        # Export jednoho API (server musí běžet na :8000)
        api = next(a for a in APIS if a["short"] == arg)
        print(f"⚠️  Ujisti se, že {arg} server běží na {api['server_url']}")
        process_api(api, skip_openapi=False)

    elif arg == "all":
        # Export souborů bez OpenAPI (servery nemusí běžet)
        print("📁 Export souborů (bez OpenAPI — servery nemusí běžet)")
        for api in APIS:
            process_api(api, skip_openapi=True)

    elif arg == "files":
        # Alias pro "all"
        print("📁 Export souborů (bez OpenAPI — servery nemusí běžet)")
        for api in APIS:
            process_api(api, skip_openapi=True)

    else:
        # Interaktivní
        print("Obě API používají port 8000 — exportuj po jednom:\n")
        print("  python export_inputs.py bookstore   # bookstore běží na :8000")
        print("  python export_inputs.py astroops    # astroops běží na :8000")
        print("  python export_inputs.py files       # jen soubory (bez OpenAPI)")
        print()

        choice = input("Co chceš exportovat? [bookstore/astroops/files]: ").strip().lower()
        if choice in ("bookstore", "astroops"):
            api = next(a for a in APIS if a["short"] == choice)
            process_api(api, skip_openapi=False)
        elif choice in ("files", "all"):
            for api in APIS:
                process_api(api, skip_openapi=True)
        else:
            print("❌ Neznámá volba.")
            sys.exit(1)

    print_structure()
    print(f"\n🎉 Export dokončen.")