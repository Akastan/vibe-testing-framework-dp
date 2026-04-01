# Vibe Testing Framework – Dokumentace projektu

## Přehled

Projekt implementuje experimentální framework pro automatické generování API testů pomocí LLM (Large Language Models). Cílem je zkoumat, jak různé úrovně kontextu (L0–L4) ovlivňují kvalitu vygenerovaných pytest testů (RQ1), jak kontext mění testovací strategii modelů (RQ2) a zda se modely z odlišných technologických ekosystémů systematicky liší ve výsledcích (RQ3). Framework funguje jako pipeline o šesti fázích: příprava kontextu → plánování → generování kódu → validace → metriky → diagnostika.

Celý experiment je řízen konfiguračním souborem `experiment.yaml` a orchestrován z `main.py`. Výsledky se ukládají jako JSON a lze z nich generovat Markdown reporty.

---

## Architektura pipeline

```
experiment.yaml
      │
      ▼
   main.py  (orchestrátor)
      │
      ├─ Fáze 1: phase1_context.py      → sestaví kontextový řetězec pro LLM
      ├─ Fáze 2: phase2_planning.py      → LLM vygeneruje testovací plán (JSON)
      ├─ Fáze 3: phase3_generation.py    → LLM vygeneruje pytest kód + repair loop
      ├─ Fáze 4: phase4_validation.py    → spustí testy proti API serveru
      ├─ Fáze 5: phase5_metrics.py       → automatické metriky kvality
      └─ Fáze 6: phase6_diagnostics.py   → diagnostická data pro analýzu
```

---

## Mapování na výzkumné otázky a hypotézy

### RQ1 — Validita a sémantická kvalita (L0→L4)

Metriky: TVR (phase5: `test_validity`), code coverage (manuální: `run_coverage_manual.py`), endpoint coverage (phase5: `endpoint_coverage`), assertion depth (phase5: `assertion_depth`).

Diagnostika: `context_size`, `helper_snapshot`, `prompt_budget`, `instruction_compliance`, `repair_trajectory` (phase6).

Hypotézy:
- **H1a** (monotónní růst TVR/assertion depth, klesající marginální užitek) — ověřuje se porovnáním přírůstků mezi sousedními levely.
- **H1b** (skok code coverage na L1→L2) — ověřuje se manuálním code coverage měřením (`run_coverage_manual.py`), konkrétně `crud.py` branch coverage.
- **H1c** (neuniformní reakce metrik) — EP coverage vysoká už na L0 vs. strmější assertion depth/code coverage.

### RQ2 — Testovací strategie (distribuce scénářů)

Metriky: `test_type_distribution` (phase5 — happy_path/error/edge_case z plánu), `status_code_diversity` (phase5).

Diagnostika: `plan_analysis` (phase6 — doménová distribuce, error focus), `context_utilization` (phase6 — halucinované status kódy).

Hypotézy:
- **H2a** (posun od happy path k error/edge) — ověřuje se z `test_type_distribution`, prahové hodnoty 60 % (L0) a 40 % (L4).
- **H2b** (růst diverzity HTTP status kódů, skok na L2) — ověřuje se z `status_code_diversity`.

### RQ3 — Rozdíly mezi modely z různých ekosystémů

Metriky: všechny metriky z phase5 porovnány napříč LLM modely. Cost-effectiveness se počítá jako poměr TVR (nebo assertion depth) ku celkovým nákladům na tokeny.

Diagnostika: `repair_trajectory` per model (konvergenční rychlost), `failure_taxonomy` per model (typy selhání), `code_patterns` per model (strategie generování).

Hypotézy:
- **H3a** (konvergence na L0, divergence na L4) — ověřuje se statistickým testem rozdílů TVR mezi modely na L0 vs. L4.
- **H3b** (vyšší cost-effectiveness open-weight) — ověřuje se výpočtem TVR/náklady a assertion_depth/náklady per model per level.

---

## Detailní popis souborů

### 1. `experiment.yaml`

Centrální konfigurační soubor řídící celý experiment. Tři hlavní sekce:

**Sekce `experiment`:** Globální parametry — název (`diplomka_v10`), úrovně kontextu (`L0`–`L4`), max iterací feedback loopu (5), počet runů na kombinaci (5 pro statistickou validitu), cílový počet testů (30) a seznam teplot (`temperatures`). Temperature jako rozměr experimentu umožňuje zkoumat vliv determinismu generování na stabilitu výstupů.

