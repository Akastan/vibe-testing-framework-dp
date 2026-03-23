# Analýza běhu: diplomka_v7 — 2026-03-23

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM modely | gemini-3.1-flash-lite-preview |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 34 endpointů) |
| Iterací | 5 |
| Runů na kombinaci | 3 |
| Testů na run | 50 |
| Celkem kombinací | 1 × 5 × 3 = 15 runů |
| Fair design | framework_rules (všechny levely) + api_knowledge (jen L1+) |
| Stale threshold | 3 |
| MAX_INDIVIDUAL_REPAIRS | 10 |

---

## 1. Souhrnná tabulka — Gemini 3.1 Flash Lite (agregace přes 3 runy)

| Level | Validity (avg ± std) | Failed (avg) | Stale (avg) | Iter (avg) | EP Cov (avg) | Assert Depth | Compliance | Čas (avg) |
|-------|---------------------|--------------|-------------|------------|--------------|-------------|------------|-----------|
| L0 | 82.7% ± 8.1 | 8.7 | 4.3 | 5.0 | 96.1% | 1.73 | 80 | 152s |
| L1 | 92.7% ± 8.1 | 3.7 | 4.0 | 4.0 | 84.3% | 1.37 | 80 | 114s |
| L2 | 99.3% ± 1.2 | 0.3 | 0.3 | 2.7 | 87.3% | 1.37 | 80 | 42s |
| L3 | 99.3% ± 1.2 | 0.3 | 0.3 | 2.3 | 77.5% | 1.30 | 87 | 42s |
| L4 | **100.0% ± 0.0** | 0 | 0 | **1.0** | 85.3% | 1.43 | **93** | 42s |

**Hlavní trend:** Validity monotónně roste L0→L4 (82.7→100%). L4 je jediný level s 100% ve všech třech runech a průměrnou 1 iterací. L2 a L3 jsou téměř identické (99.3%), ale L3 má nižší EP coverage kvůli Run 2 outlier (52.9%).

---

## 2. Stabilita napříč runy

### 2.1 Variance validity rate

| Level | Run 1 | Run 2 | Run 3 | Avg | Std | Interpretace |
|-------|-------|-------|-------|-----|-----|--------------|
| L0 | 76.0% | 94.0% | 78.0% | 82.7% | 8.1 | **Nestabilní** — Run 2 výrazně lepší |
| L1 | 84.0% | 100.0% | 94.0% | 92.7% | 8.1 | Nestabilní — Run 1 má 8 stale testů |
| L2 | 98.0% | 100.0% | 100.0% | 99.3% | 1.2 | **Stabilní** |
| L3 | 100.0% | 100.0% | 98.0% | 99.3% | 1.2 | **Stabilní** |
| L4 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0 | **Perfektně stabilní** |

**Otázka oponenta:** "Jsou vaše výsledky reprodukovatelné?"

**Odpověď:** L2–L4 jsou vysoce stabilní (std ≤ 1.2 p.p.). L0 a L1 vykazují vysokou varianci (std 8.1 p.p.) — to je očekávané a vysvětlitelné:

**L0 nestabilita:** Model bez api_knowledge volí nepředvídatelně mezi třemi architekturami:
- **Run 1:** Domain helpery (create_author, create_category, create_book s stock=10, delete_resource) — 5 helperů, ale 20 failing testů v iter 1 kvůli timeout chybám a špatným status kódům. Validity 76%.
- **Run 2:** Pouze `unique()` helper, veškerý setup inline — 1 helper, ale paradoxně nejlepší výsledek (94%). Model bez abstrakce dělal setup korektněji přímo v testech.
- **Run 3:** Generic HTTP wrapper helpery (post_resource, get_resource, put_resource, delete_resource) — 5 helperů, ale 23 failing v iter 1 (78.3% timeout). Generické wrappery neřeší doménovou logiku. Validity 78%.

**L1 nestabilita:** Run 1 měl 8 never-fixed testů (test_update_author_name, test_get_author_books, test_get_category_books_empty — testují endpointy s filtrováním kde model špatně chápe query parametry). Run 2 byl perfektní (100%). Run 3 měl 3 never-fixed (wrong_status_code na discount a stock update).

### 2.2 Konzistentní vs nestabilní kombinace

**Konzistentní** (std ≤ 1.2): L2, L3, L4

**Nestabilní** (std > 4): L0 (8.1), L1 (8.1)

---

## 3. Odpovědi na výzkumné otázky

### RQ1: Jak úroveň kontextu ovlivňuje test validity rate?

