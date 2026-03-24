# Vibe Testing Framework

Diplomová práce zkoumající, jak dobře LLM generuje API testy na základě různé úrovně kontextu.

Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky + diagnostiku.

## Výzkumné otázky

- **RQ1:** Jak úroveň kontextu (L0–L4) ovlivňuje test validity rate a liší se vliv mezi LLM modely?
- **RQ2:** Jak se liší code coverage a endpoint coverage mezi modely a úrovněmi?
- **RQ3:** Jaké typy selhání vznikají (halucinace, sémantické nepochopení, helper bugy) a liší se mezi modely/úrovněmi?

## Rozměry experimentu

5 LLM × 5 úrovní kontextu × 1 API (bookstore, plánované 3) × 5 iterací × 3 runy na kombinaci

## Struktura projektu

```
prompts/
  prompt_templates.py    # Unified prompt framework — PromptBuilder třída
  phase1_context.py      # Sestavení kontextového stringu (L0–L4)
  phase2_planning.py     # Generování JSON test plánu
  phase3_generation.py   # Generování pytest kódu + AST utility + opravy + stale detection
  phase4_validation.py   # Server management (Docker/lokální) + pytest runner
  phase5_metrics.py      # 10 automatických metrik
  phase6_diagnostics.py  # 10 diagnostik pro obhajobu (proč jsou výsledky takové)
main.py                  # Experiment runner — iteruje LLM × API × Level × Run
llm_provider.py          # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek), retry + backoff
run_coverage_manual.py   # Manuální code coverage měření
config.py                # Konfigurace pro manuální skripty
experiment.yaml          # Konfigurace experimentu + framework_rules + api_knowledge
inputs/                  # OpenAPI spec, dokumentace, zdrojový kód, DB schéma, referenční testy
outputs/                 # Vygenerované testy + pytest logy
results/                 # JSON výsledky experimentů (metrics + diagnostics)
```

---

## Pipeline — co se kde děje

### main.py — orchestrátor

Čte `experiment.yaml`, iteruje všechny kombinace LLM × API × Level × Run. Pro každou kombinaci:

1. Vytvoří `PromptBuilder` z `api_cfg` + `level` (level-dependent injection)
2. Vytvoří `StaleTracker` (per run) + `DiagRepairTracker` (per run)
3. Spustí `run_pipeline()` — volá fáze 1–6 sekvenčně
4. Po dokončení všech úrovní pro dané API zastaví server (`stop_managed_server`)
5. Uloží výsledky do `results/experiment_{name}_{timestamp}.json` (metrics + diagnostics)

Klíčový flow v repair loop:
```python
test_code, repair_info = repair_failing_tests(...)  # vrací tuple
diag_repair_tracker.annotate_last(
    repair_type=repair_info["repair_type"],
    repaired_count=repair_info["repaired_count"],
    stale_skipped=repair_info["stale_skipped"],
)
```

`repair_failing_tests()` vrací `tuple[str, dict]` — opravený kód + metadata o provedené opravě. Metadata se zapisují do `DiagRepairTracker` přes `annotate_last()`.

---

### prompt_templates.py — unified prompt framework

Třída `PromptBuilder` — centrální bod pro generování všech promptů.

**Klíčový designový princip (fair experimental design):**

Dva typy instrukcí striktně oddělené:

1. **`framework_rules`** — JAK psát testy (pytest/requests technikálie). Platí pro VŠECHNY levely. Neobsahují žádnou znalost o tom CO API dělá. Příklady: "timeout=30", "nepoužívej fixtures", "na DELETE 204 nevolej .json()". Oponent nemůže namítnout bias — je to ekvivalent "napiš to v Pythonu".

2. **`api_knowledge`** — CO API dělá (chování, pravidla, defaulty). Injektují se POUZE do L1+ (kde tato znalost přirozeně existuje v kontextu — je to v dokumentaci). L0 toto NEDOSTANE. Příklady: "stock default je 0, nastav 10", "not found vrací 404 ne 422", "quantity je delta ne absolutní hodnota".

Tím je zajištěno: **jediná proměnná mezi levely je KONTEXT**, ne skryté hinty.

Implementace: konstruktor `PromptBuilder(api_cfg, level)` — pokud `level == "L0"`, `self.api_knowledge` je prázdný list. Pro L1+ se načte z YAML.

