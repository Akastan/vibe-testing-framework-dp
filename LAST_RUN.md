# Analýza běhu: diplomka_v6 — 2026-03-22

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM modely | gemini-3.1-flash-lite-preview _(deepseek-chat — čeká na běh)_ |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 34 endpointů) |
| Iterací | 5 |
| Runů na kombinaci | 3 |
| Testů na run | 50 |
| Celkem kombinací | 1 × 5 × 3 = 15 runů (Gemini hotovo) |
| Fair design | framework_rules (všechny levely) + api_knowledge (jen L1+) |
| Stale threshold | 3 (test musí selhat 3× se stejnou chybou než je označen) |
| MAX_INDIVIDUAL_REPAIRS | 10 |

---

## 1. Souhrnná tabulka — Gemini 3.1 Flash Lite (agregace přes 3 runy)

| Level | Validity (avg ± std) | Failed (avg) | Stale (avg) | Iter (avg) | EP Cov (avg) | Assert Depth | Compliance | Čas (avg) |
|-------|---------------------|--------------|-------------|------------|--------------|-------------|------------|-----------|
| L0 | 85.3% ± 7.7 | 7.3 | 0.7 | 5.0 | 93.1% | 1.68 | 80 | 145s |
| L1 | 95.3% ± 4.1 | 2.3 | 2.3 | 3.7 | 74.5% | 1.29 | 80 | 91s |
| L2 | 96.0% ± 3.3 | 2.0 | 2.0 | 3.7 | 79.4% | 1.42 | 80 | 99s |
| L3 | **100.0% ± 0.0** | 0 | 0 | **1.0** | 81.4% | 1.30 | 87 | 42s |
| L4 | 98.7% ± 1.9 | 0.7 | 0.7 | 2.7 | 88.2% | 1.45 | 93 | 66s |

**Hlavní trend:** Validity monotónně roste L0→L3 (85→100%), L4 mírný pokles na 98.7%. L3 je jediný level s 100% ve všech třech runech.

---

## 2. Stabilita napříč runy

### 2.1 Variance validity rate

| Level | Run 1 | Run 2 | Run 3 | Avg | Std | Interpretace |
|-------|-------|-------|-------|-----|-----|--------------|
| L0 | 78.0% | 96.0% | 82.0% | 85.3% | 7.7 | **Nestabilní** — Run 2 výrazně lepší, Run 1 nejhorší |
| L1 | 96.0% | 100.0% | 90.0% | 95.3% | 4.1 | Mírná variance — Run 3 halucinuje neexistující endpointy |
| L2 | 96.0% | 100.0% | 92.0% | 96.0% | 3.3 | Přijatelná variance |
| L3 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0 | **Perfektně stabilní** |
| L4 | 100.0% | 96.0% | 100.0% | 98.7% | 1.9 | Stabilní — jen Run 2 má 2 stale |

**Otázka oponenta:** "Jsou vaše výsledky reprodukovatelné?"

**Odpověď:** L3 a L4 jsou vysoce stabilní (std ≤ 1.9 p.p.). L0 vykazuje vysokou varianci (std 7.7 p.p.) — to je očekávané, protože bez kontextu závisí kvalita testů na tom, jakou strategii model zvolí (inline setup vs generic helpery vs domain-specific helpery). L0 Run 1 vygeneroval generic wrapper helpery (api_get, api_post) místo domain helperů (create_book) → 22 failing testů v první iteraci. L0 Run 2 vygeneroval správné domain helpery rovnou → jen 5 failing. Tato strukturální náhodnost je inherentní vlastnost L0 bez kontextu.

### 2.2 Konzistentní vs nestabilní kombinace

**Konzistentní** (std ≤ 2 p.p.): L3 (0.0), L4 (1.9)

**Nestabilní** (std > 4 p.p.): L0 (7.7), L1 (4.1)

Příčina nestability L0: Model bez api_knowledge volí nepředvídatelně mezi dvěma architekturami — (a) generic HTTP wrapper helpery (api_get/api_post) kde každý test dělá setup inline, nebo (b) domain helpery (create_book s parametry). Architektura (a) vede k masivnímu selhání protože inline setup opakuje stejné chyby (chybí stock, špatný ISBN formát). Architektura (b) centralizuje setup → selhání se opravují efektivněji.

