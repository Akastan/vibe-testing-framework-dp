# Vibe Testing Framework

Diplomová práce zkoumající, jak dobře LLM generuje API testy na základě různé úrovně kontextu a jak se liší modely z různých technologických ekosystémů.

Framework přijme OpenAPI spec + kontext -> LLM vygeneruje test plán + pytest suite -> spustí proti reálnému API (Docker) -> iterativně opravuje -> měří metriky + diagnostiku.

## Výzkumné otázky

- **RQ1:** Jak rostoucí úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu a sémantickou kvalitu automaticky generovaných API testů? (TVR, code coverage, endpoint coverage, assertion depth)
- **RQ2:** Jak úroveň poskytnutého kontextu ovlivňuje celkovou testovací strategii modelů - rozložení testovacích scénářů (happy path vs. error states vs. edge cases) a diverzitu ověřovaných HTTP status kódů?
- **RQ3:** Vykazují LLM modely vzniklé v odlišných technologických ekosystémech (USA, EU, Čína) systematické rozdíly v kvalitě generovaných API testů, a mění se tyto rozdíly v závislosti na úrovni kontextu?

## Hypotézy

### H1a - Monotónní růst TVR a assertion depth s klesajícím marginálním užitkem
TVR a assertion depth porostou s kontextem (L0->L4), ale tempo růstu se zpomalí - přírůstky L3->L4 budou významně menší než L0->L1.

### H1b - Ostrý skok code coverage při přechodu na white-box (L1->L2)
Code coverage nebude růst lineárně - teprve zdrojový kód (L2) umožní modelu pokrýt interní větvení a validační logiku.

### H1c - Neuniformní reakce metrik na kontext
Endpoint coverage bude vysoká již na L0 (specifikace vyjmenovává endpointy) a poroste marginálně. Assertion depth a code coverage budou mít strmější růstovou křivku.

### H2a - Posun od happy path k error/edge case s kontextem
Na L0 bude podíl happy path testů >60 %, na L4 klesne pod 40 %.

### H2b - Monotónní růst diverzity HTTP status kódů
Největší skok nastane při přechodu na L2 (zdrojový kód odhaluje návratové kódy pro chybové stavy).

### H3a - Konvergence modelů na L0, divergence na L4
Na L0 nebudou mezi modely z různých ekosystémů statisticky významné rozdíly v TVR. S rostoucím kontextem se rozdíly prohloubí.

### H3b - Vyšší cost-effectiveness modelů s nižší cenou za token
Modely s nižší cenou za token (DeepSeek, Gemini Flash Lite) dosáhnou lepšího poměru kvalita/náklady, nejsilněji na L0–L1.

## Rozměry experimentu

3 LLM × 5 úrovní kontextu × 2 API × 5 iterací × 5 runů × 1 teplota = 150 běhů

Modely:
- **Gemini 3.1 Flash Lite** (Google, USA)
- **DeepSeek Chat** (DeepSeek, Čína)
- **Mistral Large 2411** (Mistral AI, EU/Francie)

---

## Struktura projektu

```
prompts/
  __init__.py              # Package init
  prompt_templates.py      # Unified prompt framework - PromptBuilder třída
  phase1_context.py        # Sestavení kontextového stringu (L0–L4)
  phase2_planning.py       # Generování JSON test plánu
  phase3_generation.py     # Generování pytest kódu + AST utility + opravy + stale detection
  phase4_validation.py     # Docker server management + pytest runner
  phase5_metrics.py        # 9 automatických metrik
  phase6_diagnostics.py    # 10 diagnostik pro obhajobu
main.py                    # Experiment runner - iteruje LLM × API × Level × Temp × Run
llm_provider.py            # LLM abstrakce (Gemini/DeepSeek/Mistral), retry + backoff
token_tracker.py           # Přesné měření tokenů + pricing + per-phase agregace
context_compressor.py      # Komprese kontextu (OpenAPI, zdrojový kód, dokumentace, DB schéma)
generate_report.py         # Generátor Markdown reportu z JSON výsledků
run_coverage_manual.py     # Automatizované code coverage měření (server + testy + slim)
run_metrics_only.py        # Standalone metriky na existujících testech
experiment.yaml            # Konfigurace experimentu + framework_rules
inputs/                    # OpenAPI spec, dokumentace, zdrojový kód, DB schéma, referenční testy
outputs/                   # Vygenerované testy + plány + pytest logy
results/                   # JSON výsledky experimentů (metrics + diagnostics)
coverage_results/          # Výstupní coverage JSONy (slim)
```

---

## Pipeline - co se kde děje

### main.py - orchestrátor

Čte `experiment.yaml`, iteruje všechny kombinace LLM × API × Level × Temperature × Run. Pro každou kombinaci:

1. Vytvoří LLM instanci s konkrétní teplotou přes `create_llm()`
2. Obalí ji `TrackingLLMWrapper` pro automatický token tracking
3. Vytvoří `PromptBuilder` z `api_cfg` + `level` (level-dependent injection)
4. Vytvoří `StaleTracker` (per run) + `DiagRepairTracker` (per run)
5. Spustí `run_pipeline()` - volá fáze 1–6 sekvenčně
6. Po dokončení všech úrovní pro dané API zastaví Docker kontejner
7. Uloží výsledky do `results/experiment_{name}_{timestamp}.json`

Klíčový flow v repair loop:
```python
while iteration < max_iterations and not success:
    success, output_log = run_tests_and_validate(...)
    if not success and iteration < max_iterations:
        test_code, repair_info = repair_failing_tests(
            ...,
            stale_tracker=stale_tracker,
            previous_repair_type=last_repair_type,
        )
        last_repair_type = repair_info["repair_type"]
```

