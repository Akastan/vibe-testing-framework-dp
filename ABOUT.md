# Vibe Testing Framework

Diplomová práce: jak dobře LLM generuje API testy na základě různé úrovně kontextu.
Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky.

## Pipeline (5 fází)

1. **Kontext (phase1):** Sestaví kontextový string podle úrovně L0–L4
2. **Plánování (phase2):** LLM vygeneruje JSON test plán s přesným počtem testů (retry + trim)
3. **Generování + opravy (phase3):** LLM vygeneruje pytest soubor → AST validace počtu → iterativní opravy failing testů
4. **Spuštění (phase4):** Spustí API server (Docker/lokální), reset DB, pytest s retry na infra chyby
5. **Metriky (phase5):** Validity rate, endpoint coverage, assertion depth, response validation, status code diversity, empty tests, plan adherence aj.

## Úrovně kontextu

| Úroveň | Co přidává |
|---|---|
| **L0** | Pouze OpenAPI spec (black-box) |
| **L1** | + byznys dokumentace (chybové kódy, pravidla) |
| **L2** | + zdrojový kód (main.py, crud.py, schemas.py) |
| **L3** | + DB schéma (models.py) |
| **L4** | + existující referenční testy (in-context learning) |

## Opravná strategie (phase3)

- **Izolovaná oprava:** mikro-prompt per failing test (max 10 testů)
- **Helper oprava:** detekce společné root cause (≥70% stejná chyba) nebo příliš mnoho failing → opraví helper funkce místo jednotlivých testů
- **Počet testů se nikdy nemění** – AST validace před i po opravě, revert při neshodě

## Testované API

**Bookstore API** – FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání. Docker režim (docker compose up/down mezi runy).

Repo: https://github.com/Akastan/bookstore-api

## Tech stack

- Python 3.12+, pytest, requests, coverage.py
- LLM provideři: Gemini, OpenAI, Claude, DeepSeek (abstrakce v `llm_provider.py`, retry s exponential backoff)
- Konfigurace: `experiment.yaml` (LLM × API × Level × Run)
- Server: Docker režim (doporučený) nebo lokální subprocess

## Struktura

```
prompts/
  phase1_context.py      # Sestavení kontextu
  phase2_planning.py     # Test plán (JSON)
  phase3_generation.py   # Generování + AST utility + opravy
  phase4_validation.py   # Server management + pytest runner
  phase5_metrics.py      # 10 automatických metrik
config.py
main.py                  # Experiment runner (iteruje LLM × API × Level × Run)
llm_provider.py          # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek)
run_coverage_manual.py
experiment.yaml          # Konfigurace experimentu
inputs/                  # OpenAPI, docs, source, schema, testy
outputs/                 # Generované testy + logy
results/                 # JSON výsledky
```

## Spuštění

```bash
# .env: GEMINI_API_KEY=... (nebo OPENAI_API_KEY, ANTHROPIC_API_KEY)
# experiment.yaml: nastav levels, llms, test_count
# Docker Desktop musí běžet
python main.py
```