Příčina nestability L1: Run 3 vygeneroval testy na neexistující endpointy (POST /auth/login, GET /books/search, PATCH /books/{book_id}, POST /orders/{order_id}/items) — model s dokumentací "halucinoval" endpointy které viděl popsané ale neexistují v OpenAPI spec. Tyto testy jsou neopravitelné → stale.

---

## 3. Odpovědi na výzkumné otázky (Gemini — DeepSeek doplnit)

### RQ1: Jak úroveň kontextu ovlivňuje test validity rate?

| Level | Avg Validity | Trend |
|-------|-------------|-------|
| L0 | 85.3% | Baseline — bez business knowledge |
| L1 | 95.3% | +10.0 p.p. — dokumentace dramaticky pomáhá |
| L2 | 96.0% | +0.7 p.p. — zdrojový kód minimální přidaná hodnota |
| L3 | 100.0% | +4.0 p.p. — DB schéma = perfektní výsledek |
| L4 | 98.7% | −1.3 p.p. — referenční testy mírně snižují (variance) |

**Zjištění:**

1. **Největší skok je L0→L1 (+10 p.p.).** Dokumentace poskytuje kritické informace: stock default=0, PATCH stock je query parametr ne body, POST vrací 201 ne 200, DELETE tags používá request body. Bez těchto informací model hádá a často špatně.

2. **L2→L3 je překvapivý skok na 100%.** DB schéma přidává jen 929 tokenů ale dává modelu jasný obraz datového modelu — FK constraints, nullable sloupce, CHECK constraints. Model pak lépe chápe validační logiku a generuje korektní error testy.

3. **L4 je paradoxně mírně horší než L3.** Referenční testy (+5759 tokenů) inspirují model k testování složitějších scénářů (test_apply_discount_new_book, test_list_tags_empty) které jsou náchylnější k selhání. L3 generuje jednodušší ale korektnější testy.

4. **L1 a L2 jsou téměř identické (95.3% vs 96.0%).** Zdrojový kód (+11474 tokenů) nepřináší výrazné zlepšení validity — většina potřebných informací je už v dokumentaci. Zdrojový kód pomáhá hlavně s error testy (vidí raise HTTPException) ale tyto jsou náchylnější k drift (plán 400 → kód 422).

**Proč L0 selhává — konkrétní příčiny:**
- **Chybí stock:** Model neví že API default stock=0 → create_order testy selhávají na insufficient stock
- **Špatný HTTP method:** PATCH /stock používá query params ne JSON body → stock update testy selhávají
- **Špatné status kódy:** Model hádá 422 pro not-found (OpenAPI spec říká 422 pro validaci) ale API vrací 404
- **Generic helpery:** Když model zvolí api_get/api_post wrapper strategii, chybí centralizovaný create_book helper → každý test opakuje setup chyby

### RQ2: Jak se liší endpoint coverage mezi úrovněmi?

| Level | EP Coverage (avg) | Uncovered (typicky) |
|-------|------------------|---------------------|
| L0 | **93.1%** | /reset, občas PATCH /orders/status |
| L1 | 74.5% | GET detail endpointy, PUT update endpointy |
| L2 | 79.4% | Podobné jako L1 |
| L3 | 81.4% | Variabilní — Run 2 jen 67.7% |
| L4 | **88.2%** | /reset, občas GET /categories |

**Zjištění:**

1. **L0 má paradoxně nejvyšší EP coverage (93.1%).** Model bez kontextu distribuuje testy rovnoměrně přes všechny endpointy z OpenAPI spec — nemá důvod preferovat jedny před druhými. Ale tyto testy jsou méně kvalitní (nižší validity).

2. **L1+ klesá EP coverage protože model alokuje více testů na business-critical endpointy.** S dokumentací model vidí že orders, discounts a stock management jsou složité → alokuje 3-4 testy na POST /orders místo 1-2 → méně místa pro GET /categories/{id}. To je správné chování — kvalita nad kvantitou.

3. **L3 Run 2 má nejnižší EP coverage (67.7%)** — model soustředil 24/50 testů na books domain a pominul 11 endpointů. DB schéma ukázalo složitost book tabulky (FK na author, category, stock constraint) → model se tam soustředil.

### RQ3: Mutation score

