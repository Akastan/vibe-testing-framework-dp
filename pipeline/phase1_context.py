"""
Fáze 1: Analýza a příprava kontextu pro LLM.
Načte OpenAPI specifikaci a volitelné doplňkové zdroje podle úrovně L0–L4.
"""
import yaml
import json
import os


def analyze_context(openapi_path: str, doc_path: str = None, level: str = "L0",
                    source_code_path: str = None, db_schema_path: str = None,
                    existing_tests_path: str = None) -> str:
    """
    Sestaví kontextový řetězec pro LLM na základě požadované úrovně.

    Úrovně:
        L0 – pouze OpenAPI specifikace
        L1 – L0 + byznys/technická dokumentace
        L2 – L1 + zdrojový kód endpointů
        L3 – L2 + databázové schéma
        L4 – L3 + existující testy (in-context learning)
    """
    if not os.path.exists(openapi_path):
        raise FileNotFoundError(f"Soubor {openapi_path} nebyl nalezen.")

    # --- L0: OpenAPI specifikace (základ pro všechny úrovně) ---
    with open(openapi_path, 'r', encoding='utf-8') as f:
        if openapi_path.endswith(('.yaml', '.yml')):
            data = yaml.safe_load(f)
            openapi_text = json.dumps(data, indent=2)
        elif openapi_path.endswith('.json'):
            openapi_text = f.read()
        else:
            raise ValueError("Nepodporovaný formát specifikace. Použij .yaml nebo .json")

    context = f"--- OPENAPI SPECIFIKACE ---\n{openapi_text}\n"

    # --- L1: Byznys dokumentace ---
    if level in ("L1", "L2", "L3", "L4"):
        if doc_path and os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                context += f"\n--- TECHNICKÁ A BYZNYS DOKUMENTACE ---\n{f.read()}\n"
        else:
            print(f"  ⚠️ Úroveň {level} vyžaduje dokumentaci, ale soubor nebyl nalezen: {doc_path}")

    # --- L2: Zdrojový kód endpointů ---
    if level in ("L2", "L3", "L4"):
        if source_code_path and os.path.exists(source_code_path):
            with open(source_code_path, 'r', encoding='utf-8') as f:
                context += f"\n--- ZDROJOVÝ KÓD ENDPOINTŮ ---\n{f.read()}\n"
        else:
            print(f"  ⚠️ Úroveň {level} vyžaduje zdrojový kód, ale soubor nebyl nalezen: {source_code_path}")

    # --- L3: Databázové schéma ---
    if level in ("L3", "L4"):
        if db_schema_path and os.path.exists(db_schema_path):
            with open(db_schema_path, 'r', encoding='utf-8') as f:
                context += f"\n--- DATABÁZOVÉ SCHÉMA ---\n{f.read()}\n"
        else:
            print(f"  ⚠️ Úroveň {level} vyžaduje DB schéma, ale soubor nebyl nalezen: {db_schema_path}")

    # --- L4: Existující testy (in-context learning) ---
    if level == "L4":
        if existing_tests_path and os.path.exists(existing_tests_path):
            with open(existing_tests_path, 'r', encoding='utf-8') as f:
                context += f"\n--- EXISTUJÍCÍ TESTY (UKÁZKA STYLU) ---\n{f.read()}\n"
        else:
            print(f"  ⚠️ Úroveň L4 vyžaduje existující testy, ale soubor nebyl nalezen: {existing_tests_path}")

    return context