| Level | Avg Validity | Std | Trend |
|-------|-------------|-----|-------|
| L0 | 82.7% | 8.1 | Baseline — bez business knowledge |
| L1 | 92.7% | 8.1 | +10.0 p.p. — dokumentace dramaticky pomáhá |
| L2 | 99.3% | 1.2 | +6.7 p.p. — zdrojový kód přináší velký skok |
| L3 | 99.3% | 1.2 | +0.0 p.p. — DB schéma nepřidává validity |
| L4 | 100.0% | 0.0 | +0.7 p.p. — referenční testy = perfektní |

**Zjištění:**

1. **Největší skok je L0→L1 (+10.0 p.p.).** Dokumentace poskytuje kritické informace: stock default=0 → create_book helper MUSÍ nastavit stock: 10; PATCH /stock používá query parametr ne body; POST vrací 201 ne 200; DELETE tags používá request body. Bez těchto informací model hádá a často špatně.

2. **L1→L2 je druhý největší skok (+6.7 p.p.).** Zdrojový kód poskytuje přesné informace o validaci (raise HTTPException s konkrétními status kódy), business pravidlech (discount jen pro knihy starší než rok) a error handling cestách. Model vidí přesně jaký status kód API vrací v jakém případě → dramaticky redukuje wrong_status_code chyby.

3. **L2→L3 nepřináší zlepšení validity (obě 99.3%).** DB schéma přidává jen 929 tokenů. V v6 L3 mělo 100% — v v7 Run 3 má 1 failing test (test_apply_discount_new_book_error). DB schéma pomáhá s pochopením FK constraints a datového modelu, ale informace relevantní pro validity jsou již v L2 zdrojovém kódu.

4. **L4 dosahuje 100% ve všech runech.** Referenční testy poskytují in-context learning — model kopíruje správné patterny (helper struktura, timeout, status kódy). Nulová variance = perfektní reprodukovatelnost.

5. **L0 selhává primárně na dvou kategoriích:**
   - **timeout (46.4% všech L0 chyb):** Model generuje setup který vytváří knihu inline bez stock → order selhává → DB lock → timeout na dalších callech
   - **wrong_status_code (35.7%):** Model assertuje 422 pro not-found (z OpenAPI spec) ale API vrací 404; assertuje 400 místo 409 pro duplikáty

**Proč L0 Run 2 je výrazně lepší (94% vs 76-78%):**
Run 2 použil minimalistickou strategii — pouze `unique()` helper, veškerý setup inline. Paradoxně, bez abstrakce model dělal setup korektněji: každý test si vytvořil autora+kategorii+knihu s explicitními parametry. Runy 1 a 3 použily helpery (domain resp. generic), kde chyba v helperu kaskáduje do mnoha testů.

### RQ2: Jak se liší endpoint coverage mezi úrovněmi?

| Level | EP Cov (avg) | Std | Min run | Max run |
|-------|-------------|-----|---------|---------|
| L0 | **96.1%** | 1.7 | 94.1% | 97.1% |
| L1 | 84.3% | 3.4 | 82.4% | 88.2% |
| L2 | 87.3% | 1.7 | 85.3% | 88.2% |
| L3 | 77.5% | 20.5 | **52.9%** | 91.2% |
| L4 | 85.3% | 5.1 | 82.4% | 91.2% |

**Zjištění:**

1. **L0 má paradoxně nejvyšší EP coverage (96.1%).** Model bez kontextu distribuuje testy rovnoměrně přes všechny endpointy z OpenAPI spec — nemá důvod preferovat jedny před druhými. Ale tyto testy jsou méně kvalitní (nižší validity). Jedinou konzistentně chybějící je POST /reset (korektně odfiltrovaný).

2. **L1+ klesá EP coverage protože model alokuje více testů na business-critical endpointy.** S dokumentací model vidí že orders, discounts a stock management jsou složité → alokuje 3-4 testy na POST /orders místo 1 → méně místa pro GET /categories/{id}. To je správné chování — kvalita nad kvantitou.

3. **L3 má nejnižší průměrnou EP coverage (77.5%) kvůli Run 2 outlier (52.9%).** V Run 2 model soustředil 13 testů na "GET /authors/9999" pattern (not-found testy pro různé entity) a pokryl jen 18 unikátních endpointů z plánu. 16 endpointů nebylo pokryto včetně všech GET list endpointů, GET detail, PUT update a DELETE /books. Toto je artefakt specifického plánovacího rozhodnutí modelu — DB schéma ukázalo 404 pattern pro neexistující entity a model ho nadměrně testoval.

4. **L4 má konzistentní EP coverage (82.4-91.2%).** Referenční testy ukazují balanced přístup — model kopíruje distribuci z existujících testů.

