import json
import re


def generate_test_plan(context_data: str, llm) -> dict:
    """
    Využije předaný LLM k vygenerování testovacího plánu ve formátu JSON.

    TODO (DIPLOMKA - TEMPORARY LIMIT):
    Aktuálně je v promptu natvrdo nastaven limit na max 20 nejdůležitějších testů,
    aby nedocházelo k useknutí vygenerovaného kódu ve Fázi 3 kvůli limitu output tokenů.
    Až se naimplementuje generování po částech (chunking), tento limit z promptu odstraň!
    """
    print(f"Iniciuji model ({llm.__class__.__name__}) pro Fázi 2 (Plánování)...")
    print("⚠️ UPOZORNĚNÍ: Testovací plán je dočasně omezen na max 20 nejdůležitějších testů!")

    prompt = f"""
    Jsi expert na softwarové testování (QA inženýr). Tvým úkolem je analyzovat 
    následující specifikaci a vytvořit testovací plán.

    DŮLEŽITÉ OMEZENÍ PRO TENTO BĚH:
    Vyber a vygeneruj POUZE 20 NEJDŮLEŽITĚJŠÍCH testovacích případů (test cases) 
    napříč celým API. Nesmíš jich vygenerovat více než 20 celkem! 
    Z těchto 20 testů vyber reprezentativní mix, který pokryje:
    1. Hlavní ideální průchody (Happy paths) - např. CRUD operace
    2. Kritické hraniční stavy (Edge cases)
    3. Zásadní ošetření chybových stavů (Error handling) - např. 400, 401, 404

    Vrať POUZE validní JSON v této struktuře a nic jiného:
    {{
      "test_plan": [
        {{
          "endpoint": "/cesta/k/endpointu",
          "method": "GET/POST/...",
          "test_cases": [
            {{
              "name": "Název testu",
              "type": "happy_path | edge_case | error",
              "expected_status": 200,
              "description": "Co přesně se zde testuje"
            }}
          ]
        }}
      ]
    }}

    Zde je kontext (Specifikace a dokumentace):
    {context_data}
    """

    # Využití abstrahovaného LLM providera
    raw_text = llm.generate_text(prompt)

    # Očištění výstupu od markdownu, pokud tam je
    clean_text = raw_text.strip()
    if clean_text.startswith("```json"):
        clean_text = re.sub(r'^```json\s*', '', clean_text)
        clean_text = re.sub(r'\s*```$', '', clean_text)
    elif clean_text.startswith("```"):
        clean_text = re.sub(r'^```\s*', '', clean_text)
        clean_text = re.sub(r'\s*```$', '', clean_text)

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        print(f"Chyba při parsování JSON z výstupu: {e}")
        print("Surový výstup:", raw_text)
        return {"test_plan": []}