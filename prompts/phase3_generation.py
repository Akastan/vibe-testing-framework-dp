"""
Fáze 3: Generování spustitelných Python/pytest testů pomocí LLM.
"""
import json
import re


def generate_test_code(test_plan: dict, context_data: str, llm,
                       base_url: str = "http://localhost:8000",
                       feedback: str = None) -> str:
    plan_str = json.dumps(test_plan, indent=2, ensure_ascii=False)

    prompt = f"""Napiš pytest testy v Pythonu (requests knihovna) pro toto REST API.
BASE_URL = "{base_url}"

PLÁN:
{plan_str}

KONTEXT:
{context_data}

PRAVIDLA:
- import pytest, requests na začátku
- Každý test začíná test_, je self-contained, používá timeout=5 na každém HTTP volání
- Nepoužívej fixtures ani conftest
- Na začátek přidej helper: def reset_db(): requests.post(f"{{BASE_URL}}/reset", timeout=5)
- Testy co potřebují data si je vytvoří samy (helper funkce)
- Neověřuj přesný text chybových hlášek, ověřuj jen status kód a přítomnost klíče "detail"
- Pro nejednoznačné chyby použij: assert r.status_code in [400, 404, 422]

Vrať POUZE Python kód, žádný markdown.
"""

    if feedback:
        prompt += f"\nPředchozí verze selhala:\n{feedback[-2000:]}\nVrať KOMPLETNÍ opravený kód.\n"

    raw = llm.generate_text(prompt)

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]

    return clean.strip()