# Vibe Testing Framework

Framework pro automatické generování API testů pomocí LLM. Generuje pytest testy na základě různých úrovní kontextu (L0–L4) a měří kvalitu vygenerovaných testů.

---

## Testuji s lokálním bookstorem
## https://github.com/Akastan/bookstore-api
# Testy resetují databázi
## Používám zatím jen Gemini API, má free verze omezené na počet requestů za den - aistudio.google.com - tam by po přihlášení měl jít jednoduše získat API key

---

### Předpoklady

- **Python 3.12+**
- **Docker Desktop** (musí běžet, pokud testované API používá Docker režim)
- **API klíč** pro alespoň jeden LLM provider (Gemini, OpenAI, Anthropic, DeepSeek)

### 1. Instalace

```
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
OPENAI_API_KEY=váš_klíč
ANTHROPIC_API_KEY=váš_klíč
```

Upravte `experiment.yaml` — zvolte LLM modely, úrovně kontextu, počet runů a testované API:

```yaml
experiment:
  levels: ["L0", "L1", "L2", "L3", "L4"]
  max_iterations: 5
  runs_per_combination: 3
  test_count: 30

llms:
  - name: "gemini-2.0-flash"
    provider: "gemini"
    model: "gemini-2.0-flash"
    api_key_env: "GEMINI_API_KEY"

apis:
  - name: "bookstore"
    docker: true
    source_dir: "../bookstore-api"
    base_url: "http://localhost:8000"
    inputs:
      openapi: "inputs/openapi.yaml"
      documentation: "inputs/documentation.md"
      source_code: "inputs/source_code.py"
      db_schema: "inputs/db_schema.sql"
      existing_tests: "inputs/existing_tests.py"
    api_rules:
      - "DELETE endpointy vracejí 204 s PRÁZDNÝM tělem."
      - "PATCH /books/{id}/stock používá QUERY parametr."
    helper_hints:
      - 'create_book helper MUSÍ nastavit "stock": 10'
```

### 3. Spuštění experimentu

```bash
# Docker Desktop musí běžet
# Na portu 8000 NESMÍ běžet žádný server (framework si ho spouští sám)
python main.py
```

### 4. Výstupy

```
outputs/
  test_generated_{llm}__{api}__{level}__run{N}.py    # vygenerované testy
  test_plan_{llm}__{api}__{level}__run{N}.json       # testovací plán
  ..._log.txt                                         # pytest logy všech iterací

results/
  experiment_{name}_{timestamp}.json                  # souhrnné metriky
```

### Pomocné skripty

```bash
# Měření code coverage (manuální, vyžaduje dva terminály)
# Terminál 1 (bookstore-api):
coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Terminál 2 (vibe-testing-framework):
python run_coverage_manual.py outputs/test_generated_{tag}.py
# Terminál 1: Ctrl+C, pak:
coverage json -o coverage_{tag}.json
coverage report
```

---

## Úrovně kontextu (L0–L4)

| Úroveň | Kontext | Popis |
|---------|---------|-------|
| **L0** | OpenAPI spec | Black-box baseline, pouze API specifikace |
| **L1** | L0 + dokumentace | Přidá byznys pravidla, chybové kódy, known issues |
| **L2** | L1 + zdrojový kód | Přidá implementaci endpointů (main.py, crud.py, schemas.py) |
| **L3** | L2 + DB schéma | Přidá databázové modely a constrainty |
| **L4** | L3 + existující testy | Přidá referenční testy pro in-context learning |

## Režimy spouštění API serveru

**Docker režim** (`docker: true`) — Framework spustí `docker compose up --build -d`, po dokončení `docker compose down --volumes`. Doporučeno.

**Lokální režim** — Framework spustí Python subprocess z `.venv` testovaného projektu.

---

## Výsledky experimentů

### Konfigurace posledního běhu (diplomka_v4)

| Parametr | Hodnota |
|---|---|
| **LLM** | gemini-3.1-flash-lite-preview |
| **API** | Bookstore API (34 endpointů) |
| **Max iterací** | 3 |
| **Testů na plán** | 30 |
| **Runy** | 1 |
| **Datum** | 2026-03-22 |

---