_(Bude doplněno po mutmut měření.)_

### RQ4: Jaké typy selhání vznikají?

**KRITICKÝ BUG V DIAGNOSTICE:** Všech 100% failing testů je klasifikováno jako `unknown_no_error_captured`. Funkce `_extract_error_block()` nenachází chybové bloky v pytest logu. Pravděpodobná příčina: pytest s `--tb=short` generuje jiný formát tracebacku než regex očekává. Tento bug musí být opraven před finálním během.

**Kvalitativní analýza z logů (manuální):**

Na základě názvů failing testů a repair trajektorie lze identifikovat tyto kategorie:

| Kategorie | Příklady | Typický level | Příčina |
|-----------|---------|---------------|---------|
| Stock-related | test_create_order_success, test_update_stock_negative | L0 | Chybí api_knowledge o stock default=0 |
| Status code mismatch | test_get_author_nonexistent, test_delete_shipped_order | L0 | Model assertuje 422 místo 404 |
| Neexistující endpoint | test_login_invalid_credentials, test_search_query_too_short | L1 | Model halucinuje endpointy z dokumentace |
| Sémantické nepochopení | test_apply_discount_new_book, test_list_tags_empty | L2/L4 | Model špatně chápe business pravidlo |
| Helper cascade | test_get_order_detail (závisí na create_order) | L0 | Selhání v create kaskáduje do GET |

---

## 4. Detailní rozbor selhání — Gemini per Level

### 4.1 Gemini — L0

**Pattern across 3 runů:**
- Run 1: 39/50 (78.0%) — 22 failing v iter 1, helper_fallback → isolated → 11 never-fixed
- Run 2: 48/50 (96.0%) — jen 5 failing v iter 1, 3 opraveny, 2 stale
- Run 3: 41/50 (82.0%) — 17 failing v iter 1, helper_fallback → isolated → 9 never-fixed

**Proč Run 2 je výrazně lepší:** Model vygeneroval domain-specific helpery (create_author, create_category, create_book se stock=10, published_year=2020) přímo v první generaci. Run 1 a 3 vygenerovaly generic wrapper helpery (api_get/api_post) — testy dělají setup inline a opakují stejné chyby.

**Konzistentně failing (2+ runy):**

| Test pattern | Runy | Root cause | Proč neopravitelné |
|-------------|------|------------|-------------------|
| test_update_stock_negative | 1,2,3 | Stock quantity je delta ne absolutní — model assertuje špatnou výslednou hodnotu | Repair vidí chybu ale nechápe sémantiku delta operace bez api_knowledge |
| test_create_order_* | 1,3 | Stock default=0 → insufficient stock | Bez api_knowledge model neví že musí nastavit stock > 0 |
| test_delete_*_order_* | 1,3 | Kaskáda z create_order selhání | Order se nevytvořil → delete na neexistující order |
| test_get_order_detail | 1,3 | Kaskáda z create_order | Stejný root cause |

**Sporadicky failing (1 run):**

| Test | Run | Příčina |
|------|-----|---------|
| test_login_rate_limit_exceeded | 1 | Endpoint POST /auth/login neexistuje v API — model halucinoval z obecných znalostí |
| test_get_book_not_found | 3 | Assertuje 404 ale OpenAPI spec definuje jen 422 — model správně odvodil HTTP konvenci ale repair to "opravil" zpět na 422 |

### 4.2 Gemini — L1

**Pattern across 3 runů:**
- Run 1: 48/50 (96.0%) — 3 failing, 1 opraven, 2 stale (test_get_rating_empty, test_remove_tag_nonexistent_ignored)
- Run 2: 50/50 (100.0%) — **perfektní na první pokus**
- Run 3: 45/50 (90.0%) — 5 failing, všechny stale (halucinované endpointy)

**Run 2 je perfektní** protože model s dokumentací vygeneroval přesně správné helpery a nehalucinoval žádné neexistující endpointy.

**Run 3 selhává kvůli halucinacím:** Model vytvořil testy pro POST /auth/login, GET /books/search, PATCH /books/{book_id} (partial update), POST /orders/{order_id}/items — endpointy zmíněné nebo implikované v dokumentaci ale neexistující v OpenAPI spec. Tyto testy selhávají na 404/405 a jsou principiálně neopravitelné → stale.

