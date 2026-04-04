# Vibe Testing Framework – Dokumentace projektu

## Přehled

Projekt implementuje experimentální framework pro automatické generování API testů pomocí LLM (Large Language Models). Cílem je zkoumat, jak různé úrovně kontextu (L0–L4) ovlivňují kvalitu vygenerovaných pytest testů (RQ1), jak kontext mění testovací strategii modelů (RQ2) a zda se modely z odlišných technologických ekosystémů systematicky liší ve výsledcích (RQ3). Framework funguje jako pipeline o šesti fázích: příprava kontextu -> plánování -> generování kódu -> validace -> metriky -> diagnostika.

Celý experiment je řízen konfiguračním souborem `experiment.yaml` a orchestrován z `main.py`. Výsledky se ukládají jako JSON a lze z nich generovat Markdown reporty.

---

## Architektura pipeline

```
experiment.yaml
      │
      ▼
   main.py  (orchestrátor)
      │
      ├─ Fáze 1: phase1_context.py      -> sestaví kontextový řetězec pro LLM
      ├─ Fáze 2: phase2_planning.py      -> LLM vygeneruje testovací plán (JSON)
      ├─ Fáze 3: phase3_generation.py    -> LLM vygeneruje pytest kód + repair loop
      ├─ Fáze 4: phase4_validation.py    -> spustí testy proti API serveru (Docker)
      ├─ Fáze 5: phase5_metrics.py       -> automatické metriky kvality
      └─ Fáze 6: phase6_diagnostics.py   -> diagnostická data pro analýzu
```

---

## Mapování na výzkumné otázky a hypotézy

### RQ1 - Validita a sémantická kvalita (L0->L4)

Metriky: TVR (phase5: `test_validity`), code coverage (manuální: `run_coverage_manual.py`), endpoint coverage (phase5: `endpoint_coverage`), assertion depth (phase5: `assertion_depth`).

Diagnostika: `context_size`, `helper_snapshot`, `prompt_budget`, `instruction_compliance`, `repair_trajectory` (phase6).

Hypotézy:
- **H1a** (monotónní růst TVR/assertion depth, klesající marginální užitek) - ověřuje se porovnáním přírůstků mezi sousedními levely.
- **H1b** (skok code coverage na L1->L2) - ověřuje se manuálním code coverage měřením (`run_coverage_manual.py`), konkrétně `crud.py` branch coverage.
- **H1c** (neuniformní reakce metrik) - EP coverage vysoká už na L0 vs. strmější assertion depth/code coverage.

### RQ2 - Testovací strategie (distribuce scénářů)

Metriky: `test_type_distribution` (phase5 - happy_path/error/edge_case z plánu), `status_code_diversity` (phase5).

Diagnostika: `plan_analysis` (phase6 - doménová distribuce, error focus), `context_utilization` (phase6 - halucinované status kódy).

Hypotézy:
- **H2a** (posun od happy path k error/edge) - ověřuje se z `test_type_distribution`.
- **H2b** (růst diverzity HTTP status kódů, skok na L2) - ověřuje se z `status_code_diversity`.

### RQ3 - Rozdíly mezi modely z různých ekosystémů

Metriky: všechny metriky z phase5 porovnány napříč LLM modely. Cost-effectiveness = poměr TVR (nebo assertion depth) ku celkovým nákladům na tokeny.

Diagnostika: `repair_trajectory` per model (konvergenční rychlost), `failure_taxonomy` per model (typy selhání), `code_patterns` per model (strategie generování).

Hypotézy:
- **H3a** (konvergence na L0, divergence na L4) - ověřuje se statistickým testem rozdílů TVR mezi modely na L0 vs. L4.
- **H3b** (vyšší cost-effectiveness levnějších modelů) - ověřuje se výpočtem TVR/náklady per model per level.

---

## Detailní popis souborů

### 1. `experiment.yaml`

Centrální konfigurační soubor řídící celý experiment. Tři hlavní sekce:

**Sekce `experiment`:** Globální parametry - název (`diplomka_v11`), úrovně kontextu (`L0`–`L4`), max iterací feedback loopu (5), počet runů na kombinaci (5 pro statistickou validitu), cílový počet testů (30), teplota (0.4).

