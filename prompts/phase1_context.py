import yaml
import json
import os


def analyze_context(openapi_path: str, doc_path: str = None, level: str = "L0") -> str:
    """
    Načte OpenAPI specifikaci a volitelně dokumentaci na základě úrovně L0 nebo L1.
    """
    if not os.path.exists(openapi_path):
        raise FileNotFoundError(f"Soubor {openapi_path} nebyl nalezen.")

    # Načtení OpenAPI (Základ pro všechny úrovně)
    with open(openapi_path, 'r', encoding='utf-8') as file:
        if openapi_path.endswith('.yaml') or openapi_path.endswith('.yml'):
            data = yaml.safe_load(file)
            openapi_context = json.dumps(data, indent=2)
        elif openapi_path.endswith('.json'):
            openapi_context = file.read()
        else:
            raise ValueError("Nepodporovaný formát. Použij .yaml nebo .json")

    context_result = f"--- OPENAPI SPECIFIKACE ---\n{openapi_context}\n"

    # Pokud jsme na úrovni L1 (nebo vyšší) a máme cestu k dokumentaci, přidáme ji
    if level in ["L1", "L2"] and doc_path and os.path.exists(doc_path):
        with open(doc_path, 'r', encoding='utf-8') as doc_file:
            doc_context = doc_file.read()
            context_result += f"\n--- TECHNICKÁ DOKUMENTACE ---\n{doc_context}\n"

    return context_result