Metody:
- `planning_prompt(context, test_count)` — fáze 2
- `planning_fill_prompt(plan_json, actual, target)` — doplnění plánu
- `generation_prompt(plan_json, context, base_url)` — fáze 3
- `repair_single_prompt(...)` — mikro-oprava jednoho testu
- `repair_helpers_prompt(...)` — oprava helper funkcí
- `fill_tests_prompt(...)` — doplnění chybějících testů

Interní bloky:
- `_framework_block()` — formátuje `framework_rules` (vždy)
- `_knowledge_block()` — formátuje `api_knowledge` (prázdný pro L0)
- `_stale_block()` — seznam zamrzlých testů

**Proč toto oddělení existuje:** V předchozí verzi (v4) existovaly `helper_hints` které se injektovaly do všech levelů včetně L0. Hint "stock: 10" je ale znalost z L1 dokumentace — L0 má mít jen OpenAPI spec. To znehodnocovalo srovnání L0 vs L1. Oponent by řekl: "Váš L0 není čistý black-box."

---

### phase1_context.py — sestavení kontextu

Funkce `analyze_context()` — čistě mechanická, načítá soubory podle úrovně:

| Úroveň | Co načte |
|---|---|
| **L0** | Pouze OpenAPI spec (YAML/JSON → string) |
| **L1** | + byznys dokumentace (`documentation.md`) |
| **L2** | + zdrojový kód endpointů (`source_code.py`) |
| **L3** | + DB schéma (`db_schema.sql`) |
| **L4** | + existující referenční testy (`existing_tests.py`) |

Vrací jeden kontextový string s oddělenými sekcemi (`--- OPENAPI SPECIFIKACE ---`, `--- ZDROJOVÝ KÓD ---` atd.). Phase6 diagnostika `context_size` pak měří velikost každé sekce.

---

### phase2_planning.py — generování test plánu

Funkce `generate_test_plan()`:

1. Zavolá LLM s planning promptem (z `PromptBuilder` — L0 bez api_knowledge, L1+ s ním)
2. Parsuje JSON odpověď (`_parse_plan_json` — strip markdown fences)
3. **Retry loop** (max 4 pokusů): plán má méně testů → doplní, více → ořízne
4. **Post-processing**: `_filter_reset_tests()` PŘED count validací, pak `_trim_plan()`

Výstup: JSON dict s `test_plan` → list endpointů → list `test_cases`.

Bug fix z v3→v4: filtrování reset testů se dříve volalo PO count validaci → plán měl méně testů než požadováno.

---

### phase3_generation.py — generování kódu + opravy

Největší modul. Tři části:

**1. AST utility:**
- `count_test_functions()`, `_get_test_function_names()`
- `_extract_function_code()` / `_replace_function_code()` — per-funkce manipulace
- `_extract_helpers_code()` / `_replace_helpers()` — vše nad prvním testem
- `_remove_last_n_tests()` — deterministické ořezání

Known limitation: `_extract_helpers_code()` předpokládá helpery NAD testy. Pokud LLM vloží helper MEZI testy, helper repair ho nenajde. Phase6 diagnostika `instruction_compliance.helper_between_tests` to detekuje.

**2. Generování + validace počtu:**
- `generate_test_code()` — LLM call, strip markdown fences
- `validate_test_count()` — méně → doplň přes LLM, více → ořízni

**3. Opravná strategie** (`repair_failing_tests()`):

Vrací `tuple[str, dict]` — opravený kód + `repair_info`:
```python
repair_info = {
    "repair_type": "helper_root_cause" | "helper_fallback" | "isolated" | "skipped_all_stale" | None,
    "repaired_count": int,
    "stale_skipped": int,
}
```

Rozhodovací strom:
1. Parsuj failing testy z pytest logu
2. Aktualizuj StaleTracker → přeskoč zamrzlé testy
3. Pokud `_detect_helper_root_cause()` (≥70% stejná chyba) → `_repair_helpers()` → `repair_type="helper_root_cause"`
4. Pokud > MAX_INDIVIDUAL_REPAIRS (10) repairable → `_repair_helpers()` → `repair_type="helper_fallback"`
5. Jinak → `_repair_single_test()` per test → `repair_type="isolated"`
6. Pokud všechny failing jsou stale → `repair_type="skipped_all_stale"`

Invariant: **počet testů se nikdy nemění**. AST validace před/po, revert při neshodě.

**StaleTracker** — normalizuje chyby (čísla→N, stringy→STR), porovnává mezi iteracemi. Test se stejnou chybou ≥2× po sobě = stale → přeskočen při repair, zůstává v kódu (failed test v metrikách).

