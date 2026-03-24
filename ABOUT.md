# Vibe Testing Framework

Diplomová práce zkoumající, jak dobře LLM generuje API testy na základě různé úrovně kontextu.

Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky + diagnostiku.

## Výzkumné otázky

- **RQ1:** Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje kvalitu LLM-generovaných API testů, měřenou pomocí test validity rate, hloubky asercí a míry validace response body?
- **RQ2:** Jak se liší endpoint coverage a code coverage vygenerovaných testů mezi jednotlivými úrovněmi kontextu?
- **RQ3:** Jaké typy selhání (halucinace, špatné status kódy, timeouty, sémantické chyby) se vyskytují ve vygenerovaných testech a jak se jejich distribuce mění s rostoucím kontextem?

## Rozměry experimentu

5 LLM × 5 úrovní kontextu × 1 API (bookstore) × 5 iterací × 3 runy na kombinaci

---

## Struktura projektu

```
prompts/
  __init__.py              # Package init
  prompt_templates.py      # Unified prompt framework — PromptBuilder třída
  phase1_context.py        # Sestavení kontextového stringu (L0–L4)
  phase2_planning.py       # Generování JSON test plánu
  phase3_generation.py     # Generování pytest kódu + AST utility + opravy + stale detection
  phase4_validation.py     # Server management (Docker/lokální) + pytest runner
  phase5_metrics.py        # 9 automatických metrik
  phase6_diagnostics.py    # 10 diagnostik pro obhajobu
main.py                    # Experiment runner — iteruje LLM × API × Level × Run
llm_provider.py            # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek), retry + backoff
generate_report.py         # Generátor Markdown reportu z JSON výsledků
run_coverage_manual.py     # Manuální code coverage měření
config.py                  # Konfigurace pro manuální skripty
experiment.yaml            # Konfigurace experimentu + framework_rules + api_knowledge
inputs/                    # OpenAPI spec, dokumentace, zdrojový kód, DB schéma, referenční testy
outputs/                   # Vygenerované testy + plány + pytest logy
results/                   # JSON výsledky experimentů (metrics + diagnostics)
```

---

## Pipeline — co se kde děje

### main.py — orchestrátor

Čte `experiment.yaml`, iteruje všechny kombinace LLM × API × Level × Run. Pro každou kombinaci:

1. Vytvoří `PromptBuilder` z `api_cfg` + `level` (level-dependent injection)
2. Vytvoří `StaleTracker` (per run) + `DiagRepairTracker` (per run)
3. Spustí `run_pipeline()` — volá fáze 1–6 sekvenčně
4. Po dokončení všech úrovní pro dané API zastaví server (`stop_managed_server`)
5. Uloží výsledky do `results/experiment_{name}_{timestamp}.json`

Klíčový flow v repair loop:
```python
while iteration < max_iterations and not success:
    success, output_log = run_tests_and_validate(...)
    if not success and iteration < max_iterations:
        test_code, repair_info = repair_failing_tests(
            ...,
            stale_tracker=stale_tracker,
            previous_repair_type=last_repair_type,  # alternace strategií
        )
        last_repair_type = repair_info["repair_type"]
        diag_repair_tracker.annotate_last(
            repair_type=repair_info["repair_type"],
            repaired_count=repair_info["repaired_count"],
            stale_skipped=repair_info["stale_skipped"],
        )
```

`last_repair_type` se předává mezi iteracemi — pokud helper repair nepomohl, další iterace automaticky přepne na izolovanou opravu (zabraňuje opakování nefunkční strategie).

---

### prompt_templates.py — unified prompt framework

Třída `PromptBuilder` — centrální bod pro generování všech promptů.

**Klíčový designový princip (fair experimental design):**

Dva typy instrukcí striktně oddělené:

1. **`framework_rules`** — JAK psát testy (pytest/requests technikálie). Platí pro VŠECHNY levely. Neobsahují žádnou znalost o tom CO API dělá. Příklady: "timeout=30", "nepoužívej fixtures", "na DELETE 204 nevolej .json()".

2. **`api_knowledge`** — CO API dělá (chování, pravidla, defaulty). Injektují se POUZE do L1+. L0 toto NEDOSTANE. Příklady: "stock default je 0, nastav 10", "not found vrací 404 ne 422".

Tím je zajištěno: **jediná proměnná mezi levely je KONTEXT**, ne skryté hinty.

Implementace: konstruktor `PromptBuilder(api_cfg, level)` — pokud `level == "L0"`, `self.api_knowledge` je prázdný list. Knowledge levels jsou definovány jako `("L1", "L2", "L3", "L4")`.