**Sekce `llms`:** Seznam LLM modelů k testování. Každý model má jméno, provider (gemini/openai/claude/deepseek/ollama_compat), název modelu pro API, název env proměnné s API klíčem a volitelné extra parametry (`base_url_env`, `max_tokens`, `num_ctx`, `verify_ssl`). Aktuální konfigurace zahrnuje cloudové modely (Gemini) i lokální modely přes OllamaCompat (Qwen, DeepSeek-R1).

**Sekce `apis`:** Definice testovaných API:
- Základní údaje: jméno, režim (Docker/lokální), zdrojový adresář, base URL, startup wait.
- Vstupní soubory (`inputs`): cesty k OpenAPI specifikaci, dokumentaci, zdrojovému kódu, DB schématu a existujícím testům — každý odpovídá jedné kontextové úrovni.
- `framework_rules`: Technické instrukce pro pytest/requests. Injektují se do **všech** úrovní. Neobsahují žádnou znalost o chování API.
- `api_knowledge`: Specifické znalosti o chování API. Injektují se **pouze do L1+**. Na L0 si model musí vše odvodit z OpenAPI specifikace. Oddělení zajišťuje, že jediná proměnná mezi úrovněmi je množství kontextu.

---

### 2. `main.py`

Hlavní orchestrátor experimentu (v2 — unified prompt framework, v2.1 — temperature jako rozměr).

**Načtení konfigurace:** Čte `experiment.yaml` a `.env`. Vypočítá celkový počet běhů (LLMs × APIs × levels × temperatures × runs).

**Funkce `run_pipeline()`:** Spustí jednu kombinaci (1 LLM × 1 API × 1 level × 1 run × 1 temperature):

1. Vytvoří `PromptBuilder` z API konfigurace a aktuální úrovně.
2. **Fáze 1** — `analyze_context()` sestaví kontext.
3. **Fáze 2** — `generate_test_plan()` vytvoří plán, uloží jako JSON.
4. **Fáze 3** — `generate_test_code()` vygeneruje pytest soubor, `validate_test_count()` zajistí přesný počet.
5. **Feedback loop** (Fáze 3+4 iterativně) — v cyklu do `max_iterations`:
   - Spustí testy přes `run_tests_and_validate()`.
   - Pokud projdou → konec. Pokud selžou → `repair_failing_tests()`.
   - `StaleTracker` sleduje opakující se chyby.
   - `DiagRepairTracker` zaznamenává trajektorii oprav.
   - `last_repair_type` zajišťuje alternaci repair strategií.
6. **Fáze 5** — `calculate_all_metrics()`.
7. **Fáze 6** — `collect_all_diagnostics()`.

Výstup: slovník s timestampem, identifikací běhu (včetně temperature), metrikami, diagnostikou a statusem.

**Funkce `main()`:** Vnější smyčky: LLM → API → level → temperature → run. Pro každou temperature se vytvoří nová LLM instance přes `create_llm()` s extra kwargs (`base_url`, `max_tokens`, `num_ctx`, `verify_ssl`). Po dokončení všech úrovní pro dané API zastaví server. Výsledky všech běhů se uloží do jednoho JSON v `results/`.

**Tagging systém:** `{llm}__{api}__{level}__run{id}__t{temperature}` pro pojmenování výstupních souborů.

---

### 3. `prompt_templates.py`

Centrální správa promptů. Třída `PromptBuilder` sestavuje prompty z `experiment.yaml`.

**Konstruktor:** `PromptBuilder(api_cfg, level)`. Na L0 je `api_knowledge` prázdný list, na L1+ se načte z konfigurace. Knowledge levels: `("L1", "L2", "L3", "L4")`.

**Interní bloky:**
- `_framework_block()`: Technické požadavky. Vždy přítomen.
- `_knowledge_block()`: Znalosti o API. Prázdný pro L0 — klíčový mechanismus experimentu.
- `_stale_block()`: Seznam zamrzlých testů pro LLM.

**Prompty pro Fázi 2 (plánování):**
- `planning_prompt()`: Analýza API + plán s přesným počtem testů. JSON formát, typy testů (happy_path/edge_case/error), zákaz /reset. Kontext nahoře, tvrdá pravidla a JSON vynucení dole.
- `planning_fill_prompt()`: Doplnění chybějících testů — dostane aktuální plán.

**Prompty pro Fázi 3 (generování + opravy):**
- `generation_prompt()`: Generování pytest kódu z plánu. Instrukce: unikátní názvy (uuid4), kvalita asercí (nejen status kód), side effects.
- `repair_single_prompt()`: Mikro-prompt pro opravu jednoho testu. Dostane kód, chybu, helpery, stale testy.
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

