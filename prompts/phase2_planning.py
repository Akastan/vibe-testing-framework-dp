"""
Fáze 2: Generování testovacího plánu pomocí LLM.
"""
import json
import re


def generate_test_plan(context_data: str, llm, level: str = "L0") -> dict:
    """
    Instruuje LLM k vytvoření strukturovaného testovacího plánu (JSON).

    TODO (DIPLOMKA - TEMPORARY LIMIT):
    Aktuálně je v promptu limit na max 20 testů kvůli output token limitu.
    Po implementaci chunkingu tento limit odstraň.
    """
    print(f"  Iniciuji model ({llm.__class__.__name__}) pro Fázi 2 (Plánování)...")
    print("  ⚠️ Testovací plán je dočasně omezen na max 20 nejdůležitějších testů.")

    # Doplňující instrukce podle úrovně kontextu
    level_hint = ""
    if level == "L0":
        level_hint = """
    KONTEXT: Máš k dispozici POUZE OpenAPI specifikaci (black-box testování).
    Vycházej striktně z definovaných endpointů, schémat a status kódů.
    Nemáš přístup k vnitřní implementaci – testuj pouze veřejné chování API."""
    elif level == "L1":
        level_hint = """
    KONTEXT: Máš k dispozici OpenAPI specifikaci A technickou/byznys dokumentaci.
    Dokumentace obsahuje informace o známých chybách (Known Issues) a reálném chování serveru.
    KRITICKY DŮLEŽITÉ: Pokud dokumentace uvádí, že server vrací jiný kód než specifikace
    (např. 500 místo 404), použij v expected_status kód, který server REÁLNĚ vrací."""

    prompt = f"""
Jsi expert na softwarové testování (QA inženýr). Tvým úkolem je analyzovat
následující kontext a vytvořit testovací plán pro REST API.
{level_hint}

OMEZENÍ: Vyber POUZE 20 NEJDŮLEŽITĚJŠÍCH testovacích případů celkem.
Vytvoř reprezentativní mix pokrývající:
1. Hlavní happy paths (CRUD operace, login, inventory)
2. Kritické edge cases (nevalidní vstupy, hraniční hodnoty)
3. Ošetření chybových stavů (chybějící zdroje, nevalidní formáty)

Vrať POUZE validní JSON (žádný markdown, žádný text okolo):
{{
  "test_plan": [
    {{
      "endpoint": "/cesta/k/endpointu",
      "method": "GET",
      "test_cases": [
        {{
          "name": "popisny_nazev_testu",
          "type": "happy_path",
          "expected_status": 200,
          "description": "Co přesně se testuje"
        }}
      ]
    }}
  ]
}}

Pravidla pro pole "type": použij POUZE jednu z hodnot "happy_path", "edge_case", "error".
Pravidla pro pole "name": použij snake_case bez diakritiky.

Zde je kontext:
{context_data}
"""

    raw = llm.generate_text(prompt)

    # Očištění od markdown wrapperu
    clean = raw.strip()
    clean = re.sub(r'^```(?:json)?\s*', '', clean)
    clean = re.sub(r'\s*```$', '', clean)

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"  ❌ Chyba při parsování JSON: {e}")
        print(f"  Surový výstup (prvních 500 znaků): {raw[:500]}")
        return {"test_plan": []}