**Hardcoded konstanty a jejich zdůvodnění:**

| Konstanta | Hodnota | Zdůvodnění |
|---|---|---|
| `StaleTracker.threshold` | 2 | Nejnižší smysluplná hodnota. 1 = jakýkoli fail je stale. |
| `MAX_INDIVIDUAL_REPAIRS` | 10 | ~1/3 test suite (při 30 testech). Víc = drahé per-test LLM cally. |
| `_detect_helper_root_cause` ratio | 0.7 | 50% = příliš agresivní, 90% = příliš konzervativní. |
| `max_iterations` | 5 | Z dat v3: iterace 4–5 přináší minimální zlepšení, ale zachováváme pro úplnost dat. |
| `test_count` | 50 | Zvýšeno z 30: dramaticky zlepšuje EP coverage (91% vs 58% na L0). |

---

### phase4_validation.py — spuštění testů

Funkce `run_tests_and_validate()`:

1. Uloží kód do `outputs/`, zajistí server (Docker/lokální)
2. Resetuje DB (`POST /reset`)
3. Spustí pytest s `--timeout=30`
4. Detekce infra chyb (DB locked, connection refused) → retry (max 2×)
5. Detekce single root cause (≥80% stejná chyba) → FRAMEWORK HINT do logu

Server běží napříč iteracemi — restartuje se jen při výpadku.

---

### phase5_metrics.py — automatické metriky

10 metrik počítaných z vygenerovaného kódu + pytest logu + test plánu:

1. **Test Validity Rate** — passed / total
2. **Endpoint Coverage** — endpointy v plánu vs OpenAPI spec
3. **Assertion Depth** — průměr AST assert statementů na test
4. **Response Validation** — % testů ověřujících response body
5. **Test Type Distribution** — happy_path / error / edge_case z plánu
6. **Status Code Diversity** — unique status kódy v kódu
7. **Empty Test Detection** — testy s 0 asercemi
8. **Avg Test Length** — průměrný počet řádků na test
9. **HTTP Method Coverage** — GET/POST/PUT/DELETE/PATCH distribuce
10. **Plan Adherence** — shoda názvů plán vs kód

Plus `stale_tests` metrika přidávaná v main.py.

Manuální metriky mimo pipeline: code coverage (coverage.py), mutation score (mutmut).

---

### phase6_diagnostics.py — diagnostika pro obhajobu

**Účel:** Neměří kvalitu testů (to dělá phase5). Měří PROČ jsou výsledky takové jaké jsou. Data pro odpovědi na otázky oponenta u obhajoby.

10 diagnostik:

| # | Diagnostika | Otázka oponenta | Co měří |
|---|---|---|---|
| 1 | `context_size` | "Nepřetížili jste model kontextem?" | Znaky, řádky, odhadované tokeny per sekce kontextu |
| 2 | `plan_analysis` | "Proč L2 má víc error testů?" | Distribuce testů per endpoint, per domain, per typ; concentration score |
| 3 | `helper_snapshot` | "Proč L0 order testy selhávají?" | Signatury helperů, default hodnoty, přítomnost stock/unique polí |
| 4 | `prompt_budget` | "Nenarážíte na token limit?" | Využití kontextového okna (kontext + plán + instrukce vs window) |
| 5 | `instruction_compliance` | "Dodržel model vaše instrukce?" | Chybějící timeout, použití unique(), volání /reset, helper mezi testy |
| 6 | `repair_trajectory` | "Kolik iterací bylo potřeba?" | Failing count per iterace, typ opravy, konvergence, never-fixed testy, per-iteration failure details |
| 7 | `failure_taxonomy` | "Jaké typy chyb vznikají?" | Automatická klasifikace: wrong_status_code, helper_cascade, key_error, value_mismatch, unknown_no_error_captured |
| 8 | `code_patterns` | "Jak komplexní jsou testy?" | HTTP callů per test, helper callů, side-effect checks, chaining |
| 9 | `plan_code_drift` | "Generoval model co plánoval?" | Testy jen v plánu / jen v kódu, status kód drift (plán≠kód) |
| 10 | `context_utilization` | "Využil model kontext?" | Pole z kontextu použitá v kódu, halucinované status kódy |