Sekce odděleny hlavičkou `--- NÁZEV SEKCE ---`. Chybějící soubor → varování, pokračuje.

---

### 5. `phase2_planning.py`

Generuje testovací plán (JSON) pomocí LLM.

**`generate_test_plan()`:** Max 4 pokusy k dosažení přesného počtu testů:
1. Generování přes `planning_prompt()`.
2. Filtrování reset testů (`_filter_reset_tests()`) — odstraní endpointy i test_cases s „reset".
3. Doplnění (`planning_fill_prompt()`) nebo ořezání (`_trim_plan()`).

**`_parse_plan_json()`:** 3-úrovňový parser: přímý parse → regex hledání `test_plan` klíče → hledání prvního `{` a posledního `}`. Odstraňuje markdown code blocks.

Výstup: `{"test_plan": [{"endpoint": "...", "method": "...", "test_cases": [{"name": "...", "type": "...", "expected_status": N, "description": "..."}]}]}`.

---

### 6. `phase3_generation.py`

Nejkomplexnější modul — generování pytest kódu a iterativní opravy.

**AST Utility:**
- `count_test_functions()`: Počítá `test_*` funkce.
- `_get_test_function_names()`: Seřazený seznam názvů.
- `_get_function_range()`: Rozsah řádků (včetně dekorátorů).
- `_extract_function_code()` / `_replace_function_code()`: Extrakce/nahrazení per-funkce.
- `_extract_helpers_code()` / `_replace_helpers()`: Vše nad prvním testem.
- `_remove_last_n_tests()`: Ořezání přebytku.

**Pytest Log Parsing:**
- `_parse_failing_test_names()`: Regex `FAILED\s+\S+::(\w+)`.
- `_extract_error_for_test()`: Chybová hláška (max 1500 znaků).
- `_detect_helper_root_cause()`: ≥70 % stejná normalizovaná chyba → signal pro helper repair.

**`StaleTracker`:** Sleduje opakující se chyby. Normalizace: čísla→N, stringy→STR, adresy→ADDR. Test se stejnou chybou ≥ threshold (default 2) po sobě jdoucích iterací **kde byl pokus o opravu** = stale. Testy přeskočené kvůli capu nenabírají historii.

**`generate_test_code()`:** LLM call, strip markdown fences.

**`validate_test_count()`:** Přebytek → `_remove_last_n_tests()`. Nedostatek → `fill_tests_prompt()` + AST validace syntaxe.

**`repair_failing_tests()`:** Rozhodovací strom:
1. Parsuj failing testy, aktualizuj StaleTracker, přeskoč stale.
2. Zkontroluj `previous_repair_type`: pokud helper repair nepomohl → přeskoč na izolovaný.
3. `_detect_helper_root_cause()` → `repair_helpers_prompt()`.
4. `> MAX_INDIVIDUAL_REPAIRS` (10) repairable → fallback helper repair.
5. Per-test izolované opravy (max 10, 5s delay).
6. Pokud všechny stale → přeskoč celou opravu.

Invariant: počet testů se nemění (AST kontrola před/po, revert při neshodě).

Vrací `(opravený_kód, repair_info)` — `repair_info` obsahuje `repair_type` (helper_root_cause / helper_fallback / isolated / skipped_all_stale), `repaired_count`, `stale_skipped`.

---

### 7. `phase4_validation.py`

Spouští testy proti API serveru. Dva režimy: lokální (Python subprocess z .venv) a Docker (docker compose).

**Správa serveru:**
- Globální slovníky `_managed_servers` (lokální) a `_docker_servers` (Docker) — reference napříč iteracemi.
- Server se restartuje jen když neodpovídá na `/health`.
- Docker: `docker compose up --build -d`, restart = down + up s `--volumes`.

**`run_tests_and_validate()`:**
1. Uloží kód do `outputs/`.
2. Zajistí server (start/restart).
3. Reset DB (`POST /reset`).
4. Pytest: `-v --tb=short --disable-warnings --timeout=30 --timeout-method=thread`, subprocess timeout 900s.
5. Logy se appendují do `{output}_log.txt`.

**Infra retry:** `database is locked`, `ConnectionRefused`, `Read timed out` → restart serveru + retry (max 2×, 5s delay). Detekce přes kompilovaný regex `_infra_regex`.

**Single root cause:** ≥80 % stejná normalizovaná chyba → hint do logu: „Všechny chyby mají stejnou příčinu, zkontroluj self-contained testy."

