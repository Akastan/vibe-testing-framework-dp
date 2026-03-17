"""
Fáze 2: Generování testovacího plánu pomocí LLM.
"""
import json
import re


def generate_test_plan(context_data: str, llm, level: str = "L0", test_count: int = 40) -> dict:
    prompt = f"""Analyzuj toto API a vytvoř testovací plán s PŘESNĚ {test_count} testy.
Rozhodni sám, které endpointy a scénáře jsou nejdůležitější pro otestování.

Vrať POUZE validní JSON:
{{
  "test_plan": [
    {{
      "endpoint": "/cesta",
      "method": "GET",
      "test_cases": [
        {{
          "name": "nazev_testu",
          "type": "happy_path",
          "expected_status": 200,
          "description": "Popis co test ověřuje"
        }}
      ]
    }}
  ]
}}

PRAVIDLA:
- type = "happy_path" | "edge_case" | "error"
- name = snake_case bez diakritiky, unikátní napříč celým plánem
- endpoint musí být přesná cesta z API (s path parametry jako {{book_id}})
- method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
- Jeden endpoint (method+path) = jeden objekt v poli, s více test_cases uvnitř

Kontext:
{context_data}
"""

    raw = llm.generate_text(prompt)

    clean = raw.strip()
    clean = re.sub(r'^```(?:json)?\s*', '', clean)
    clean = re.sub(r'\s*```$', '', clean)

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error: {e}")
        return {"test_plan": []}