**Sekce `llms`:** Tři LLM modely z různých ekosystémů:
- Gemini 3.1 Flash Lite Preview (Google, USA) - provider `gemini`
- DeepSeek Chat (DeepSeek, Čína) - provider `deepseek`
- Mistral Large 2411 (Mistral AI, EU/Francie) - provider `mistral`

Každý model má jméno, provider, název modelu pro API a název env proměnné s API klíčem.

**Sekce `apis`:** Definice testovaných API:
- Základní údaje: jméno, Docker režim, zdrojový adresář, base URL, startup wait.
- Vstupní soubory (`inputs`): cesty k OpenAPI specifikaci, dokumentaci, zdrojovému kódu, DB schématu a existujícím testům - každý odpovídá jedné kontextové úrovni.
- `framework_rules`: Technické instrukce pro pytest/requests. Injektují se do **všech** úrovní. Neobsahují žádnou znalost o chování API.
- `api_knowledge`: Prázdný list - specifické znalosti o API byly přesunuty do dokumentace (L1+), aby jediná proměnná mezi levely byl kontext.

---

### 2. `main.py`

Hlavní orchestrátor experimentu.

**Načtení konfigurace:** Čte `experiment.yaml` a `.env`. Vypočítá celkový počet běhů (LLMs × APIs × levels × temperatures × runs).

**`TrackingLLMWrapper`:** Transparentní proxy nad LLM providerem. Zachytává `(text, usage_dict)` z `generate_text()`, zaznamenává tokeny do `TokenTracker` a vrací volajícímu jen text. Phase moduly tak nevyžadují žádné úpravy.

**Funkce `run_pipeline()`:** Spustí jednu kombinaci (1 LLM × 1 API × 1 level × 1 run × 1 temperature):

1. Vytvoří `TokenTracker` a `TrackingLLMWrapper`.
2. Vytvoří `PromptBuilder` z API konfigurace a aktuální úrovně.
3. **Fáze 1** - `analyze_context()` sestaví kontext, `compress_context()` zredukuje tokeny.
4. **Fáze 2** - `generate_test_plan()` vytvoří plán, uloží jako JSON.
5. **Fáze 3** - `generate_test_code()` vygeneruje pytest soubor, `validate_test_count()` zajistí přesný počet.
6. **Feedback loop** (Fáze 3+4 iterativně) - v cyklu do `max_iterations`:
   - Spustí testy přes `run_tests_and_validate()`.
   - Pokud projdou -> konec. Pokud selžou -> `repair_failing_tests()`.
   - `StaleTracker` sleduje opakující se chyby.
   - `DiagRepairTracker` zaznamenává trajektorii oprav.
   - `last_repair_type` zajišťuje alternaci repair strategií.
   - Early stop: všechny failing testy jsou stale -> přerušení cyklu.
7. **Fáze 5** - `calculate_all_metrics()`.
8. **Fáze 6** - `collect_all_diagnostics()`.

Výstup: slovník s timestampem, identifikací běhu, metrikami, diagnostikou, token usage a kompresními statistikami.

**Funkce `main()`:** Vnější smyčky: LLM -> API -> level -> temperature -> run. Po dokončení všech úrovní pro dané API zastaví Docker kontejner. Výsledky všech běhů se uloží do jednoho JSON v `results/`. Na konci vypíše agregované token statistiky a celkovou cenu.

**Tagging systém:** `{llm}__{api}__{level}__run{id}__t{temperature}` pro pojmenování výstupních souborů.

---

### 3. `prompt_templates.py`

Centrální správa promptů. Třída `PromptBuilder` sestavuje prompty z `experiment.yaml`.

**Konstruktor:** `PromptBuilder(api_cfg, level)`. Na L0 je `api_knowledge` prázdný list, na L1+ se načte z konfigurace.

**Interní bloky:**
- `_framework_block()`: Technické požadavky. Vždy přítomen.
- `_knowledge_block()`: Znalosti o API. Prázdný pro L0 - klíčový mechanismus experimentu.
- `_stale_block()`: Seznam zamrzlých testů pro LLM.

