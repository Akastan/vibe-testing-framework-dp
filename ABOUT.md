# Vibe Testing Framework

Diplomová práce zkoumající, jak dobře LLM generuje API testy na základě různé úrovně kontextu.

Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky.

## Výzkumné otázky

- **RQ1:** Jak úroveň kontextu (L0–L4) ovlivňuje test validity rate a liší se vliv mezi LLM modely?
- **RQ2:** Jak se liší code coverage a endpoint coverage mezi modely a úrovněmi?
- **RQ3:** Jak efektivně detekují vygenerované testy záměrně vnesené chyby (mutation score)?
- **RQ4:** Jaké typy selhání vznikají (halucinace, sémantické nepochopení, helper bugy) a liší se mezi modely/úrovněmi?

## Rozměry experimentu

5 LLM × 5 úrovní kontextu × 3 API × 5 iterací × 3 runy na kombinaci

## Struktura projektu

```
prompts/
  prompt_templates.py    # Unified prompt framework — PromptBuilder třída
  phase1_context.py      # Sestavení kontextového stringu (L0–L4)
  phase2_planning.py     # Generování JSON test plánu
  phase3_generation.py   # Generování pytest kódu + AST utility + opravy + stale detection
  phase4_validation.py   # Server management (Docker/lokální) + pytest runner
  phase5_metrics.py      # 10 automatických metrik
main.py                  # Experiment runner — iteruje LLM × API × Level × Run
llm_provider.py          # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek), retry + backoff
run_coverage_manual.py   # Manuální code coverage měření
config.py                # Konfigurace pro manuální skripty
experiment.yaml          # Konfigurace experimentu + API-specifická pravidla
inputs/                  # OpenAPI spec, dokumentace, zdrojový kód, DB schéma, referenční testy
outputs/                 # Vygenerované testy + pytest logy
results/                 # JSON výsledky experimentů
```

---

## Pipeline — co se kde děje

### main.py — orchestrátor

Čte `experiment.yaml`, iteruje všechny kombinace LLM × API × Level × Run. Pro každou kombinaci:

1. Vytvoří `PromptBuilder` z `api_cfg` (načte `api_rules` a `helper_hints` z YAML)
2. Vytvoří `StaleTracker` (per run, resetuje se mezi runy)
3. Spustí `run_pipeline()` — volá fáze 1–5 sekvenčně
4. Po dokončení všech úrovní pro dané API zastaví server (`stop_managed_server`)
5. Uloží výsledky do `results/experiment_{name}_{timestamp}.json`

### prompt_templates.py — unified prompt framework

Třída `PromptBuilder` — centrální bod pro generování všech promptů. Vytvářena z `api_cfg` (z YAML), injektuje API-specifická pravidla do šablon.

Klíčový princip: **žádné hardcoded API-specifické instrukce v kódu**. Všechna pravidla (jaký status kód vrací DELETE, jak volat PATCH stock, jaký default stock nastavit v helperu) jsou v `experiment.yaml` pod `api_rules` a `helper_hints`.

Metody:
- `planning_prompt()` — fáze 2, generování test plánu
- `planning_fill_prompt()` — doplnění plánu když má méně testů než požadováno
- `generation_prompt()` — fáze 3, generování pytest souboru z plánu
- `repair_single_prompt()` — mikro-oprava jednoho failing testu
- `repair_helpers_prompt()` — oprava helper funkcí při společné root cause
- `fill_tests_prompt()` — doplnění chybějících testů (count validace)

Interní bloky které se injektují do promptů:
- `_rules_block()` — formátuje `api_rules` z YAML
- `_helper_hints_block()` — formátuje `helper_hints` z YAML
- `_stale_block()` — seznam zamrzlých testů (ať je LLM neopravuje)

### phase1_context.py — sestavení kontextu

Funkce `analyze_context()` — čistě mechanická, načítá soubory podle úrovně:

| Úroveň | Co načte |
|---|---|
| **L0** | Pouze OpenAPI spec (YAML/JSON → string) |
| **L1** | + byznys dokumentace (`documentation.md`) |
| **L2** | + zdrojový kód endpointů (`source_code.py`) |
| **L3** | + DB schéma (`db_schema.sql`) |
| **L4** | + existující referenční testy (`existing_tests.py`) |

Vrací jeden velký kontextový string s jasně oddělenými sekcemi (`--- OPENAPI SPECIFIKACE ---`, `--- ZDROJOVÝ KÓD ---` atd.).

### phase2_planning.py — generování test plánu

Funkce `generate_test_plan()`:

1. Zavolá LLM s planning promptem (z `PromptBuilder`)
2. Parsuje JSON odpověď (`_parse_plan_json` — strip markdown fences)
3. **Retry loop** (max 4 pokusů): pokud plán má méně testů → doplní, pokud více → ořízne
4. **Post-processing**: `_filter_reset_tests()` odstraní testy na `/reset` endpoint (model je generuje i přes instrukci), pak `_trim_plan()` na přesný počet

Výstup: JSON dict s `test_plan` → list endpointů → list `test_cases` (name, type, expected_status, description).

Důležité: filtrování reset testů probíhá PŘED count validací (dřívější bug: filtrovalo se až po, takže plán měl méně testů než požadováno).

### phase3_generation.py — generování kódu + opravy

Největší a nejsložitější modul. Tři hlavní části:

**1. AST utility funkce** — manipulace s Python kódem na úrovni AST:
- `count_test_functions()` — počet `test_*` funkcí
- `_get_test_function_names()` — seznam názvů v pořadí
- `_extract_function_code()` / `_replace_function_code()` — extrakce/nahrazení jedné funkce
- `_extract_helpers_code()` / `_replace_helpers()` — vše nad prvním testem (importy, konstanty, helpery)
- `_remove_last_n_tests()` — ořezání přebytečných testů

**2. Generování a validace počtu:**
- `generate_test_code()` — zavolá LLM s generation promptem, vrátí Python kód
- `validate_test_count()` — pokud méně testů → doplní přes LLM, pokud více → ořízne (`_remove_last_n_tests`)

**3. Opravná strategie** (`repair_failing_tests()`):

Rozhodovací strom:
1. Parsuj failing testy z pytest logu (`_parse_failing_test_names`)
2. Aktualizuj `StaleTracker` — přeskoč zamrzlé testy
3. Pokud `_detect_helper_root_cause()` = True (≥70% stejná chyba) → `_repair_helpers()` (oprav helper funkce)
4. Pokud > 10 repairable testů → `_repair_helpers()` jako fallback
5. Jinak → `_repair_single_test()` per failing test (mikro-prompt, 5s pauza mezi cally kvůli rate limitům)

Invariant: **počet testů se nikdy nemění**. AST validace před i po opravě, revert při neshodě.

**StaleTracker** — sleduje normalizované chyby testů napříč iteracemi. Test je "stale" pokud má stejnou chybu ≥2× po sobě. Stale testy se přeskakují při repair (šetří LLM cally), ale zůstávají v kódu (validity metrika je férová — stale test = failed test).

### phase4_validation.py — spuštění testů

Funkce `run_tests_and_validate()`:

1. Uloží kód do `outputs/`
2. Zajistí běžící server (Docker nebo lokální subprocess)
3. Resetuje DB (`POST /reset`)
4. Spustí pytest s `--timeout=30`
5. Detekce infrastrukturních chyb (DB locked, connection refused) → retry (max 2×)
6. Detekce single root cause (≥80% stejná chyba) → přidá FRAMEWORK HINT do logu

Dva režimy serveru:
- **Docker** (`docker: true` v YAML): `docker compose up --build -d`, health check, restart při výpadku
- **Lokální**: Python subprocess z `.venv`, auto-restart

Server běží napříč iteracemi a úrovněmi — restartuje se jen když přestane odpovídat.

### phase5_metrics.py — automatické metriky

10 metrik počítaných z vygenerovaného kódu + pytest logu + test plánu:

1. **Test Validity Rate** — `passed / total` z pytest výstupu
2. **Endpoint Coverage** — endpointy v plánu vs endpointy v OpenAPI spec
3. **Assertion Depth** — průměr AST `assert` statementů na test
4. **Response Validation** — % testů co ověřují response body (regex na `.json()[`, `data[`, `"id" in` atd.)
5. **Test Type Distribution** — happy_path / error / edge_case z plánu
6. **Status Code Diversity** — unique `status_code == NNN` z kódu
7. **Empty Test Detection** — testy s 0 asercemi
8. **Avg Test Length** — průměrný počet řádků na test (AST)
9. **HTTP Method Coverage** — GET/POST/PUT/DELETE/PATCH distribuce z plánu
10. **Plan Adherence** — kolik testů z plánu se vygenerovalo (shoda názvů)

Navíc: **stale_tests** metrika (počet + názvy zamrzlých testů) — přidávána v `main.py`.

Manuální metriky (mimo pipeline): code coverage (coverage.py), mutation score (mutmut).

---

## experiment.yaml — konfigurace

```yaml
experiment:
  name: "diplomka_v4"
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 5
  runs_per_combination: 3
  test_count: 30

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"
  # + další modely...

apis:
  - name: "bookstore"
    docker: true
    source_dir: "../bookstore-api"
    base_url: "http://localhost:8000"
    inputs: { openapi, documentation, source_code, db_schema, existing_tests }

    # API-specifická pravidla injektovaná do promptů přes PromptBuilder:
    api_rules:
      - "DELETE endpointy vracejí 204 s PRÁZDNÝM tělem."
      - "PATCH /books/{id}/stock používá QUERY parametr: params={\"quantity\": N}"
      # ...
    helper_hints:
      - "create_book helper MUSÍ nastavit \"stock\": 10"
      - "Pro test discountu na novou knihu vytvoř knihu ROVNOU přes POST s published_year=2026"
      # ...
```

Klíčové: `api_rules` a `helper_hints` jsou jediné místo kde jsou API-specifické instrukce. Při přidání nového API stačí přidat nový blok v `apis` s odpovídajícími pravidly.

---

## Testované API

**Bookstore API** — FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení (kniha starší než rok). Docker režim.

---

## Známé poznatky z experimentů

### Vliv kontextu
- **L0 (jen spec)** — paradoxně nejstabilnější validity (~96%). Bez kontextu model generuje konzervativní testy.
- **L1 (+ byznys docs)** — nejefektivnější kontext pro pochopení pravidel API.
- **L2/L3 (+ zdrojový kód/DB)** — mohou regresovat. Zdrojový kód vede k halucinacím (neexistující endpointy, PATCH místo PUT).
- **L4 (+ referenční testy)** — zrychluje konvergenci (kopíruje funkční patterny), ale model generuje ambicióznější edge cases které pak selhávají.
- **Více kontextu ≠ automaticky lepší** — neznalost implementace chrání před chybnými předpoklady.

### Typické příčiny selhání
1. **Chybějící stock v helperu** (~33% selhání) — `create_book` bez `stock: 10` → order testy kaskádově padají. Řešeno přes `helper_hints`.
2. **Discount test s PATCH/PUT** (~42%) — model chce změnit `published_year` ale endpoint neexistuje. Řešeno přes `helper_hints`.
3. **Špatný status kód** (~50%) — záměny 422↔404, 400↔409. Částečně opravitelné repair loopem.
4. **Sémantické nepochopení** (~33%) — model neví kolik stock helper nastavuje, nerozumí stock aritmetice.
5. **Halucinace** (~17%) — testy pro chování které API nemá (Content-Type validace, query param validace).

### Repair loop
- Iterace 1→2: největší skok (helper opravy, jednoduché status kódy)
- Iterace 3+: minimální přínos — zbývající failing testy jsou principiálně neopravitelné
- Stale detection šetří ~60 zbytečných LLM callů per experiment

---

## Spuštění

```bash
# .env soubor s API klíči:
# GEMINI_API_KEY=...
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
# DEEPSEEK_API_KEY=...

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