**Konzistentně nepokryté endpointy (2+ levely):**
- `POST /reset` — korektně odfiltrovaný ve všech levelech
- `GET /categories/{category_id}` — chybí v L0 Run 1, L2 Run 1+2, L3 Run 3, L4 Run 1+3
- `GET /tags/{tag_id}` — chybí v L1 Run 1+3, L2 Run 1+3, L4 Run 2+3
- `GET /categories` — chybí v L2 Run 1, L3 Run 2, L4 Run 2+3

### RQ3: Mutation score

_(Bude doplněno po mutmut měření.)_

### RQ4: Jaké typy selhání vznikají?

**Failure taxonomy z první iterace (čerstvé tracebacky):**

| Level | Celkem failures (iter 1) | wrong_status_code | timeout | assertion_mismatch | other |
|-------|-------------------------|-------------------|---------|-------------------|-------|
| L0 | 53 (3 runy) | 17 (32.1%) | 31 (58.5%) | 1 (1.9%) | 4 (7.5%) |
| L1 | 14 (3 runy) | 13 (92.9%) | 0 (0%) | 1 (7.1%) | 0 (0%) |
| L2 | 2 (3 runy) | 2 (100%) | 0 (0%) | 0 (0%) | 0 (0%) |
| L3 | 1 (3 runy) | 1 (100%) | 0 (0%) | 0 (0%) | 0 (0%) |
| L4 | 0 (3 runy) | — | — | — | — |

**Klíčová zjištění:**

1. **Timeout je dominantní problém L0 (58.5%).** Příčina: model bez api_knowledge generuje setup kde kniha nemá dostatečný stock → create_order selhává → DB se zamkne → následné HTTP cally timeout. Toto se neobjevuje na L1+ protože api_knowledge říká "stock: 10".

2. **wrong_status_code je hlavní problém L1 (92.9%).** Model s dokumentací ví jaké chyby testovat, ale ne vždy správně odhadne konkrétní HTTP status kód. Typické záměny: 400↔409 (business error vs conflict), 404↔422 (not found vs validation), 200↔201 (success vs created).

3. **L2+ má minimální selhání.** Zdrojový kód obsahuje explicitní `raise HTTPException(status_code=...)` → model vidí přesný kód.

4. **L4 má nulové selhání.** Referenční testy poskytují přesné příklady správných assertů.

---

## 4. Detailní rozbor selhání — per Level

### 4.1 L0 — Black-box (pouze OpenAPI spec)

**Pattern across 3 runů:**
- Run 1: 38/50 (76.0%) — 20F v iter 1, helper_fallback+isolated, 12 never-fixed
- Run 2: 47/50 (94.0%) — 10F v iter 1, isolated, 3 never-fixed
- Run 3: 39/50 (78.0%) — 23F v iter 1, helper_fallback+isolated, 11 never-fixed

**Proč Run 2 je výrazně lepší:**
Run 2 má pouze 1 helper (`unique()`). Veškerý setup je inline — každý test vytváří POST /authors, POST /categories, POST /books s explicitními parametry. Model bez helperů nedělá chybu v centralizovaném setupu → méně kaskádových selhání. Runy 1 a 3 mají helpery kde chyba v helperu (timeout kvůli chybějícímu stock) propaguje do 10+ testů.

**Kategorie never-fixed testů (across runů):**

| Kategorie | Příklady | Počet (celkem) | Root cause |
|-----------|---------|----------------|------------|
| Timeout z inline setupu | test_book_price_update, test_list_book_reviews, test_patch_book_partial_update | 8 | Setup vytváří knihu přes inline POST který timeoutuje kvůli DB lock z předchozích testů |
| Wrong status code | test_create_category_duplicate_name (400→409), test_create_author_missing_required_fields (422→200), test_update_category_description (200→422) | 7 | Model assertuje špatný HTTP kód bez znalosti API chování |
| Assertion mismatch | test_list_books_filter_by_author, test_get_books_pagination_limit | 3 | Model špatně chápe query parametry (filter vs pagination) |
| Stock/order kaskáda | test_create_order_success, test_get_order_detail, test_delete_pending_order | 5 | Chybí stock → order se nevytvoří → navazující testy selhávají |
| Neexistující endpoint | test_delete_invalid_order_status (PATCH ne DELETE pro status) | 3 | Model hádá endpoint URL bez kontextu |

**Timeout pattern detail:**
Run 3 má 78.3% timeoutů (18/23). Model použil generic helpery (post_resource, get_resource) které interně volají requests bez specifického error handlingu. Když první book creation selhá (chybí povinné pole nebo FK constraint), helper vrátí error response místo JSON → další kód spadne → DB connection zůstane otevřená → timeout chain.

### 4.2 L1 — OpenAPI + dokumentace

