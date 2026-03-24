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
  test_count: 50

llms:
  - name: "gemini-3.1-flash-lite-preview"
    provider: "gemini"
    model: "gemini-3.1-flash-lite-preview"
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
    framework_rules:
      - "Timeout=30 na každém HTTP volání."
      - "Unikátní stringy přes uuid4."
      - "Na DELETE s 204 nevolej .json()."
      - "Nepoužívej fixtures, conftest, setup_module."
      - "Nevolej /reset endpoint."
      - "Každý test musí být self-contained."
    api_knowledge:
      - 'create_book helper MUSÍ nastavit "stock": 10'
      - "DELETE /books/{id}/tags používá REQUEST BODY: json={\"tag_ids\": [...]}."
      - "PATCH /books/{id}/stock používá QUERY parametr: params={\"quantity\": N}."
      - "Stock quantity je DELTA, ne absolutní hodnota."
      - "Pro 'not found' endpointy API vrací 404, ne 422."
      - "POST endpointy vracejí 201 při úspěchu, ne 200."
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
  experiment_{name}_{timestamp}.json                  # souhrnné metriky + diagnostiky
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

---

## Výsledky experimentů (diplomka_v7)

### Konfigurace posledního běhu

| Parametr | Hodnota |
|---|---|
| **LLM** | gemini-3.1-flash-lite-preview |
| **API** | Bookstore API (34 endpointů) |
| **Max iterací** | 5 |
| **Testů na plán** | 50 |
| **Runy na kombinaci** | 3 |
| **Stale threshold** | 3 |
| **Datum** | 2026-03-23 |

---

### RQ1: Vliv kontextu na test validity rate

*Jak úroveň kontextu (L0–L4) ovlivňuje test validity rate a liší se tento vliv mezi LLM modely?*

#### Validity per level (gemini-3.1-flash-lite, v7 — 3 runy × 5 iter)

| Level | Run 1 | Run 2 | Run 3 | Avg ± Std | Failed (avg) | Stale (avg) | Iter (avg) |
|-------|-------|-------|-------|-----------|--------------|-------------|------------|
| L0 | 76.0% | 94.0% | 78.0% | 82.7% ± 8.1 | 8.7 | 4.3 | 5.0 |
| L1 | 84.0% | 100.0% | 94.0% | 92.7% ± 8.1 | 3.7 | 4.0 | 4.0 |
| L2 | 98.0% | 100.0% | 100.0% | 99.3% ± 1.2 | 0.3 | 0.3 | 2.7 |
| L3 | 100.0% | 100.0% | 98.0% | 99.3% ± 1.2 | 0.3 | 0.3 | 2.3 |
| L4 | 100.0% | 100.0% | 100.0% | **100.0% ± 0.0** | 0 | 0 | **1.0** |

#### Analýza trendu L0→L4

**L0→L1: +10.0 p.p. (82.7% → 92.7%) — Největší skok**

Dokumentace poskytuje kritické informace které model z OpenAPI spec nemůže odvodit:
- **Stock default = 0:** API vytváří knihy s nulovým skladem. Bez api_knowledge model neví že musí v helperu nastavit `stock: 10` → objednávky selhávají na "insufficient stock" → kaskáda failů.
- **PATCH /stock je query parametr:** Model hádá JSON body → 422 validation error.
- **POST vrací 201, ne 200:** Model assertuje 200 → wrong_status_code.
- **404 pro not-found:** OpenAPI spec definuje jen 422 pro chyby. Model správně "halucinuje" 404 z obecných znalostí, ale ne konzistentně.

Konkrétní dopad: L0 má průměrně 17.7 failing testů v první iteraci vs L1 jen 4.7.

**L1→L2: +6.7 p.p. (92.7% → 99.3%) — Druhý největší skok**

Zdrojový kód (+11,474 tokenů) eliminuje ambiguitu status kódů. Model vidí:
```python
raise HTTPException(status_code=409, detail="ISBN already exists")
raise HTTPException(status_code=400, detail="Discount not applicable")
```
→ assertuje přesný kód. L1 selhává protože dokumentace říká "vrací chybu" ale nespecifikuje 400 vs 409 vs 422.

Důkaz: L1 failure taxonomy = 92.9% wrong_status_code. L2 má jen 2 failing testy celkem (across 3 runů).

