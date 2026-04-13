# Vibe Testing Framework

**Experimentální pipeline pro výzkum automatického generování API testů pomocí velkých jazykových modelů s odstupňovaným kontextem.**

> Framework navržený jako praktická část diplomové práce. Zkoumá, jak úroveň poskytnutého kontextu (od holé OpenAPI specifikace po referenční testy) ovlivňuje validitu, sémantickou kvalitu a strukturální pokrytí automaticky generovaných pytest testů - a zda se tento vliv liší napříč LLM modely z různých technologických ekosystémů.

---

## 1. Výzkumný rámec

### 1.1 Motivace

Generování testů pomocí LLM je atraktivní, ale nedostatečně prozkoumané z hlediska jedné zásadní proměnné: **kolik a jaký kontext model skutečně potřebuje**. Většina existujících přístupů pracuje s fixním vstupem (typicky jen OpenAPI specifikace). Tento framework zavádí pět odstupňovaných úrovní kontextu (L0–L4), které postupně přecházejí od čistě black-box testování k white-box přístupu, a měří dopad každého přírůstku na kvalitu výstupu.

### 1.2 Výzkumné otázky

Framework je navržen tak, aby přímo poskytoval data pro zodpovězení tří výzkumných otázek:

**RQ1 - Validita, kvalita a testovací strategie:** Jak rostoucí úroveň kontextu (L0–L4) ovlivňuje Test Validity Rate, hloubku asercí, distribuci testovacích scénářů a diverzitu ověřovaných HTTP status kódů? Výsledky jsou agregovány přes všechny testované modely.

**RQ2 - Strukturální pokrytí:** Jak úroveň kontextu ovlivňuje endpoint coverage (pokrytí koncových bodů API) a code coverage (pokrytí zdrojového kódu)? Hypotéza předpokládá, že endpoint coverage saturuje brzy (L0), zatímco code coverage vykazuje ostrý skok při zpřístupnění zdrojového kódu (L2).

**RQ3 - Mezimodelové rozdíly:** Vykazují LLM modely z odlišných ekosystémů (americký, čínský, evropský) systematické rozdíly v kvalitě generovaných testů? Zkoumá se konvergence výkonu s rostoucím kontextem a nákladová efektivita (cost-effectiveness) jednotlivých modelů.

### 1.3 Nezávislá proměnná: Kontextové úrovně L0–L4

Klíčovým designovým rozhodnutím je, že **jedinou nezávislou proměnnou mezi úrovněmi je objem poskytnutého kontextu**. Prompt templates, framework rules i API knowledge zůstávají identické - mění se pouze to, co LLM „vidí" jako vstup.

| Úroveň | Obsah kontextu | Charakter testování |
|--------|----------------|---------------------|
| **L0** | OpenAPI specifikace | Čistý black-box |
| **L1** | L0 + byznys/technická dokumentace | Black-box s doménovou znalostí |
| **L2** | L1 + zdrojový kód endpointů | Přechod na white-box |
| **L3** | L2 + databázové schéma (DDL) | White-box s datovým modelem |
| **L4** | L3 + existující testy (in-context learning) | Plný white-box s exempláři |

Sestavení kontextu zajišťuje modul `phase1_context.py`, který na základě parametru `level` podmíněně načítá jednotlivé zdroje a spojuje je do jednoho kontextového řetězce se sekčními oddělovači (`--- NÁZEV SEKCE ---`).

### 1.4 Testované API

Experimentálním subjektem je **Bookstore API** - REST API pro systém knihkupectví implementované v Pythonu (FastAPI + SQLAlchemy + SQLite). API pokrývá 50 koncových bodů napříč 7 doménami (autoři, kategorie, knihy, recenze, tagy, objednávky, administrace) a zahrnuje stavový automat objednávek, soft delete, validaci skladových zásob, M:N relace, API key autentizaci a maintenance mode. Tato komplexnost poskytuje dostatečný prostor pro generování netriviálních testovacích scénářů.

---

## 2. Architektura systému

### 2.1 Přehled modulů

Repozitář je organizován do šesti fází pipeline, podpůrných modulů a konfiguračních souborů:

