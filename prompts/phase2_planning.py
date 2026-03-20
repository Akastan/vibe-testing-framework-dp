"""
Fáze 2: Generování testovacího plánu pomocí LLM.
Zajišťuje přesný počet testů přes retry loop + doplnění/ořezání.
"""
import json
import re


def _count_plan_tests(plan: dict) -> int:
    return sum(
        len(ep.get("test_cases", []))
        for ep in plan.get("test_plan", [])
    )


def _trim_plan(plan: dict, target: int) -> dict:
    """Ořízne plán na přesně target testů (odebere od konce)."""
    to_remove = _count_plan_tests(plan) - target
    if to_remove <= 0:
        return plan

    for ep in reversed(plan.get("test_plan", [])):
        cases = ep.get("test_cases", [])
        while cases and to_remove > 0:
            cases.pop()
            to_remove -= 1
        if to_remove == 0:
            break

    plan["test_plan"] = [ep for ep in plan["test_plan"] if ep.get("test_cases")]
    return plan


def _parse_plan_json(raw: str) -> dict:
    clean = raw.strip()
    clean = re.sub(r'^```(?:json)?\s*', '', clean)
    clean = re.sub(r'\s*```$', '', clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error: {e}")
        return {"test_plan": []}


def generate_test_plan(context_data: str, llm, level: str = "L0", test_count: int = 40) -> dict:
    base_prompt = f"""Analyzuj toto API a vytvoř testovací plán s PŘESNĚ {test_count} testy.
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
- PŘESNĚ {test_count} testů celkem, ani více ani méně

Kontext:
{context_data}
"""

    MAX_ATTEMPTS = 4

    # === Generování plánu s retry ===
    plan = {"test_plan": []}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        actual = _count_plan_tests(plan)

        if actual == test_count:
            break

        if actual == 0:
            # Prázdný plán → generuj od nuly
            if attempt > 1:
                print(f"  [Plán] Retry {attempt}: plán prázdný, opakuji generování...")
            raw = llm.generate_text(base_prompt)
            plan = _parse_plan_json(raw)

        elif actual < test_count:
            # Málo testů → doplň
            missing = test_count - actual
            print(f"  [Plán] {actual} testů, doplňuji {missing}...")
            fill_prompt = (
                f"Tento testovací plán má {actual} testů, ale potřebuji PŘESNĚ {test_count}. "
                f"Přidej {missing} nových testů. Zaměř se na endpointy a scénáře které ještě "
                f"nejsou dostatečně pokryté (edge cases, error handling, validace).\n\n"
                f"Vrať CELÝ plán (starý + nový) jako validní JSON.\n\n"
                f"Aktuální plán:\n{json.dumps(plan, indent=2, ensure_ascii=False)}"
            )
            raw = llm.generate_text(fill_prompt)
            new_plan = _parse_plan_json(raw)
            if _count_plan_tests(new_plan) > 0:
                plan = new_plan

        else:
            # Moc testů → ořízni (deterministicky, nepotřebuje LLM)
            break

    # === Post-processing ===
    actual = _count_plan_tests(plan)
    if actual > test_count:
        print(f"  [Plán] {actual} testů → ořezávám na {test_count}")
        plan = _trim_plan(plan, test_count)
    elif actual < test_count:
        print(f"  [Plán] ⚠️ {actual} testů (cíl {test_count}) po {MAX_ATTEMPTS} pokusech")
    else:
        print(f"  [Plán] ✅ Přesně {test_count} testů")

    return plan