"""
Fáze 2: Generování testovacího plánu pomocí LLM (v2 — unified prompt framework).

Změny oproti v1:
- Prompt se generuje přes PromptBuilder (API pravidla z YAML)
- Filtrování /reset testů přímo v post-processingu (ne až po count validaci)
"""
import json
import re

from prompts.prompt_templates import PromptBuilder


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


def _filter_reset_tests(plan: dict) -> dict:
    """Odstraní testy na /reset endpoint z plánu."""
    filtered = []
    removed = 0
    for ep in plan.get("test_plan", []):
        endpoint = ep.get("endpoint", "").lower()
        if "/reset" in endpoint:
            removed += len(ep.get("test_cases", []))
            continue

        # Filtruj i jednotlivé test_cases s "reset" v názvu
        cases = ep.get("test_cases", [])
        clean_cases = [
            tc for tc in cases
            if "reset" not in tc.get("name", "").lower()
        ]
        removed += len(cases) - len(clean_cases)

        if clean_cases:
            ep["test_cases"] = clean_cases
            filtered.append(ep)

    if removed > 0:
        print(f"  [Plán] Odfiltrováno {removed} reset testů")

    plan["test_plan"] = filtered
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


def generate_test_plan(context_data: str, llm,
                       prompt_builder: PromptBuilder,
                       level: str = "L0",
                       test_count: int = 40) -> dict:

    base_prompt = prompt_builder.planning_prompt(context_data, level, test_count)

    MAX_ATTEMPTS = 4

    plan = {"test_plan": []}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Filtruj reset testy PŘED počítáním
        plan = _filter_reset_tests(plan)
        actual = _count_plan_tests(plan)

        if actual == test_count:
            break

        if actual == 0:
            if attempt > 1:
                print(f"  [Plán] Retry {attempt}: plán prázdný, opakuji generování...")
            raw = llm.generate_text(base_prompt)
            plan = _parse_plan_json(raw)

        elif actual < test_count:
            missing = test_count - actual
            print(f"  [Plán] {actual} testů, doplňuji {missing}...")
            fill_prompt = prompt_builder.planning_fill_prompt(
                json.dumps(plan, indent=2, ensure_ascii=False),
                actual, test_count,
            )
            raw = llm.generate_text(fill_prompt)
            new_plan = _parse_plan_json(raw)
            if _count_plan_tests(new_plan) > 0:
                plan = new_plan
        else:
            break

    # === Post-processing ===
    plan = _filter_reset_tests(plan)  # Finální filtrování
    actual = _count_plan_tests(plan)

    if actual > test_count:
        print(f"  [Plán] {actual} testů → ořezávám na {test_count}")
        plan = _trim_plan(plan, test_count)
    elif actual < test_count:
        print(f"  [Plán] ⚠️ {actual} testů (cíl {test_count}) po {MAX_ATTEMPTS} pokusech")
    else:
        print(f"  [Plán] ✅ Přesně {test_count} testů")

    return plan