```
├── main.py                        # Orchestrátor experimentu
├── experiment.yaml                # Deklarativní konfigurace experimentu
│
├── prompts/                       # Fáze pipeline
│   ├── phase1_context.py          # Sestavení kontextu (L0–L4)
│   ├── phase2_planning.py         # Generování testovacího plánu (JSON)
│   ├── phase3_generation.py       # Generování kódu + repair loop
│   ├── phase4_validation.py       # Spuštění testů (Docker/lokální server)
│   ├── phase5_metrics.py          # Automatické metriky kvality
│   ├── phase6_diagnostics.py      # Diagnostická data pro obhajobu
│   └── prompt_templates.py        # Unified Prompt Framework (v7)
│
├── llm_provider.py                # Agnostická LLM abstrakce
├── token_tracker.py               # Přesný token/cost tracking
├── context_compressor.py          # Redukce tokenů kontextu
├── export_inputs.py               # Export vstupních dat z API repozitáře
├── run_coverage_manual.py         # Manuální měření code coverage (RQ2)
│
├── inputs/api1_bookstore/         # Vstupní data pro Bookstore API
│   ├── openapi.yaml               # L0: OpenAPI specifikace
│   ├── documentation.md           # L1: Technická dokumentace
│   ├── source_code.py             # L2: Zdrojový kód (4 soubory spojené)
│   ├── db_schema.sql              # L3: DDL schéma (SQLite)
│   └── existing_tests.py          # L4: Referenční testy
│
├── outputs/                       # Vygenerované testy + pytest logy
└── results/                       # Výsledkové JSON soubory experimentu
```

### 2.2 Odpovědnosti jednotlivých vrstev

**Orchestrace (`main.py`):** Načte `experiment.yaml`, iteruje přes kartézský součin `LLMs × APIs × Levels × Temperatures × Runs`, pro každou kombinaci spustí `run_pipeline()` a agreguje výsledky do výstupního JSON. Klíčovou součástí je `TrackingLLMWrapper` - transparentní proxy, která obaluje libovolného LLM providera a automaticky zachytává tokeny do `TokenTracker` bez nutnosti modifikovat kód fázových modulů.

**Prompt Framework (`prompt_templates.py`, v7):** Třída `PromptBuilder` centralizuje generování všech promptů. Inicializuje se z `api_cfg` (framework rules, API knowledge) a `level`. Každý prompt je sestaven z kontextu, interních bloků (`_framework_block`, `_knowledge_block`, `_context_block`, `_stale_block`) a striktních instrukcí pro výstupní formát. V7 přidává kontext API do repair promptů, takže LLM má při opravách přístup ke specifikaci - ne jen k chybovému hlášení.

**LLM abstrakce (`llm_provider.py`):** Factory pattern s `create_llm()` umožňuje přepínat mezi providery (Gemini, DeepSeek, Mistral) změnou jediného řádku v YAML konfiguraci. Každý provider implementuje `generate_text() -> tuple[str, dict | None]`, kde druhý prvek je standardizovaný usage dict. Sdílená `RetryMixin` třída poskytuje exponenciální backoff s konfigurovatelným maximem 8 pokusů a základní prodlevou 30 sekund, s rozpoznáváním retryable HTTP kódů (429, 503) i textových indikátorů rate limitingu.

**Context Compressor (`context_compressor.py`):** Redukuje vstupní kontext o 25–50 % bez sémantické ztráty. Komprese je per-section: OpenAPI specifikace (odstranění 422 bloků, operationId, tags, validačních schémat), zdrojový kód (strip docstringů, celořádkových komentářů, redundantních importů), dokumentace (deduplikace prázdných řádků, dekorativní řádky), DB schéma (komentáře). Existující testy (L4) se záměrně nekomprimují, protože slouží jako exempláře pro in-context learning. Modul vrací `CompressionStats` s per-section metrikami pro diagnostiku.

---

## 3. Core Pipeline - životní cyklus jednoho běhu

Jeden běh (`run_pipeline`) představuje kompletní cyklus od načtení konfigurace po výstupní JSON s metrikami. Následující popis zachycuje přesný průběh, jak je implementován v `main.py`.

### Fáze 1 - Sestavení a komprese kontextu

Modul `phase1_context.analyze_context()` na základě parametru `level` podmíněně načte vstupní soubory a sestaví je do jednoho řetězce se sekčními oddělovači. Následně `context_compressor.compress_context()` aplikuje per-section kompresi a vrátí komprimovaný kontext spolu se statistikami úspor. Komprese typicky ušetří 30–45 % tokenů na úrovni L2+.