### RQ1: Vliv kontextu na test validity rate

*Jak úroveň kontextu (L0–L4) ovlivňuje test validity rate a liší se tento vliv mezi LLM modely?*

#### Validity per level (gemini-3.1-flash-lite, v4 — 1 run)

| Level | Validity | Failed | Stale | Iterace k konvergenci |
|-------|----------|--------|-------|-----------------------|
| L0 | 80.0% | 6 | 6 | 3 (max) |
| **L1** | **100%** | 0 | 0 | **1** |
| L2 | 96.67% | 1 | 1 | 3 (max) |
| **L3** | **100%** | 0 | 0 | **1** |
| **L4** | **100%** | 0 | 0 | **1** |

#### Srovnání v3 vs v4 (stejný model, v3 = 2 runy × 5 iter, v4 = 1 run × 3 iter)

| Level | v3 Validity (avg) | v4 Validity | Změna |
|-------|-------------------|-------------|-------|
| L0 | 96.61% | 80.0% | ↓ regrese (helper hint side effect) |
| L1 | 90.00% | **100%** | ↑ +10 p.p. |
| L2 | 93.33% | 96.67% | ↑ +3.3 p.p. |
| L3 | 96.67% | **100%** | ↑ +3.3 p.p. |
| L4 | 93.33% | **100%** | ↑ +6.7 p.p. |

**Zjištění:** L1 (byznys dokumentace) je nejefektivnější kontext — 100% validity na první iteraci. L0 bez kontextu selhává na špatných status kódech a nesprávné interpretaci prompt hintů.

---

### RQ2: Code coverage a endpoint coverage

*Jak se liší code coverage a endpoint coverage mezi modely a úrovněmi kontextu?*

#### Endpoint coverage per level

| Level | EP Coverage | Pokryté / Celkem | Trend |
|-------|-------------|-------------------|-------|
| L0 | 58.82% | 20 / 34 | — |
| L1 | 55.88% | 19 / 34 | ↓ |
| L2 | 61.76% | 21 / 34 | ↑ |
| L3 | 61.76% | 21 / 34 | = |
| L4 | 50.00% | 17 / 34 | ↓↓ |

**Zjištění:** Endpoint coverage **klesá s kontextem** u L4 (50%). Více kontextu vede k hlubšímu ale užšímu testování. L4 nepokrývá ani `/health` endpoint.

#### Nepokryté endpointy (konzistentně chybějící)

Tyto endpointy nejsou pokryté v žádném levelu:
- `PUT /authors/{id}`, `PUT /categories/{id}`, `PUT /tags/{id}` — update endpointy
- `GET /tags`, `GET /tags/{id}` — tag listing/detail
- `GET /categories`, `GET /categories/{id}` — category listing/detail (kromě L3)
- `POST /reset` — korektně odfiltrovaný

#### Code coverage (manuální měření — TBD)

Code coverage bude měřeno manuálně přes `coverage.py` pro každý level.

---

### RQ3: Mutation score

*Jak efektivně detekují vygenerované testy záměrně vnesené chyby?*

Mutation testing (mutmut) bude provedeno na `app/crud.py` pro každý level. TBD.

---

### RQ4: Typy a příčiny selhání

*Jak se liší typy selhání mezi modely a úrovněmi kontextu?*

#### Distribuce selhání (v4, 7 failing testů celkem)

| Typ selhání | Počet | Levely | Opravitelné? |
|-------------|-------|--------|--------------|
| Špatný status kód (422↔404) | 5 | L0, L2 | Částečně (repair opraví jednoduché záměny) |
| Helper hint side effect | 1 | L0 | NE (vyžaduje úpravu hintu) |
| Stock aritmetika | 1 | L0 | NE (model nechápe sémantiku) |

#### Srovnání typů selhání v3 vs v4

| Typ selhání | v3 (10 runů) | v4 (5 runů) | Změna |
|-------------|-------------|-------------|-------|
| Chybějící stock v helperu | 33% | **0%** | ✅ Eliminováno |
| Discount PATCH/PUT bug | 42% | **0%** | ✅ Eliminováno |
| Špatný status kód | 50% | 40% | ~ Stabilní |
| Sémantické nepochopení | 33% | 20% | ↓ Zlepšení |
| Halucinace | 17% | 20% | ~ Stabilní |
| Helper hint side effect | 0% | 20% | ⚠️ Nový |