**RepairTracker** (v phase6):
- `record_iteration()` — zaznamenává pytest výsledek + sbírá per-iteration `failure_details` (volá `_extract_error_block` + `_classify_single_failure` pro každý failing test v dané iteraci)
- `annotate_last()` — doplní repair metadata (`repair_type`, `repaired_count`, `stale_skipped`) k poslední iteraci. Volá se v main.py po `repair_failing_tests()`.
- `get_trajectory()` — vrací kompletní trajektorii včetně `failure_categories` (agregace ze všech iterací)

**Failure taxonomy strategie:**
`collect_all_diagnostics()` bere taxonomii z **první iterace** RepairTrackeru (tam jsou čerstvé tracebacky). Pozdější iterace mají stale testy s identickými/zkrácenými chybami. Fallback: parsuj z posledního pytest logu pokud RepairTracker nemá data.

**Error extraction (`_extract_error_block`)** má tři fallback strategie:
1. FAILURES sekce (plný traceback s `_{2,} test_name _{2,}`)
2. Short test summary řádek (`FAILED ...::test_name - error message`)
3. Jakýkoli řádek obsahující test_name + "assert"

---

## experiment.yaml — konfigurace (v5)

```yaml
experiment:
  name: "diplomka_v5"
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 5
  runs_per_combination: 3
  test_count: 50

llms:
  - name: "gemini-2.0-flash"
    provider: "gemini"
    model: "gemini-2.0-flash"
    api_key_env: "GEMINI_API_KEY"
  # + gpt-4o-mini, claude-sonnet, deepseek-chat, gemini-3.1-flash-lite

apis:
  - name: "bookstore"
    docker: true
    source_dir: "../bookstore-api"
    base_url: "http://localhost:8000"
    inputs: { openapi, documentation, source_code, db_schema, existing_tests }

    # JAK psát testy — platí pro VŠECHNY levely:
    framework_rules:
      - "Timeout=30 na každém HTTP volání."
      - "Unikátní stringy přes uuid4."
      - "Na DELETE s 204 nevolej .json()."
      - "Nepoužívej fixtures, conftest, setup_module."
      - "Nevolej /reset endpoint."
      - "Každý test musí být self-contained."

    # CO API dělá — jen pro L1+ (L0 to nedostane):
    api_knowledge:
      - "create_book helper MUSÍ nastavit 'stock': 10, jinak objednávky selžou (API default je 0)."
      - "Helper create_book má mít default published_year=2020. Pro test discountu na NOVOU knihu vytvoř knihu s published_year aktuálního roku PŘÍMO V TESTU."
      - "DELETE /books/{id}/tags používá REQUEST BODY: json={\"tag_ids\": [...]}."
      - "PATCH /books/{id}/stock používá QUERY parametr: params={\"quantity\": N}, ne JSON body."
      - "Stock quantity je DELTA (přičte/odečte), ne absolutní hodnota."
      - "Pro 'not found' endpointy API vrací 404, ne 422."
      - "POST endpointy vracejí 201 při úspěchu, ne 200."
```

---

## Testované API

**Bookstore API** — FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení (kniha starší než rok). Docker režim.

---

## Známé poznatky z experimentů

### Vliv kontextu (v5 data — 1 run, gemini-3.1-flash-lite, 50 testů)

| Level | Validity | EP Coverage | Stale | Iter | Compliance | Poznámka |
|---|---|---|---|---|---|---|
| L0 | 90.0% | 91.18% | 5 | 5 | 80 | Nemá helpery, inline setup |
| L1 | 96.0% | **97.06%** | 2 | 5 | 80 | Nejširší pokrytí endpointů |
| L2 | 98.0% | 82.35% | 1 | 5 | 80 | 46% error testů, vidí zdrojový kód |
| L3 | **100%** | 91.18% | 0 | **2** | 80 | Jediný 100%, repair opravil oba failing |
| L4 | 98.0% | 94.12% | 1 | 5 | **100** | Plný compliance díky referenčním testům |

### Klíčová zjištění z diagnostik

**Context size:** L0=20k tokenů (1 sekce), L4=41k tokenů (5 sekcí). Prompt budget max 36% okna — model má dostatek prostoru.

**Helper snapshot:** L0 nemá create_* helpery — generuje inline setup. L1–L3 mají 4 helpery. L4 má 6 helperů (+tag, +order) s asserty v těle.

**Instruction compliance:** L0–L3 ignorují timeout=30 na 100% HTTP callů. L4 dodržuje díky referenčním testům (in-context learning efekt). Měřitelný finding pro diplomku.