**L2→L3: +0.0 p.p. (obě 99.3%) — DB schéma nepřidává validity**

DB schéma přidává 929 tokenů (FK constraints, NOT NULL, CHECK). Informace relevantní pro validity testů jsou již v zdrojovém kódu (validační logika). DB schéma pomáhá s pochopením datového modelu ale nepřináší nové informace pro správné assertování.

Exception: L3 Run 2 měl EP coverage 52.9% — model se soustředil na not-found testy inspirovaný FK constraints.

**L3→L4: +0.7 p.p. (99.3% → 100.0%) — Referenční testy = perfekce**

Referenční testy (+5,759 tokenů) poskytují:
1. **Přesné helper patterny** — `create_test_book(author_id, category_id, stock=10, published_year=2020)` s `assert r.status_code == 201`
2. **In-context learning pro status kódy** — model kopíruje přesné asserty
3. **Timeout compliance** — 66% L4 runů má timeout na všech HTTP callech (vs 0% na L0-L2)
4. **Nulová variance** — std = 0.0, perfektní reprodukovatelnost

#### Stabilita a reprodukovatelnost

| Level | Std | Interpretace |
|-------|-----|--------------|
| L0 | 8.1 | Nestabilní — závisí na strategii helperů (inline vs domain vs generic) |
| L1 | 8.1 | Nestabilní — model někdy halucinuje neexistující endpointy nebo špatně chápe filtrování |
| L2 | 1.2 | Stabilní — zdrojový kód eliminuje ambiguitu |
| L3 | 1.2 | Stabilní — ale EP coverage variabilní (52.9-91.2%) |
| L4 | 0.0 | Perfektně stabilní — referenční testy standardizují output |

**Příčina L0 nestability — tři architektonické strategie:**

Model bez kontextu nedeterministicky volí jednu ze tří strategií:
1. **Domain helpers** (Run 1: create_author, create_book, delete_resource) — 76% validity. Helpery mají stock=10 ale ostatní parametry špatně → 20 failing.
2. **Žádné helpers** (Run 2: pouze unique()) — **94%** validity. Paradoxně nejlepší! Inline setup je explicitní → méně kaskádových chyb.
3. **Generic HTTP wrappers** (Run 3: post_resource, get_resource) — 78% validity. Wrappery neřeší doménovou logiku → 78% timeout chain.

Toto je klíčový finding: **centralizovaná abstrakce bez doménových znalostí je horší než žádná abstrakce**.

---

### RQ2: Endpoint coverage a code coverage

*Jak se liší code coverage a endpoint coverage mezi modely a úrovněmi kontextu?*

#### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Avg | Std | Uncovered (typicky) |
|-------|-------|-------|-------|-----|-----|---------------------|
| L0 | 97.1% | 94.1% | 97.1% | **96.1%** | 1.7 | POST /reset, občas PATCH /orders/status |
| L1 | 82.4% | 82.4% | 88.2% | 84.3% | 3.4 | GET detail + GET tags endpointy |
| L2 | 85.3% | 88.2% | 88.2% | 87.3% | 1.7 | GET categories, GET tags/{id} |
| L3 | 91.2% | **52.9%** | 88.2% | 77.5% | 20.5 | Variabilní — Run 2 outlier |
| L4 | 91.2% | 82.4% | 82.4% | 85.3% | 5.1 | GET reviews, GET categories/{id} |

**Zjištění:**

1. **L0 má paradoxně nejvyšší EP coverage (96.1%) ale nejnižší validity (82.7%).** Inverzní vztah coverage-validity: model bez kontextu rozloží 50 testů rovnoměrně přes 33 endpointů (1-3 testy na endpoint). Ale tyto testy selhávají na špatných status kódech a timeoutech. L1+ model soustředí testy na business-critical endpointy (POST /orders 3-4 testy, POST /books/discount 3 testy) → vyšší validity ale nižší EP coverage.

2. **L3 Run 2 outlier (52.9%)** dramaticky zkresluje průměr. Model vytvořil 13 not-found testů (GET /authors/9999, GET /categories/9999 atd.) a pokryl jen 18 endpointů. Bez tohoto outlier by L3 medián byl 88.2%. Příčina: DB schéma s FK constraints inspirovalo model k masivnímu testování referenční integrity místo CRUD operací.

