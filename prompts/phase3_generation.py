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

TECHNICKÉ POŽADAVKY (aby testy šly spustit):
- import pytest, requests, uuid na začátku
- Každý test začíná test_, používá timeout=30 na každém HTTP volání
- Nepoužívej fixtures, conftest, setup_module, setup_function ani žádné pytest hooks.
- Databáze se resetuje automaticky PŘED spuštěním testů (framework to zajistí).
  Negeneruj test na reset databáze a NEVOLEJ /reset endpoint nikde v kódu.
- Každý test musí být self-contained – vytvoří si vlastní data přes helper funkce.

UNIKÁTNÍ NÁZVY (povinné, jinak testy kolidují):
- Pro unikátní názvy použij uuid4 suffix:
    def unique(prefix="test"):
        return f"{{prefix}}_{{uuid.uuid4().hex[:8]}}"
- V KAŽDÉM helper volání generuj unikátní názvy:
    def create_author(name=None):
        name = name or unique("Author")
        r = requests.post(f"{{BASE_URL}}/authors", json={{"name": name}}, timeout=30)
        assert r.status_code == 201
        return r.json()

SPECIFIKA TOHOTO API (bez tohoto testy spadnou):
- DELETE endpointy vracejí 204 s PRÁZDNÝM tělem. Nevolej .json() na 204 odpovědích.
- DELETE /books/{{id}}/tags používá REQUEST BODY: requests.delete(..., json={{"tag_ids": [...]}})
- PATCH /books/{{id}}/stock používá QUERY parametr: params={{"quantity": N}}, ne JSON body.
- Neověřuj přesný text chybových hlášek, ověřuj status kód a přítomnost klíče "detail".

Vrať POUZE Python kód, žádný markdown.
"""

    if feedback:
        prompt += f"""
PŘEDCHOZÍ VERZE SELHALA. Analyzuj chyby a oprav je:
{feedback[-3000:]}

Vrať KOMPLETNÍ opravený kód se VŠEMI testy.
Pokud vidíš 409 Conflict chyby, ujisti se že každý test používá unique() helper.
"""

    raw = llm.generate_text(prompt)

    clean = raw.strip()
    if clean.startswith("```python"):
        clean = clean[9:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]

    return clean.strip()