"""
Fáze 3: Generování spustitelných Python/pytest testů pomocí LLM.
"""
import json
import re

from config import API_BASE_URL


def generate_test_code(test_plan: dict, context_data: str, llm, feedback: str = None) -> str:
    """
    Instruuje LLM k napsání pytest testů na základě testovacího plánu.
    Pokud je předán feedback (chybový log), model se pokusí kód opravit.
    """
    print(f"  Iniciuji model ({llm.__class__.__name__}) pro Fázi 3 (Generování kódu)...")

    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    prompt = f"""
Jsi expert na QA automatizaci. Napiš plně funkční a spustitelné testy
v Pythonu pomocí knihoven `pytest` a `requests`.

TESTOVACÍ PLÁN K IMPLEMENTACI:
{plan_str}

KONTEXT API (zdroj pravdy pro datové typy, schémata a endpointy):
{context_data}

BASE URL: {API_BASE_URL}

STRIKTNÍ POŽADAVKY NA KÓD:
1. Na začátek souboru vlož: import pytest, import requests
2. Definuj BASE_URL = "{API_BASE_URL}" jako globální konstantu.
3. Každá testovací funkce musí začínat prefixem test_ (aby ji pytest našel).
4. Každý test musí obsahovat HLUBOKÉ ASERCE:
   - Ověř HTTP status kód (assert response.status_code == ...)
   - Pokud odpověď vrací JSON, ověř strukturu (klíče, typy hodnot)
   - Ověř Content-Type hlavičku kde je to relevantní
5. Pro POST/PUT requesty vždy nastav header Content-Type: application/json.
6. Nepoužívej žádné fixtures ani conftest – testy musí být self-contained.
7. Nepoužívej žádné knihovny třetích stran kromě pytest a requests.

VRAŤ POUZE čistý Python kód. Žádné vysvětlivky, žádný markdown.
"""

    if feedback:
        prompt += f"""

POZOR: Předchozí verze kódu selhala s touto chybou:
--- ZAČÁTEK CHYBOVÉHO LOGU ---
{feedback[-3000:]}
--- KONEC CHYBOVÉHO LOGU ---

Analyzuj chybu a vrať KOMPLETNÍ opravený Python kód (ne jen opravu).
"""

    raw = llm.generate_text(prompt)

    # Očištění markdown wrapperu
    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]

    return clean.strip()