**Konzistentně failing:**

| Test pattern | Runy | Root cause |
|-------------|------|------------|
| test_get_rating_empty | 1 | Model assertuje average_rating == None ale API vrací jiný formát (0 nebo chybí klíč) |
| test_remove_tag_nonexistent_ignored | 1 | Model očekává 200 při odebírání neexistujícího tagu ale API vrací jiný status |

### 4.3 Gemini — L2

**Pattern across 3 runů:**
- Run 1: 48/50 (96.0%) — 2 stale (test_transition_delivered_to_shipped, test_list_orders_no_results)
- Run 2: 49/49 (100.0%) — **perfektní** (plán měl jen 49 testů kvůli JSON parse error)
- Run 3: 46/50 (92.0%) — 4 stale (test_apply_discount_new_book_fails, test_patch_book_price_success, test_delete_book_removes_it_from_list, test_update_author_details_success)

**Run 2 je perfektní** — model se zdrojovým kódem vygeneroval korektní testy na první pokus. Ale plán měl jen 49 testů kvůli opakovanému JSON parse error při doplňování.

**Typické stale testy na L2:**
- test_transition_delivered_to_shipped: Model vidí status transition logiku ve zdrojovém kódu ale špatně chápe validní přechody (delivered→shipped není validní)
- test_apply_discount_new_book_fails: Model testuje discount na novou knihu (published_year=aktuální rok) ale buď špatně konstruuje "novou" knihu nebo assertuje špatný status kód
- test_patch_book_price_success / test_update_author_details_success: Testy z Run 3 fill-in (doplněné LLM) — kvalita nižší než originální generace

### 4.4 Gemini — L3

**Všechny 3 runy: 50/50 (100.0%) na první iteraci.**

L3 je jediný level kde model konzistentně generuje perfektní testy bez jakékoliv opravy. DB schéma poskytuje:
- FK constraints → model ví jaké entity musí existovat před vytvořením závislých
- CHECK constraints → model generuje korektní boundary testy
- NOT NULL / UNIQUE → model ví které validační chyby testovat

**Instruction compliance:** Run 1 má compliance=100 (model přidal timeout=30), Run 2 a 3 mají 80 (chybí timeout). Toto je nedeterministické — model někdy poslouchá framework_rules, někdy ne.

### 4.5 Gemini — L4

**Pattern across 3 runů:**
- Run 1: 49/50 → 50/50 po 1 repair (test_create_book_duplicate_isbn opraven v iter 2)
- Run 2: 48/50 (96.0%) — 2 stale (test_apply_discount_new_book, test_list_tags_empty)
- Run 3: 50/50 (100.0%) — **perfektní na první pokus**

**L4 specifika:**
- **Více helperů:** 5-6 helperů vs 4 na L1-L3. Model s referenčními testy vytváří create_test_tag a create_test_order helpery navíc.
- **Asserty v helperech:** L4 helpery mají `assert r.status_code == 201` — selhání v setupu je viditelné okamžitě. L0-L2 helpery asserty nemají.
- **Compliance:** Run 1 a 3 mají compliance=100 (model kopíruje timeout=30 z referenčních testů). Run 2 má 80 — model z referenčních testů timeout nepřevzal.
- **Naming:** L4 pojmenovává helpery `create_test_*` (kopíruje z referenčních testů) vs L1-L3 `create_*`.

**Stale v Run 2:**
- test_apply_discount_new_book: Model testuje discount pro knihu s published_year=aktuální rok. Api_knowledge říká "pro test discountu na NOVOU knihu vytvoř knihu s published_year aktuálního roku PŘÍMO V TESTU" — ale model to implementuje přes helper kde published_year=2020 → pak přepisuje → sémantická chyba.
- test_list_tags_empty: Test s 7 assertama (přespříliš složitý) — model vytváří komplexní multi-step test který selhává na jednom z kroků.

---

## 5. Diagnostiky — cross-cutting analýzy

### 5.1 Context size a prompt budget

| Level | Tokeny (est) | Sekce | Budget (% okna 128k) |
|-------|-------------|-------|----------------------|
| L0 | 20,737 | 1 (OpenAPI) | 20.1% |
| L1 | 22,538 | 2 (+docs: +1,788) | 21.5% |
| L2 | 34,023 | 3 (+source: +11,474) | 30.3% |
| L3 | 34,961 | 4 (+schema: +929) | 31.1% |
| L4 | 40,734 | 5 (+tests: +5,759) | 35.8% |