**Prompty pro Fázi 2 (plánování):**
- `planning_prompt()`: Analýza API + plán s přesným počtem testů. JSON formát, typy testů (happy_path/edge_case/error), zákaz /reset.
- `planning_fill_prompt()`: Doplnění chybějících testů - dostane aktuální plán.

**Prompty pro Fázi 3 (generování + opravy):**
- `generation_prompt()`: Generování pytest kódu z plánu. Instrukce: unikátní názvy (uuid4), kvalita asercí, side effects.
- `repair_batch_prompt()`: Hromadná oprava více failing testů v jednom promptu.
- `repair_helpers_prompt()`: Oprava helper funkcí při společné root cause.
- `fill_tests_prompt()`: Dogenerování chybějících testů.

---

### 4. `phase1_context.py`

Sestavuje kontextový řetězec. Funkce `analyze_context()`:

| Úroveň | Co načte |
|---|---|
| L0 | Pouze OpenAPI spec (YAML/JSON) |
| L1 | + byznys/technická dokumentace |
| L2 | + zdrojový kód endpointů |
| L3 | + databázové schéma (SQL) |
| L4 | + existující referenční testy (in-context learning) |

Sekce odděleny hlavičkou `--- NÁZEV SEKCE ---`. Chybějící soubor -> varování, pokračuje.

---

### 5. `phase2_planning.py`

Generuje testovací plán (JSON) pomocí LLM.

**`generate_test_plan()`:** Max 4 pokusy k dosažení přesného počtu testů:
1. Generování přes `planning_prompt()`.
2. Filtrování reset testů (`_filter_reset_tests()`) - odstraní endpointy i test_cases s „reset".
3. Doplnění (`planning_fill_prompt()`) nebo ořezání (`_trim_plan()`).

**`_parse_plan_json()`:** 3-úrovňový parser: přímý parse -> regex hledání `test_plan` klíče -> hledání prvního `{` a posledního `}`. Odstraňuje markdown code blocks.

Výstup: `{"test_plan": [{"endpoint": "...", "method": "...", "test_cases": [...]}]}`.

---

### 6. `phase3_generation.py`

Nejkomplexnější modul - generování pytest kódu a iterativní opravy.

**AST Utility:**
- `count_test_functions()`, `_get_test_function_names()`, `_get_function_range()`
- `_extract_function_code()` / `_replace_function_code()`: Extrakce/nahrazení per-funkce.
- `_extract_helpers_code()` / `_replace_helpers()`: Vše nad prvním testem.
- `_remove_last_n_tests()`: Ořezání přebytku.

**Pytest Log Parsing:**
- `_parse_failing_test_names()`: Regex `FAILED\s+\S+::(\w+)`.
- `_extract_error_for_test()`: Chybová hláška (max 1500 znaků).
- `_detect_helper_root_cause()`: ≥70 % stejná normalizovaná chyba -> signal pro helper repair.

**`StaleTracker`:** Sleduje opakující se chyby. Normalizace: čísla->N, stringy->STR, adresy->ADDR. Test je stale pokud má ≥1 izolovanou + ≥1 helper opravu se stejnou normalizovanou chybou.

**`generate_test_code()`:** LLM call, strip markdown fences.

**`validate_test_count()`:** Přebytek -> `_remove_last_n_tests()`. Nedostatek -> `fill_tests_prompt()` + AST validace.

**`repair_failing_tests()`:** Rozhodovací strom:
1. Parsuj failing testy, odfiltruj stale.
2. Pokud všechny stale -> `all_stale_early_stop`.
3. Alternace: `previous_repair_type == "isolated"` -> helper repair, jinak -> batch isolated repair.
4. Aktualizuj stale tracker.

Invariant: počet testů se nemění (AST kontrola před/po, revert při neshodě).

---

### 7. `phase4_validation.py`

Spouští testy proti API serveru přes Docker.

**Docker management:**
- Globální slovník `_docker_servers` - reference napříč iteracemi.
- Server se restartuje jen když neodpovídá na `/health`.
- `docker compose up --build -d`, restart = down + up s `--volumes`.

**`run_tests_and_validate()`:**
1. Uloží kód do `outputs/`.
2. Zajistí Docker kontejner (start/restart).
3. Reset DB (`POST /reset`).
4. Pytest: `-v --tb=short --disable-warnings --timeout=30 --timeout-method=thread`, subprocess timeout 900s.
5. Logy se appendují do `{output}_log.txt`.