**Pattern across 3 runů:**
- Run 1: 42/50 (84.0%) — 8F v iter 1, isolated, 0 fixed, 8 never-fixed
- Run 2: 50/50 (100.0%) — 2F v iter 1, isolated, 2 fixed v iter 2
- Run 3: 47/50 (94.0%) — 4F v iter 1, isolated, 1 fixed, 3 never-fixed

**Run 2 je perfektní** protože model s dokumentací vygeneroval přesně správné helpery a testoval endpointy které existují. Jen 2 testy selhaly v iter 1 (wrong_status_code na test_create_book_no_author a test_apply_discount_new_book_error) — oba opraveny repair loopem.

**Run 1 selhává nejvíce (84.0%):** 8 never-fixed testů, všechny wrong_status_code:
- test_update_author_name: assertuje 200 ale PUT /authors vrací jiný kód
- test_apply_discount_valid: assertuje 200 ale POST /discount vrací jiný formát
- test_get_author_books: assertuje 200 na GET /books?author_id=X — endpoint existuje ale vrací jiný formát
- test_get_category_books_empty: assertuje 200 na GET /books?category_id=X s prázdným výsledkem
- test_list_books_filtering_by_category: assertion_value_mismatch — filtrování vrací víc knih než očekáváno
- test_list_books_invalid_pagination: assertuje 422 pro špatný page param ale API vrací 200 s prázdným listem
- test_create_review_nonexistent_book: assertuje 404 ale API vrací 422
- test_create_order_insufficient_stock: assertuje 400 ale API vrací jiný kód

**Klíčový finding:** L1 selhání jsou sémantická — model chápe co testovat (business pravidla z dokumentace) ale ne vždy správně odhadne přesný status kód nebo response formát. Dokumentace popisuje chování slovně ("vrací chybu při nedostatečném skladu") ale nespecifikuje přesný HTTP kód.

### 4.3 L2 — OpenAPI + dokumentace + zdrojový kód

**Pattern across 3 runů:**
- Run 1: 49/50 (98.0%) — 1 stale (test_login_with_malformed_json — POST /auth/login neexistuje)
- Run 2: 50/50 (100.0%) — 1F v iter 1 (test_create_book_nonexistent_author 422→404), opraveno
- Run 3: 50/50 (100.0%) — perfektní na první pokus

**L2 je dramaticky stabilnější než L1.** Zdrojový kód eliminuje ambiguitu status kódů — model vidí `raise HTTPException(status_code=409, detail="...")` a assertuje přesně 409.

**Jediný stale test (Run 1):** test_login_with_malformed_json — model viděl ve zdrojovém kódu validační logiku a vytvořil test pro POST /auth/login, endpoint který neexistuje. Model "halucinoval" autentizační endpoint ze zdrojového kódu kde viděl JSON parsing.

### 4.4 L3 — OpenAPI + dokumentace + zdrojový kód + DB schéma

**Pattern across 3 runů:**
- Run 1: 50/50 (100.0%) — perfektní na první pokus
- Run 2: 50/50 (100.0%) — perfektní na první pokus, ale EP coverage jen 52.9%
- Run 3: 49/50 (98.0%) — 1 stale (test_apply_discount_new_book_error)

**Run 2 EP coverage anomálie:** Model soustředil 13/50 testů na "not found" pattern (GET /authors/9999, GET /categories/9999 atd.) — 62% error testů. EP coverage klesla na 52.9% protože model nepokryl GET list, PUT update a většinu DELETE endpointů. DB schéma ukázalo FK constraints a NOT NULL → model se soustředil na testování integrity constraints místo CRUD operací.

**Run 3 stale test:** test_apply_discount_new_book_error — model testuje discount pro knihu s published_year aktuálního roku. Assertuje status 400 ale API vrací jiný kód. Tento test selhává opakovaně protože model nechápe přesnou sémantiku "nová kniha" (published_year ≥ aktuální rok - 1 vs = aktuální rok).

### 4.5 L4 — Kompletní kontext + referenční testy

**Všechny 3 runy: 50/50 (100.0%) na první iteraci.**

L4 je jediný level kde všechny 3 runy dosáhly perfektního výsledku bez jakékoliv opravy. Referenční testy poskytují:
- Přesné helper signatury s timeout=30 a assert status_code v těle
- Správné status kódy pro každý typ operace
- Korektní setup pattern (create_test_author → create_test_category → create_test_book)
- Pattern pro order testy (create_test_order helper)

---

## 5. Diagnostiky — cross-cutting analýzy

### 5.1 Context size a prompt budget

