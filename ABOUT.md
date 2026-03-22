# Vibe Testing Framework

Diplomová práce: jak dobře LLM generuje API testy na základě různé úrovně kontextu.
Framework přijme OpenAPI spec + kontext → LLM vygeneruje test plán + pytest suite → spustí proti reálnému API → iterativně opravuje → měří metriky.

## Výzkumné otázky

**RQ1:** Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje test validity rate vygenerovaných API testů a liší se tento vliv mezi LLM modely?

**RQ2:** Jak se liší code coverage (řádkové pokrytí) a endpoint coverage vygenerovaných testů mezi LLM modely a úrovněmi kontextu?

**RQ3:** Jak efektivně detekují LLM-generované testy záměrně vnesené chyby (mutanty) v kódu API a liší se mutation score mezi LLM modely a úrovněmi kontextu?

**RQ4:** Jak se liší typy a příčiny selhání vygenerovaných testů (halucinované endpointy, sémantické nepochopení API, chyby v helper funkcích) mezi LLM modely a úrovněmi kontextu?

## Pipeline (5 fází)

1. **Kontext (phase1):** Sestaví kontextový string podle úrovně L0–L4
2. **Plánování (phase2):** LLM vygeneruje JSON test plán s přesným počtem testů (retry + trim + filtrování /reset testů)
3. **Generování + opravy (phase3):** LLM vygeneruje pytest soubor → AST validace počtu → iterativní opravy failing testů
4. **Spuštění (phase4):** Spustí API server (Docker/lokální), reset DB, pytest s retry na infra chyby
5. **Metriky (phase5):** 10 automatických metrik (viz níže). Code coverage se měří manuálně přes `run_coverage_manual.py`.

## Úrovně kontextu

| Úroveň | Co přidává |
|---|---|
| **L0** | Pouze OpenAPI spec (black-box) |
| **L1** | + byznys dokumentace (chybové kódy, pravidla, known issues) |
| **L2** | + zdrojový kód (main.py, crud.py, schemas.py) |
| **L3** | + DB schéma (models.py) |
| **L4** | + existující referenční testy (in-context learning) |

## Opravná strategie (phase3)

- **Izolovaná oprava:** mikro-prompt per failing test (max 10 testů)
- **Helper oprava:** detekce společné root cause (≥70% stejná chyba, první E-řádek per test) nebo příliš mnoho failing → opraví helper funkce místo jednotlivých testů
- **Stale detection:** zamrzlé testy (stejná chyba ≥2× po sobě) se přeskakují — šetří LLM cally, testy zůstávají v kódu (validity metrika je férová)
- **Počet testů se nikdy nemění** – AST validace před i po opravě, revert při neshodě

## Automatické metriky (phase5)

1. **Test Validity Rate** – % testů které projdou (passed / total)
2. **Endpoint Coverage** – % API endpointů pokrytých v test plánu (vs OpenAPI spec)
3. **Assertion Depth** – průměrný počet assertů na test
4. **Response Validation** – % testů ověřujících response body (ne jen status kód)
5. **Test Type Distribution** – poměr happy_path / error / edge_case v plánu
6. **Status Code Diversity** – kolik různých HTTP status kódů testy ověřují
7. **Empty Test Detection** – testy s 0 asercemi
8. **Avg Test Length** – průměrný počet řádků na test
9. **HTTP Method Coverage** – distribuce GET/POST/PUT/DELETE/PATCH v plánu
10. **Plan Adherence** – kolik testů z plánu se skutečně vygenerovalo

## Manuální metriky

- **Code Coverage** – řádkové pokrytí zdrojového kódu API (coverage.py, měřeno přes `run_coverage_manual.py`)
- **Mutation Score** – % zabitých mutantů (mutmut na app/crud.py, plánováno)

## Testované API

**Bookstore API** – FastAPI + SQLite, 34 endpointů (autoři, kategorie, knihy, recenze, tagy, objednávky). Byznys logika: slevy, stock management, order status transitions, kaskádové mazání, unique ISBN, discount omezení (kniha starší než rok). Docker režim.

Repo: https://github.com/Akastan/bookstore-api

## Tech stack

- Python 3.12+, pytest, requests, coverage.py, mutmut
- LLM provideři: Gemini, OpenAI, Claude, DeepSeek (abstrakce v `llm_provider.py`, retry s exponential backoff)
- Konfigurace: `experiment.yaml` (LLM × API × Level × Run)
- Server: Docker režim (doporučený) nebo lokální subprocess

## Konfigurace experimentu (experiment.yaml)

- **levels:** L0–L4
- **max_iterations:** 5 (feedback loop)
- **runs_per_combination:** 3 (statistická validita)
- **test_count:** 30

## Struktura

```
prompts/
  phase1_context.py      # Sestavení kontextu
  phase2_planning.py     # Test plán (JSON)
  phase3_generation.py   # Generování + AST utility + opravy + stale detection
  phase4_validation.py   # Server management + pytest runner
  phase5_metrics.py      # 10 automatických metrik
main.py                  # Experiment runner (iteruje LLM × API × Level × Run)
llm_provider.py          # LLM abstrakce (Gemini/OpenAI/Claude/DeepSeek)
run_coverage_manual.py   # Manuální code coverage měření
config.py                # Konfigurace pro manuální skripty
experiment.yaml          # Konfigurace experimentu
inputs/                  # OpenAPI, docs, source, schema, testy
outputs/                 # Generované testy + logy
results/                 # JSON výsledky experimentů
```

## Spuštění

```bash
# .env: GEMINI_API_KEY=... (nebo OPENAI_API_KEY, ANTHROPIC_API_KEY)
# experiment.yaml: nastav levels, llms, test_count
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

## Známé poznatky

- **L1 (byznys docs) je nejefektivnější kontext** — model pochopí pravidla API a generuje korektní testy, často 100% validity na první iteraci
- **L2/L3 mohou regresovat** — zdrojový kód/DB schéma vedou k halucinacím (neexistující endpointy), špatným HTTP metodám (PATCH místo PUT), sémantickému nepochopení (záporné quantity ≠ chyba)
- **L4 (existující testy) dramaticky zrychluje konvergenci** — model kopíruje funkční patterny, 100% validity za 1–2 iterace
- **Více kontextu ≠ automaticky lepší** — neznalost implementace chrání před chybnými předpoklady
- **Assertion depth ~2.0** po úpravě promptu (dříve ~1.0)
- **Stale failure pattern** — 2–3 testy zamrznou na stejné chybě a repair loop je nedokáže opravit (principiálně neopravitelné: halucinovaný endpoint, špatná premise testu)
- **Reset test v plánu** — model generuje test na /reset endpoint i přes instrukci v promptu, řešeno filtrováním v phase2