**Otázka oponenta:** "Nepřetížili jste model kontextem?"

**Odpověď:** Maximální prompt budget je 35.8% (L4). Model má vždy >82k tokenů volných pro generování kódu (~400 řádků Python). Kontext nepřetěžuje model — L4 má nejlepší compliance a druhý nejlepší validity přesto že má největší kontext. Navíc L2→L3 přidává jen 929 tokenů ale přináší skok validity z 96% na 100% — důkaz že kvalita kontextu je důležitější než kvantita.

### 5.2 Helper snapshot — strukturální rozdíly

| Level | Helperů (avg) | create_book stock | published_year default | Asserty v helperu | Strategie |
|-------|--------------|-------------------|----------------------|-------------------|-----------|
| L0 | 4-7 | Variabilní (Run 2 ano, Run 1+3 ne) | Variabilní | Ne | Buď domain helpers nebo generic wrappers |
| L1 | 4 | ✅ stock=10 | 2020 | Ne | Konzistentní domain helpers |
| L2 | 4 | ✅ stock=10 | 2020 | Ne | Stejné jako L1 |
| L3 | 4 | ✅ stock=10 | 2020 | Občas (Run 3) | Lépe parametrizované (name=None) |
| L4 | **5-6** | ✅ stock=10 | 2020 | **Ano** | +create_test_tag, +create_test_order, asserty |

**Otázka oponenta:** "Proč L0 testy selhávají víc?"

**Odpověď:** L0 nemá stabilní helper architekturu. Ve 2 ze 3 runů vygeneroval generic HTTP wrapper helpery (api_get/api_post) místo domain-specific helperů. Bez create_book helperu s stock=10 selhávají všechny testy vyžadující knihu s dostatečným skladem (orders, stock update, reviews na konkrétní knihu). L1+ api_knowledge explicitně říká "create_book MUSÍ nastavit stock:10" → model to konzistentně implementuje.

### 5.3 Instruction compliance

| Level | Missing timeout (avg) | Compliance score (avg) |
|-------|----------------------|------------------------|
| L0 | 61.3/61.3 (100%) | 80 |
| L1 | 70.3/70.3 (100%) | 80 |
| L2 | 71.0/71.0 (100%) | 80 |
| L3 | 47.7/71.3 (67%) | **87** |
| L4 | 20.7/63.0 (33%) | **93** |

**Finding — in-context learning efekt na compliance:**

L0-L2 ignorují framework_rule "Timeout=30 na každém HTTP volání" na 100% callů. Model čte pravidlo ale neimplementuje ho.

L3 Run 1 má compliance=100 (timeout na všech callech) ale Run 2+3 ne — nedeterministické.

L4 Run 1+3 mají compliance=100 — model kopíruje `timeout=30` z referenčních testů (in-context learning). Run 2 paradoxně ne.

**Implikace:** Referenční testy (L4) jsou výrazně efektivnější nástroj pro vynucení coding standards než textové instrukce (framework_rules). Toto je měřitelný in-context learning efekt — model lépe dodržuje pravidla když vidí příklady než když čte instrukce.

### 5.4 Status code halucinace

| Level | Kódy v OpenAPI spec | Halucinované v kódu | Korektní? |
|-------|-------------------|--------------------|-----------| 
| L0 | 200, 201, 204, 422 | **404**, 400, 429 | 404 ✅ (HTTP konvence), 400 ✅ (generic error), 429 ❌ (rate limit neexistuje) |
| L1 | +400, 404, 409 | 401 (Run 3) | ❌ (API nemá autentizaci) |
| L2 | +400, 404, 409 | žádné | — |
| L3 | +400, 404, 409 | žádné | — |
| L4 | +400, 404, 409 | žádné | — |

**Otázka oponenta:** "Halucinuje model status kódy?"

**Odpověď:** L0 halucinuje 404 — ale je to **korektní halucinace**. OpenAPI spec definuje jen 422 pro chyby, ale API skutečně vrací 404 pro not-found. Model odvodil správné HTTP konvence z obecných znalostí. Naopak 429 (rate limit) je nekorektní — API nemá rate limiting, model vytvořil test_login_rate_limit_exceeded na neexistující funkcionalitu.