**Infra retry:** `database is locked`, `ConnectionRefused`, `Read timed out` -> restart kontejneru + retry (max 2×, 5s delay). Detekce přes kompilovaný regex.

**Single root cause:** ≥80 % stejná normalizovaná chyba -> hint do logu.

---

### 8. `phase5_metrics.py`

9 automatických metrik:

**RQ1 (validita):**
- `parse_test_validity_rate()`: passed/failed/errors z pytest výstupu, `validity_rate_pct`.
- `calculate_assertion_depth()`: Průměrný počet asercí na test (AST).
- `calculate_response_validation()`: % testů kontrolujících response body.
- `calculate_endpoint_coverage()`: % endpointů z OpenAPI spec pokrytých v plánu.
- `calculate_plan_adherence()`: Shoda plánovaných vs vygenerovaných názvů testů.

**RQ2 (strategie):**
- `calculate_test_type_distribution()`: Rozložení happy_path/error/edge_case z plánu.
- `calculate_status_code_diversity()`: Počet unikátních HTTP status kódů.

**Doplňkové:**
- `detect_empty_tests()`: Testy bez asercí.
- `calculate_avg_test_length()`: Průměrný počet řádků na test.

Manuální metriky: code coverage (branch) přes `run_coverage_manual.py` + coverage.py.

---

### 9. `phase6_diagnostics.py`

10 diagnostik - neměří kvalitu testů, ale PROČ jsou výsledky takové:

**RQ1:**
- `measure_context_size()`: Znaky, řádky, odhadované tokeny, rozpad po sekcích.
- `snapshot_helpers()`: Signatury helperů, délky, stock field, default published_year.
- `estimate_prompt_budget()`: Tokeny vs context window.
- `check_instruction_compliance()`: missing_timeout, uses_unique, calls_reset, uses_fixtures -> compliance_score.
- `RepairTracker`: Průběh oprav - passed/failed per iterace, repair_type, konvergenční iterace, never-fixed/fixed, failure categories z 1. iterace.

**RQ2:**
- `analyze_plan()`: Distribuce testů per endpoint/doména, top3 koncentrace, přeskočené endpointy.

**RQ3 (diagnostická podpora):**
- `classify_failures()`: Kategorie: wrong_status_code, helper_cascade, key_error, attribute_error, connection_error, timeout, type_error, json_decode_error, assertion_value_mismatch, other.
- `analyze_code_patterns()`: avg HTTP calls, avg helper calls, % side effect checks, % chaining.
- `analyze_plan_code_drift()`: planned vs actual count, matched/extra, status_code_drift.
- `analyze_context_utilization()`: Endpointy z kontextu vs v plánu, halucinované status kódy.

---

### 10. `llm_provider.py`

Abstrakce nad LLM API providery. 3 provideři se sdílenou retry logikou.

**`LLMProvider` (ABC):** Metoda `generate_text(prompt) -> tuple[str, dict | None]`.

**`RetryMixin`:** Exponenciální backoff (base 30s, max 8 pokusů). Retryable: 503, 429, UNAVAILABLE, RESOURCE_EXHAUSTED, high demand, rate_limit. Globální `call_delay` (5s) mezi voláními.

**Implementace providerů:**
- `GeminiProvider`: `google.genai`, `generate_content()`. Temperature z configu.
- `DeepSeekProvider`: OpenAI-kompatibilní API, base_url `https://api.deepseek.com`. Default temperature 0.7.
- `MistralProvider`: Mistral AI SDK (`mistralai`), `chat.complete()`. Default temperature 0.7, max_tokens 8192.

**Factory `create_llm()`:** Filtruje kwargs podle `inspect.signature()` konstruktoru - předá jen parametry, které daný provider přijímá.

---

### 11. `token_tracker.py`

