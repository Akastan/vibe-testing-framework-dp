"""
Centrální export vstupních dat pro vibe-testing-framework (Bookstore API).

Stahuje kontext (L0-L4) z lokálního repozitáře a ukládá do složky inputs/bookstore.
Pokud není repozitář nalezen na výchozí cestě, zeptá se na ni.
"""

import os
import sys
import shutil
import requests
import yaml
import glob
import sqlite3

SERVER_URL = "http://localhost:8000"
FRAMEWORK_INPUTS = os.path.join("inputs", "api1_bookstore")

FILES_TO_EXPORT = {
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


def get_repo_path() -> str:
    """Zjistí cestu k repozitáři. Zkusí výchozí, jinak se zeptá uživatele."""
    default_path = "../bookstore-api"

    if os.path.isdir(default_path):
        print(f"✅ Nalezena výchozí složka repozitáře: {default_path}")
        return default_path

    print(f"⚠️ Výchozí složka '{default_path}' nebyla nalezena.")
    while True:
        user_path = input("Najděte složku bookstore-api (zadejte absolutní nebo relativní cestu, např. C:/Projekty/bookstore-api): ").strip()

        # Odstranění uvozovek, pokud uživatel přetáhl složku do terminálu
        user_path = user_path.strip("\"'")

        if not user_path:
            print("❌ Cesta nesmí být prázdná. (Pro zrušení stiskněte Ctrl+C)")
            continue

        if os.path.isdir(user_path):
            print(f"✅ Složka nalezena: {user_path}")
            return user_path
        else:
            print(f"❌ Složka '{user_path}' neexistuje. Zkuste to prosím znovu.")


def export_openapi(output_dir):
    """L0: Stáhne OpenAPI spec z běžícího serveru."""
    url = f"{SERVER_URL}/openapi.json"
    path = os.path.join(output_dir, "openapi.yaml")

    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        spec = r.json()

        title = spec.get("info", {}).get("title", "")
        print(f"  ℹ️  API title: {title}")

        path_count = len(spec.get("paths", {}))
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
        print(f"  ✅ L0: OpenAPI spec ({path_count} cest) → {path}")

    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  L0: Nelze stáhnout OpenAPI z {url}. Běží server? (Chyba: {e})")
        print("      Pokračuji bez L0 (OpenAPI).")


def export_file(repo_path, file_key, output_name, output_dir, step_name):
    """L1, L3, L4: Zkopíruje jeden soubor z repozitáře."""
    src = os.path.join(repo_path, FILES_TO_EXPORT[file_key])
    dst = os.path.join(output_dir, output_name)

    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  ✅ {step_name}: Zkopírováno ({size:,} B) → {dst}")
    else:
        print(f"  ⚠️  {step_name}: Nenalezeno v {src} — přeskakuji")


def export_source_code(repo_path, output_dir):
    """L2: Spojí specifikované zdrojové kódy do jednoho souboru."""
    dst = os.path.join(output_dir, "source_code.py")
    total_lines = 0
    files_processed = 0

    with open(dst, "w", encoding="utf-8") as out:
        for rel_path in FILES_TO_EXPORT["l2_source"]:
            fpath = os.path.join(repo_path, rel_path)

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
        print(f"  ❌ L2: Žádné zdrojové soubory nenalezeny.")


def export_db_schema(repo_path, output_dir):
    """L3: Zkopíruje DB schéma. Pokud neexistuje, pokusí se vygenerovat z SQLite."""
    src = os.path.join(repo_path, FILES_TO_EXPORT["l3_schema"])
    dst = os.path.join(output_dir, "db_schema.sql")

    if os.path.exists(src):
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  ✅ L3: DB schéma ({size:,} B) → {dst}")
        return

    db_files = glob.glob(os.path.join(repo_path, "*.db"))
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


def print_structure():
    """Vypíše strukturu výstupních souborů."""
    print(f"\nVýstupní struktura:")
    if os.path.exists(FRAMEWORK_INPUTS):
        files = os.listdir(FRAMEWORK_INPUTS)
        print(f"  {FRAMEWORK_INPUTS}/")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(FRAMEWORK_INPUTS, f))
            print(f"    {f} ({size:,} B)")
    else:
        print(f"  Složka {FRAMEWORK_INPUTS} nebyla vytvořena.")


def main():
    print(f"\n📦 Export vstupů pro Bookstore API\n{'═' * 40}")

    # Získání správné cesty
    repo_path = get_repo_path()

    print(f"\n🚀 Zahajuji export ze složky: {repo_path}")
    os.makedirs(FRAMEWORK_INPUTS, exist_ok=True)

    # L0: OpenAPI
    export_openapi(FRAMEWORK_INPUTS)

    # L1: Dokumentace
    export_file(repo_path, "l1_docs", "documentation.md", FRAMEWORK_INPUTS, "L1")

    # L2: Zdrojové kódy
    export_source_code(repo_path, FRAMEWORK_INPUTS)

    # L3: DB Schéma
    export_db_schema(repo_path, FRAMEWORK_INPUTS)

    # L4: Testy
    export_file(repo_path, "l4_tests", "existing_tests.py", FRAMEWORK_INPUTS, "L4")

    print(f"{'─' * 40}")
    print_structure()
    print(f"\n🎉 Export dokončen.")


if __name__ == "__main__":
    main()