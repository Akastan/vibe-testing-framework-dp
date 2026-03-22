"""
Unified Prompt Framework – šablony promptů pro všechny fáze pipeline.

Princip: Prompt = Base Template + API Rules (z YAML) + Context (z phase1) + Runtime Data.
Žádné hardcoded API-specifické instrukce v kódu.

Použití:
    builder = PromptBuilder(api_cfg)
    prompt = builder.planning_prompt(context, level, test_count)
    prompt = builder.generation_prompt(test_plan, context, base_url)
    prompt = builder.repair_single_prompt(test_name, test_code, error, helpers, base_url)
    prompt = builder.repair_helpers_prompt(helpers, sample_errors, failing_count, base_url)
    prompt = builder.fill_tests_prompt(missing, helpers, existing_names, context, base_url)
"""
from __future__ import annotations


class PromptBuilder:
    """Sestavuje prompty z experiment.yaml konfigurace pro dané API."""

    def __init__(self, api_cfg: dict):
        self.api_name = api_cfg["name"]
        self.api_rules: list[str] = api_cfg.get("api_rules", [])
        self.helper_hints: list[str] = api_cfg.get("helper_hints", [])
        self.base_url = api_cfg["base_url"]

    # ──────────────────────────────────────────────────
    #  Interní helpery pro sestavení bloků
    # ──────────────────────────────────────────────────

    def _rules_block(self) -> str:
        """Formátuje API-specifická pravidla jako blok textu."""
        if not self.api_rules:
            return ""
        lines = "\n".join(f"- {r}" for r in self.api_rules)
        return f"\nSPECIFIKA TOHOTO API (bez dodržení testy spadnou):\n{lines}\n"

    def _helper_hints_block(self) -> str:
        """Formátuje hinty pro helper funkce."""
        if not self.helper_hints:
            return ""
        lines = "\n".join(f"- {r}" for r in self.helper_hints)
        return f"\nPRAVIDLA PRO HELPER FUNKCE:\n{lines}\n"

    def _stale_block(self, stale_tests: list[str] | None = None) -> str:
        """Blok se seznamem zamrzlých testů (neopravovat)."""
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

    def planning_prompt(self, context: str, level: str, test_count: int) -> str:
        return f"""Analyzuj toto API a vytvoř testovací plán s PŘESNĚ {test_count} testy.
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
- endpoint musí být přesná cesta z API specifikace (s path parametry jako {{book_id}})
- method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
- Jeden endpoint (method+path) = jeden objekt v poli, s více test_cases uvnitř
- PŘESNĚ {test_count} testů celkem, ani více ani méně
- NEGENERUJ test na reset databáze ani /reset endpoint
{self._rules_block()}
Kontext:
{context}
"""

    def planning_fill_prompt(self, current_plan_json: str, actual: int, target: int) -> str:
        missing = target - actual
        return (
            f"Tento testovací plán má {actual} testů, ale potřebuji PŘESNĚ {target}. "
            f"Přidej {missing} nových testů. Zaměř se na endpointy a scénáře které ještě "
            f"nejsou dostatečně pokryté (edge cases, error handling, validace).\n\n"
            f"Vrať CELÝ plán (starý + nový) jako validní JSON.\n\n"
            f"Aktuální plán:\n{current_plan_json}"
        )

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Generování kódu
    # ══════════════════════════════════════════════════

    def generation_prompt(self, plan_json: str, context: str, base_url: str) -> str:
        return f"""Napiš pytest testy v Pythonu (requests knihovna) pro toto REST API.
BASE_URL = "{base_url}"

PLÁN:
{plan_json}

KONTEXT:
{context}

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
{self._helper_hints_block()}
KVALITA ASERCÍ (důležité pro kvalitu testů):
- Nekontroluj POUZE status kód. Každý test by měl ověřit i odpověď:
  - Happy path (201/200): ověř klíče v response body (assert "id" in data, assert data["name"] == ...)
  - Error (400/404/409/422): ověř assert "detail" in r.json()
  - GET seznam: ověř strukturu (assert "items" in data nebo assert isinstance(data, list))
  - Side effects: po vytvoření objednávky ověř snížení skladu, po smazání ověř 404 na GET
- Příklad dobrého testu:
    def test_create_author_valid():
        name = unique("Author")
        r = requests.post(f"{{BASE_URL}}/authors", json={{"name": name}}, timeout=30)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == name
        assert "id" in data
{self._rules_block()}
Vrať POUZE Python kód, žádný markdown.
"""

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Opravy – izolovaná oprava jednoho testu
    # ══════════════════════════════════════════════════

    def repair_single_prompt(
        self, test_name: str, test_code: str, error_msg: str,
        helpers: str, base_url: str,
        stale_tests: list[str] | None = None,
    ) -> str:
        return f"""Oprav POUZE tuto jednu testovací funkci. Vrať POUZE opravenou funkci.

BASE_URL = "{base_url}"

DOSTUPNÉ HELPERY:
{helpers}

SELHÁVAJÍCÍ TEST:
{test_code}

CHYBA:
{error_msg}

PRAVIDLA:
- Vrať POUZE opravenou funkci (def test_...(): ...), žádné importy ani helpery.
- Neměň název funkce.
- Zachovej timeout=30 na HTTP voláních.
- Používej existující helper funkce, nevymýšlej nové.
- Pokud test ověřuje jen status kód, přidej i kontrolu response body.
{self._rules_block()}{self._stale_block(stale_tests)}
"""

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Opravy – oprava helper funkcí
    # ══════════════════════════════════════════════════

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
{self._helper_hints_block()}
PRAVIDLA:
- Vrať POUZE opravené helpery a importy (vše co je nad test funkcemi).
- Zachovej signatury helperů kompatibilní s existujícími testy.
- Zajisti unikátní názvy přes uuid4 (unique() helper).
- Žádný markdown, jen Python kód.
{self._rules_block()}
"""

    # ══════════════════════════════════════════════════
    #  FÁZE 3: Doplnění chybějících testů
    # ══════════════════════════════════════════════════

    def fill_tests_prompt(
        self, missing: int, helpers: str, existing_names: list[str],
        context: str, base_url: str,
    ) -> str:
        names_str = ", ".join(existing_names)
        return f"""Vygeneruj PŘESNĚ {missing} nových pytest testů pro toto REST API.
BASE_URL = "{base_url}"

DOSTUPNÉ HELPERY (použi je, nevymýšlej nové):
{helpers}

EXISTUJÍCÍ TESTY (tyto názvy NEPOUŽÍVEJ):
{names_str}

KONTEXT API:
{context[:3000]}

PRAVIDLA:
- Vrať POUZE {missing} nových test funkcí (def test_...(): ...).
- Žádné importy, žádné helpery, žádný markdown.
- Každý test musí být self-contained, používat timeout=30, unique() helper.
- Zaměř se na scénáře které existující testy nepokrývají.
- Nekontroluj jen status kód — ověřuj i response body.
{self._rules_block()}
"""