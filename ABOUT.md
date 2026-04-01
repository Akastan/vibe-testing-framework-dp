# Vibe Testing Framework

Diplomová práce zkoumající, jak dobře LLM generuje API testy na základě různé úrovně kontextu a jak se liší modely z různých technologických ekosystémů.

Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky + diagnostiku.

## Výzkumné otázky

- **RQ1:** Jak rostoucí úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu a sémantickou kvalitu automaticky generovaných API testů? (TVR, code coverage, endpoint coverage, assertion depth)
- **RQ2:** Jak úroveň poskytnutého kontextu ovlivňuje celkovou testovací strategii modelů — rozložení testovacích scénářů (happy path vs. error states vs. edge cases) a diverzitu ověřovaných HTTP status kódů?
- **RQ3:** Vykazují LLM modely vzniklé v odlišných technologických ekosystémech (USA, EU, Čína, open-weight) systematické rozdíly v kvalitě generovaných API testů, a mění se tyto rozdíly v závislosti na úrovni kontextu?

## Hypotézy

### H1a — Monotónní růst TVR a assertion depth s klesajícím marginálním užitkem
TVR a assertion depth porostou s kontextem (L0→L4), ale tempo růstu se zpomalí — přírůstky L3→L4 budou významně menší než L0→L1.

### H1b — Ostrý skok code coverage při přechodu na white-box (L1→L2)
Code coverage nebude růst lineárně — teprve zdrojový kód (L2) umožní modelu pokrýt interní větvení a validační logiku.

### H1c — Neuniformní reakce metrik na kontext
Endpoint coverage bude vysoká již na L0 (specifikace vyjmenovává endpointy) a poroste marginálně. Assertion depth a code coverage budou mít strmější růstovou křivku.

### H2a — Posun od happy path k error/edge case s kontextem
Na L0 bude podíl happy path testů >60 %, na L4 klesne pod 40 %.

### H2b — Monotónní růst diverzity HTTP status kódů
Největší skok nastane při přechodu na L2 (zdrojový kód odhaluje návratové kódy pro chybové stavy).

### H3a — Konvergence modelů na L0, divergence na L4
Na L0 nebudou mezi modely z různých ekosystémů statisticky významné rozdíly v TVR. S rostoucím kontextem se rozdíly prohloubí.

### H3b — Vyšší cost-effectiveness open-weight modelů
Open-weight modely dosáhnou lepšího poměru kvalita/náklady na všech úrovních, nejsilněji na L0–L1.

## Rozměry experimentu

N LLM × 5 úrovní kontextu × 1 API (bookstore) × 5 iterací × 5 runů × M teplot na kombinaci

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
main.py                    # Experiment runner — iteruje LLM × API × Level × Temp × Run
llm_provider.py            # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek/OllamaCompat), retry + backoff
generate_report.py         # Generátor Markdown reportu z JSON výsledků
run_coverage_manual.py     # Automatizované code coverage měření (server + testy + slim)
config.py                  # Konfigurace pro manuální skripty
experiment.yaml            # Konfigurace experimentu + framework_rules + api_knowledge
inputs/                    # OpenAPI spec, dokumentace, zdrojový kód, DB schéma, referenční testy
outputs/                   # Vygenerované testy + plány + pytest logy
results/                   # JSON výsledky experimentů (metrics + diagnostics)
coverage_results/          # Výstupní coverage JSONy (slim)
```

---

## Pipeline — co se kde děje

### main.py — orchestrátor

Čte `experiment.yaml`, iteruje všechny kombinace LLM × API × Level × Temperature × Run. Pro každou kombinaci:

1. Vytvoří LLM instanci s konkrétní teplotou přes `create_llm()`
2. Vytvoří `PromptBuilder` z `api_cfg` + `level` (level-dependent injection)
3. Vytvoří `StaleTracker` (per run) + `DiagRepairTracker` (per run)
4. Spustí `run_pipeline()` — volá fáze 1–6 sekvenčně
5. Po dokončení všech úrovní pro dané API zastaví server (`stop_managed_server`)
6. Uloží výsledky do `results/experiment_{name}_{timestamp}.json`

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
```

`last_repair_type` se předává mezi iteracemi — pokud helper repair nepomohl, další iterace automaticky přepne na izolovanou opravu.

Temperature jako rozměr experimentu: `temperatures` list v `experiment.yaml` definuje, přes které teploty se iteruje. LLM instance se vytváří per-temperature.

---

### prompt_templates.py — unified prompt framework