| Level | Tokeny (est) | Sekce | Budget (% okna 128k) |
|-------|-------------|-------|----------------------|
| L0 | 20,737 | 1 (OpenAPI) | 20.1% |
| L1 | 22,538 | 2 (+docs: +1,788) | 21.5% |
| L2 | 34,023 | 3 (+source: +11,474) | 30.5% |
| L3 | 34,961 | 4 (+schema: +929) | 31.1% |
| L4 | 40,734 | 5 (+tests: +5,759) | 35.8% |

**Otázka oponenta:** "Nepřetížili jste model kontextem?"

**Odpověď:** Maximální prompt budget je 35.8% (L4). Model má vždy >82k tokenů volných pro generování. L4 s největším kontextem dosahuje nejlepších výsledků (100% validity, 0 stale) — kontext nepřetěžuje model. L2→L3 přidává jen 929 tokenů ale udržuje stejnou validity (99.3%) — důkaz že kvalita kontextu je důležitější než kvantita.

### 5.2 Helper snapshot — strukturální rozdíly

| Level | Helperů (avg) | create_book stock | Asserty v helperu | Strategie |
|-------|--------------|-------------------|-------------------|-----------|
| L0 | 3.7 | Variabilní | Ne | Run 1: domain, Run 2: žádné, Run 3: generic wrappers |
| L1 | 4.0 | ✅ stock=10 | Ne | Konzistentní domain helpers |
| L2 | 4.0 | ✅ stock=10 | Run 3 ano | Stejné jako L1, Run 1 create_test_* naming |
| L3 | 4.3 | ✅ stock=10 | Run 2 ano | Lépe parametrizované (name=None), Run 2 +create_tag |
| L4 | **5.3** | ✅ stock=10 | **Ano (všechny)** | +create_test_tag, Run 2 +create_test_order |

**Klíčový finding:** L4 helpery mají `assert r.status_code == 201` v těle — selhání v setupu je viditelné okamžitě. L0-L1 helpery nemají asserty → setup tiše selhává a kaskáduje.

### 5.3 Instruction compliance

| Level | Missing timeout (avg %) | Compliance score (avg) |
|-------|------------------------|------------------------|
| L0 | 100% | 80 |
| L1 | 85% | 80 |
| L2 | 100% | 80 |
| L3 | 64% | **87** |
| L4 | 34% | **93** |

**Finding — in-context learning efekt na compliance:**

L0-L2 ignorují framework_rule "Timeout=30 na každém HTTP volání" na 85-100% callů. Model čte pravidlo ale neimplementuje ho.

L3 Run 3 má compliance=100 (timeout na všech 75 callech), Run 1+2 mají 80 — nedeterministické.

L4 Run 2+3 mají compliance=100 — model kopíruje `timeout=30` z referenčních testů. Run 1 nemá timeout přesto že referenční testy ho obsahují.

**Implikace:** Referenční testy (L4) jsou výrazně efektivnější nástroj pro vynucení coding standards než textové instrukce (framework_rules). Toto je měřitelný in-context learning efekt.

### 5.4 Status code halucinace

| Level | Kódy v OpenAPI spec | Halucinované v kódu | Korektní? |
|-------|-------------------|--------------------|-----------| 
| L0 | 200, 201, 204, 422 | **404**, 400 | 404 ✅ (HTTP konvence), 400 ✅ (generic error) |
| L1 | +400, 404, 409 | žádné | — |
| L2 | +400, 404, 409 | žádné | — |
| L3 | +400, 404, 409 | žádné | — |
| L4 | +400, 404, 409 | žádné | — |

**L0 halucinuje 404** — ale je to **korektní halucinace**. OpenAPI spec definuje jen 422 pro chyby, ale API skutečně vrací 404 pro not-found. Model odvodil správné HTTP konvence z obecných znalostí. L1+ dostávají 404 v dokumentaci → nehalucinují.

### 5.5 Test type distribution

| Level | Happy % | Error % | Edge % | Error-focused EP (avg) |
|-------|---------|---------|--------|------------------------|
| L0 | **69.3%** | 28.7% | 2.0% | 13.7 |
| L1 | 55.3% | **44.7%** | 0% | 17.3 |
| L2 | 56.0% | **44.0%** | 0% | 16.3 |
| L3 | 53.3% | **46.7%** | 0% | 14.7 |
| L4 | 60.7% | 36.0% | **3.3%** | 15.0 |

**Trend:** L0 generuje 69% happy path — bez kontextu model neví jaké error scénáře testovat. L1+ dramaticky zvyšuje error testy (44-47%) protože dokumentace popisuje business rules. L4 má nejvíce edge case testů (3.3%) — referenční testy inspirují k boundary testing.

### 5.6 Plan-code drift