L1 halucinuje 401 (Unauthorized) v Run 3 kvůli testům na POST /auth/login — endpoint neexistuje, model ho halucinoval z dokumentace.

L2+ nehalucinuje — zdrojový kód a DB schéma poskytují přesné informace o validaci.

### 5.5 Test type distribution

| Level | Happy % | Error % | Edge % | Error-focused endpoints |
|-------|---------|---------|--------|------------------------|
| L0 | **69%** | 24% | 7% | 12 avg |
| L1 | 44% | **46%** | 5% | 18 avg |
| L2 | 50% | **46%** | 4% | 18 avg |
| L3 | 55% | **44%** | 1% | 16 avg |
| L4 | 44% | **43%** | **13%** | 20 avg |

**Trend:** L0 generuje 69% happy path — bez kontextu model neví jaké error scénáře testovat. L1+ dramaticky zvyšuje error testy (44-46%) protože dokumentace popisuje business rules (stock insufficient, duplicate ISBN, invalid status transition). L4 má nejvíce edge case testů (13%) — referenční testy inspirují k boundary testing.

### 5.6 Plan-code drift

| Level | Drift count (avg) | Nejčastější pattern |
|-------|-------------------|---------------------|
| L0 | 2.0 | Plán 422 → kód 404 (not-found konvence) |
| L1 | 2.0 | Plán 204 → kód bez status assert (side-effect tests) |
| L2 | 2.0 | Plán 400 → kód 422 (Pydantic validace) |
| L3 | 2.3 | Plán 201 → kód bez status assert; plán 400 → kód 422 |
| L4 | 4.0 | Plán 201 → kód bez assert; plán 204 → kód bez assert |

**Opakující se pattern:** Plán říká 400 (business rule), kód assertuje 422 (Pydantic validace). Model při generování kódu přehodnocuje plánovaný status kód — ví že FastAPI automaticky vrací 422 pro invalid input, ne 400.

L4 má nejvyšší drift (4.0) protože referenční testy inspirují model k side-effect testům kde se status kód neassertuje přímo (ověřuje se výsledek operace přes GET).

### 5.7 Code patterns — komplexita testů

| Level | Avg HTTP calls | Avg helper calls | Avg total | Side-effect % | Chaining % |
|-------|---------------|-----------------|-----------|---------------|------------|
| L0 | **1.15** | 1.05 | 2.21 | **5.3%** | 25.3% |
| L1 | 1.35 | **2.01** | 3.36 | 7.3% | 14.7% |
| L2 | 1.37 | 2.05 | 3.42 | 7.4% | 24.0% |
| L3 | 1.37 | 2.11 | 3.48 | 4.7% | 21.3% |
| L4 | 1.17 | **2.44** | 3.61 | 5.3% | **33.3%** |

**L0 má nejméně helper callů (1.05)** — bez kontextu model méně často používá helpery a dělá víc setup inline. To vede k delším testům a větší duplicitě kódu.

**L4 má nejvíce helper callů (2.44) a chaining (33.3%)** — referenční testy ukazují pattern `data = r.json()["field"]` → model to kopíruje. Více chaining = testy ověřují response body, ne jen status kódy.

### 5.8 Repair trajectory

| Level | Avg convergence iter | Avg never-fixed | Total repairs | Total stale | Repair úspěšnost |
|-------|---------------------|-----------------|---------------|-------------|------------------|
| L0 | 2.0 | 6.7 | 38.0 | 0.7 | **Částečná** — opraví ~50% ale zbytek neopravitelný |
| L1 | 2.3 | 2.3 | 7.3 | 2.3 | Nízká — stale od počátku |
| L2 | 2.0 | 2.0 | 6.0 | 2.0 | Nízká — stale od počátku |
| L3 | — | 0 | 0 | 0 | **Nepotřebuje repair** |
| L4 | 2.5 | 0.7 | 2.3 | 0.7 | **Dobrá** — 1 test opraven v Run 1 |

**Otázka oponenta:** "Funguje váš repair loop?"