Třída `PromptBuilder` — centrální bod pro generování všech promptů.

**Klíčový designový princip (fair experimental design):**

Dva typy instrukcí striktně oddělené:

1. **`framework_rules`** — JAK psát testy (pytest/requests technikálie). Platí pro VŠECHNY levely. Neobsahují žádnou znalost o tom CO API dělá. Příklady: "timeout=30", "nepoužívej fixtures", "na DELETE 204 nevolej .json()".

2. **`api_knowledge`** — CO API dělá (chování, pravidla, defaulty). Injektují se POUZE do L1+. L0 toto NEDOSTANE. Příklady: "stock default je 0, nastav 10", "not found vrací 404 ne 422".

Tím je zajištěno: **jediná proměnná mezi levely je KONTEXT**, ne skryté hinty.

Implementace: konstruktor `PromptBuilder(api_cfg, level)` — pokud `level == "L0"`, `self.api_knowledge` je prázdný list.

Interní bloky:
- `_framework_block()` — technické požadavky, injektovány vždy
- `_knowledge_block()` — znalost API, prázdný pro L0
- `_stale_block()` — informuje LLM o zamrzlých testech

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

Vrací jeden kontextový string s oddělenými sekcemi (`--- NÁZEV SEKCE ---`).

---

### phase2_planning.py — generování testovacího plánu

Funkce `generate_test_plan()` — iterativní proces (max 4 pokusy):

1. Vygeneruje plán přes LLM s `planning_prompt()`
2. Odfiltruje `/reset` testy (`_filter_reset_tests()`)
3. Doplní chybějící přes `planning_fill_prompt()` nebo ořízne přebytečné přes `_trim_plan()`

Výstup: JSON s `test_plan` obsahující pole endpointů s vnořenými `test_cases`.

---

### phase3_generation.py — generování kódu + opravy

Největší modul. Tři části:

**1. AST utility** — bezpečná manipulace s Python kódem přes AST:
- Počítání, extrakce, nahrazení per-funkce
- Manipulace helperů (vše nad prvním testem)
- Ořezání přebytku

**2. Generování + validace počtu:**
- `generate_test_code()` — LLM call, strip markdown fences
- `validate_test_count()` — AST kontrola, ořez/doplnění

**3. Opravná strategie** (`repair_failing_tests()`):

1. Parsuj failing testy z pytest logu
2. StaleTracker → přeskoč zamrzlé testy
3. Pokud předchozí helper repair nepomohl → přeskoč na izolovaný repair
4. `_detect_helper_root_cause()` (≥70 % stejná chyba) → oprav helpery
5. Pokud > 10 repairable → fallback na helper repair
6. Jinak → per-test izolované opravy (max 10)

Invariant: **počet testů se nikdy nemění**.

**StaleTracker** — normalizuje chyby, test se stejnou chybou ≥2× po sobě = stale → přeskočen.

---

### phase4_validation.py — spuštění testů

Dva režimy: lokální (Python subprocess) a Docker.

1. Uloží kód, zajistí server, resetuje DB (`POST /reset`)
2. Spustí pytest s `--timeout=30`
3. Infra retry: DB locked, connection refused → restart + retry (max 2×)
4. Single root cause detection (≥80 %) → hint do logu

---

### phase5_metrics.py — automatické metriky

9 metrik mapovaných na výzkumné otázky:

**RQ1:** test_validity (TVR), assertion_depth, response_validation, endpoint_coverage, plan_adherence
**RQ2:** test_type_distribution (happy/error/edge), status_code_diversity
**Doplňkové:** empty_tests, avg_test_length

Manuální: code coverage (`run_coverage_manual.py`), mutation score (mutmut).

---

### phase6_diagnostics.py — diagnostika pro obhajobu

10 diagnostik — PROČ jsou výsledky takové:

- `context_size` — tokeny per sekce
- `plan_analysis` — distribuce testů per endpoint/doména
- `helper_snapshot` — signatury, stock field, default year
- `prompt_budget` — tokeny vs context window
- `instruction_compliance` — timeout, unique, reset, fixtures → score
- `repair_trajectory` — průběh oprav, konvergence, never-fixed/fixed
- `failure_taxonomy` — wrong_status_code, helper_cascade, timeout, ...
- `code_patterns` — avg HTTP/helper calls, side effects, chaining
- `plan_code_drift` — planned vs actual, status code drift
- `context_utilization` — endpointy z kontextu vs halucinované kódy

---

### llm_provider.py — LLM abstrakce