### Fáze 2 - Generování testovacího plánu

`phase2_planning.generate_test_plan()` vygeneruje strukturovaný JSON plán s přesně `test_count` testy (konfigurovatelné, výchozí 30). Plán specifikuje pro každý endpoint sadu test cases s atributy `name`, `type` (happy_path | edge_case | error), `expected_status` a `description`.

Robustnost generování zajišťuje iterativní smyčka (max 4 pokusy):
1. Generování základního plánu
2. Filtrování `/reset` testů (`_filter_reset_tests`)
3. Kontrola počtu - pokud chybí testy, doplnění přes `planning_fill_prompt`
4. Pokud je testů více než cíl, ořez od konce (`_trim_plan`)
5. Finální filtrování a validace přesného počtu

JSON parsing je tříúrovňový: přímý parse -> regex hledání `test_plan` klíče -> hledání prvního `{` a posledního `}`. Tato odolnost je nezbytná, protože LLM modely občas obalí JSON do prose textu nebo markdown bloků.

### Fáze 3 - Generování kódu

`phase3_generation.generate_test_code()` převede plán na spustitelný Python kód (pytest + requests). Vygenerovaný kód prochází automatickými post-processingovými kroky:

- **Import Sanitizer:** Odstraňuje nedostupné knihovny (PIL, numpy, pandas, ...) a automaticky přidává chybějící importy standardní knihovny na základě detekce vzorů v kódu (např. `datetime.now` -> `from datetime import datetime`).
- **Truncation Detection:** Pokud je kód syntakticky nevalidní (typicky kvůli `max_tokens` limitu), `_salvage_truncated_code()` postupně ořezává od konce, dokud AST parse neprojde - zachrání tak maximum kompletních testů.
- **Count Validation:** `validate_test_count()` zajistí, že počet testů odpovídá plánu - buď ořízne přebytečné testy od konce, nebo vygeneruje doplňkové testy přes `fill_tests_prompt`.

### Fáze 3+4 - Iterativní Repair Loop

Jádro frameworku. Po počátečním generování vstupuje kód do smyčky (max `max_iterations`, výchozí 7), kde se střídají validace (Fáze 4) a opravy (Fáze 3):

```
┌─────────────────────────────────────────────┐
│  Iterace 1..max_iterations                  │
│                                             │
│  1. Uloží kód -> spustí pytest (Fáze 4)     │
│  2. Všechny testy prošly? -> KONEC           │
│  3. Stale filtrování (refresh + detect)     │
│  4. Všechny failing jsou stale? -> EARLY STOP│
│  5. Rozhodnutí: isolated vs. helper repair  │
│  6. LLM oprava -> AST splice -> zpět na 1.   │
└─────────────────────────────────────────────┘
```

#### Dva typy oprav

**Isolated Repair:** Opravuje jednotlivé selhávající testy. LLM dostane kód testu, chybové hlášení, dostupné helpery a API kontext. Odpověď se parsuje přes AST a jednotlivé funkce se chirurgicky nahrazují v master kódu pomocí `_replace_function_code()`. Batch mode - opravuje až `MAX_INDIVIDUAL_REPAIRS` (10) testů v jednom LLM callu.

**Helper Repair:** Opravuje sdílené helper funkce (create_book, create_author, unique, ...). Aktivuje se, když root cause analýza zjistí, že ≥70 % selhání má normalizovaně stejnou chybu (`_detect_helper_root_cause`). LLM dostane kompletní blok helperů, ukázky chyb a API kontext. Nové helpery procházejí safety validací (`_validate_helpers_safe`): nesmí ztratit žádný import ani helper funkci oproti originálu.

#### Alternační logika (v5)

Typ opravy se střídá podle sofistikované logiky:

| Předchozí oprava | Chyby se změnily? | Další akce |
|------------------|-------------------|------------|
| Žádná (1. iterace) | -                 | Isolated |
| Isolated | -                 | Helper |
| Helper | Ano (≥50 % testů) | **Znovu helper** (progres!) |
| Helper | Ne                | Isolated |

Tato alternace zabraňuje oscilaci: pokud helper repair udělal progres (chyby se změnily), dostane další šanci místo přepnutí na isolated. Detekce progresu probíhá porovnáním normalizovaných chybových hlášení (`_normalize_error` redukuje čísla na `N`, řetězce na `STR`, adresy na `ADDR`).