Interní bloky:
- `_framework_block()` — technické požadavky, injektovány vždy
- `_knowledge_block()` — znalost API, prázdný pro L0
- `_stale_block()` — informuje LLM o zamrzlých testech, které nemá opravovat

Metody: `planning_prompt()`, `planning_fill_prompt()`, `generation_prompt()`, `repair_single_prompt()`, `repair_helpers_prompt()`, `fill_tests_prompt()`.

---

### phase1_context.py — sestavení kontextu

Funkce `analyze_context()` — načítá soubory podle úrovně:

| Úroveň | Co načte |
|---|---|
| **L0** | Pouze OpenAPI spec |
| **L1** | + byznys dokumentace |
| **L2** | + zdrojový kód endpointů |
| **L3** | + DB schéma |
| **L4** | + existující referenční testy |

Vrací jeden kontextový string s oddělenými sekcemi (`--- NÁZEV SEKCE ---`). Podporuje YAML i JSON formát OpenAPI specifikace. Pokud soubor pro požadovanou úroveň neexistuje, vypíše varování ale pokračuje.

---

### phase2_planning.py — generování testovacího plánu

Funkce `generate_test_plan()` — iterativní proces (max 4 pokusy) k dosažení přesného počtu testů:

1. Vygeneruje plán přes LLM s `planning_prompt()`
2. Odfiltruje testy na `/reset` endpoint (`_filter_reset_tests()`)
3. Pokud je testů málo → doplní přes `planning_fill_prompt()`
4. Pokud je testů moc → ořízne od konce přes `_trim_plan()`

Výstup: JSON s klíčem `test_plan`, obsahující pole endpointů s vnořenými `test_cases`. Každý test_case má `name`, `type` (happy_path/edge_case/error), `expected_status`, `description`.

---

### phase3_generation.py — generování kódu + opravy

Největší modul. Tři části:

**1. AST utility** — bezpečná manipulace s Python kódem přes Abstract Syntax Tree:
- `count_test_functions()` — počítání testů
- `_get_test_function_names()` — seřazený seznam názvů
- `_extract_function_code()` / `_replace_function_code()` — extrakce/nahrazení per-funkce
- `_extract_helpers_code()` / `_replace_helpers()` — manipulace helperů (vše nad prvním testem)
- `_remove_last_n_tests()` — ořezání přebytku

**2. Generování + validace počtu:**
- `generate_test_code()` — LLM call, strip markdown fences
- `validate_test_count()` — AST kontrola, ořez přebytečných / doplnění chybějících testů

**3. Opravná strategie** (`repair_failing_tests()`):

Rozhodovací strom:
1. Parsuj failing testy z pytest logu (`_parse_failing_test_names()`)
2. Aktualizuj StaleTracker → přeskoč zamrzlé testy
3. Zkontroluj `previous_repair_type`: pokud předchozí iterace zkoušela helper repair a nepomohlo → přeskoč kroky 4–5, jdi rovnou na 6
4. Pokud `_detect_helper_root_cause()` (≥70 % stejná normalizovaná chyba) → oprav helpery (`repair_helpers_prompt`)
5. Pokud > `MAX_INDIVIDUAL_REPAIRS` (10) repairable testů → fallback na helper repair
6. Jinak → per-test izolované opravy (max 10, s 5s delay mezi voláními)
7. Pokud všechny failing jsou stale → přeskoč celou opravu

Invariant: **počet testů se nikdy nemění**. AST validace před/po, pokud se změní → revert.

**StaleTracker** — normalizuje chyby (čísla→N, stringy→STR, adresy→ADDR), porovnává mezi iteracemi. Test se stejnou chybou ≥ `threshold` (default 2) po sobě jdoucích iterací **kde byl pokus o opravu** = stale → přeskočen při repair. Testy přeskočené kvůli capu nenabírají stale historii.

---

### phase4_validation.py — spuštění testů

Podporuje dva režimy: lokální (Python subprocess z .venv) a Docker (docker compose).

1. Uloží kód do `outputs/`, zajistí server (start/restart podle potřeby)
2. Resetuje DB (`POST /reset`) před každým spuštěním
3. Spustí pytest s `--timeout=30 --timeout-method=thread`, celkový subprocess timeout 900s
4. Detekce infra chyb (DB locked, connection refused, timeout) → restart serveru + retry (max 2×)
5. Detekce single root cause (≥80 % stejná chyba) → přidá hint do logu pro LLM
6. Pytest logy se appendují do `{output}_log.txt` pro každou iteraci

Server management: globální slovníky `_managed_servers` (lokální) a `_docker_servers` (Docker) drží reference napříč iteracemi. Server se restartuje jen když přestane odpovídat na `/health`.

---

### phase5_metrics.py — automatické metriky