---

### prompt_templates.py - unified prompt framework

Třída `PromptBuilder` - centrální bod pro generování všech promptů.

**Klíčový designový princip (fair experimental design):**

Dva typy instrukcí striktně oddělené:

1. **`framework_rules`** - JAK psát testy (pytest/requests technikálie). Platí pro VŠECHNY levely. Neobsahují žádnou znalost o tom CO API dělá.

2. **`api_knowledge`** - CO API dělá (chování, pravidla, defaulty). Injektují se POUZE do L1+. L0 toto NEDOSTANE.

Tím je zajištěno: **jediná proměnná mezi levely je KONTEXT**, ne skryté hinty.

Metody: `planning_prompt()`, `planning_fill_prompt()`, `generation_prompt()`, `repair_batch_prompt()`, `repair_helpers_prompt()`, `fill_tests_prompt()`.

---

### phase1_context.py - sestavení kontextu

| Úroveň | Co načte                      |
|--------|-------------------------------|
| **L0** | Pouze OpenAPI spec            |
| **L1** | + byznys dokumentace          |
| **L2** | + zdrojový kód endpointů      |
| **L3** | + DB schéma                   |
| **L4** | + existující referenční testy |

---

### phase2_planning.py - generování testovacího plánu

Iterativní proces (max 4 pokusy): generování -> filtrování /reset testů -> doplnění/ořezání na přesný počet.

---

### phase3_generation.py - generování kódu + opravy

Tři části: AST utility, generování + validace počtu, opravná strategie.

Opravná strategie alternuje: batch isolated repair -> helper repair -> batch isolated -> ...

**StaleTracker** - test s ≥1 izolovanou + ≥1 helper opravou se stejnou chybou = stale -> přeskočen.

Invariant: **počet testů se nikdy nemění** (AST kontrola).

---

### phase4_validation.py - spuštění testů (Docker)

1. Zajistí Docker kontejner (start/restart)
2. Reset DB (`POST /reset`)
3. Pytest s `--timeout=30`
4. Infra retry: DB locked, connection refused -> restart + retry (max 2×)
5. Single root cause detection (≥80 %) -> hint do logu

---

### phase5_metrics.py - automatické metriky

9 metrik: test_validity (TVR), assertion_depth, response_validation, endpoint_coverage, plan_adherence, test_type_distribution, status_code_diversity, empty_tests, avg_test_length.

Manuální: code coverage (`run_coverage_manual.py`).

---

### phase6_diagnostics.py - diagnostika pro obhajobu

10 diagnostik: context_size, plan_analysis, helper_snapshot, prompt_budget, instruction_compliance, repair_trajectory, failure_taxonomy, code_patterns, plan_code_drift, context_utilization.

---

### llm_provider.py - LLM abstrakce

3 provideři se společnou retry logikou (RetryMixin):

- `GeminiProvider` - `google.genai`
- `DeepSeekProvider` - OpenAI-kompatibilní API (`api.deepseek.com`)
- `MistralProvider` - Mistral AI SDK

Factory: `create_llm(provider, api_key, model, temperature, **kwargs)`.

---

## Hardcoded konstanty

| Konstanta                         | Hodnota | Kde                    | Zdůvodnění                             |
|-----------------------------------|---------|------------------------|----------------------------------------|
| `MAX_INDIVIDUAL_REPAIRS`          | 10      | `phase3_generation.py` | ~1/3 test suite (při 30 testech)       |
| `_detect_helper_root_cause` ratio | 0.7     | `phase3_generation.py` | Práh pro společnou příčinu             |
| `_detect_single_root_cause` ratio | 0.8     | `phase4_validation.py` | Práh pro hint                          |
| `max_iterations`                  | 5       | `experiment.yaml`      | Iterace 4–5 přináší minimální zlepšení |
| `test_count`                      | 30      | `experiment.yaml`      | Počet testů na run                     |
| `MAX_ATTEMPTS` (plánování)        | 4       | `phase2_planning.py`   | Max pokusů pro plán                    |
| `INFRA_RETRY_MAX`                 | 2       | `phase4_validation.py` | Max retry při infra chybách            |
| `RetryMixin.max_retries`          | 8       | `llm_provider.py`      | Max retry při LLM API chybách          |
| `RetryMixin.base_delay`           | 30s     | `llm_provider.py`      | Base delay exponenciálního backoff     |
| `pytest --timeout`                | 30s     | `phase4_validation.py` | Timeout na test                        |
| `subprocess timeout`              | 900s    | `phase4_validation.py` | Celkový timeout na pytest              |

---

## Testované API

**Bookstore API** - FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení. Docker režim.

---

## Spuštění

```bash
# .env: GEMINI_API_KEY=... DEEPSEEK_API_KEY=... MISTRAL_API_KEY=...
# Docker Desktop musí běžet
python main.py
```

## Code coverage

```bash
python run_coverage_manual.py outputs/test_generated_...__L0__run1__t0_4.py
python run_coverage_manual.py outputs/
python run_coverage_manual.py --slim coverage_full.json coverage_slim.json
```

## Generování reportu

```bash
python generate_report.py
```

## Tech stack

- Python 3.12+, pytest, requests, coverage.py
- LLM: Gemini (google-genai), DeepSeek (openai SDK), Mistral (mistralai SDK)
- Konfigurace: YAML + dotenv
- Server: Docker compose
- AST manipulace: Python `ast` modul