#### StaleTracker - prevence zacyklení

`StaleTracker` sleduje opakující se chyby testů napříč iteracemi. Test je označen jako **stale**, pokud:
1. Má alespoň jeden pokus o izolovanou opravu
2. Má alespoň jeden pokus o helper opravu
3. Poslední chyba z obou typů je identická (normalizovaně)

Stale testy jsou vyřazeny z repair kandidátů, čímž se šetří LLM tokeny. Klíčová je metoda `refresh_with_current_errors()` (v5): pokud se chyba stale testu mezitím změnila (typicky jako vedlejší efekt helper repair), test se **odblokuje** a dostane novou šanci.

Pokud jsou **všechny** failing testy stale, framework provede **early stop** - ušetří zbývající iterace a příslušné LLM cally, protože další opravy by byly zbytečné.

#### Bezpečnostní mechanismy

- **Regression Rollback:** Po každé opravě se porovná počet testů před a po. Pokud se liší (LLM omylem smazal nebo přidal testy), změna se revertuje.
- **AST Validation:** Každá opravená funkce i celý kód procházejí `ast.parse()` - syntakticky nevalidní opravy se tiše přeskočí.
- **Regex Fallback:** Pokud AST parsing response selže, `_extract_functions_regex()` zkusí extrahovat funkce přes regulární výraz.

### Fáze 4 - Spuštění testů v izolovaném prostředí

`phase4_validation.run_tests_and_validate()` zajišťuje celý životní cyklus testovacího prostředí:

1. **Server Management:** Podpora lokálního režimu (Python subprocess z `.venv`) i Docker režimu (`docker compose up`). Server běží persistentně napříč iteracemi - restartuje se pouze při selhání health checku. API Identity Tracking zajišťuje, že na daném portu vždy běží správné API (klíčové při sekvenčním testování více API).