**Odpověď:** Repair loop je efektivní hlavně pro L0 kde opravuje ~50% failing testů (22→11 v Run 1, 17→9 v Run 3). Klíčový je helper_fallback → isolated repair pattern: první iterace zkusí opravit helpery (pokud >10 failing), druhá přepne na izolovaný repair prvních 10 testů. Pro L1-L2 repair loop je méně efektivní — failing testy jsou typicky sémantické chyby (špatné chápání business pravidla) které izolovaný repair neopraví.

L3 repair loop nikdy nepotřebuje — model generuje perfektní testy na první pokus.

**Improvement oproti v5:** Helper repair fallback + isolated repair přepínání funguje správně. V předchozí verzi se helper repair opakoval donekonečna bez efektu. Nyní: helper → selhání → isolated → stale detection.

---

## 6. Bugy a limitace

### 6.1 failure_taxonomy: 100% unknown_no_error_captured

Všechny failing testy mají `category: "unknown_no_error_captured"` a `error_summary: ""`. Funkce `_extract_error_block()` v phase6 nenachází chybové bloky v pytest logu. Buď:
- pytest `--tb=short` generuje jiný formát než regex očekává
- RepairTracker sbírá failure_details z iterace kde pytest log ještě nebyl zpracován

**Dopad:** Sekce failure_taxonomy v JSON je nepoužitelná. Manuální analýza z názvů testů a repair trajectorie (viz sekce 4).

**Fix potřebný:** Otestovat `_extract_error_block()` na skutečném pytest logu z tohoto běhu.

### 6.2 Plan count: L2 Run 2 má jen 49 testů

Plánování selhalo 2× na JSON parse error, třetí pokus vygeneroval jen 49 testů. Framework nevynutil 50. `phase2_planning.py` má MAX_ATTEMPTS=4 ale po 4 pokusech akceptuje <50 testů.

**Dopad:** Minimální — 49 vs 50 testů neovlivňuje závěry. Ale pro fair srovnání by všechny runy měly mít stejný počet.

### 6.3 Instruction compliance: timeout nedeterministický

L3 Run 1 má compliance=100, Run 2+3 mají 80. L4 Run 1+3 mají 100, Run 2 má 80. Model nedeterministicky dodržuje/ignoruje timeout pravidlo. Toto komplikuje tvrzení "L4 zlepšuje compliance" — efekt existuje ale není 100%.

---

## 7. Appendix — surová data per run

### Gemini 3.1 Flash Lite

<details>
<summary>L0 — Run 1 (78.0%)</summary>

```
Validity: 78.0% (39/50)
EP Coverage: 97.06% (33/34)
Assert Depth: 1.76
Stale: 0
Iterations: 5
Helpers: 7 (generic wrappers: api_get, api_post, api_put, api_delete, create_resource, delete_resource + unique)
Repair: iter1=22F→helper_fallback, iter2=22F→isolated(10), iter3=14F→helper_fallback, iter4=14F→isolated(10), iter5=11F
Never-fixed: test_get_book_rating_success, test_update_stock_negative, test_remove_tags_from_book_success,
  test_create_order_success, test_get_order_detail, test_delete_pending_order, test_delete_confirmed_order_fail,
  test_update_status_success, test_update_status_invalid, test_update_status_logic_flow, test_login_rate_limit_exceeded
Fixed: test_add_tags_to_book_success, test_apply_discount_success, test_apply_discount_too_high,
  test_create_review_out_of_range, test_create_review_success, test_delete_author_success,
  test_delete_book_success, test_get_author_non_existent, test_list_reviews_success,
  test_update_book_success, test_update_stock_increase
```
</details>

<details>
<summary>L0 — Run 2 (96.0%)</summary>

```
Validity: 96.0% (48/50)
EP Coverage: 94.12% (32/34)
Assert Depth: 1.50
Stale: 2 (test_update_stock_negative, test_delete_delivered_order_error)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book with stock=10)
Repair: iter1=5F→isolated(5), iter2=2F→isolated(2), iter3=2F→isolated→stale, iter4=stale_skip, iter5=stale
Fixed: test_get_author_nonexistent, test_delete_author_success, test_get_order_not_found
```
</details>

<details>
<summary>L0 — Run 3 (82.0%)</summary>