| Level | Drift count (avg) | Plan adherence (avg) |
|-------|-------------------|---------------------|
| L0 | 4.7 | 81.3% |
| L1 | 1.7 | 82.7% |
| L2 | 2.3 | 100% |
| L3 | 1.0 | 100% |
| L4 | 2.7 | 99.3% |

**L0 má nejvyšší drift (4.7)** a nejnižší plan adherence (81.3%). Model při generování kódu přejmenuje a předělá testy oproti plánu — bez kontextu je plán vágní a kód se odchyluje.

**L2-L4 mají 99-100% plan adherence** — model se zdrojovým kódem generuje přesně to co naplánoval.

### 5.7 Code patterns — komplexita testů

| Level | Avg HTTP calls | Avg helper calls | Side-effect % | Chaining % |
|-------|---------------|-----------------|---------------|------------|
| L0 | 1.35 | 0.72 | 9.3% | 24.0% |
| L1 | 1.37 | 2.07 | 6.0% | 12.7% |
| L2 | 1.33 | 2.05 | 5.3% | 24.0% |
| L3 | 1.34 | 2.07 | 4.7% | 18.0% |
| L4 | 1.16 | **2.25** | 3.3% | **33.3%** |

**L0 má nejméně helper callů (0.72)** — Run 2 nemá žádné domain helpery → průměr klesá. Model bez kontextu méně často používá helpery a dělá víc setup inline.

**L4 má nejvíce helper callů (2.25) a chaining (33.3%)** — referenční testy ukazují pattern `data = r.json()["field"]` → model to kopíruje. Více chaining = testy ověřují response body, ne jen status kódy.

### 5.8 Repair trajectory

| Level | Avg 1st iter fails | Avg final fails | Avg fixed | Avg never-fixed | Repair úspěšnost |
|-------|--------------------|-----------------|-----------|-----------------|-----------------| 
| L0 | 17.7 | 8.7 | 9.0 | 8.7 | 50.8% |
| L1 | 4.7 | 3.7 | 1.0 | 3.7 | 21.3% |
| L2 | 0.7 | 0.3 | 0.3 | 0.3 | 50.0% |
| L3 | 0.3 | 0.3 | 0 | 0.3 | 0% |
| L4 | 0 | 0 | 0 | 0 | — |

**Otázka oponenta:** "Funguje váš repair loop?"

**Odpověď:** Repair loop je nejefektivnější pro L0 kde opravuje ~51% failing testů (17.7→8.7 průměrně). Typický pattern: iter 1 = helper_fallback (opraví helper funkce), iter 2 = isolated (opraví prvních 10 jednotlivých testů), iter 3+ = stale detection (zbývající testy jsou neopravitelné).

Pro L1 repair loop opraví jen ~21% — selhání jsou sémantická (wrong_status_code) a model nemá informaci k opravě.

L4 repair loop nepotřebuje — 0 selhání ve všech runech.

**Konvergence:** L0 konverguje průměrně ve 2.7 iteraci (failing count se stabilizuje). L1 konverguje ve 2.0. L2-L4 konvergují v 1-2 iteracích.

### 5.9 Response validation

| Level | Avg response validation % |
|-------|--------------------------|
| L0 | 52.0% |
| L1 | 30.7% |
| L2 | 36.7% |
| L3 | 29.3% |
| L4 | **46.7%** |

**Paradox:** L0 má nejvyšší response validation (52%) protože model bez kontextu kontroluje response body aby ověřil správnost — "nedůvěřuje" API. L1 má nejnižší (30.7%) protože model s dokumentací věří že API dělá co dokumentace říká → kontroluje jen status kódy. L4 opět zvyšuje (46.7%) protože referenční testy obsahují body checks.

---

## 6. Bugy a limitace

### 6.1 L3 Run 2 EP coverage outlier (52.9%)

Model soustředil 13 testů na GET /authors/9999 pattern (not-found pro různé entity) → pokryl jen 18 unikátních endpointů. Toto je artefakt modelu, ne bugu ve frameworku — plan_analysis ukazuje `"GET /authors/9999": 13` testů.

**Dopad:** Zkresluje L3 EP coverage průměr. Medián (88.24%) by byl reprezentativnější.

### 6.2 L1 Run 1 — 8 never-fixed testů

Run 1 měl 8 testů které selhaly od první iterace a nikdy nebyly opraveny. Repair loop je zkusil 2× (isolated), pak je označil jako stale. Příčina: testují endpointy s filtrováním/paginací kde model špatně chápe API chování (GET /books?author_id= vrací jiný formát než očekáváno).

### 6.3 Timeout chain v L0