5 providerů se společnou retry logikou (RetryMixin):

- `GeminiProvider` — `google.genai`, temperature z configu
- `OpenAIProvider` — `openai`, default temp 0.7
- `ClaudeProvider` — `anthropic`, max_tokens 8192
- `DeepSeekProvider` — OpenAI-kompatibilní, base_url deepseek.com
- `OllamaCompatProvider` — lokální modely přes OpenAI-kompatibilní API, `httpx` klient s volitelným SSL, `num_ctx` konfigurace, strip `<think>` bloků

Factory: `create_llm(provider, api_key, model, temperature, **kwargs)` — filtruje kwargs podle parametrů konstruktoru.

---

### run_coverage_manual.py — automatizované code coverage

Kompletní coverage cyklus v jednom příkazu: spustí server s coverage → testy → zastaví server → generuje JSON → slim.

Podporuje: jeden soubor, celý adresář, glob pattern. Výstup do `coverage_results/`.

---

### generate_report.py — Markdown report

Načte JSON výsledky, agreguje per-run i průměry per-level per-LLM. Dvě sekce: detailní výsledky + průměry pro RQ.

---

## experiment.yaml — konfigurace

```yaml
experiment:
  name: "diplomka_v10"
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 5
  runs_per_combination: 5
  test_count: 30
  temperatures: [0.4]

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"

  - name: "qwen25-coder-32b"
    provider: "ollama_compat"
    model: "qwen2.5-coder:32b-fast"
    api_key_env: "LOCAL_LLM_KEY"
    base_url_env: "LOCAL_LLM_URL"
    max_tokens: 16384
    num_ctx: 32768
    verify_ssl: false

apis:
  - name: "bookstore"
    docker: true
    framework_rules: [...]   # JAK psát testy — všechny levely
    api_knowledge: [...]      # CO API dělá — pouze L1+
```

---

## Hardcoded konstanty

| Konstanta | Hodnota | Kde | Zdůvodnění |
|---|---|---|---|
| `StaleTracker.threshold` | 2 | `phase3_generation.py` | 2× stejná chyba → stale |
| `MAX_INDIVIDUAL_REPAIRS` | 10 | `phase3_generation.py` | ~1/3 test suite (při 30 testech) |
| `_detect_helper_root_cause` ratio | 0.7 | `phase3_generation.py` | Práh pro společnou příčinu |
| `_detect_single_root_cause` ratio | 0.8 | `phase4_validation.py` | Práh pro hint |
| `max_iterations` | 5 | `experiment.yaml` | Iterace 4–5 přináší minimální zlepšení |
| `test_count` | 30 | `experiment.yaml` | Počet testů na run |
| `MAX_ATTEMPTS` (plánování) | 4 | `phase2_planning.py` | Max pokusů pro plán |
| `INFRA_RETRY_MAX` | 2 | `phase4_validation.py` | Max retry při infra chybách |
| `RetryMixin.max_retries` | 5 | `llm_provider.py` | Max retry při LLM API chybách |
| `RetryMixin.base_delay` | 10s | `llm_provider.py` | Base delay exponenciálního backoff |
| `time.sleep(15)` | 15s | `llm_provider.py` | Globální zpomalení pro free Gemini API |
| `pytest --timeout` | 30s | `phase4_validation.py` | Timeout na test |
| `subprocess timeout` | 900s | `phase4_validation.py` | Celkový timeout na pytest |

---

## Testované API

**Bookstore API** — FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení. Docker režim.

---

## Spuštění

```bash
# .env: GEMINI_API_KEY=... OPENAI_API_KEY=... ANTHROPIC_API_KEY=... DEEPSEEK_API_KEY=... LOCAL_LLM_KEY=... LOCAL_LLM_URL=...
# Docker Desktop musí běžet
python main.py
```

## Code coverage

```bash
# Jeden soubor:
python run_coverage_manual.py outputs/test_generated_...__L0__run1__t0_4.py

# Celý adresář:
python run_coverage_manual.py outputs/

# Jen slim:
python run_coverage_manual.py --slim coverage_full.json coverage_slim.json
```

## Generování reportu

```bash
python generate_report.py
# → last_run_auto.md
```

## Tech stack

- Python 3.12+, pytest, requests, coverage.py, mutmut
- LLM: Gemini, OpenAI, Claude, DeepSeek, OllamaCompat (lokální modely)
- Konfigurace: YAML + dotenv
- Server: Docker compose nebo lokální subprocess
- AST manipulace: Python `ast` modul