2. **Database Reset:** Před každým pytest spuštěním se volá `/reset` endpoint. Preventivně se kontroluje a vypíná maintenance mode (řeší „poisoning" - test zapnul maintenance a nestihl ho vypnout).

3. **Pytest Execution:** `pytest -v --tb=short --timeout=30 --timeout-method=thread` s globálním limitem 900 sekund. Logy se ukládají do souborů pro pozdější analýzu.

4. **Infrastructure Retry:** Detekce infrastrukturních chyb (DB locked, connection refused, maintenance poisoning) s automatickým retry (max 2 pokusy, 5s prodleva). Infrastrukturní chyby se nepředávají LLM k opravě - to by bylo plýtvání tokeny.

5. **Single Root Cause Detection:** Pokud ≥80 % selhání má identickou normalizovanou chybu, framework to rozpozná a přidá do logu hint pro LLM.

### Fáze 5 - Automatické metriky

`phase5_metrics.calculate_all_metrics()` vyhodnocuje kvalitu vygenerovaných testů pomocí devíti metrik:

| Metrika | RQ | Co měří | Jak                                                      |
|---------|----|---------|----------------------------------------------------------|
| **Test Validity Rate** | RQ1 | % testů které projdou | Parsování pytest výstupu (passed/failed/errors)          |
| **Endpoint Coverage** | RQ2 | % API endpointů pokrytých plánem | Průnik endpointů z OpenAPI spec a test_plan              |
| **Assertion Depth** | RQ1 | Průměrný počet asercí na test | AST analýza - `assert` statementy + volání assert funkcí |
| **Response Validation** | RQ1 | % testů ověřujících response body | Regex detekce vzorů `.json()[`, `data[`, `"id" in` atd.  |
| **Test Type Distribution** | RQ1/RQ3 | Rozložení happy_path / error / edge_case | Agregace z test_plan                                     |
| **Status Code Diversity** | RQ3 | Počet unikátních ověřovaných status kódů | Regex `status_code == \d{3}` ve vygenerovaném kódu       |
| **Empty Tests** | RQ1 | Počet testů bez asercí | Per-test AST analýza                                     |
| **Avg Test Length** | RQ1 | Průměrná délka testu v řádcích | AST `end_lineno - lineno`                                |
| **Plan Adherence** | RQ1 | % plánovaných testů přítomných v kódu | Průnik názvů z plánu a z AST                             |

Navíc se počítá **Token Efficiency** (cost-effectiveness): `(tests_passed × assertion_depth) / cost_usd` - metrika přímo adresující hypotézu H3b o nákladové efektivitě modelů.

### Fáze 6 - Diagnostika pro obhajobu

`phase6_diagnostics.collect_all_diagnostics()` generuje data, která neměří kvalitu testů, ale **vysvětlují proč jsou výsledky takové, jaké jsou**. Slouží primárně pro odpovědi na otázky oponenta:

| Diagnostika | Odpovídá na                                                                                  |
|-------------|----------------------------------------------------------------------------------------------|
| **Context Size** | „Nepřetížili jste model?" - per-section rozpad (chars, lines, est_tokens)                    |
| **Plan Analysis** | Koncentrace testů per endpoint, doménová distribuce, přeskočené endpointy                    |
| **Helper Snapshot** | Proč L0 selhává - signatury helperů, přítomnost stock/assertion/default year                 |
| **Prompt Budget** | Kolik kontextového okna zabírá prompt vs. kolik zbývá pro výstup                             |
| **Instruction Compliance** | Dodržení framework rules - timeout, unique helper, reset, fixtures (skóre 0–100)             |
| **Failure Taxonomy** | Klasifikace selhání do kategorií: wrong_status_code, helper_cascade, key_error, timeout, ... |
| **Repair Trajectory** | Per-iterace záznam: passed/failed, repair_type, stale_count - vizualizace konvergence        |
| **Code Patterns** | Průměrný počet HTTP callů a helperů na test, % side-effect checks, % chaining                |
| **Plan-Code Drift** | Kolik testů z plánu chybí v kódu, kolik přebývá, drift status kódů                           |
| **Context Utilization** | Které status kódy z kontextu se objevily v testech vs. které jsou „halucinované"             |

`RepairTracker` (diagnostický) zaznamenává trajektorii oprav po iteracích, včetně failure details z první iterace (čerstvé tracebacky pro taxonomii).

---

## 4. Klíčové inženýrské mechanismy

### 4.1 Zpracování a izolace kontextu

Kontextový řetězec je sestavován inkrementálně s jasnými sekčními oddělovači. Toto má dva účely: (1) LLM vidí strukturovaný vstup s explicitními sekcemi, (2) `context_compressor` dokáže aplikovat per-section kompresi. Oddělovač `--- NÁZEV SEKCE ---` slouží současně jako parsovatelný marker pro kompresor i jako vizuální separátor pro LLM.

Důležité designové rozhodnutí: `api_knowledge` v `experiment.yaml` je od verze v11 prázdné pole. Veškeré doménové hinty byly přesunuty do `documentation.md` (sekce „Poznámky pro integraci a testování"), čímž se zajistilo, že **jedinou nezávislou proměnnou mezi levely je skutečně jen objem kontextu** - ne skryté hinty v konfiguraci.

### 4.2 Unified Prompt Framework

`PromptBuilder` (v7) centralizuje veškerou prompt engineering logiku. Klíčové vlastnosti:

- **Level-aware knowledge block:** `_knowledge_block()` se aktivuje pouze pro L1+ úrovně - na L0 model nemá přístup k doménovým hintům.
- **Context-aware repair prompty:** Od v7 obsahují `repair_batch_prompt` i `repair_helpers_prompt` zkrácený API kontext (max 4000 znaků), takže LLM při opravách rozumí očekávanému chování API.
- **Stale block:** `_stale_block()` informuje LLM o neopravitelných testech, aby na ně neplýtval kapacitou.
- **Framework rules z YAML:** Pravidla jako „timeout=30 na každém HTTP volání" nebo „na DELETE s 204 nevolej .json()" jsou deklarativně konfigurována v `experiment.yaml` a automaticky vkládána do promptů.
- **Striktní output instrukce:** Každý prompt končí explicitním požadavkem na formát výstupu (`ONLY VALID JSON` / `ONLY VALID PYTHON CODE`, `NO MARKDOWN BLOCKS`).

### 4.3 Agnostická LLM integrace

Architektura je navržena tak, aby přidání nového providera vyžadovalo implementaci jediné metody `generate_text() -> tuple[str, dict | None]`:

- **Factory pattern:** `create_llm(provider, api_key, model, temperature)` s automatickým filtrováním kwargs podle signatury konstruktoru.
- **Retry logika:** Sdílená `RetryMixin` s exponenciálním backoffem (30s base, max 240s cap, 8 pokusů). Rozpoznává retryable patterns jak z HTTP kódů (429, 503), tak z textových zpráv (`rate_limit`, `RESOURCE_EXHAUSTED`, `Too Many Requests`). Mezi cally se vkládá `call_delay` (5s) jako prevence rate limitingu.
- **Token tracking:** Transparentní - `TrackingLLMWrapper` zachytává usage dict z každého LLM callu a zapisuje ho do `TokenTracker` s metadaty o fázi a detailu. Fázové moduly volají `wrapper.generate_text(prompt) -> str` beze změny - neví o trackingu.

### 4.4 Přesný Token a Cost Tracking

`TokenTracker` akumuluje per-call záznamy s rozlišením fáze (planning, generation, generation_fill, repair) a volitelným detailem (iter2_helper). Agreguje prompt_tokens, completion_tokens, total_tokens a cached_tokens.

Cost model využívá tabulku `DEFAULT_PRICING` s cenami per 1M tokenů (duben 2026) pro všechny podporované modely. Podporuje cached input pricing (Gemini, DeepSeek) - rozlišuje non-cached a cached prompt tokeny a počítá reálnou úsporu díky cachování.

Výstup: `summary()` (plný breakdown per phase) a `summary_slim()` (flat dict pro rychlou agregaci) - obojí se ukládá do výsledkového JSON.

### 4.5 AST-based Code Manipulation

Veškeré manipulace s vygenerovaným kódem probíhají přes Python AST, nikoliv přes textové nahrazování:

- `_get_function_range()` - lokalizuje funkci v kódu (start line, end line, včetně dekorátorů)
- `_replace_function_code()` - chirurgicky nahradí jednu funkci, zbytek kódu zůstane nedotčen
- `_extract_helpers_code()` - extrahuje vše před prvním `test_` funkcí
- `_replace_helpers()` - nahradí helper blok při zachování testů
- `_remove_last_n_tests()` - odebírá testy od konce (pro count trimming)
- `count_test_functions()` - spolehlivý počet testů (vs. regex který by mohl chybovat)

Každá mutace prochází `ast.parse()` validací - syntakticky nevalidní výsledek se tiše zahodí a ponechá se originál.

---

## 5. Datové struktury a výstupní formáty

### 5.1 Experiment YAML

Deklarativní konfigurace celého experimentu:

```yaml
experiment:
  name: "diplomka_v11"
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 7       # Repair loop budget
  runs_per_combination: 1  # Opakování pro statistickou robustnost
  test_count: 30           # Cílový počet testů na běh
  temperatures: [0.4]      # LLM sampling temperature

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"

apis:
  - name: "bookstore"
    docker: true
    base_url: "http://localhost:8000"
    framework_rules: [...]   # Pravidla vkládaná do promptů
    api_knowledge: []         # Prázdné od v11 - hinty v documentation.md
    inputs:
      openapi: "inputs/api1_bookstore/openapi.yaml"
      documentation: "inputs/api1_bookstore/documentation.md"
      source_code: "inputs/api1_bookstore/source_code.py"
      db_schema: "inputs/api1_bookstore/db_schema.sql"
      existing_tests: "inputs/api1_bookstore/existing_tests.py"
```

### 5.2 Výstupní JSON - struktura jednoho běhu

Každý běh produkuje kompletní záznam obsahující:

```
{
  "timestamp", "llm", "api", "level", "run_id", "temperature",
  "iterations_used", "all_tests_passed", "early_stopped",
  "elapsed_seconds", "plan_test_count",
  "output_filename", "plan_filename",

  "metrics": {
    "test_validity":        { validity_rate_pct, tests_passed, ... },
    "endpoint_coverage":    { endpoint_coverage_pct, uncovered_endpoints, ... },
    "assertion_depth":      { assertion_depth, total_assertions, ... },
    "response_validation":  { response_validation_pct, ... },
    "test_type_distribution": { distribution: { happy_path, error, edge_case } },
    "status_code_diversity": { diversity_count, unique_status_codes, ... },
    "empty_tests":          { empty_count, empty_tests[] },
    "avg_test_length":      { avg_lines },
    "plan_adherence":       { adherence_pct, planned, found_in_code },
    "stale_tests":          { stale_count, stale_names[] },
    "token_efficiency":     { score, cost_usd, formula }
  },

  "diagnostics": {
    "context_size", "plan_analysis", "helper_snapshot",
    "prompt_budget", "instruction_compliance",
    "failure_taxonomy", "repair_trajectory",
    "code_patterns", "plan_code_drift", "context_utilization"
  },

  "token_usage":      { per_phase breakdown },
  "token_usage_slim": { total_tokens, cost_total_usd, ... },
  "compression":      { savings_pct, per_section, ... }
}
```

### 5.3 Artefakty na disku

Každý běh generuje:
- `test_generated_{tag}.py` - finální vygenerovaný testovací soubor
- `test_plan_{tag}.json` - testovací plán ve formátu JSON
- `test_generated_{tag}_log.txt` - kompletní pytest logy ze všech iterací

Tag má formát `{model}__{api}__{level}__run{N}__t{temperature}`, např. `gemini-3_1-flash-lite-preview__bookstore__L0__run1__t0_4`.

---

## 6. Manuální metriky a doplňkové nástroje

### 6.1 Code Coverage (`run_coverage_manual.py`)

Endpoint coverage (Fáze 5) měří pokrytí API z pohledu specifikace. **Code coverage** měří pokrytí zdrojového kódu serveru - to vyžaduje spuštění serveru s `coverage run` a je proto odděleno od automatické pipeline:

1. Spuštění Bookstore API s `coverage run --source app`
2. Reset databáze přes `/reset`
3. Spuštění vygenerovaných testů přes pytest
4. Graceful shutdown serveru (SIGINT pro uložení coverage dat)
5. Generování full coverage JSON + slim verze (per-function summary pro `crud.py` a `main.py`)

Nástroj podporuje batch režim (celý adresář), glob patterns i jednotlivé soubory. Výstupem je `coverage_{tag}.json` s per-function pokrytím a souhrnná tabulka.

### 6.2 Export vstupů (`export_inputs.py`)

Automatizovaný export vstupních dat z repozitáře Bookstore API do složky `inputs/`. Stahuje OpenAPI specifikaci z běžícího serveru, kopíruje dokumentaci, spojuje zdrojové kódy do jednoho souboru (se `# ═══ FILE: cesta ═══` separátory) a extrahuje DB schéma (pokud DDL soubor neexistuje, vygeneruje ho z SQLite databáze).

---

## 7. Reprodukovatelnost a omezení

### 7.1 Garance reprodukovatelnosti

- **Deterministic pipeline:** Stejná konfigurace YAML + stejné vstupní soubory + stejný LLM model produkují srovnatelné (ne identické, kvůli stochastické povaze LLM) výsledky.
- **Fixní temperature:** Experiment používá `temperature=0.4` pro redukci variance.
- **Kompletní logging:** Každý LLM call, pytest spuštění, repair rozhodnutí a metrika je zaznamenána - experiment je plně auditovatelný.
- **Verze kontextu:** `api_knowledge: []` od v11 eliminuje skryté proměnné mezi úrovněmi.

### 7.2 Známá omezení

- **Single API:** Experiment je validován na jednom testovacím API (Bookstore). Generalizace na API s odlišnou architekturou (GraphQL, gRPC, event-driven) nebyla testována.
- **LLM variabilita:** I při nízké teplotě existuje inherentní variance výstupů. Pro statistickou robustnost je doporučeno `runs_per_combination ≥ 3`.
- **Code coverage jako manuální metrika:** Vyžaduje přístup ke zdrojovému kódu API a lokální spuštění - nelze plně automatizovat v rámci CI pipeline.
- **Token pricing:** Ceny v `DEFAULT_PRICING` odpovídají dubnu 2026 a mohou se měnit.

---

## 8. Shrnutí

Vibe Testing Framework je end-to-end experimentální pipeline, která transformuje výzkumnou otázku „jak kontext ovlivňuje kvalitu LLM-generovaných testů" do měřitelných, reprodukovatelných a obhajitelných dat. Šestifázová architektura s iterativním repair loopem, AST-based manipulací kódu, přesným token trackingem a dvouvrstvým systémem metrik (automatické + diagnostické) poskytuje robustní základ pro kvantitativní analýzu vlivu kontextových úrovní L0–L4 na validitu, pokrytí a nákladovou efektivitu automaticky generovaných API testů.