Run 3 měl 78.3% timeout chyb (18/23 failing testů). Generic HTTP wrapper helpery (post_resource, get_resource) nemají specifický error handling → první selhání zablokuje DB → chain timeoutů. Framework detekuje infra chyby a restartuje, ale s generickými helpery se chyba opakuje.

---

## 7. Srovnání v6 vs v7

| Metrika | v6 (stale_threshold=3) | v7 (stale_threshold=3) | Změna |
|---------|----------------------|----------------------|-------|
| L0 validity | 85.3% ± 7.7 | 82.7% ± 8.1 | ↓ -2.6 p.p. (v rámci variance) |
| L1 validity | 95.3% ± 4.1 | 92.7% ± 8.1 | ↓ -2.6 p.p. (vyšší variance) |
| L2 validity | 96.0% ± 3.3 | **99.3% ± 1.2** | ↑ +3.3 p.p. |
| L3 validity | 100.0% ± 0.0 | 99.3% ± 1.2 | ↓ -0.7 p.p. (1 stale v Run 3) |
| L4 validity | 98.7% ± 1.9 | **100.0% ± 0.0** | ↑ +1.3 p.p. (perfektní) |

**Hlavní změny v7:**
- L2 zlepšení: 2 ze 3 runů perfektní (vs 1 v v6)
- L4 perfektní: všechny 3 runy 100% (vs 2 v v6)
- L0/L1 mírně horší ale v rámci variance
- failure_taxonomy nyní funguje (v6 mělo 100% unknown_no_error_captured bug)

---

## 8. Code coverage

_(Bude doplněno po manuálním měření coverage.py.)_

---

## 9. Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1 (76.0%)</summary>

```
Validity: 76.0% (38/50)
EP Coverage: 97.06% (33/34)
Assert Depth: 1.94
Stale: 8
Iterations: 5
Helpers: 5 (unique, create_author, create_category, create_book stock=10 year=2020, delete_resource)
Plan adherence: 46% (27 testů jen v kódu, 27 jen v plánu)
Failure taxonomy (iter 1): wrong_status_code 8 (40%), timeout 8 (40%), other 3 (15%), assertion_mismatch 1 (5%)
Repair: iter1=20F→helper_fallback, iter2=14F→isolated(10), iter3=12F→helper_fallback, iter4=12F→isolated(10), iter5=12F
Never-fixed (12): test_update_stock_success, test_update_author_name_only, test_list_book_reviews,
  test_book_price_update, test_create_category_duplicate_name, test_list_books_filter_by_author,
  test_update_order_status_invalid, test_get_books_pagination_limit, test_create_author_missing_required_fields,
  test_update_category_description, test_create_review_for_nonexistent_book, test_patch_book_partial_update
Fixed (8): test_apply_discount_success, test_create_order_success, test_create_review_invalid_rating,
  test_delete_author_success, test_delete_book, test_get_author_invalid_id, test_get_book_details,
  test_update_order_status_success
```
</details>

<details>
<summary>L0 — Run 2 (94.0%)</summary>

```
Validity: 94.0% (47/50)
EP Coverage: 94.12% (32/34) — chybí PATCH /orders/{order_id}/status
Assert Depth: 1.56
Stale: 4
Iterations: 5
Helpers: 1 (unique only — veškerý setup inline!)
Plan adherence: 98% (49/50)
Failure taxonomy (iter 1): wrong_status_code 4 (40%), timeout 5 (50%), other 1 (10%)
Repair: iter1=10F→isolated(10), iter2=4F→isolated(4), iter3=3F→stale_skip, iter4=3F→stale_skip, iter5=3F
Never-fixed (3): test_delete_author_success, test_update_stock_negative, test_get_missing_order
Fixed (7): test_apply_discount_success, test_create_review_success, test_delete_book_item,
  test_delete_shipped_order_fail, test_get_book_detail, test_get_nonexistent_author, test_update_book_stock_count
```
</details>

<details>
<summary>L0 — Run 3 (78.0%)</summary>

```
Validity: 78.0% (39/50)
EP Coverage: 97.06% (33/34)
Assert Depth: 1.68
Stale: 1
Iterations: 5
Helpers: 5 (unique, post_resource, get_resource, put_resource, delete_resource — generic wrappers!)
Plan adherence: 100%
Failure taxonomy (iter 1): wrong_status_code 5 (21.7%), timeout 18 (78.3%)
Repair: iter1=23F→helper_fallback, iter2=23F→isolated(10), iter3=14F→helper_fallback, iter4=14F→isolated(10), iter5=11F
Never-fixed (11): test_list_books_page_overflow, test_get_rating_success, test_apply_discount_too_high,
  test_remove_tags_from_book, test_create_order_success, test_get_order_detail, test_delete_pending_order,
  test_delete_invalid_order_status, test_update_order_to_shipped, test_update_order_to_cancelled,
  test_update_order_invalid_transition
Fixed (12): test_add_tags_to_book, test_apply_discount_success, test_create_review_invalid_rating,
  test_create_review_success, test_delete_author_success, test_delete_book_success, test_get_book_detail,
  test_get_nonexistent_author, test_get_nonexistent_book, test_list_reviews_success, test_update_book_title,
  test_update_stock_increase
```
</details>

