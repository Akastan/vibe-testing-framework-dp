"""
Unified Prompt Framework – v7 (context-aware repair + safe helpers).

Změny oproti v6:
  - repair_batch_prompt: přidán kontext API → LLM ví CO opravuje
  - repair_helpers_prompt: přidán kontext + explicitní instrukce zachovat importy
  - Oba repair prompty obsahují _knowledge_block() pro L1+
"""
from __future__ import annotations


class PromptBuilder:
    """Sestavuje prompty z experiment.yaml konfigurace pro dané API + level."""

    _KNOWLEDGE_LEVELS = ("L1", "L2", "L3", "L4")

    def __init__(self, api_cfg: dict, level: str):
        self.api_name = api_cfg["name"]
        self.level = level
        self.base_url = api_cfg["base_url"]
        self.framework_rules: list[str] = api_cfg.get("framework_rules", [])

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

    def _context_block(self, context: str, max_chars: int = 4000) -> str:
        """Zkrácený kontext API pro repair prompty."""
        if not context:
            return ""
        trimmed = context[:max_chars]
        if len(context) > max_chars:
            trimmed += "\n... (zkráceno)"
        return f"\nAPI KONTEXT (pro pochopení očekávaného chování):\n{trimmed}\n"

    # ══════════════════════════════════════════════════
    #  FÁZE 2: Plánování
    # ══════════════════════════════════════════════════

    def planning_prompt(self, context: str, test_count: int) -> str:
        return f"""Analyzuj toto API a připrav se na vytvoření testovacího plánu.

API KONTEXT:
{context}
{self._knowledge_block()}
=========================================
CRITICAL INSTRUCTIONS FOR OUTPUT:
Na základě API kontextu výše vytvoř testovací plán s PŘESNĚ {test_count} testy.

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

Rozhodni sám, které endpointy a scénáře jsou nejdůležitější pro otestování.
PLAN EXACTLY {test_count} TESTS.
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
   - Tato funkce přidá 9 znaků (_ + 8 unique znaků). Důležité pro názvy omezené na počet znaků
   - V KAŽDÉM helper volání generuj unikátní názvy.
2. KVALITA ASERCÍ: Nekontroluj POUZE status kód. Každý test by měl ověřit i odpověď:
   - Happy path (201/200): ověř klíče v response body (assert "id" in data)
   - Error: ověř detail (assert "detail" in r.json())
   - GET seznam: ověř strukturu (assert "items" in data nebo assert isinstance(data, list))
   - Side effects: po vytvoření ověř snížení skladu, po smazání ověř 404 na GET
3. UKLÍZENÍ GLOBÁLNÍHO STAVU (TEARDOWN):
   - Pokud test mění globální stav API (např. zapíná maintenance mode, mění globální nastavení), MUSÍŠ tento stav v tom samém testu na konci vrátit zpět do výchozího stavu (vypnout ho)! 
   - Pokud to neuděláš, zablokuješ API a všechny další testy spadnou na 503.
4. NEGENERUJ test na reset databáze ani /reset endpoint

STRIKTNĚ SE DRŽ PLÁNU A VYGENERUJ PŘESNĚ DANÝ POČET TESTŮ.
YOU MUST RESPOND WITH ONLY VALID PYTHON CODE.
NO MARKDOWN BLOCKS (do not use ```python), NO PROSE, NO EXPLANATIONS.
"""

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Opravy
    # ══════════════════════════════════════════════════

    def repair_batch_prompt(
        self,
        test_entries: list[tuple[str, str, str]],
        helpers: str,
        context: str,
        base_url: str,
        stale_tests: list[str] | None = None,
    ) -> str:
        """Hromadná oprava více failing testů v jednom promptu.

        Args:
            test_entries: [(test_name, test_code, error_msg), ...]
            helpers: kód helper funkcí
            context: API kontext (zkrácený)
            base_url: base URL API
            stale_tests: seznam stale testů (pro info)
        """
        tests_block = ""
        for i, (name, code, error) in enumerate(test_entries, 1):
            tests_block += f"\n── TEST {i}: {name} ──\n"
            tests_block += f"CODE:\n{code}\n"
            tests_block += f"ERROR:\n{error}\n"

        return f"""Oprav tyto selhávající testovací funkce. Každý test má svůj kód a chybu.
BASE_URL = "{base_url}"
{self._context_block(context)}
DOSTUPNÉ HELPERY (NEMĚŇ JE, pouze je používej):
{helpers}

SELHÁVAJÍCÍ TESTY ({len(test_entries)}):
{tests_block}
{self._knowledge_block()}{self._stale_block(stale_tests)}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Oprav KAŽDOU funkci výše. Zachovej přesné názvy funkcí.
- Používej existující helper funkce, nevymýšlej nové.
- Analyzuj CHYBU u každého testu a oprav PŘÍČINU, ne jen symptom:
  - Pokud assert selže na špatném status kódu → zkontroluj jestli test posílá správná data dle API kontextu
  - Pokud assert selže na hodnotě v response → zkontroluj jestli test ověřuje správné pole/hodnotu
  - Pokud test padne na setup (helper) → zkontroluj jestli test správně vytváří prerekvizity
- Vrať POUZE opravené funkce (def test_...), žádné helpery ani importy.

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (all {len(test_entries)} fixed functions).
NO MARKDOWN BLOCKS, NO PROSE, NO IMPORTS, NO HELPERS, NO EXPLANATIONS.
"""

    def repair_helpers_prompt(
        self, helpers: str, sample_errors: list[str],
        failing_count: int, context: str, base_url: str,
    ) -> str:
        errors_text = "\n".join(sample_errors)
        return f"""Většina testů padá kvůli bugu v helper funkcích. Oprav helpery.
BASE_URL = "{base_url}"
{self._context_block(context)}
AKTUÁLNÍ HELPERY (vrať KOMPLETNÍ opravenou verzi VČETNĚ VŠECH importů):
{helpers}

UKÁZKY CHYB ({failing_count} testů celkem padá):
{errors_text}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Vrať KOMPLETNÍ blok: všechny importy + všechny helper funkce.
- NEVYNECHEJ žádný import ani helper který je v AKTUÁLNÍ verzi výše.
- Zachovej signatury helperů kompatibilní s existujícími testy.
- Zajisti unikátní názvy přes uuid4 (unique() helper).
- Analyzuj CHYBY a oprav ROOT CAUSE v helperech:
  - Pokud helpery posílají špatný formát dat → oprav dle API kontextu
  - Pokud helpery neposílají povinné hlavičky (API key, ETag) → přidej je
  - Pokud helpery mají špatnou URL/metodu → oprav dle API kontextu

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (all imports + all helpers).
NO MARKDOWN BLOCKS, NO PROSE, NO EXPLANATIONS.
The code MUST start with import statements.
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