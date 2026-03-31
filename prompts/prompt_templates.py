"""
Unified Prompt Framework – v5 (fair experimental design).

Klíčový princip oddělení:
  - framework_rules: JAK psát testy (pytest/requests technikálie).
    Injektují se do VŠECH levelů. Neobsahují znalost o API.
  - api_knowledge: CO API dělá (chování, pravidla, defaulty).
    Injektují se POUZE do L1+ (kde tato znalost přirozeně existuje v kontextu).

Tím je zajištěno že jediná proměnná mezi levely je KONTEXT.

Použití:
    builder = PromptBuilder(api_cfg, level="L0")
    prompt = builder.planning_prompt(context, test_count)
    prompt = builder.generation_prompt(plan_json, context, base_url)
    ...
"""
from __future__ import annotations


class PromptBuilder:
    """Sestavuje prompty z experiment.yaml konfigurace pro dané API + level."""

    # L1+ dostane api_knowledge, L0 ne
    _KNOWLEDGE_LEVELS = ("L1", "L2", "L3", "L4")

    def __init__(self, api_cfg: dict, level: str):
        self.api_name = api_cfg["name"]
        self.level = level
        self.base_url = api_cfg["base_url"]

        # Framework rules — platí vždy
        self.framework_rules: list[str] = api_cfg.get("framework_rules", [])

        # API knowledge — jen pro L1+
        if level in self._KNOWLEDGE_LEVELS:
            self.api_knowledge: list[str] = api_cfg.get("api_knowledge", [])
        else:
            self.api_knowledge = []

    # ──────────────────────────────────────────────────
    #  Interní bloky
    # ──────────────────────────────────────────────────

    def _framework_block(self) -> str:
        if not self.framework_rules:
            return ""
        lines = "\n".join(f"- {r}" for r in self.framework_rules)
        return f"\nTECHNICKÉ POŽADAVKY FRAMEWORKU:\n{lines}\n"

    def _knowledge_block(self) -> str:
        """Vrací blok s API knowledge. Prázdný pro L0."""
        if not self.api_knowledge:
            return ""
        lines = "\n".join(f"- {r}" for r in self.api_knowledge)
        return (
            f"\nZNÁMÉ CHOVÁNÍ TOHOTO API (použij při psaní helperů a assertů):\n"
            f"{lines}\n"
        )

    def _stale_block(self, stale_tests: list[str] | None = None) -> str:
        if not stale_tests:
            return ""
        names = ", ".join(stale_tests)
        return (
            f"\nZAMRZLÉ TESTY (neopravuj, jsou principiálně neopravitelné):\n"
            f"{names}\n"
            f"Soustřeď se POUZE na ostatní failing testy.\n"
        )

    # ══════════════════════════════════════════════════
    #  FÁZE 2: Plánování
    # ══════════════════════════════════════════════════

    def planning_prompt(self, context: str, test_count: int) -> str:
        # ZMĚNA: Kontext je nahoře. Znalosti uprostřed. Tvrdá pravidla a JSON vynucení úplně dole.
        return f"""Analyzuj toto API a připrav se na vytvoření testovacího plánu.

API KONTEXT:
{context}
{self._knowledge_block()}
=========================================
CRITICAL INSTRUCTIONS FOR OUTPUT:
Na základě API kontextu výše vytvoř testovací plán s PŘESNĚ {test_count} testy.
Rozhodni sám, které endpointy a scénáře jsou nejdůležitější pro otestování.

PRAVIDLA PRO TESTY:
- type = "happy_path" | "edge_case" | "error"
- name = snake_case bez diakritiky, unikátní napříč celým plánem
- endpoint musí být přesná cesta z API specifikace (s path parametry jako {{book_id}})
- method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
- Jeden endpoint (method+path) = jeden objekt v poli, s více test_cases uvnitř
- PŘESNĚ {test_count} testů celkem, ani více ani méně
- NEGENERUJ test na reset databáze ani /reset endpoint

POŽADOVANÁ JSON STRUKTURA:
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

YOU MUST RESPOND WITH ONLY VALID JSON. 
NO MARKDOWN, NO PROSE, NO EXPLANATIONS.
Start your response with {{ and end with }}.
"""

    def planning_fill_prompt(self, current_plan_json: str, actual: int, target: int) -> str:
        missing = target - actual
        return (
            f"Tento testovací plán má {actual} testů, ale potřebuji PŘESNĚ {target}.\n\n"
            f"AKTUÁLNÍ PLÁN:\n{current_plan_json}\n\n"
            f"=========================================\n"
            f"CRITICAL INSTRUCTIONS FOR OUTPUT:\n"
            f"Přidej {missing} nových testů. Zaměř se na endpointy a scénáře které ještě "
            f"nejsou dostatečně pokryté (edge cases, error handling, validace).\n"
            f"Vrať CELÝ plán (starý + nový).\n\n"
            f"YOU MUST RESPOND WITH ONLY VALID JSON.\n"
            f"NO MARKDOWN, NO PROSE, NO EXPLANATIONS.\n"
            f"Start your response with {{ and end with }}."
        )

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Generování kódu
    # ══════════════════════════════════════════════════

    def generation_prompt(self, plan_json: str, context: str, base_url: str) -> str:
        return f"""Budeš psát pytest testy v Pythonu (requests knihovna) pro toto REST API.
BASE_URL = "{base_url}"

KONTEXT API:
{context}

PLÁN TESTŮ:
{plan_json}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
1. UNIKÁTNÍ NÁZVY (povinné, jinak testy kolidují):
   - Pro unikátní názvy použij uuid4 suffix: def unique(prefix="test"): return f"{{prefix}}_{{uuid.uuid4().hex[:8]}}"
   - V KAŽDÉM helper volání generuj unikátní názvy.
2. KVALITA ASERCÍ: Nekontroluj POUZE status kód. Každý test by měl ověřit i odpověď:
   - Happy path (201/200): ověř klíče v response body (assert "id" in data)
   - Error: ověř detail (assert "detail" in r.json())
   - GET seznam: ověř strukturu (assert "items" in data nebo assert isinstance(data, list))
   - Side effects: po vytvoření ověř snížení skladu, po smazání ověř 404 na GET

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE.
NO MARKDOWN BLOCKS (do not use ```python), NO PROSE, NO EXPLANATIONS.
"""

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Opravy
    # ══════════════════════════════════════════════════

    def repair_single_prompt(
        self, test_name: str, test_code: str, error_msg: str,
        helpers: str, base_url: str,
        stale_tests: list[str] | None = None,
    ) -> str:
        return f"""Oprav tuto jednu selhávající testovací funkci.
BASE_URL = "{base_url}"

DOSTUPNÉ HELPERY:
{helpers}

SELHÁVAJÍCÍ TEST:
{test_code}

CHYBA PŘI BĚHU:
{error_msg}
{self._knowledge_block()}{self._stale_block(stale_tests)}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Oprav funkci, neměň její název.
- Používej existující helper funkce, nevymýšlej nové.
- Pokud test ověřuje jen status kód, přidej i kontrolu response body.

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (the fixed function only).
NO MARKDOWN BLOCKS, NO PROSE, NO IMPORTS, NO EXPLANATIONS.
"""

    def repair_helpers_prompt(
        self, helpers: str, sample_errors: list[str],
        failing_count: int, base_url: str,
    ) -> str:
        errors_text = "\n".join(sample_errors)
        return f"""Většina testů padá kvůli bugu v helper funkcích. Oprav helpery.
BASE_URL = "{base_url}"

AKTUÁLNÍ HELPERY:
{helpers}

UKÁZKY CHYB ({failing_count} testů celkem padá):
{errors_text}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Zachovej signatury helperů kompatibilní s existujícími testy.
- Zajisti unikátní názvy přes uuid4 (unique() helper).

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (the fixed helpers and imports).
NO MARKDOWN BLOCKS, NO PROSE, NO EXPLANATIONS.
"""

    def fill_tests_prompt(
        self, missing: int, helpers: str, existing_names: list[str],
        context: str, base_url: str,
    ) -> str:
        names_str = ", ".join(existing_names)
        return f"""Vygeneruj nové pytest testy pro toto REST API.
BASE_URL = "{base_url}"

KONTEXT API:
{context[:3000]}

DOSTUPNÉ HELPERY (použij je, nevymýšlej nové):
{helpers}

EXISTUJÍCÍ TESTY (tyto názvy NEPOUŽÍVEJ):
{names_str}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Vygeneruj PŘESNĚ {missing} nových test funkcí (def test_...(): ...).
- Každý test musí být self-contained.
- Zaměř se na scénáře které existující testy nepokrývají.
- Nekontroluj jen status kód — ověřuj i response body.

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE ({missing} new functions).
NO MARKDOWN BLOCKS, NO IMPORTS, NO HELPERS, NO PROSE, NO EXPLANATIONS.
"""