### L1

<details>
<summary>L1 — Run 1 (84.0%)</summary>

```
Validity: 84.0% (42/50)
EP Coverage: 82.35% (28/34)
Assert Depth: 1.60
Stale: 8
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 48%
Failure taxonomy (iter 1): assertion_mismatch 1, wrong_status_code 7
Repair: iter1=8F→isolated(8), iter2=8F→isolated(8), iter3=8F→stale_skip, iter4=8F→stale_skip, iter5=8F
Never-fixed (8): test_list_books_filtering_by_category, test_create_review_nonexistent_book,
  test_create_order_insufficient_stock, test_update_author_name, test_apply_discount_valid,
  test_get_author_books, test_list_books_invalid_pagination, test_get_category_books_empty
Fixed: 0 (žádný test nebyl opraven)
```
</details>

<details>
<summary>L1 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 82.35% (28/34)
Iterations: 2 (1 repair iterace)
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Failure taxonomy (iter 1): wrong_status_code 2
Fixed (2): test_create_book_no_author, test_apply_discount_new_book_error
```
</details>

<details>
<summary>L1 — Run 3 (94.0%)</summary>

```
Validity: 94.0% (47/50)
EP Coverage: 88.24% (30/34)
Stale: 4
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Failure taxonomy (iter 1): wrong_status_code 4
Repair: iter1=4F→isolated(4), iter2=4F→isolated(4), iter3=3F→stale_skip, iter4=3F→stale_skip, iter5=3F
Never-fixed (3): test_list_books_invalid_query_params, test_apply_discount_new_book_fails,
  test_update_book_stock_nullable
Fixed (1): test_create_order_malformed_json
```
</details>

### L2

<details>
<summary>L2 — Run 1 (98.0%)</summary>

```
Validity: 98.0% (49/50)
EP Coverage: 85.29% (29/34)
Stale: 1 (test_login_with_malformed_json — POST /auth/login neexistuje)
Iterations: 5
Helpers: 4 (unique, create_test_author, create_test_category, create_test_book)
Plan adherence: 100%
Compliance: 80
```
</details>

<details>
<summary>L2 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 88.24% (30/34)
Iterations: 2 (1 repair)
Helpers: 4 (unique, create_author, create_category, create_book)
Fixed (1): test_create_book_nonexistent_author (422→404)
```
</details>

<details>
<summary>L2 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 88.24% (30/34)
Iterations: 1 (perfektní na první pokus)
Helpers: 4 (unique, create_author, create_category, create_book) — has_assertion=true
Compliance: 80
```
</details>

### L3

<details>
<summary>L3 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 91.18% (31/34)
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book)
Compliance: 80
```
</details>

<details>
<summary>L3 — Run 2 (100.0%) ✅ — nízká EP coverage</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 52.94% (18/34) — OUTLIER
Iterations: 1
Helpers: 5 (+create_tag, has_assertion=true, name=None params)
Compliance: 80
Domain focus: authors 17/50 (34%) — 13 testů na not-found pattern
Test type: 38% happy, 62% error
```
</details>

<details>
<summary>L3 — Run 3 (98.0%)</summary>

```
Validity: 98.0% (49/50)
EP Coverage: 88.24% (30/34)
Stale: 1 (test_apply_discount_new_book_error)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book)
Compliance: 100 (timeout na všech 75 callech!)
```
</details>

### L4

<details>
<summary>L4 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 91.18% (31/34)
Iterations: 1
Helpers: 5 (unique, create_test_author, create_test_category, create_test_book, create_test_tag) — all with assertion
Compliance: 80
Response validation: 62% (highest across all runs)
Chaining: 46% (highest across all runs)
```
</details>

<details>
<summary>L4 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 82.35% (28/34)
Iterations: 1
Helpers: 6 (+create_test_order) — all with assertion
Compliance: 100 (timeout na všech 61 callech)
```
</details>

<details>
<summary>L4 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 82.35% (28/34)
Iterations: 1
Helpers: 5 (unique, create_test_author, create_test_category, create_test_book, create_test_tag) — all with assertion
Compliance: 100 (timeout na všech 62 callech)
```
</details>