**Status code hallucination:** L0 "halucinoval" 404 (není v OpenAPI spec). Ale 404 je správný! Model odvodil korektní HTTP konvenci z obecných znalostí.

**EP coverage s 50 testy:** Trend "klesá s kontextem" z v4 (30 testů) se nepotvrdil. Byl artefakt malého počtu testů. S 50 testy L1 pokrývá 97%.

**Test type distribution:** L0=68% happy_path, L4=54% error. Více kontextu → více error testů. `plan_analysis.error_focused_endpoints` ukazuje že L4 testuje error na 23 endpointech (vs L0 na 14).

**Plan-code drift:** Opakující se pattern: plán říká 400 (business rule), kód assertuje 422 (Pydantic validace). Model při generování kódu přehodnotí plánovaný status kód.

### Repair loop

- L3 je jediný level kde repair opravil **oba** failing testy (iter 1→2)
- L0: repair opravil 1/6 (stock_negative), zbylých 5 stale
- L1/L2/L4: 0 oprav, failing testy jsou stale od první iterace
- Stale detection funguje: identifikuje neopravitelné testy po 2 iteracích

### Srovnání v4 (30 testů) vs v5 (50 testů)

| Metrika | v4 | v5 | Změna |
|---|---|---|---|
| L0 EP coverage | 58.82% | 91.18% | +32 p.p. (víc testů = víc endpointů) |
| L1 EP coverage | 55.88% | 97.06% | +41 p.p. |
| L0 validity | 80% | 90% | +10 p.p. (bez api_knowledge hints) |
| L3 validity | 100% | 100% | stabilní |

---

## Výstupní JSON struktura

Každý run produkuje objekt s:

```json
{
  "llm": "gemini-2.0-flash",
  "api": "bookstore",
  "level": "L2",
  "run_id": 1,
  "iterations_used": 5,
  "all_tests_passed": false,
  "metrics": {
    "test_validity": { "validity_rate_pct": 98.0 },
    "endpoint_coverage": { "endpoint_coverage_pct": 82.35 },
    "assertion_depth": { "assertion_depth": 1.34 },
    "stale_tests": { "stale_count": 1, "stale_names": ["test_..."] }
  },
  "diagnostics": {
    "context_size": { "total_est_tokens": 34023, "sections": {"OPENAPI": {...}, "SOURCE": {...}} },
    "plan_analysis": { "domain_distribution": {"books": 24, "orders": 10}, "top3_concentration_pct": 20.0 },
    "helper_snapshot": { "helpers": {"create_book": {"has_stock_field": true, "default_published_year": 2020}} },
    "failure_taxonomy": { "categories": {"wrong_status_code": 1}, "per_test": {"test_x": {"category": "...", "error_summary": "..."}} },
    "code_patterns": { "summary": {"avg_http_calls": 1.32, "pct_side_effect_checks": 4.0} },
    "repair_trajectory": {
      "convergence_iteration": 2,
      "never_fixed_tests": ["test_..."],
      "fixed_tests": ["test_..."],
      "failure_categories": {"test_x": "wrong_status_code"},
      "iterations": [{"iteration": 1, "failed": 2, "repair_type": "isolated", "failure_details": {...}}]
    },
    "instruction_compliance": { "missing_timeout": 69, "compliance_score": 80 },
    "context_utilization": { "status_codes_hallucinated": [] },
    "plan_code_drift": { "drift_count": 3, "status_code_drift": {"test_x": {"planned": 400, "actual_in_code": [422]}} }
  }
}
```

---

## Spuštění

```bash
# .env: GEMINI_API_KEY=... OPENAI_API_KEY=... ANTHROPIC_API_KEY=... DEEPSEEK_API_KEY=...
# Docker Desktop musí běžet
python main.py
```

## Manuální code coverage

```bash
# Terminál 1 (bookstore-api):
cd ../bookstore-api && .venv/Scripts/Activate.ps1
coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminál 2 (vibe-testing-framework):
python run_coverage_manual.py outputs/test_generated_{tag}.py

# Terminál 1: Ctrl+C, pak:
coverage json -o coverage_{tag}.json
coverage report
```

## Tech stack

- Python 3.12+, pytest, requests, coverage.py, mutmut
- LLM: Gemini, OpenAI, Claude, DeepSeek (abstrakce v `llm_provider.py`)
- Konfigurace: YAML + dotenv
- Server: Docker compose (doporučený) nebo lokální subprocess