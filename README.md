# Vibe Testing Framework

Experimentální pipeline pro automatické generování API testů pomocí velkých jazykových modelů (LLM) s odstupňovaným kontextem L0–L4.

Praktická část diplomové práce zkoumající, jak objem a typ poskytnutého kontextu ovlivňuje validitu, kvalitu a pokrytí automaticky generovaných pytest testů - a zda se tento vliv liší napříč LLM modely z odlišných technologických ekosystémů.

> Podrobný technický popis architektury, pipeline, metrik a designových rozhodnutí viz **[ABOUT.md](ABOUT.md)**.

---

## Testované API

Framework je validován na **Bookstore API** - REST API pro systém knihkupectví (50 endpointů, 7 domén, stavový automat objednávek, soft delete, M:N relace, API key autentizace).

**Repozitář:** [github.com/Akastan/bookstore-api](https://github.com/Akastan/bookstore-api)

---

## Požadavky

- **Python 3.11+** (testováno na 3.12)
- **Docker** a **Docker Compose** (pro spuštění testovaného API)
- API klíče pro zvolené LLM providery (viz konfigurace níže)

---

## Instalace

### 1. Klonování repozitářů

```bash
# Framework
git clone <repo-url> vibe-testing-framework
cd vibe-testing-framework

# Testované API (do sousední složky)
git clone https://github.com/Akastan/bookstore-api ../bookstore-api
```

### 2. Python prostředí

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Závislosti

```bash
pip install pyyaml requests python-dotenv pytest pytest-timeout
```

Podle zvoleného LLM provideru nainstaluj příslušný SDK:

```bash
# Gemini
pip install google-genai

# DeepSeek (OpenAI-kompatibilní)
pip install openai

# Mistral
pip install mistralai
```

### 4. API klíče

Vytvoř soubor `.env` v kořenu projektu:

```env
GEMINI_API_KEY=tvůj-klíč
DEEPSEEK_API_KEY=tvůj-klíč
MISTRAL_API_KEY=tvůj-klíč
```

Framework načítá klíče přes `python-dotenv`. Stačí nastavit pouze klíče pro modely, které chceš používat.

### 5. Export vstupních dat

Při prvním spuštění (nebo po změně testovaného API) vyexportuj vstupní data:

```bash
# Nejdříve spusť Bookstore API (aby se stáhla OpenAPI specifikace)
cd ../bookstore-api
docker compose up --build -d
cd ../vibe-testing-framework

# Export
python export_inputs.py
```

Skript vytvoří složku `inputs/api1_bookstore/` s pěti soubory (openapi.yaml, documentation.md, source_code.py, db_schema.sql, existing_tests.py).

Po exportu můžeš API zastavit - framework si ho spustí sám:

```bash
cd ../bookstore-api && docker compose down && cd ../vibe-testing-framework
```

---

## Konfigurace

Veškeré parametry experimentu jsou v souboru **`experiment.yaml`**:

```yaml
experiment:
  name: "diplomka_v11"
  levels: ["L0", "L1", "L2", "L3", "L4"]   # Kontextové úrovně
  max_iterations: 7                          # Max iterací repair loopu
  runs_per_combination: 1                    # Počet opakování
  test_count: 30                             # Cílový počet testů na běh
  temperatures: [0.4]                        # Sampling temperature

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
    api_key_env: "GEMINI_API_KEY"

  # Odkomentuj pro přidání dalších modelů:
  # - name: "deepseek-chat"
  #   provider: "deepseek"
  #   model: "deepseek-chat"
  #   api_key_env: "DEEPSEEK_API_KEY"

  # - name: "mistral-large-2411"
  #   provider: "mistral"
  #   model: "mistral-large-2411"
  #   api_key_env: "MISTRAL_API_KEY"
```

**Celkový počet běhů** = `|llms| × |apis| × |levels| × |runs| × |temperatures|`. Při výchozí konfiguraci (1 model × 1 API × 5 levelů × 1 run × 1 teplota) = 5 běhů.

### Kontextové úrovně

| Úroveň | Co LLM dostane | Přechod               |
|---------|-----------------|-----------------------|
| L0 | OpenAPI specifikace | Black-box             |
| L1 | + technická dokumentace | + doménová znalost    |
| L2 | + zdrojový kód endpointů | -> White-box          |
| L3 | + databázové schéma | + datový model        |
| L4 | + existující testy | + in-context learning |

---

## Spuštění

### Kompletní experiment

```bash
python main.py
```

Framework automaticky:
1. Spustí Bookstore API v Dockeru
2. Pro každou kombinaci (model × level × run) provede celou pipeline
3. Po dokončení API zastaví
4. Uloží výsledky do `results/experiment_{name}_{timestamp}.json`

### Typický výstup na konzoli

```
🔬 EXPERIMENT: diplomka_v11
   1 LLMs × 1 APIs × 5 levels × 1 runs = 5 běhů
   Max iterací: 7 | Testů na plán: 30

🤖 LLM: gemini-3.1-flash-lite-preview
📦 API: bookstore

[1/5]
=================================================================
  gemini-3.1-flash-lite-preview | bookstore | L0 | Běh 1
=================================================================

  📦 Komprese kontextu:
     Celkem: 4,821 -> 3,102 tokenů (−35.7%, −1,719 tokenů)

  [Fáze 2] Generování plánu (30 testů)...
  Plán: 30 testů
  [Fáze 3+4] Generování kódu (max 7 iterací)...
  Testů v kódu: 30 (plán: 30)

  --- Iterace 1/7 ---
    16 passed, 14 failed
  ❌ Testy selhaly. Opravuji...

  --- Iterace 2/7 ---
    19 passed, 11 failed
  ...

  Validity:   53.33% (16/30)
  Endpoint:   36.0% (18/50)
  Assert:     1.37 avg (41 total)
  Tokeny:     42,198 total (31,205 in / 10,993 out) | 6 calls
  Cena celkem: $0.0244
```

---

## Výstupy

### Struktura složek

```
outputs/
├── test_generated_{model}__{api}__{level}__run{N}__t{temp}.py   # Vygenerované testy
├── test_plan_{model}__{api}__{level}__run{N}__t{temp}.json      # Testovací plán
└── test_generated_..._log.txt                                    # Pytest logy

results/
└── experiment_{name}_{timestamp}.json                            # Kompletní výsledky
```

### Klíčové metriky ve výsledkovém JSON

Každý běh obsahuje blok `metrics` s:

| Metrika | Popis |
|---------|-------|
| `test_validity.validity_rate_pct` | % testů které projdou pytest |
| `endpoint_coverage.endpoint_coverage_pct` | % API endpointů pokrytých v plánu |
| `assertion_depth.assertion_depth` | Průměrný počet asercí na test |
| `response_validation.response_validation_pct` | % testů ověřujících response body |
| `status_code_diversity.diversity_count` | Počet unikátních ověřovaných HTTP kódů |
| `test_type_distribution.distribution` | Rozložení happy_path / error / edge_case |
| `token_efficiency.score` | Cost-effectiveness: (passed × assert_depth) / cost_usd |

A blok `diagnostics` s daty pro hlubší analýzu (failure taxonomy, repair trajectory, context utilization, instruction compliance, ...).

---

## Manuální měření Code Coverage

Code coverage vyžaduje spuštění API serveru s `coverage` instrumentací a je proto odděleno od hlavní pipeline:

```bash
# Jeden testovací soubor
python run_coverage_manual.py outputs/test_generated_gemini-3_1-flash-lite-preview__bookstore__L0__run1__t0_4.py

# Všechny vygenerované testy
python run_coverage_manual.py outputs/

# Glob pattern
python run_coverage_manual.py "outputs/test_generated_*__L2__*.py"
```

Výsledky se ukládají do `coverage_results/` jako slim JSON s per-function pokrytím.

---

## Struktura projektu

```
vibe-testing-framework/
│
├── main.py                    # Orchestrátor experimentu
├── experiment.yaml            # Konfigurace (modely, úrovně, parametry)
├── .env                       # API klíče (není v Gitu)
│
├── prompts/                   # Pipeline fáze
│   ├── __init__.py
│   ├── prompt_templates.py    # Unified Prompt Framework v7
│   ├── phase1_context.py      # Sestavení kontextu L0–L4
│   ├── phase2_planning.py     # Generování testovacího plánu
│   ├── phase3_generation.py   # Generování kódu + repair loop
│   ├── phase4_validation.py   # Pytest execution + server management
│   ├── phase5_metrics.py      # Automatické metriky
│   └── phase6_diagnostics.py  # Diagnostická data
│
├── llm_provider.py            # LLM abstrakce (Gemini, DeepSeek, Mistral)
├── token_tracker.py           # Token/cost tracking
├── context_compressor.py      # Komprese kontextu (~30–45% úspora)
├── export_inputs.py           # Export vstupních dat z API repozitáře
├── run_coverage_manual.py     # Manuální code coverage
│
├── inputs/                    # Vstupní data (generuje export_inputs.py)
│   └── api1_bookstore/
│       ├── openapi.yaml
│       ├── documentation.md
│       ├── source_code.py
│       ├── db_schema.sql
│       └── existing_tests.py
│
├── outputs/                   # Vygenerované testy + logy
├── results/                   # Výsledkové JSON soubory
├── coverage_results/          # Code coverage výsledky
│
├── ABOUT.md                   # Technická dokumentace architektury
└── README.md                  # Tento soubor
```

---

## Přidání nového LLM modelu

1. Implementuj třídu v `llm_provider.py` dědící z `LLMProvider` a `RetryMixin`
2. Metoda `generate_text(prompt) -> tuple[str, dict | None]` musí vracet text a usage dict
3. Přidej token extraction funkci do `token_tracker.py`
4. Zaregistruj provider v `PROVIDERS` dict
5. Přidej pricing do `DEFAULT_PRICING` v `token_tracker.py`
6. Přidej konfiguraci do `experiment.yaml`

---

## Přidání nového testovaného API

1. Připrav vstupní soubory (minimálně OpenAPI specifikaci)
2. Přidej konfiguraci do `apis` sekce v `experiment.yaml`
3. Volitelně přidej `framework_rules` specifické pro dané API
4. Spusť `export_inputs.py` nebo vlož soubory manuálně do `inputs/`

---

## Časté problémy

| Problém                          | Řešení                                                                                                     |
|----------------------------------|------------------------------------------------------------------------------------------------------------|
| `API_KEY nenalezen`              | Zkontroluj `.env` soubor a název proměnné v `experiment.yaml`                                              |
| Server nenaběhl (timeout)        | Zvyš `startup_wait` v YAML; zkontroluj `docker compose logs`                                               |
| Všechny testy padají na 503      | Test nechal zapnutý maintenance mode - framework to detekuje a opravuje automaticky, ale zkontroluj logy   |
| Rate limit (429)                 | Framework automaticky čeká s exponenciálním backoffem (až 240s); pro agresivnější limity zvyš `base_delay` |
| Truncated kód (syntax error)     | Automatický salvage ořízne na poslední kompletní test; u modelů s nízkým max_tokens snižte `test_count`    |
| Early stop - všechny testy stale | Repair loop vyčerpal možnosti; zkontroluj diagnostiku `failure_taxonomy` pro root cause                    |

---

## Licence

Tento projekt je součástí diplomové práce. Použití pro akademické a výzkumné účely.

---

## Autor

**Bc. Martin Chuděj** - Diplomová práce, 2026