Přesné měření tokenů z API response (ne odhad chars//3).

**`TokenTracker`:** Akumulátor per run. Zaznamenává phase, prompt/completion/cached tokeny. Agreguje per-phase i celkově. Počítá cenu v USD z pricing tabulky.

**Pricing tabulka:** USD per 1M tokenů pro Gemini, DeepSeek a Mistral modely. Zahrnuje cached_input rate kde je k dispozici.

**Extrakce usage:** Per-provider funkce: `extract_usage_gemini()`, `extract_usage_openai()` (pro DeepSeek), `extract_usage_mistral()`. Vrací jednotný dict `{prompt_tokens, completion_tokens, total_tokens, cached_tokens}`.

---

### 12. `context_compressor.py`

Redukce tokenů bez ztráty sémantické kvality. Per-section komprese:

- **OpenAPI spec** (~40-50% redukce): strip 422 bloků, operationId, tags, validation error schémata.
- **Zdrojový kód** (~25-35%): strip docstringy, celořádkové komentáře, nepoužívané importy.
- **Dokumentace** (~10-15%): duplicitní prázdné řádky, dekorativní řádky, tabulkové oddělovače.
- **DB schéma** (~20%): SQL komentáře, prázdné řádky.
- **Existující testy**: nekomprimovány (in-context learning).

**`CompressionStats`:** Statistiky per sekce pro diagnostiku.

---

### 13. `run_coverage_manual.py`

Automatizované měření code coverage (RQ1: H1b). Kompletní cyklus v jednom příkazu.

**Podporované vstupy:** Jeden soubor, celý adresář (`test_generated_*.py`), glob pattern.

**Workflow `run_single()`:**
1. Vyčistí předchozí `.coverage` data.
2. Spustí server s `coverage run --source app -m uvicorn app.main:app`.
3. Počká na health check, resetuje DB.
4. Spustí pytest.
5. Graceful shutdown serveru (SIGINT) - aby coverage uložil data.
6. Generuje coverage JSON + slim verze.

**`slim_coverage()`:** Redukce na per-file summary + per-function detail jen pro `crud.py` a `main.py`.

**Platform support:** Unix: `os.setsid()` + `os.killpg()`. Windows: `CTRL_C_EVENT`.

---

### 14. `run_metrics_only.py`

Standalone spuštění metrik na existujících vygenerovaných testech. Podporuje `--file`, `--plan`, `--tag` nebo automatický výběr posledního souboru. Vyžaduje běžící server.

---

### 15. `generate_report.py`

Generuje Markdown report z JSON výsledků. Dvousekční report per LLM:
1. Detailní výsledky per run.
2. Průměry pro výzkumné otázky (RQ1, RQ2).

---

### 16. `__init__.py`

Prázdný init - `prompts/` jako Python package.

---

## Klíčové designové principy

**Oddělení framework_rules a api_knowledge:** Jediná nezávislá proměnná je kontext. `framework_rules` vždy, `api_knowledge` pouze L1+.

**AST-based manipulace kódu:** Veškerá manipulace přes Python AST parser. Žádné brittle regex nahrazování.

**Stale detection:** Test s ≥1 izolovanou + ≥1 helper opravou se stejnou chybou -> stale -> přeskočen. Šetří LLM volání, zabraňuje nekonečným smyčkám.

**Alternace repair strategií:** Batch isolated -> helper -> batch isolated -> helper -> ...

**Infra retry:** DB locked, connection refused -> automatický restart Docker kontejneru + retry.

**Invariant: počet testů se nemění.** AST kontrola před/po, revert při neshodě.

**Token tracking:** Přesné měření z API response, per-phase agregace, pricing kalkulace.

**Kontextová komprese:** Per-section komprese bez ztráty sémantického obsahu. Statistiky v diagnostice.

**Docker-only server management:** Všechna API běží přes `docker compose`. Čistý stav přes `down --volumes`.

---

## Struktura výstupů

```
outputs/
  test_generated_{tag}.py      - vygenerovaný testovací soubor
  test_plan_{tag}.json          - testovací plán z LLM
  test_generated_{tag}_log.txt  - pytest logy všech iterací

results/
  experiment_{name}_{timestamp}.json  - kompletní výsledky běhu

coverage_results/
  coverage_{tag}.json           - slim coverage JSON
  summary.json                  - souhrnná tabulka všech coverage měření
```

Každý výsledek v JSON obsahuje: identifikaci běhu, metriky, diagnostiku, token usage, kompresní statistiky a metadata (čas, iterace, status).