9 metrik mapovaných na výzkumné otázky:

**RQ1 (validita):**
- `test_validity` — passed/failed/errors z pytest výstupu, validity_rate_pct
- `assertion_depth` — průměrný počet asercí na test (AST: assert statementy + funkce s "assert" v názvu)
- `response_validation` — % testů kontrolujících response body (regex detekce: `.json()[`, `data[`, `"id" in` atd.)
- `test_type_distribution` — rozložení happy_path/error/edge_case z plánu

**RQ2 (pokrytí):**
- `endpoint_coverage` — % endpointů z OpenAPI specifikace pokrytých v plánu
- `plan_adherence` — shoda plánovaných vs skutečně vygenerovaných testů (porovnání názvů)

**RQ3 (selhání):**
- `status_code_diversity` — počet unikátních HTTP status kódů v testech

**Doplňkové:**
- `empty_tests` — testy bez asercí
- `avg_test_length` — průměrný počet řádků na test

Plus `stale_tests` (z StaleTracker) — přidáno v `main.py`.

Manuální metriky mimo pipeline: code coverage (`run_coverage_manual.py` + coverage.py), mutation score (mutmut).

---

### phase6_diagnostics.py — diagnostika pro obhajobu

10 diagnostik — neměří kvalitu testů (to dělá phase5), ale PROČ jsou výsledky takové jaké jsou:

**RQ1:**
- `context_size` — znaky, řádky, odhadované tokeny, rozpad po sekcích
- `helper_snapshot` — signatury helperů, délky, zda obsahují stock field, default published_year
- `instruction_compliance` — missing timeout, uses_unique, calls_reset, uses_fixtures → compliance_score (0–100)
- `prompt_budget` — odhad tokenů (kontext + plán + overhead) vs context window modelu
- `repair_trajectory` — průběh oprav přes iterace (passed/failed, repair_type, konvergenční iterace, never_fixed/fixed testy, failure categories z 1. iterace)

**RQ2:**
- `plan_analysis` — distribuce testů per endpoint/doména, top3 koncentrace, přeskočené endpointy

**RQ3:**
- `failure_taxonomy` — kategorizace selhání: wrong_status_code, helper_cascade, key_error, attribute_error, connection_error, timeout, type_error, json_decode_error, assertion_value_mismatch, other, unknown_no_error_captured. Bere data z **první iterace** RepairTrackeru (čerstvé tracebacky).
- `code_patterns` — avg HTTP calls, avg helper calls, % side effect checks, % chaining
- `plan_code_drift` — planned vs actual count, matched/extra, status_code_drift
- `context_utilization` — endpointy z kontextu vs v plánu, status kódy halucinované vs z kontextu

---

### llm_provider.py — LLM abstrakce

Abstraktní třída `LLMProvider` s metodou `generate_text(prompt) → str`.

**RetryMixin** — sdílená retry logika: exponenciální backoff (base 10s, max 5 pokusů). Retryable kódy: `503`, `429`, `UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `high demand`, `rate_limit`.

**Pozor:** `"Server disconnected"` a podobné connection errory aktuálně NEJSOU v retryable kódech — spadnou při prvním pokusu.

Globální `time.sleep(15)` na úrovni modulu — zpomalení pro free Gemini API (max 15 RPM).

4 providery:
- `GeminiProvider` — `google.genai`, `generate_content()`, **nenastavuje temperature** (Google default)
- `OpenAIProvider` — `openai`, `chat.completions.create()`, temperature=0.7
- `ClaudeProvider` — `anthropic`, `messages.create()`, max_tokens=8192, **nenastavuje temperature**
- `DeepSeekProvider` — OpenAI-kompatibilní API, base_url=`https://api.deepseek.com`, temperature=0.7

Factory: `create_llm(provider, api_key, model)` → instancíruje správný provider.

---

### generate_report.py — Markdown report

Načte JSON výsledky z `results/`, agreguje data per-run i průměry per-level. Generuje dvousekční Markdown:

1. **Detailní výsledky** — tabulka pro každý run se všemi levely a metrikami
2. **Průměry pro výzkumné otázky** — RQ1 (validity, stale, iterace, empty, adherence) a RQ2 (endpoint coverage, assertion depth, avg length, response validation)

---

### run_coverage_manual.py — manuální code coverage

Dvou-terminálový workflow (testy běží proti externímu serveru → coverage se sbírá na straně serveru):

1. `run_tests(test_file)` — ověří server, resetuje DB, spustí pytest
2. `slim_coverage(input, output)` — zredukuje coverage JSON z ~3000+ řádků na ~100 řádků (per-file summary + per-function detail jen pro `crud.py` a `main.py`)

---