3. **EP coverage klesá s kontextem (L0→L1: -11.8 p.p.)** protože model s business znalostmi alokuje více testů na komplexní endpointy. Konkrétně: L0 alokuje průměrně 1.5 testu na endpoint, L1+ alokuje 3-4 testy na POST /orders a POST /books/discount (protože dokumentace popisuje complex business rules).

4. **Konzistentně nepokryté endpointy:**
   - `POST /reset` — korektně odfiltrovaný (framework_rule)
   - `GET /categories/{category_id}`, `GET /tags/{tag_id}` — jednoduché detail endpointy, model je považuje za low-value
   - `GET /categories` — list endpoint, pokrytý méně často na L2+

#### Code coverage (manuální měření — coverage.py, app/ celkem 635 statements)

| Level | Code Cov (avg) | Std | crud.py avg | main.py avg |
|-------|----------------|-----|-------------|-------------|
| L0 | 86.3%          | 6.2 | 71.0%       | 93.3%       |
| L1 | 91.0%          | 1.7 | 81.3%       | 95.3%       |
| L2 | 93.9%          | 1.0 | 87.1%       | 96.7%       |
| L3 | 92.7%          | 3.5 | 84.8%       | 95.6%       |
| L4 | 95.0%          | 1.1 | 89.7%       | 96.7%       |

**Zjištění:**

1. **L0→L1: +4.7 p.p. code coverage (86.3→91.0%).** Dokumentace pomáhá s korektním setup → více testů projde → více kódu je proexecutováno. Nejhůře pokryté CRUD funkce na L0: update_order_status (21%), get_book_average_rating (22%), remove_tags_from_book (29%) — přesně domény kde L0 selhává kvůli timeout chain.

2. **Paradox EP coverage vs code coverage:** L0 má EP coverage 96.1% ale code coverage jen 86.3%. L1 má EP coverage 84.3% ale code coverage 91.0%. Vysvětlení: L0 zavolá endpoint ale test failne → endpoint je "pokrytý" ale kód za error handling path není executed. L1 pokrývá méně endpointů ale testy procházejí → kód je proexecutovaný hlouběji. **Code coverage lépe odráží skutečnou kvalitu testů než endpoint coverage.**

3. **L0 variance je vysoká (std 6.2):** Koreluje s validity rate — run s 76% validity má code coverage 78%, run s 94% validity má 93%. Code coverage silně závisí na počtu passing testů.

4. **crud.py je diferenciátor (L0 71% vs L1 81%):** main.py je thin wrapper (jen routy), coverage je vždy 93%+. Rozdíl mezi levely se projevuje v crud.py kde je business logika — order management, discount pravidla, stock aritmetika.

---

### RQ3: Mutation score

*Jak efektivně detekují vygenerované testy záměrně vnesené chyby?*

_(Bude doplněno po mutmut měření na app/crud.py.)_

---

### RQ4: Typy a příčiny selhání

*Jaké typy selhání vznikají (halucinace, sémantické nepochopení, helper bugy) a liší se mezi modely/úrovněmi?*

#### Failure taxonomy — agregace z první iterace (čerstvé chyby)

| Typ selhání | L0 (53 failů) | L1 (14 failů) | L2 (2 faily) | L3 (1 fail) | L4 (0) |
|-------------|---------------|---------------|--------------|-------------|--------|
| **wrong_status_code** | 17 (32%) | 13 (93%) | 2 (100%) | 1 (100%) | — |
| **timeout** | 31 (58%) | 0 | 0 | 0 | — |
| **assertion_mismatch** | 1 (2%) | 1 (7%) | 0 | 0 | — |
| **other** | 4 (8%) | 0 | 0 | 0 | — |

#### Detailní analýza per kategorie

**1. Timeout (L0 only — 58% L0 failů)**

Timeout je dominantní problém L0 a neobjevuje se na žádném jiném levelu. Příčina je kaskádová:
- Model bez api_knowledge vytvoří knihu bez stock (API default = 0)
- Test create_order selhá na "insufficient stock"
- SQLite DB connection zůstane v nekonzistentním stavu
- Následné HTTP cally timeoutují (30s limit)

Evidence: L0 Run 3 má 78% timeout (18/23 failů). Run 3 používá generic wrappers (post_resource, get_resource) bez error handlingu → chain propagace.

L1+ má api_knowledge `"create_book MUSÍ nastavit stock: 10"` → model vždy vytvoří knihu s dostatečným skladem → žádné timeout chain.

