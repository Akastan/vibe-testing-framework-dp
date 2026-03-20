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
m

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
  test_count: 50

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"

apis:
  - name: "bookstore"
    docker: true                          # Docker režim (doporučeno)
    source_dir: "../bookstore-api"        
    base_url: "http://localhost:8000"
    startup_wait: 20.0
    inputs:
      openapi: "inputs/openapi.yaml"
      documentation: "inputs/documentation.md"
      source_code: "inputs/source_code.py"
      db_schema: "inputs/db_schema.sql"
      existing_tests: "inputs/existing_tests.py"
```

### 3. Příprava vstupů

Testované API musí mít exportované vstupy v adresáři `inputs/`. Pro bookstore-api:

```
# Spusťte server (lokálně nebo přes Docker)
cd ../bookstore-api
docker compose up -d

# Exportujte vstupy
cd ../vibe-testing-framework
python export_inputs.py
```

### 4. Spuštění experimentu

```
# Ujistěte se, že na portu 8000 NEBĚŽÍ žádný server (framework si ho spouští sám)
docker compose -f ../bookstore-api/docker-compose.yml down 2>nul

# Spusťte experiment
python main.py
```

Framework automaticky spustí API server (Docker nebo lokálně), vygeneruje testy, spustí je, opravuje chyby ve feedback loop a měří metriky.

### 5. Výstupy

```
outputs/
  test_generated_{llm}__{api}__{level}__run{N}.py    # vygenerované testy
  test_plan_{llm}__{api}__{level}__run{N}.json       # testovací plán
  ..._log.txt                                         # pytest logy všech iterací

results/
  experiment_{name}_{timestamp}.json                  # souhrnné metriky
```

### Pomocné skripty

```
# Spustit metriky na existujících testech (server musí běžet)
python run_metrics_only.py --tag "gemini-3_1-flash-lite-preview__bookstore__L#__run#"

# Měření code coverage (manuální, vyžaduje dva terminály)
# V prvním na /bookstore-api/:
coverage run --source app -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# V druhém na /vibe-testing-framework/:
python run_coverage_manual.py outputs/test_generated_L#_run#.py
# Po konci runu CTRL + C na první (bookstore) a potom také na první:
coverage json -o <nazev>.json
coverage report
```

## Úrovně kontextu (L0–L4)

| Úroveň | Kontext | Popis |
|---------|---------|-------|
| **L0** | OpenAPI spec | Black-box baseline, pouze API specifikace |
| **L1** | L0 + dokumentace | Přidá byznys pravidla, chybové kódy, known issues |
| **L2** | L1 + zdrojový kód | Přidá implementaci endpointů (main.py, crud.py, schemas.py) |
| **L3** | L2 + DB schéma | Přidá databázové modely aConstrainty |
| **L4** | L3 + existující testy | Přidá referenční testy pro in-context learning |

## Měřené metriky

| Metrika | Popis |
|---------|-------|
| **Test Validity Rate** | % testů které projdou (passed / total) |
| **Endpoint Coverage** | % API endpointů pokrytých v testovacím plánu |
| **Assertion Depth** | Průměrný počet asercí na test |
| **Iteration Delta** | Změna validity mezi 1. a poslední iterací |
| **Code Coverage** | Pokrytí zdrojového kódu API (manuální měření) |

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
│   ├── phase1_context.py      # Sestavení kontextu pro LLM
│   ├── phase2_planning.py     # Generování testovacího plánu
│   ├── phase3_generation.py   # Generování pytest kódu
│   ├── phase4_validation.py   # Spuštění testů + feedback loop
│   └── phase5_metrics.py      # Výpočet metrik
├── main.py                    # Hlavní experiment runner
├── llm_provider.py            # Abstrakce nad LLM providery
├── config.py                  # Konfigurace pro manuální skripty
├── experiment.yaml            # Konfigurace experimentu
├── run_metrics_only.py        # Samostatné měření metrik
├── run_coverage_manual.py     # Manuální měření code coverage
├── .env                       # API klíče (není v gitu)
└── requirements.txt
```

## Režimy spouštění API serveru

Framework podporuje dva režimy pro spouštění testovaného API:

**Docker režim** (`docker: true` v experiment.yaml) — Framework spustí `docker compose up --build -d`, testuje přes HTTP, po dokončení zavolá `docker compose down --volumes`. Každý run začíná s čistou databází. Doporučeno pro izolaci a reprodukovatelnost.

**Lokální režim** (výchozí, bez `docker: true`) — Framework spustí Python subprocess z `.venv` testovaného projektu. Vyžaduje `server_cmd` v konfiguraci. Databáze se čistí voláním `POST /reset`.

---

## Výsledky experimentu

### Konfigurace

| Parametr | Hodnota |
|---|---|
| **LLM** | gemini-3.1-flash-lite-preview |
| **API** | Bookstore API (34 endpointů) |
| **Max iterací** | 5 |
| **Datum** | 2026-03-18 |
| **Run** | 1 (první reálný pokus) |

### Souhrn

| Úroveň | Validity | Endpoint Cov | Assertion Depth | Iterací | Čas | Všechny OK |
|---|---|---|---|---|---|---|
| **L0** | 58.33% | 94.12% | 1.00 | 5/5 | ~18 min | ❌ |
| **L1** | 94.34% | 97.06% | 1.00 | 5/5 | ~28 min | ❌ |
| **L2** | **100.0%** | 76.47% | 1.04 | 4/5 | ~22 min | ✅ |
| **L3** | 89.47% | 82.35% | 1.00 | 5/5 | ~21 min | ❌ |
| **L4** | **100.0%** | 79.41% | 1.00 | 2/5 | ~11 min | ✅ |

### Code Coverage

| Úroveň | crud.py | main.py | TOTAL |
|---|---|---|---|
| **L0** | 54% | 85% | **77%** |
| **L1** | 81% | 98% | **91%** |
| **L2** | 83% | 93% | **91%** |
| **L3** | 64% | 89% | **82%** |
| **L4** | 83% | 95% | **92%** |

### Pozorování

1. **L0 selhává na triviálním problému.** Bez kontextu model nedokáže opravit ani hardcoded ISBN v helperu – 20 testů padá kvůli jednomu řádku.
2. **L1 přináší dramatické zlepšení.** Byznys dokumentace pomohla modelu pochopit unikátnost ISBN a byznys pravidla. Skok z 58% na 94%.
3. **L2 dosáhlo 100% validity.** Přístup ke zdrojovému kódu umožnil modelu plně pochopit chování API.
4. **L3 regresovalo.** Přidání DB schématu paradoxně zhoršilo výsledky – více kontextu nemusí automaticky znamenat lepší výsledky.
5. **L4 je nejefektivnější.** S existujícími testy jako vzorem model dosáhl 100% validity za pouhé 2 iterace.
6. **Assertion depth je konzistentně nízká (~1.0).** Model generuje převážně jeden assert na test.
7. **Endpoint coverage klesá s kontextem.** L0/L1 pokrývají 94–97%, L2–L4 jen 76–82% – více kontextu vede k menšímu počtu testů ale vyšší přesnosti.

## Licence

Projekt pro diplomovou práci – testování REST API pomocí LLM.