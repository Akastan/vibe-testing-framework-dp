# Vibe Testing Framework

Framework pro automatické generování API testů pomocí LLM. Generuje pytest testy na základě různých úrovní kontextu (L0–L4), porovnává modely z různých ekosystémů a měří kvalitu vygenerovaných testů.

Diplomová práce zkoumající tři výzkumné otázky: vliv kontextu na kvalitu testů (RQ1), vliv kontextu na testovací strategii (RQ2) a rozdíly mezi LLM modely z odlišných technologických ekosystémů (RQ3).

---

## Testovaná API

| API | Endpointy | Status kódy | Zaměření | Repozitář |
|-----|-----------|-------------|----------|-----------|
| **Bookstore API** | 40 | 10 | RQ1 (validita, coverage) | [github.com/Akastan/bookstore-api](https://github.com/Akastan/bookstore-api) |
| **AstroOps API** | 20 | 22 | RQ2 (strategie, diverzita kódů) | [github.com/Akastan/astroops-api](https://github.com/Akastan/astroops-api) |

Obě API běží na **portu 8000** — framework je spouští sekvenčně (jedno po druhém).

---

### Předpoklady

- **Python 3.12+**
- **Docker Desktop** (musí běžet, pokud testované API používá Docker režim)
- **API klíč** pro alespoň jeden LLM provider (Gemini, DeepSeek, Mistral)
- Naklonované repozitáře obou API vedle tohoto frameworku:
  ```
  projekty/
  ├── vibe-testing-framework/
  ├── bookstore-api/
  └── astroops-api/
  ```

### 1. Instalace

```bash
git clone https://github.com/Akastan/vibe-testing-framework.git
cd vibe-testing-framework

python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Konfigurace

Vytvořte `.env` soubor s API klíči:

```env
GEMINI_API_KEY=váš_klíč
DEEPSEEK_API_KEY=váš_klíč
MISTRAL_API_KEY=váš_klíč
```

Upravte `experiment.yaml` — zvolte LLM modely, úrovně kontextu, počet runů a testované API.

### 3. Export vstupních dat

Framework potřebuje kontextová data (OpenAPI spec, dokumentace, zdrojový kód, DB schéma, testy) z obou API. Export se provádí centrálně přes `export_inputs.py`:

```bash
# Spusť bookstore na :8000, pak:
python export_inputs.py bookstore

# Zastav bookstore, spusť astroops na :8000, pak:
python export_inputs.py astroops

# Nebo jen soubory bez OpenAPI (servery nemusí běžet):
python export_inputs.py files
```

Výstupní struktura:
```
inputs/
├── api1_bookstore/
│   ├── openapi.yaml        # L0
│   ├── documentation.md    # L1
│   ├── source_code.py      # L2
│   ├── db_schema.sql       # L3
│   └── existing_tests.py   # L4
└── api2_astroops/
    ├── openapi.yaml
    ├── documentation.md
    ├── source_code.py
    ├── db_schema.sql
    └── existing_tests.py
```

### 4. Spuštění experimentu

```bash
# Docker Desktop musí běžet
# Na portu 8000 NESMÍ běžet žádný server (framework si ho spouští sám)
python main.py
```

### 5. Výstupy

```
outputs/
  test_generated_{llm}__{api}__{level}__run{N}__t{temp}.py   # vygenerované testy
  test_plan_{llm}__{api}__{level}__run{N}__t{temp}.json      # testovací plán
  ..._log.txt                                                  # pytest logy všech iterací

results/
  experiment_{name}_{timestamp}.json                           # souhrnné metriky + diagnostiky

coverage_results/
  coverage_{tag}.json                                          # slim coverage JSON
  summary.json                                                 # souhrnná tabulka
```

### 6. Pomocné skripty

```bash
# Automatizované měření code coverage (jeden soubor):
python run_coverage_manual.py outputs/test_generated_{tag}.py

# Celý adresář:
python run_coverage_manual.py outputs/

# Glob pattern:
python run_coverage_manual.py "outputs/test_generated_*__L0__*.py"

# Jen slim existujícího coverage JSON:
python run_coverage_manual.py --slim coverage_full.json coverage_slim.json

# Generování Markdown reportu:
python generate_report.py
```

---

## Výzkumné otázky a hypotézy

### RQ1 — Jak rostoucí úroveň kontextu (L0–L4) ovlivňuje validitu a sémantickou kvalitu API testů?

Metriky: TVR (Test Validity Rate), code coverage (branch), endpoint coverage, assertion depth.

| Hypotéza | Predikce |
|----------|----------|
| **H1a** | TVR a assertion depth monotónně rostou, ale s klesajícím marginálním užitkem (L3→L4 < L0→L1) |
| **H1b** | Code coverage udělá ostrý skok na L1→L2 (zdrojový kód odhalí interní větvení) |
| **H1c** | EP coverage vysoká už na L0, assertion depth a code coverage mají strmější růst |

### RQ2 — Jak kontext ovlivňuje testovací strategii (distribuce scénářů, diverzita status kódů)?

Metriky: test_type_distribution (happy/error/edge), status_code_diversity.

| Hypotéza | Predikce |
|----------|----------|
| **H2a** | Happy path: L0 >60 %, L4 <40 %. S kontextem roste podíl error/edge testů |
| **H2b** | Diverzita HTTP status kódů monotónně roste, největší skok na L2 |

### RQ3 — Liší se modely z různých ekosystémů (USA, EU, Čína) v kvalitě testů?

Metriky: všechny z RQ1 porovnané napříč modely, cost-effectiveness.

| Hypotéza | Predikce |
|----------|----------|
| **H3a** | Na L0 bez významných rozdílů, na L4 statisticky významné rozdíly |
| **H3b** | Open-weight modely mají vyšší cost-effectiveness (kvalita/náklady), nejsilněji na L0–L1 |

---

## Úrovně kontextu (L0–L4)

| Úroveň | Kontext | Popis |
|---------|---------|-------|
| **L0** | OpenAPI spec | Black-box baseline, pouze API specifikace |
| **L1** | L0 + dokumentace | Přidá byznys pravidla, chybové kódy, known issues |
| **L2** | L1 + zdrojový kód | Přidá implementaci endpointů (main.py, crud.py, schemas.py) |
| **L3** | L2 + DB schéma | Přidá databázové modely a constrainty |
| **L4** | L3 + existující testy | Přidá referenční testy pro in-context learning |

---

## Klíčový designový princip — fair experimental design

Dva typy instrukcí striktně oddělené:

- **`framework_rules`** — JAK psát testy (pytest/requests technikálie). Platí pro **všechny** levely. Neobsahují žádnou znalost o chování API.
- **`api_knowledge`** — CO API dělá (chování, pravidla, defaulty). Injektují se **pouze do L1+**. Na L0 toto model NEDOSTANE.

Tím je zajištěno, že **jediná proměnná mezi levely je kontext**, ne skryté hinty.

---

## Výsledky experimentů (diplomka_v10)

### Konfigurace

| Parametr | Hodnota |
|----------|---------|
| **LLM** | gemini-3.1-flash-lite-preview |
| **API** | Bookstore API (34 endpointů, FastAPI + SQLite) |
| **Max iterací** | 5 |
| **Testů na plán** | 30 |
| **Runy na kombinaci** | 5 |
| **Stale threshold** | 2 |
| **Temperature** | 0.4 |
| **Datum** | 2026-03-31 |

---

### RQ1: Vliv kontextu na validitu a kvalitu

#### Validity rate per level (5 runů, temperature 0.4)

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg ± Std |
|-------|-------|-------|-------|-------|-------|-----------|
| L0 | 90.0% | 96.67% | 90.0% | 83.33% | 96.67% | **91.33% ± 5.5** |
| L1 | 96.67% | 100.0% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |
| L2 | 100.0% | 96.67% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |
| L3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0% ± 0.0** |
| L4 | 96.67% | 100.0% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |

**Klíčové zjištění:**

- **L0→L1 je nejvýznamnější skok** (+8 p.b.). `api_knowledge` odstraňuje tři hlavní kategorie selhání: špatné status kódy (200 vs 201), špatné formáty requestů (JSON body vs query param na PATCH /stock), chybějící prerekvizity (stock default 0).
- **L3 dosáhlo 100 % ve všech 5 runech** — nulová variance. Temperature 0.4 eliminovala destruktivní outlier z v9.
- **L2–L4 přinášejí marginální zlepšení** — potvrzení H1a (klesající marginální užitek).

#### Code coverage per level

| Level | Avg | Std | crud.py Avg | main.py Avg |
|-------|-----|-----|-------------|-------------|
| L0 | 78.9% | 4.5 | 56.5% | 87.2% |
| L1 | **85.3%** | 0.7 | **70.7%** | 88.7% |
| L2 | 84.7% | 0.7 | 70.1% | 87.2% |
| L3 | 84.0% | 1.3 | 68.5% | 86.7% |
| L4 | 84.4% | 0.6 | 69.0% | 87.7% |

- **L1 má nejvyšší code coverage** (85.3 %) navzdory nižší EP coverage než L0.
- **crud.py je diferenciátor:** L0 gap (main.py − crud.py) = 30.7 p.b., L1+ gap = ~18 p.b.
- **H1b částečně falzifikována:** Skok code coverage nastává na L0→L1 (ne L1→L2).

#### Endpoint coverage per level

| Level | Avg | Std |
|-------|-----|-----|
| L0 | **70.0%** | 3.8 |
| L1 | 59.41% | 3.2 |
| L2 | 52.94% | 2.1 |
| L3 | 49.41% | 2.4 |
| L4 | 55.88% | 3.5 |

- **EP coverage klesá s kontextem** — model s více znalostmi soustředí testy na business-critical endpointy místo rovnoměrného rozkládání. Potvrzení H1c.
- **EP coverage ≠ kvalita:** L0 Run 4 má nejvyšší EP coverage (76.47 %) ale nejnižší validity (83.33 %).

#### Assertion depth a response validation

| Level | Assert Depth | Response Validation |
|-------|-------------|---------------------|
| L0 | **1.81** | **56.0%** |
| L1 | 1.34 | 30.67% |
| L2 | 1.43 | 41.33% |
| L3 | 1.41 | 39.33% |
| L4 | 1.44 | 46.0% |

- **Assertion depth paradox:** L0 má nejvyšší depth (1.81) a response validation (56 %) — model bez kontextu „nedůvěřuje" API, ale značná část asercí je nesprávná. H1a částečně falzifikována pro assertion depth.

---

### RQ2: Vliv kontextu na testovací strategii

#### Test type distribution

| Level | Happy Path | Error | Edge Case |
|-------|-----------|-------|-----------|
| L0 | **60.67%** | 38.0% | 1.33% |
| L1 | 53.33% | 46.67% | 0% |
| L2 | 53.33% | 46.67% | 0% |
| L3 | 49.33% | **50.67%** | 0% |
| L4 | 47.33% | **52.0%** | 0.67% |

- **H2a potvrzena pro L0** (60.67 % happy path > 60 %). L4 nedosáhlo pod 40 % happy path (47.33 %) — práh je blízko ale ne pod 40 %.
- **Trend je konzistentní:** S kontextem roste podíl error testů (38 % → 52 %).

#### Status code diversity

| Level | Unique kódy (avg) |
|-------|--------------------|
| L0 | 5.0 |
| L1 | 6.8 |
| L2 | 7.0 |
| L3 | 7.0 |
| L4 | 6.6 |

- **H2b potvrzena:** Diverzita roste s kontextem. L0 halucinuje 404 korektně z HTTP konvencí.

---

### Failure taxonomy (první iterace, 5 runů)

| Typ selhání | L0 (48 failů) | L1 (3) | L2 (1) | L3 (1) | L4 (1) |
|-------------|---------------|--------|--------|--------|--------|
| wrong_status_code | 15 (31.3%) | 3 (100%) | 1 (100%) | 1 (100%) | 1 (100%) |
| timeout | 24 (50.0%) | 0 | 0 | 0 | 0 |
| other | 8 (16.7%) | 0 | 0 | 0 | 0 |
| assertion_mismatch | 1 (2.1%) | 0 | 0 | 0 | 0 |

- **Timeout je L0-only problém** (50 % L0 selhání). Příčina: kaskádový chain z chybějícího stock.
- **L1+ zbytková chyba = wrong_status_code** kolem discount boundary a edge case validací.

### Repair loop efektivita

| Level | Avg failing (iter 1) | Fix rate | Iterace ke konvergenci |
|-------|---------------------|----------|------------------------|
| L0 | 9.6 | 72.9% | 5.0 (max) |
| L1 | 0.6 | 66.7% | 2.6 |
| L2 | 0.2 | 0% | 1.8 |
| L3 | 0.2 | 100% | 1.4 |
| L4 | 0.2 | 0% | 1.8 |

- **Repair loop je nejhodnotnější pro L0** — opraví průměrně 7 z 9.6 selhání.
- **L4 téměř nikdy nepotřebuje repair** — 4/5 runů prošly na první iteraci.

### Instruction compliance — in-context learning efekt

| Level | Timeout compliance | Compliance score |
|-------|--------------------|-----------------|
| L0–L3 | 0% (20/20 runů) | 80 |
| L4 | **80%** (4/5 runů) | **96** |

- **Referenční testy jsou efektivnější než textové instrukce** pro vynucení coding standards.

---

## Struktura projektu

```
vibe-testing-framework/
├── inputs/
│   ├── api1_bookstore/        # Kontextová data pro Bookstore API
│   └── api2_astroops/         # Kontextová data pro AstroOps API
├── outputs/                   # Vygenerované testy a logy
├── results/                   # JSON výsledky experimentů
├── coverage_results/          # Slim coverage JSONy
├── prompts/
│   ├── prompt_templates.py    # Unified prompt framework (PromptBuilder)
│   ├── phase1_context.py      # Sestavení kontextu pro LLM
│   ├── phase2_planning.py     # Generování testovacího plánu
│   ├── phase3_generation.py   # Generování pytest kódu + opravy + stale detection
│   ├── phase4_validation.py   # Spuštění testů + server management (Docker/lokální)
│   ├── phase5_metrics.py      # Výpočet metrik (9 automatických)
│   └── phase6_diagnostics.py  # Diagnostiky pro obhajobu (10 diagnostik)
├── main.py                    # Hlavní experiment runner (LLM × API × Level × Temp × Run)
├── llm_provider.py            # Abstrakce nad LLM providery (Gemini/DeepSeek/Mistral)
├── token_tracker.py           # Přesné měření tokenů + pricing
├── context_compressor.py      # Komprese kontextu (token savings)
├── experiment.yaml            # Konfigurace experimentu
├── export_inputs.py           # Centrální export dat z obou API
├── generate_report.py         # Generátor Markdown reportu z JSON výsledků
├── run_coverage_manual.py     # Automatizované měření code coverage
├── .env                       # API klíče (není v gitu)
└── requirements.txt
```

## LLM Provideři

| Provider | Model | Ekosystém |
|----------|-------|-----------|
| `gemini` | Gemini 3.1 Flash Lite Preview | Google (USA) |
| `deepseek` | DeepSeek Chat | DeepSeek (Čína) |
| `mistral` | Mistral Large 2411 | Mistral AI (EU/Francie) |

## Licence

Projekt pro diplomovou práci – Vibe Testing: využití vibe codingu pro automatizované generování testů softwaru.