**2. Wrong status code (dominantní na L1, přítomný na L0-L3)**

Nejčastější záměny:
| Záměna | Výskyt | Příčina |
|--------|--------|---------|
| 422→404 | L0 | OpenAPI spec definuje jen 422 pro chyby, ale API vrací 404 pro not-found |
| 400→409 | L1 | Model assertuje generic 400 ale API vrací specifický 409 (conflict) |
| 400→422 | L1, L2 | Model assertuje 400 (business) ale FastAPI vrací 422 (Pydantic validation) |
| 200→201 | L0 | Model neví že POST vrací 201 |
| 200→422 | L0 | Model assertuje success ale endpoint vyžaduje specifický formát |

Evidence: L1 Run 1 má 7/8 failů = wrong_status_code. Model s dokumentací ví co testovat (business pravidla) ale ne přesný HTTP kód.

L2 eliminuje tuto kategorii protože zdrojový kód obsahuje `raise HTTPException(status_code=409)` → model vidí přesný kód.

**3. Assertion value mismatch (sporadický)**

Příklady:
- test_list_books_filtering_by_category (L1 Run 1): `assert response.json()[0]["category_id"] == cat["id"]` — filtrování vrací víc knih než očekáváno kvůli sdílené DB
- test_list_books_filter_by_author (L0 Run 1): `assert all(b["author_id"] == auth["id"] for b in r.json())` — DB obsahuje knihy z předchozích testů

Root cause: testy nejsou plně izolované — sdílená DB obsahuje data z jiných testů. Framework volá POST /reset před pytest ale ne mezi jednotlivými testy.

**4. Halucinace endpointů**

| Level | Halucinovaný endpoint | Příčina |
|-------|----------------------|---------|
| L0 | — | Model se drží OpenAPI spec |
| L1 | — | Model se drží dokumentace |
| L2 Run 1 | POST /auth/login | Model viděl JSON parsing ve zdrojovém kódu a odvodil autentizační endpoint |
| L3 | — | DB schéma nemá auth tabulku → model nehalucinuje |
| L4 | — | Referenční testy nepokrývají auth → model to nekopíruje |

**5. Korektní halucinace status kódů (L0)**

L0 "halucinuje" 404 a 400 — tyto kódy nejsou v OpenAPI spec (která definuje jen 200, 201, 204, 422). Ale API skutečně vrací 404 pro not-found a 400 pro business errors. Model odvodil správné HTTP konvence z obecných znalostí. Toto ukazuje že LLM má silný prior pro HTTP standardy i bez explicitního kontextu.

#### Opravitelnost selhání per level

| Level | Avg failing (iter 1) | Avg fixed | Avg never-fixed | Fix rate |
|-------|---------------------|-----------|-----------------|----------|
| L0 | 17.7 | 9.0 | 8.7 | 50.8% |
| L1 | 4.7 | 1.0 | 3.7 | 21.3% |
| L2 | 0.7 | 0.3 | 0.3 | ~50% |
| L3 | 0.3 | 0 | 0.3 | 0% |
| L4 | 0 | 0 | 0 | — |

**Repair loop je nejefektivnější pro L0** (50.8% fix rate). Typický repair flow: iter 1 helper_fallback opraví centrální helper → 6 testů projde. Iter 2 isolated repair opraví prvních 10 individuálních testů → dalších 2-3 projde. Zbývající testy jsou stale (timeout chain nebo špatná sémantika).

**Repair loop je neefektivní pro L1** (21.3%). Failing testy jsou sémantické (wrong_status_code) — repair vidí chybu ale nemá informaci jaký je správný kód → opravuje "jinak špatně".

---

### Další metriky kvality testů

#### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Val (avg) | Empty Tests | Avg Lines |
|-------|--------------------|--------------------|-------------|-----------|
| L0 | **1.73** | **52.0%** | 0 | 5.85 |
| L1 | 1.37 | 30.7% | 0 | 6.17 |
| L2 | 1.37 | 36.7% | 0 | 5.91 |
| L3 | 1.30 | 29.3% | 0 | 6.01 |
| L4 | 1.43 | 46.7% | 0 | 6.31 |

**L0 má nejvyšší assertion depth (1.73) a response validation (52%).** Paradox: model bez kontextu "nedůvěřuje" API → kontroluje response body aby ověřil správnost. L1+ model "věří" dokumentaci → kontroluje jen status kódy (30.7% response val na L1).