**Zjištění:** `helper_hints` eliminovaly 2 největší kategorie selhání (stock + discount), ale zavedly nový typ na L0. Špatný status kód zůstává hlavním problémem (inherentní pro L0 bez kontextu).

---

### Další metriky kvality testů

#### Assertion depth a response validation per level

| Level | Assert Depth | Response Val | Empty Tests | Avg Lines |
|-------|-------------|-------------|-------------|-----------|
| L0 | 1.87 | 73.33% | 0 | 5.8 |
| L1 | 1.43 | 40.0% | 0 | 5.1 |
| L2 | **2.03** | **100%** | 0 | 5.9 |
| L3 | **2.03** | 93.33% | 0 | 5.5 |
| L4 | 1.67 | 60.0% | 0 | 6.1 |

**Zjištění:** L2 generuje nejkvalitnější testy (nejvyšší assertion depth + 100% response validation). L1 má paradoxně nejnižší response validation (40%) přes 100% validity — model kontroluje jen status kódy.

#### Status code diversity per level

| Level | Unique kódy | Chybějící kódy |
|-------|-------------|----------------|
| L0 | 4 | 400, 404, 409 |
| L1 | 7 | — (všechny) |
| L2 | 6 | 204 |
| L3 | 7 | — (všechny) |
| L4 | 7 | — (všechny) |

#### Test type distribution per level

| Level | Happy Path | Error | Edge Case |
|-------|-----------|-------|-----------|
| L0 | 70.0% | 26.7% | 3.3% |
| L1 | 30.0% | **63.3%** | 6.7% |
| L2 | 16.7% | **76.7%** | 6.7% |
| L3 | 43.3% | 56.7% | 0% |
| L4 | 53.3% | 46.7% | 0% |

**Zjištění:** L2 se zdrojovým kódem generuje 76.7% error testů — vidí error handling cesty v kódu. L0 generuje 70% happy path — bez kontextu model testuje hlavně "jde to zavolat?".

---

### Efektivita repair loop

#### Konvergence iterací

| Level | Iter 1 | Iter 2 | Iter 3 | Finální stav |
|-------|--------|--------|--------|-------------|
| L0 | 21 fail | 6 fail | 6 fail (stale) | 80% |
| L1 | 0 fail | — | — | 100% |
| L2 | 1 fail | 1 fail | 1 fail (stale) | 96.67% |
| L3 | 0 fail | — | — | 100% |
| L4 | 0 fail | — | — | 100% |

**Zjištění:** Repair loop je efektivní jen v iteraci 1→2 (helper opravy). Iterace 3+ nepřináší zlepšení — zbývající testy jsou principiálně neopravitelné. Stale detection správně identifikuje tyto testy.

---

## Struktura projektu

```
vibe-testing-framework/
├── inputs/                    # Vstupní data pro testování
│   ├── openapi.yaml
│   ├── documentation.md
│   ├── source_code.py
│   ├── db_schema.sql
│   └── existing_tests.py
├── outputs/                   # Vygenerované testy a logy
├── results/                   # JSON výsledky experimentů
├── prompts/
│   ├── prompt_templates.py    # Unified prompt framework (PromptBuilder)
│   ├── phase1_context.py      # Sestavení kontextu pro LLM
│   ├── phase2_planning.py     # Generování testovacího plánu
│   ├── phase3_generation.py   # Generování pytest kódu + opravy + stale detection
│   ├── phase4_validation.py   # Spuštění testů + server management
│   └── phase5_metrics.py      # Výpočet metrik
├── main.py                    # Hlavní experiment runner
├── llm_provider.py            # Abstrakce nad LLM providery
├── config.py                  # Konfigurace pro manuální skripty
├── experiment.yaml            # Konfigurace experimentu + api_rules + helper_hints
├── run_coverage_manual.py     # Manuální měření code coverage
├── .env                       # API klíče (není v gitu)
└── requirements.txt
```

## Licence

Projekt pro diplomovou práci – testování REST API pomocí LLM.