```
Validity: 82.0% (41/50)
EP Coverage: 88.24% (30/34)
Assert Depth: 1.78
Stale: 0
Iterations: 5
Helpers: 6 (generic wrappers: api_get, api_post, api_put, api_delete, handle_response + unique)
Repair: iter1=17F→helper_fallback, iter2=17F→isolated(10), iter3=12F→helper_fallback, iter4=12F→isolated(10), iter5=9F
Never-fixed: test_get_book_not_found, test_update_book_invalid_isbn, test_update_stock_negative,
  test_add_tags_to_book_success, test_create_order_success, test_create_order_invalid_email,
  test_get_order_detail_success, test_get_order_not_found, test_delete_pending_order
Fixed: test_delete_author_success, test_update_book_price, test_delete_book_success,
  test_create_review_success, test_create_review_invalid_rating, test_apply_discount_success,
  test_apply_discount_over_limit, test_update_stock_success
```
</details>

<details>
<summary>L1 — Run 1 (96.0%)</summary>

```
Validity: 96.0% (48/50)
EP Coverage: 58.82% (20/34)
Stale: 2 (test_get_rating_empty, test_remove_tag_nonexistent_ignored)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10)
Fixed: test_create_book_missing_author
```
</details>

<details>
<summary>L1 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 82.35% (28/34)
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 published_year=2020)
```
</details>

<details>
<summary>L1 — Run 3 (90.0%)</summary>

```
Validity: 90.0% (45/50)
EP Coverage: 82.35% (28/34)
Stale: 5 (test_login_invalid_credentials, test_login_empty_body, test_search_query_too_short,
  test_partial_update_invalid_field, test_update_book_price_persistence)
Iterations: 5
Empty tests: 4 (test_order_status_transition_valid, test_delete_shipped_order_fails,
  test_get_order_details_success, test_add_item_to_locked_order)
Hallucinated endpoints: POST /auth/login, GET /books/search, PATCH /books/{book_id}, POST /orders/{order_id}/items
Status code hallucinated: 401
```
</details>

<details>
<summary>L2 — Run 1 (96.0%)</summary>

```
Validity: 96.0% (48/50)
EP Coverage: 79.41% (27/34)
Stale: 2 (test_transition_delivered_to_shipped, test_list_orders_no_results)
Iterations: 5
```
</details>

<details>
<summary>L2 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (49/49) — plán měl jen 49 testů kvůli JSON parse error
EP Coverage: 79.41% (27/34)
Iterations: 1
```
</details>

<details>
<summary>L2 — Run 3 (92.0%)</summary>

```
Validity: 92.0% (46/50)
EP Coverage: 79.41% (27/34)
Stale: 4 (test_apply_discount_new_book_fails, test_patch_book_price_success,
  test_delete_book_removes_it_from_list, test_update_author_details_success)
Iterations: 5
Plan adherence: 90% (5 testů jen v plánu, 5 jen v kódu — fill-in nahradil plánované)
```
</details>

<details>
<summary>L3 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 94.12% (32/34)
Iterations: 1
Compliance: 100 (timeout na všech callech)
```
</details>

<details>
<summary>L3 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 67.65% (23/34) — nejnižší EP cov ze všech runů
Iterations: 1
Compliance: 80
Domain focus: books 24/50 testů (48%)
```
</details>

<details>
<summary>L3 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 82.35% (28/34)
Iterations: 1
Compliance: 80
Helpers: create_author(name=None), create_category(name=None) — lépe parametrizované
Helper asserty: Ano (create_book, create_author, create_category)
```
</details>

<details>
<summary>L4 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 88.24% (30/34)
Iterations: 2 (1 test opraven)
Compliance: 100
Helpers: 5 (unique, create_test_author, create_test_category, create_test_book, create_test_tag)
Fixed: test_create_book_duplicate_isbn
```
</details>

<details>
<summary>L4 — Run 2 (96.0%)</summary>

```
Validity: 96.0% (48/50)
EP Coverage: 82.35% (28/34)
Stale: 2 (test_apply_discount_new_book, test_list_tags_empty)
Iterations: 5
Compliance: 80
Helpers: 6 (+create_test_order)
```
</details>

<details>
<summary>L4 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (50/50)
EP Coverage: 94.12% (32/34)
Iterations: 1
Compliance: 100
Helpers: 5 (unique, create_test_author, create_test_category, create_test_book, create_test_tag)
```
</details>