**L4 zvyšuje response validation zpět (46.7%)** protože referenční testy obsahují body checks (`assert r.json()["name"] == ...`).

#### Test type distribution

| Level | Happy Path | Error | Edge Case |
|-------|-----------|-------|-----------|
| L0 | **69.3%** | 28.7% | 2.0% |
| L1 | 55.3% | **44.7%** | 0% |
| L2 | 56.0% | **44.0%** | 0% |
| L3 | 53.3% | **46.7%** | 0% |
| L4 | 60.7% | 36.0% | **3.3%** |

**Více kontextu → více error testů.** L0 generuje 69% happy path — bez kontextu model testuje "jde to zavolat?". L1+ dramaticky zvyšuje error testy (44-47%) protože dokumentace a zdrojový kód popisují error cesty. L4 přidává edge case testy (3.3%) inspirované referenčními testy.

#### Status code diversity

| Level | Unique kódy (avg) | Halucinované |
|-------|-------------------|--------------|
| L0 | 5.7 | 404 ✅, 400 ✅ |
| L1 | 7.0 | žádné |
| L2 | 6.7 | žádné |
| L3 | 7.0 | žádné |
| L4 | 7.0 | žádné |

L1+ konzistentně používá všech 7 kódů (200, 201, 204, 400, 404, 409, 422) — dokumentace je definuje. L0 "halucinuje" 404 a 400 korektně z HTTP konvencí.

#### Instruction compliance — in-context learning efekt

| Level | Timeout compliance (avg %) | Compliance score (avg) |
|-------|---------------------------|------------------------|
| L0 | 0% | 80 |
| L1 | 15% | 80 |
| L2 | 0% | 80 |
| L3 | 36% | 87 |
| L4 | **66%** | **93** |

**Měřitelný in-context learning efekt:** Framework_rule "Timeout=30 na každém HTTP volání" je ignorován na L0-L2 (0-15% compliance). L3 Run 3 dodržuje timeout na 100% callů (nedeterministické). L4 Run 2+3 dodržují timeout na 100% — model kopíruje `timeout=30` z referenčních testů.

**Implikace pro praxi:** Referenční testy (in-context examples) jsou výrazně efektivnější nástroj pro vynucení coding standards než textové instrukce. Toto je klíčový finding pro automatizované generování testů v produkčním prostředí.

---

### Efektivita repair loop

#### Konvergence iterací (průměr přes 3 runy)

| Level | Iter 1 (avg fail) | Iter 2 | Iter 3 | Iter 4 | Iter 5 | Finální |
|-------|-------------------|--------|--------|--------|--------|---------|
| L0 | 17.7 | 13.7 | 9.7 | 9.7 | 8.7 | 82.7% |
| L1 | 4.7 | 4.0 | 3.7 | 3.7 | 3.7 | 92.7% |
| L2 | 0.7 | 0.3 | 0.3 | 0.3 | 0.3 | 99.3% |
| L3 | 0.3 | 0.3 | 0.3 | 0.3 | 0.3 | 99.3% |
| L4 | 0 | — | — | — | — | 100.0% |

**Zjištění:**
1. **Většina oprav proběhne v iteraci 1→2.** L0 opraví průměrně 4.0 testů, L1 opraví 0.7, L2 opraví 0.3.
2. **Iterace 3+ přináší minimální zlepšení.** Zbývající failing testy jsou principiálně neopravitelné (wrong_status_code kde model nemá informaci o správném kódu).
3. **Stale detection funguje:** Identifikuje neopravitelné testy po 3 iteracích → přeskočí je a šetří LLM cally.
4. **L4 nikdy nepotřebuje repair** — 0 selhání ve všech 3 runech.

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
│   ├── phase5_metrics.py      # Výpočet metrik
│   └── phase6_diagnostics.py  # Diagnostiky pro obhajobu
├── main.py                    # Hlavní experiment runner
├── llm_provider.py            # Abstrakce nad LLM providery
├── config.py                  # Konfigurace pro manuální skripty
├── experiment.yaml            # Konfigurace experimentu
├── run_coverage_manual.py     # Manuální měření code coverage
├── .env                       # API klíče (není v gitu)
└── requirements.txt
```

## Licence

Projekt pro diplomovou práci – testování REST API pomocí LLM.