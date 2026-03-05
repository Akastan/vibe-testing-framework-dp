import json

def generate_test_code(test_plan: dict, context_data: str, llm, feedback: str = None) -> str:
    """
    Využije předaný LLM k vygenerování spustitelných Python/pytest testů.
    """
    print(f"Iniciuji model ({llm.__class__.__name__}) pro Fázi 3 (Generování kódu)...")

    # Převod test_plan dict zpět na string pro vložení do promptu
    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    prompt = f"""
    Jsi expert na QA automatizaci. Tvojí úlohou je napsat plně funkční a spustitelné 
    testy v jazyce Python pomocí knihoven `pytest` a `requests`.

    Tady je testovací plán, který musíš implementovat:
    {plan_str}

    Zde je kontext rozhraní (slouží jako zdroj pravdy pro datové typy a endpointy):
    {context_data}

    Základní URL pro testy je: https://petstore3.swagger.io/api/v3

    POŽADAVKY NA KÓD:
    1. Každý test musí mít hluboké aserce (ověřuj status kód, strukturu JSON odpovědi a hlavičky).
    2. Předpokládej, že importy `pytest` a `requests` jsou k dispozici.
    3. Vygeneruj POUZE čistý a spustitelný Python kód. Nepiš žádné vysvětlivky, žádný markdown text okolo.
    """

    if feedback:
        prompt += f"""
        UPOZORNĚNÍ: Předchozí verze tvého kódu při spuštění selhala s touto chybou:
        {feedback}
        Analyzuj tuto chybu a kód oprav. Znovu vrať POUZE opravený Python kód.
        """

    raw_text = llm.generate_text(prompt)

    # Očištění výstupu od ```python markdown bloku
    clean_text = raw_text.strip()
    if clean_text.startswith("```python"):
        clean_text = clean_text[9:]  # Odstraní ```python
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]  # Odstraní ```
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3] # Odstraní koncový ```

    return clean_text.strip()