### config.py — konfigurace pro manuální skripty

Cesty k adresářům (`outputs/`, `results/`, `inputs/`), cesta k OpenAPI spec, Python interpret v .venv API projektu. Hlavní experiment tyto hodnoty nepoužívá — řídí se `experiment.yaml`.

---

## experiment.yaml — konfigurace (v9)

```yaml
experiment:
  name: "diplomka_v9"
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 5
  runs_per_combination: 3
  test_count: 30

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"

apis:
  - name: "bookstore"
    docker: true
    source_dir: "../bookstore-api"
    base_url: "http://localhost:8000"
    startup_wait: 20.0
    inputs:
      openapi: "inputs/openapi.yaml"
      documentation: "inputs/documentation.md"
      source_code: "inputs/source_code.py"
      db_schema: "inputs/db_schema.sql"
      existing_tests: "inputs/existing_tests.py"

    framework_rules:
      - "Timeout=30 na každém HTTP volání."
      - "Unikátní stringy přes uuid4: unique(prefix) → f'{prefix}_{uuid.uuid4().hex[:8]}'"
      - "Nepoužívej fixtures, conftest, setup_module."
      - "Nevolej /reset endpoint — framework resetuje DB automaticky."
      - "Každý test musí být self-contained (vytvoří si data přes helpery)."
      - "Na DELETE s 204 nevolej .json() — tělo je prázdné."

    api_knowledge:
      - "create_book helper MUSÍ nastavit 'stock': 10, jinak objednávky selžou na insufficient stock (API default je 0)."
      - "Helper create_book má mít default published_year=2020. Pro test discountu na NOVOU knihu vytvoř knihu s published_year aktuálního roku PŘÍMO V TESTU."
      - "DELETE /books/{id}/tags používá REQUEST BODY: json={\"tag_ids\": [...]}."
      - "PATCH /books/{id}/stock používá QUERY parametr: params={\"quantity\": N}, ne JSON body."
      - "Stock quantity je DELTA (přičte/odečte), ne absolutní hodnota."
      - "Pro 'not found' endpointy API vrací 404, ne 422."
      - "POST endpointy vracejí 201 při úspěchu, ne 200."
```

---

## Hardcoded konstanty

| Konstanta | Hodnota | Kde | Zdůvodnění |
|---|---|---|---|
| `StaleTracker.threshold` | 2 | `phase3_generation.py` | Test musí selhat 2× se stejnou chybou než je označen jako stale |
| `MAX_INDIVIDUAL_REPAIRS` | 10 | `phase3_generation.py` | ~1/3 test suite (při 30 testech) |
| `_detect_helper_root_cause` ratio | 0.7 | `phase3_generation.py` | Práh pro detekci společné příčiny selhání |
| `_detect_single_root_cause` ratio | 0.8 | `phase4_validation.py` | Práh pro hint o jednotné root cause |
| `max_iterations` | 5 | `experiment.yaml` | Iterace 4–5 přináší minimální zlepšení |
| `test_count` | 30 | `experiment.yaml` | Počet testů na run |
| `MAX_ATTEMPTS` (plánování) | 4 | `phase2_planning.py` | Max pokusů pro dosažení cílového počtu testů v plánu |
| `INFRA_RETRY_MAX` | 2 | `phase4_validation.py` | Max retry při infra chybách (DB locked, connection) |
| `INFRA_RETRY_DELAY` | 5s | `phase4_validation.py` | Pauza mezi retry při infra chybách |
| `RetryMixin.max_retries` | 5 | `llm_provider.py` | Max retry při LLM API chybách |
| `RetryMixin.base_delay` | 10s | `llm_provider.py` | Base delay pro exponenciální backoff |
| `time.sleep(15)` | 15s | `llm_provider.py` (module-level) | Globální zpomalení pro free Gemini API (15 RPM) |
| `pytest --timeout` | 30s | `phase4_validation.py` | Timeout na jednotlivý test |
| `subprocess timeout` | 900s | `phase4_validation.py` | Celkový timeout na pytest proces |

---

## Testované API

**Bookstore API** — FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení. Docker režim s `docker-compose.yml`.

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

# Slim:
python run_coverage_manual.py --slim ../bookstore-api/coverage_full.json coverage_{tag}.json
```

## Generování reportu

```bash
python generate_report.py
# → last_run_auto.md
```

## Tech stack

- Python 3.12+, pytest, requests, coverage.py, mutmut
- LLM: Gemini, OpenAI, Claude, DeepSeek (abstrakce v `llm_provider.py`)
- Konfigurace: YAML + dotenv
- Server: Docker compose nebo lokální subprocess
- AST manipulace: Python `ast` modul pro bezpečnou práci s kódem