---

### 8. `phase5_metrics.py`

9 automatických metrik:

**RQ1 (validita):**
- `parse_test_validity_rate()`: passed/failed/errors z pytest výstupu, `validity_rate_pct`. Fallback na počítání `PASSED`/`FAILED` řetězců.
- `calculate_assertion_depth()`: Průměrný počet asercí na test (AST: `assert` statementy + funkce s „assert" v názvu).
- `calculate_response_validation()`: % testů kontrolujících response body (regex: `.json()[`, `data[`, `"id" in`, `len(`, atd.).
- `calculate_endpoint_coverage()`: % endpointů z OpenAPI spec pokrytých v plánu.
- `calculate_plan_adherence()`: Shoda plánovaných vs vygenerovaných názvů testů.

**RQ2 (strategie):**
- `calculate_test_type_distribution()`: Rozložení happy_path/error/edge_case z plánu.
- `calculate_status_code_diversity()`: Počet unikátních HTTP status kódů (regex `status_code == NNN`).

**Doplňkové:**
- `detect_empty_tests()`: Testy bez asercí.
- `calculate_avg_test_length()`: Průměrný počet řádků na test.

**`calculate_all_metrics()`:** Agreguje vše + `stale_tests` (přidáno v `main.py`).

Manuální metriky: code coverage (branch) přes `run_coverage_manual.py` + coverage.py, mutation score (mutmut).

---

### 9. `phase6_diagnostics.py`

10 diagnostik — neměří kvalitu testů, ale PROČ jsou výsledky takové:

**RQ1:**
- `measure_context_size()`: Znaky, řádky, odhadované tokeny (chars/3), rozpad po sekcích. Odpovídá na: „přetížili jste model?"
- `snapshot_helpers()`: Signatury helperů, délky, stock field, default published_year, aserce. Pro analýzu proč L0 selhává.
- `estimate_prompt_budget()`: Tokeny (kontext + plán + overhead) vs context window. Zbývá dost pro výstup?
- `check_instruction_compliance()`: missing_timeout, uses_unique, calls_reset, uses_fixtures → compliance_score (0–100).
- `RepairTracker`: Průběh oprav — passed/failed per iterace, repair_type, konvergenční iterace, never-fixed/fixed, failure categories z 1. iterace.

**RQ2:**
- `analyze_plan()`: Distribuce testů per endpoint/doména, top3 koncentrace, přeskočené endpointy, error focus.

**RQ3 (diagnostická podpora):**
- `classify_failures()`: Kategorie: wrong_status_code, helper_cascade, key_error, attribute_error, connection_error, timeout, type_error, json_decode_error, assertion_value_mismatch, other, unknown_no_error_captured. Data z první iterace RepairTrackeru.
- `analyze_code_patterns()`: avg HTTP calls, avg helper calls, % side effect checks, % chaining.
- `analyze_plan_code_drift()`: planned vs actual count, matched/extra, status_code_drift.
- `analyze_context_utilization()`: Endpointy z kontextu vs v plánu, halucinované status kódy.

**`collect_all_diagnostics()`:** Agreguje vše. Failure taxonomy preferuje RepairTracker (první iterace).

---

### 10. `llm_provider.py`

Abstrakce nad LLM API providery. 5 providerů se sdílenou retry logikou.

**`LLMProvider` (ABC):** Metoda `generate_text(prompt) → str`.

**`RetryMixin`:** Exponenciální backoff (base 10s, max 5 pokusů). Retryable: 503, 429, UNAVAILABLE, RESOURCE_EXHAUSTED, high demand, rate_limit. Globální `time.sleep(15)` pro free Gemini API.

**Implementace providerů:**
- `GeminiProvider`: `google.genai`, `generate_content()`. Temperature z configu (None → Google default, explicitní → nastaví).
- `OpenAIProvider`: `openai`, `chat.completions.create()`. Default temperature 0.7.
- `ClaudeProvider`: `anthropic`, `messages.create()`, max_tokens 8192. Temperature volitelná.
- `DeepSeekProvider`: OpenAI-kompatibilní, base_url `https://api.deepseek.com`. Default temperature 0.7.
- `OllamaCompatProvider`: Pro lokální modely (Qwen, DeepSeek-R1). OpenAI-kompatibilní API přes `httpx.Client` s volitelným SSL (`verify_ssl`). Konfiguruje `max_tokens`, `num_ctx` (context window), `extra_body={"options": {"num_ctx": N}}`. Strip `<think>...</think>` bloků z reasoning modelů (DeepSeek-R1).

**Factory `create_llm()`:** Filtruje kwargs podle `inspect.signature()` konstruktoru — předá jen parametry, které daný provider přijímá.

---

### 11. `run_coverage_manual.py`

Automatizované měření code coverage (RQ1: H1b). Kompletní cyklus v jednom příkazu.

**Podporované vstupy:** Jeden soubor, celý adresář (`test_generated_*.py`), glob pattern.

**Workflow `run_single()`:**
1. Vyčistí předchozí `.coverage` data.
2. Spustí server s `coverage run --source app -m uvicorn app.main:app`.
3. Počká na health check (`/health`).
4. Resetuje DB (`POST /reset`).
5. Spustí pytest.
6. Graceful shutdown serveru (SIGINT/CTRL_C_EVENT) — aby coverage uložil data.
7. Generuje coverage JSON (`coverage json`).
8. Slim + uloží do `coverage_results/`.

**`slim_coverage()`:** Redukce z ~3000+ řádků na ~100. Per-file summary (covered_lines, num_statements, percent_covered). Per-function detail jen pro `crud.py` a `main.py` (business logika).

**`tag_from_filename()`:** Extrahuje tag z názvu souboru pro pojmenování výstupu: `test_generated_model__bookstore__L0__run1__t0_4.py` → `model__L0__run1`.

**`print_summary()`:** Souhrnná tabulka (tag, coverage %, passed, failed) + průměr. Uloží summary JSON.

**Platform support:** Unix: `os.setsid()` + `os.killpg()` pro graceful SIGINT. Windows: `CTRL_C_EVENT` s dočasným `SIG_IGN` na vlastním procesu.

---

### 12. `generate_report.py`

Generuje Markdown report z JSON výsledků.

**`load_and_aggregate_data()`:** Načte JSONy z `results/`. Extrahuje metriky per run, agreguje průměry per level per LLM. Data ukládá dvakrát — per-run (detailní) a agregovaně (průměry). Přeskakuje chybné runy (`"error"` klíč).

**`generate_markdown()`:** Dvousekční report per LLM:
1. **Detailní výsledky:** Tabulka pro každý run — validity, EP coverage, stale, iterace, empty, assertion depth, response validation, adherence.
2. **Průměry pro výzkumné otázky:** RQ1 (validity, stale, iterace, empty, adherence), RQ2 (EP coverage, assertion depth, avg length, response validation).

---

### 13. `config.py`

Konfigurace pro manuální skripty. Cesty k adresářům, OpenAPI spec, Python interpret v .venv API projektu. Hlavní experiment používá `experiment.yaml`.

---

### 14. `__init__.py`

Prázdný init — `prompts/` jako Python package. Umožňuje `from prompts.prompt_templates import PromptBuilder`.

---

## Klíčové designové principy

**Oddělení framework_rules a api_knowledge:** Jediná nezávislá proměnná je kontext. `framework_rules` vždy, `api_knowledge` pouze L1+.

**AST-based manipulace kódu:** Veškerá manipulace přes Python AST parser. Žádné brittle regex nahrazování.

**Stale detection:** Normalizované chyby ≥2× po sobě → stale → přeskočen. Šetří LLM volání, zabraňuje nekonečným smyčkám. Testy přeskočené kvůli capu nenabírají historii.

**Alternace repair strategií:** helper repair nepomohl → další iterace automaticky izolovaný repair.

**Infra retry:** DB locked, connection refused → automatický restart serveru + retry (ne LLM selhání).

**Invariant: počet testů se nemění.** AST kontrola před/po, revert při neshodě.

**Temperature jako rozměr experimentu:** LLM instance se vytváří per-temperature. Umožňuje zkoumat vliv determinismu na stabilitu.

**Multi-provider architektura:** 5 providerů (cloud + lokální) s jednotným rozhraním. Factory s introspektivním filtrováním kwargs.

---

## Struktura výstupů

```
outputs/
  test_generated_{tag}.py      — vygenerovaný testovací soubor
  test_plan_{tag}.json          — testovací plán z LLM
  test_generated_{tag}_log.txt  — pytest logy všech iterací

results/
  experiment_{name}_{timestamp}.json  — kompletní výsledky běhu

coverage_results/
  coverage_{tag}.json           — slim coverage JSON
  summary.json                  — souhrnná tabulka všech coverage měření
```

Každý výsledek v JSON obsahuje: identifikaci běhu (včetně temperature), metriky, diagnostiku a metadata (čas, iterace, status).