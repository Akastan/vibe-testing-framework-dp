# 🔬 Analýza chování modelu Mistral Large 2512 - Experiment v12

> **Vibe Testing Framework** · Automatické generování API testů s progresivním kontextem  
> Zpracováno: 25 běhů (5 úrovní × 5 běhů), API: Bookstore (50 endpointů)  
> Datum analýzy: 15. 4. 2026

---

## 1. Konfigurace a přehled experimentu

### 1.1 Konfigurace

| Parametr | Hodnota |
|---|---|
| **LLM model** | `mistral-large-2512` |
| **Testovaná API** | Bookstore (50 endpointů) |
| **Teplota** | 0.4 |
| **Plánovaný počet testů** | 30 na běh |
| **Maximální iterace oprav** | 3 |
| **Počet běhů na úroveň** | 5 (L0–L3), 5 (L4), celkem 25 |
| **Komprese kontextu** | Ano (především OpenAPI spec: ~48% úspora) |
| **Celkové náklady experimentu** | **$1.1221** |

### 1.2 Přehled úrovní kontextu

| Úroveň | Sekce kontextu | Est. tokenů | Prompt budget |
|---|---|---|---|
| **L0** | OpenAPI specifikace | 15 958 | ~15% |
| **L1** | + Technická/byznys dokumentace | 23 783 | ~21% |
| **L2** | + Zdrojový kód endpointů | 43 917 | ~37% |
| **L3** | + Databázové schéma | 44 770 | ~38% |
| **L4** | + Existující testy (ukázka stylu) | 53 438 | ~42% |

### 1.3 Celkové shrnutí modelu

Mistral Large 2512 je v kontextu Vibe Testing Frameworku **konzervativní, ale spolehlivý generátor testů**. Vykazuje paradoxní chování: jeho nejspolehlivější výkon (z hlediska validity) podává na úrovních s nejmenším a středním kontextem (L0–L1), zatímco přidání hlubšího kontextu (L2–L4) přináší ambicioznější, ale **méně stabilní testy**. Klíčovým zjištěním je, že model má **nulovou schopnost self-correction** - ani v jediném ze 25 běhů nedokázal opravit test, který selhal v první iteraci (výjimkou je jediný opravený test v L4 run4). Endpoint coverage zůstává stabilně nízký (24–36%) a silně soustředěný na domény `authors` a `books`, přičemž celé oblasti API (orders, exports, tags, admin) jsou systematicky ignorovány.

---

## 2. Co se v datech děje - Analýza hlavních metrik

### 2.1 Validity Rate

| Úroveň | Průměr | Min | Max | Trend |
|---|---|---|---|---|
| **L0** | **96.7%** | 90.0% | 100.0% | ⬆ Vysoká, ale ne perfektní |
| **L1** | **99.3%** | 96.7% | 100.0% | ⬆ **Nejlepší úroveň** |
| **L2** | **92.7%** | 86.7% | 96.7% | ⬇ Pokles |
| **L3** | **90.0%** | 83.3% | 96.7% | ⬇ **Nejhorší úroveň** |
| **L4** | **92.0%** | 86.7% | 96.7% | ↔ Mírné zlepšení oproti L3 |

**Klíčové zjištění:** Existuje jasný vzorec **obrácené U-křivky** - validity stoupá z L0 na L1 (peak), pak klesá přes L2 a L3, a mírně se zotavuje na L4. 

**L1 je „sweet spot":** Technická dokumentace dodává modelu dostatečné vodítko, aniž by jej zahlcovala. V L1 měly 4 z 5 běhů 100% validity, přičemž jediný failure byl triviální assertion mismatch (`test_get_nonexistent_author`).

**L2–L3 přinášejí ambicióznější, ale riskantnější testy:** Model se pokouší testovat složitější scénáře (soft-delete, discount, rate limiting), které ale neumí správně implementovat.

### 2.2 Endpoint Coverage

| Úroveň | Průměr | Min | Max |
|---|---|---|---|
| **L0** | **28.0%** | 28.0% | 28.0% |
| **L1** | **27.6%** | 26.0% | 28.0% |
| **L2** | **26.8%** | 24.0% | 30.0% |
| **L3** | **25.2%** | 24.0% | 26.0% |
| **L4** | **30.8%** | 26.0% | 36.0% |

**Klíčová zjištění:**

- **L0 je rigidně konzistentní:** Všech 5 běhů pokrývá přesně 28% (14/50) endpointů - model s holou OpenAPI spec vždy vybírá identickou podmnožinu.
- **L1–L3 paradoxně snižují pokrytí:** Přidání kontextu vede model ke koncentraci na menší, ale „zajímavější" sadu endpointů.
- **L4 je nejlepší v EP coverage:** Ukázkové testy fungují jako „roadmap" a model pokrývá až 36% (18/50). Běh L4 run2 je **globální maximum** celého experimentu.
- Přesto zůstává **30+ endpointů (60%+) trvale nepokrytých** na všech úrovních.

**Systematicky ignorované oblasti API:**

Přes všech 25 běhů nikdy nebyly pokryty: `DELETE /orders/{order_id}`, `GET /exports/{job_id}`, `POST /exports/books`, `POST /exports/orders`, `GET /orders/{order_id}/invoice`, `POST /orders/{order_id}/items`, `GET /statistics/summary`, `POST /admin/maintenance`, `GET /admin/maintenance`. Model zcela ignoruje moduly: **orders (CRUD)**, **exports**, **admin/maintenance** a **statistics**.

### 2.3 Staleness a opravný cyklus

| Úroveň | Průměr stale | Celkem stale | Self-correction rate | Vždy 1. iterace? |
|---|---|---|---|---|
| **L0** | 1.0 | 5 | **0.0%** | 3/5 běhů |
| **L1** | 0.2 | 1 | **0.0%** | 4/5 běhů |
| **L2** | 2.2 | 11 | **0.0%** | 0/5 běhů |
| **L3** | 3.0 | 15 | **0.0%** | 0/5 běhů |
| **L4** | 2.4 | 12 | **4.0%** (1 fix) | 0/5 běhů |

**Toto je nejkritičtější zjištění celého experimentu:**

Mistral Large 2512 má **de facto nulovou schopnost self-correction.** Opravný cyklus (3 iterace: isolated -> helper_fallback -> all_stale_early_stop) nikdy nevede k úspěšné opravě testu - s jedinou výjimkou: v L4 run4 byl opraven `test_create_author_valid_data` (1 z 5 selhání, tedy 20% self-correction v tomto konkrétním běhu). Across the board je self-correction rate **0.0%** ve 24 z 25 běhů.

To znamená, že **každá iterace opravy po první je čistá ztráta** - spotřebuje tokeny, ale nepřinese žádné zlepšení. Testy, které selžou poprvé, se stávají „stale" a jsou přeskočeny.

**Recidivující selhání** (testy, které selhávají opakovaně):

| Test | Počet selhání (z 25) | Příčina                                                                              |
|---|---|--------------------------------------------------------------------------------------|
| `test_restore_soft_deleted_book` | **9×** | `assert data["is_deleted"] is False` - model nerozumí mechanismu soft-delete/restore |
| `test_apply_discount_exceeding_rate_limit` | **5×** | `assert status == 200` - špatná předpověď status kódu                                |
| `test_apply_discount_to_eligible_book` | **3×** | `assert discounted_price == price * 0.9` - špatná aritmetika/logika slevy            |
| `test_apply_discount_rate_limit_exceeded` | **3×** | Stejný problém jako výše, jen jiný název v L4                                        |
| `test_delete_author_with_associated_books` | **2×** | `assert status == 409` - model očekává 409 Conflict                                  |
| `test_create_author_duplicate_name` | **2×** | `assert status == 409` - duplikace v L3                                              |

### 2.4 Token usage, komprese a cena

| Úroveň | Prům. cena | Prům. prompt tokenů | Prům. completion tokenů | Celk. tokenů | Komprese |
|---|---|---|---|---|---|
| **L0** | **$0.0231** | ~26 252 | ~6 631 | ~32 883 | 48.1% |
| **L1** | **$0.0322** | ~41 258 | ~7 826 | ~49 084 | 38.8% |
| **L2** | **$0.0514** | ~77 570 | ~8 387 | ~85 957 | 26.2% |
| **L3** | **$0.0521** | ~79 119 | ~8 347 | ~87 466 | 25.8% |
| **L4** | **$0.0657** | ~105 303 | ~8 707 | ~114 010 | 22.6% |

**Cenová analýza:**

- **L0 -> L1:** +39% cena za marginální zlepšení validity (+2.6pp), ale kvalitativně lepší testy.
- **L1 -> L2:** +60% cena za **pokles validity (-6.6pp)** - nejhorší ROI v experimentu.
- **L2 -> L3:** +1.4% cena za pokles validity (-2.7pp) - databázové schéma téměř nezlepšuje nic.
- **L3 -> L4:** +26% cena za zlepšení EP coverage (+5.6pp), ale stagnující validity.

**Token efficiency (passed × assertion_depth / cost):**

| Úroveň | Prům. efektivita |
|---|---|
| **L0** | 2 484 |
| **L1** | 2 386 |
| **L2** | 1 638 |
| **L3** | 1 702 |
| **L4** | 1 260 |

Efektivita monotónně klesá. L0 produkuje nejvíce „hodnoty na dolar," i když L1 generuje kvalitativně lepší testy (vyšší assertion depth, validace odpovědí).

**Komprese kontextu:** OpenAPI specifikace se komprimuje o ~48%, ale kód endpointů (L2+) jen o ~2.3% a databázové schéma prakticky vůbec (0.1%). To znamená, že od L2 výš platíme za téměř nekomprimovaný zdrojový kód.

---

## 3. Detailní rozbor Code Coverage

### 3.1 Souborové pokrytí - souhrnný přehled

| Soubor | L0 | L1 | L2 | L3 | L4 | Charakter |
|---|---|---|---|---|---|---|
| `app/__init__.py` | 100% | 100% | 100% | 100% | 100% | Trivální (prázdný init) |
| `app/database.py` | 100% | 100% | 100% | 100% | 100% | Automaticky pokryt testem |
| `app/models.py` | 100% | 100% | 100% | 100% | 100% | Pokryt importem |
| `app/schemas.py` | 100% | 100% | 100% | 100% | 100% | Pokryt validací |
| **`app/main.py`** | **69.7%** | **67.8%** | **70.2%** | **69.6%** | **68.9%** | **Stabilní, ale nekompletní** |
| **`app/crud.py`** | **36.6%** | **37.2%** | **39.2%** | **37.1%** | **39.6%** | **Nejslabší článek** |
| **Celkový průměr** | **66.9%** | **66.5%** | **68.0%** | **67.1%** | **67.8%** | **Stagnace ±1.5pp** |

### 3.2 Analýza `app/crud.py` - kritický soubor

`crud.py` je srdce aplikace - obsahuje veškerou business logiku (CRUD operace, slevy, objednávky, exporty). Přesto je pokryt jen z **36–40%** napříč všemi úrovněmi.

**Proč tak nízké pokrytí?**

1. **Model testuje jen authors a books CRUD:** Funkce jako `create_author`, `get_author`, `create_book`, `get_book`, `update_book`, `delete_book` jsou pokryty dobře.
2. **Kompletně nepokryté funkce v crud.py (odhad na základě EP coverage):**
   - `get_authors` (list s filtrací a paginací) - model ji občas zasáhne, ale nekonzistentně
   - `create_order`, `get_orders`, `get_order`, `delete_order` - celý modul objednávek
   - `export_books`, `export_orders`, `get_export_job` - exporty
   - `get_statistics_summary` - statistiky
   - `apply_discount` - model se pokouší (a selhává), pokrytí je nestabilní
   - `restore_book` - soft-delete/restore logika, opakovaný failure
   - `clone_book` - klonování knihy
   - `bulk_create_books` - hromadné vytváření
   - `manage_tags` - správa tagů
   - `manage_categories` - správa kategorií (občas pokryto)

3. **Funkce se 100% pokrytím (stabilně přes všechny úrovně):**
   - `create_author`, `get_author` (by ID)
   - `create_book`, `get_book` (by ID)
   - `update_author`, `delete_author`
   - `reset_database` (kde je volán)

### 3.3 Analýza `app/main.py` - routovací vrstva

`main.py` (~70% coverage) definuje FastAPI routy. Nepokryté ~30% odpovídá endpointům, které model nikdy nevolá - orders, exports, admin, statistics, bulk operations, tag/category management.

**Zajímavé pozorování:** Pokrytí `main.py` je na L2 mírně vyšší (70.2%) díky tomu, že model vidí zdrojový kód a snaží se testovat více endpointů. Na L3 ale klesne zpět (69.6%) - přidání DB schématu model spíše „rozptyluje."

### 3.4 Variabilita coverage v rámci úrovní

| Úroveň | Min celk. | Max celk. | Spread | Nejlepší běh |
|---|---|---|---|---|
| **L0** | 66.70% | 67.10% | **0.40pp** | run1 |
| **L1** | 65.81% | 67.79% | **1.98pp** | run2 |
| **L2** | 66.70% | 70.96% | **4.26pp** | run1 ⭐ |
| **L3** | 66.11% | 68.09% | **1.98pp** | run1 |
| **L4** | 66.01% | 68.78% | **2.77pp** | run1 |

**L2 run1 je globální maximum code coverage (70.96%)** - v tomto běhu model dosáhl 44.70% na `crud.py` a 73.13% na `main.py`. Jde o outlier způsobený tím, že model v tomto konkrétním plánu zacílil na 15 unikátních endpointů (nejvíce z L2) a zasáhl i méně časté oblasti.

**L0 je nejstabilnější** (spread 0.40pp) - bez doplňkového kontextu model vždy generuje téměř identický plán.

---

## 4. Proč se to děje - Kauzalita a obhajoba dat

### 4.1 Proč L1 překonává L0 v kvalitě (ne jen validitě)?

**Assertion depth:** L0 = 1.96, L1 = **2.57** (+31%). Technická dokumentace dává modelu informace o byznys pravidlech (validace, chybové stavy, formáty odpovědí), což vede k sofistikovanějším asercím.

**Response validation:** L0 = 44.7%, L1 = **70.0%** (+56%). Model v L1 mnohem častěji kontroluje tělo odpovědi, ne jen status kód.

**Compliance score:** L1 má 2 běhy se score 100 (vs. 0 v L0) - model lépe dodržuje instrukce (timeout u HTTP calls).

**Rozšíření domén:** L1 přidává `categories` a `tags` do test plánu (v L0 jen `authors`, `books` a `other`), ačkoliv EP coverage se paradoxně nemění.

### 4.2 Proč L2–L3 zhoršují validity?

Model vidí zdrojový kód endpointů a pokouší se testovat **implementační detaily**, které ale neumí správně předpovědět:

1. **Soft-delete/restore mechanismus:** Model v L2+ opakovaně generuje `test_restore_soft_deleted_book`, kde předpokládá, že `is_deleted` se změní na `False` po restore callu. Ale skutečná implementace se zjevně chová jinak (9 selhání z 25).

2. **Discount logika:** Model generuje testy na `apply_discount` s předpoklady o rate limitech a cenové kalkulaci, které neodpovídají skutečné implementaci (celkem 11 selhání v discount-related testech).

3. **Conflict handling (409):** V L3 model vidí databázové schéma a pokouší se testovat unique constraints (`duplicate_name`, `delete_with_associated_books`), ale API nevrací 409 - pravděpodobně vrací jiný kód (422 nebo 400).

**Mechanismus selhání:** Model „vidí" v kódu vzorce, které ho svádějí k předpokladům o chování API. Bez zdrojového kódu (L0–L1) generuje konzervativnější testy, které projdou. Se zdrojovým kódem (L2+) se snaží být chytřejší, ale jeho **inferenční schopnosti nestačí** na odvození přesného chování ze surového kódu.

### 4.3 Proč L3 přidává téměř nulovou hodnotu?

Databázové schéma zabírá jen ~2 533 znaků (853 tokenů) - marginální nárůst kontextu. Ale:

- **Validity klesá** (L2: 92.7% -> L3: 90.0%)
- **EP coverage klesá** (L2: 26.8% -> L3: 25.2%)
- **Stale count roste** (L2: 2.2 -> L3: 3.0)
- **Cena je téměř stejná** ($0.0514 vs $0.0521)

DB schéma přidává informace o unique constraints a foreign keys, což model svádí ke generování constraint-based testů (`duplicate_name`, `delete_with_books`), které ale selhávají kvůli nesprávné předpovědi status kódů. **DB schéma je „toxický kontext"** pro tento model.

### 4.4 Proč L4 zlepšuje EP coverage, ale ne validity?

Ukázkové testy (26 000 znaků, 0% komprese) fungují jako **template**:

- Model v L4 generuje **8 helperů** (vs. 4–6 v nižších úrovních), včetně `reset_db` a `setup_book_with_deps`.
- **EP coverage roste na 30.8%** (max 36%) - model „kopíruje" testovací vzory z ukázek.
- L4 run1 volá `POST /reset` (jediný běh v celém experimentu!) - přímo z ukázkových testů.
- Ale validity zůstává na 92% kvůli přetrvávajícím problémům s restore a discount testy.

**L4 run4 - anomálie:** Jako jediný běh z 25 má self-correction rate 20% (opravil `test_create_author_valid_data`). Ale současně má 5 selhání z 30 (83.3% first-shot) a 3 assertion_value_mismatch - model v tomto běhu zjevně „překopíroval" vzory z ukázkových testů špatně (např. assertions na konkrétní stringy `"George Orwell_bio_English novelist"`).

### 4.5 Anomálie a zvláštnosti

1. **L0 run3 vs L0 run1:** Identická konfigurace, ale run3 má 90% validity (3 selhání) vs. run1 se 100%. Příčina: stochastické chování při teplotě 0.4 - model občas generuje ambiciózní testy (`bulk_create`, validace `min_length`), které projdou v jednom běhu a ne v jiném.

2. **L2 run1 - outlier:** Code coverage 70.96% (vs. průměr 68.0%) a EP coverage 30% (vs. průměr 26.8%), ale validity jen 86.67% (nejhorší v L2). Ukazuje trade-off: **širší pokrytí = více šancí na selhání.**

3. **L4 run2 - nejlepší EP coverage experimentu:** 36% (18/50 endpointů), ale přesto jen 96.67% validity. Model v tomto běhu rozšířil plán na 18 unikátních endpointů s nejnižší top3 koncentrací (26.7%).

4. **Nulová schopnost fixu across the board:** Self-correction rate 0.0% ve 24/25 běhů je silný indikátor, že opravný cyklus je u Mistralu neúčinný. Náklady na iterace 2–3 jsou čistá ztráta.

---

## 5. Detailní rozpis jednotlivých úrovní a běhů

<details>
<summary><strong>📊 Úroveň L0 - Pouze OpenAPI specifikace (15 958 tokenů)</strong></summary>

### Charakteristika úrovně

Model s holou OpenAPI specifikací generuje **konzervativní, jednoduché, ale funkční testy**. Vykazuje extrémní konzistenci v plánování (vždy 14 endpointů, vždy stejné domény). Testy mají nízkou assertion depth (1.96) a nízkou response validation (44.7%), ale vysokou validity (96.7%). Compliance je stabilní na 80/100 (chybí timeout u HTTP calls - model bez dokumentace neví o tomto požadavku).

**Rozložení test typů:** ~55% happy_path, ~42% error, ~3% edge_case - model preferuje jednoduché pozitivní a negativní scénáře.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | ✅ 100% | ✅ 100% | ⚠️ 90.0% | ⚠️ 93.3% | ✅ 100% |
| **EP Coverage** | 28.0% | 28.0% | 28.0% | 28.0% | 28.0% |
| **Stale** | 0 | 0 | 3 | 2 | 0 |
| **Iterace** | 1 | 1 | 3 | 3 | 1 |
| **Assertion Depth** | 1.97 | 1.70 | 2.40 | 1.70 | 2.03 |
| **Response Valid.** | 46.7% | 40.0% | 50.0% | 36.7% | 50.0% |
| **Cena** | $0.0207 | $0.0218 | $0.0258 | $0.0259 | $0.0212 |
| **Code Cov.** | 67.10% | 66.90% | 66.70% | 66.70% | 66.90% |
| **crud.py** | 36.95% | 36.69% | 36.43% | 36.43% | 36.69% |
| **main.py** | 70.07% | 69.73% | 69.39% | 69.39% | 69.73% |

**Selhání v L0:**
- Run 3: `test_bulk_create_books_with_valid_data` (wrong status), `test_create_author_with_invalid_name_length` a `test_create_book_with_invalid_isbn_length` (assertion on validation message format)
- Run 4: `test_list_books_with_invalid_price_range_returns_422` (wrong status), `test_upload_unsupported_file_type_returns_415` (file handling error)

</details>

<details>
<summary><strong>📊 Úroveň L1 - + Technická dokumentace (23 783 tokenů)</strong></summary>

### Charakteristika úrovně

**Nejlepší úroveň experimentu z hlediska validity (99.3%).** Přidání technické/byznys dokumentace výrazně zvyšuje kvalitu testů: assertion depth roste na 2.57 (+31%), response validation na 70.0% (+56%). Model začíná testovat `categories` a `tags`. Dva běhy dosahují compliance 100 (správné timeout).

Technická dokumentace zjevně obsahuje informace o chybových stavech a validačních pravidlech, které model efektivně využívá pro generování přesnějších assertions.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | ✅ 100% | ⚠️ 96.7% | ✅ 100% | ✅ 100% | ✅ 100% |
| **EP Coverage** | 28.0% | 26.0% | 28.0% | 28.0% | 28.0% |
| **Stale** | 0 | 1 | 0 | 0 | 0 |
| **Iterace** | 1 | 3 | 1 | 1 | 1 |
| **Assertion Depth** | 2.67 | 3.07 | 2.23 | 2.40 | 2.47 |
| **Response Valid.** | 53.3% | 80.0% | 76.7% | 70.0% | 70.0% |
| **Cena** | $0.0306 | $0.0339 | $0.0356 | $0.0304 | $0.0304 |
| **Code Cov.** | 66.30% | 67.79% | 65.81% | 66.40% | 66.40% |
| **crud.py** | 36.95% | 38.50% | 36.18% | 37.21% | 37.21% |
| **main.py** | 67.35% | 70.41% | 66.67% | 67.35% | 67.35% |

**Selhání v L1:**
- Run 2: `test_get_nonexistent_author` - assertion mismatch na `detail == "Author not found"` (model hádá formát chybové hlášky).

**Zajímavost:** Run 2 má paradoxně nejlepší assertion depth (3.07) a response validation (80%), ale jako jediný selhal - ambicióznější testy nesou vyšší riziko.

</details>

<details>
<summary><strong>📊 Úroveň L2 - + Zdrojový kód endpointů (43 917 tokenů)</strong></summary>

### Charakteristika úrovně

**Přelomová, ale problematická úroveň.** Zdrojový kód endpointů (60 371 znaků po kompresi) zdvojnásobuje kontext oproti L1. Model reaguje generováním sofistikovanějších testů: assertion depth roste na 3.04, response validation na 89.3%. Ale **všech 5 běhů vyžaduje 3 iterace** - model vždy generuje testy, které selhávají.

**Nové testovací scénáře specifické pro L2:** soft-delete/restore, discount logic, rate limiting, author cascade delete - všechny odvozené z viděného zdrojového kódu, všechny problematické.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | ⚠️ 86.7% | ⚠️ 96.7% | ⚠️ 93.3% | ⚠️ 90.0% | ⚠️ 96.7% |
| **EP Coverage** | 30.0% | 26.0% | 28.0% | 26.0% | 24.0% |
| **Stale** | 4 | 1 | 2 | 3 | 1 |
| **Iterace** | 3 | 3 | 3 | 3 | 3 |
| **Assertion Depth** | 3.30 | 3.27 | 2.50 | 2.97 | 3.17 |
| **Response Valid.** | 90.0% | 93.3% | 86.7% | 86.7% | 90.0% |
| **Cena** | $0.0528 | $0.0518 | $0.0504 | $0.0529 | $0.0490 |
| **Code Cov.** | 70.96% | 67.99% | 67.59% | 66.70% | 66.70% |
| **crud.py** | 44.70% | 39.02% | 40.05% | 36.18% | 35.92% |
| **main.py** | 73.13% | 70.41% | 67.69% | 69.73% | 70.07% |

**Opakovaná selhání L2:**
- `test_restore_soft_deleted_book`: **4/5 běhů** (run1, run3, run4, run5)
- `test_delete_author_with_associated_books`: **2/5 běhů** (run1, run2)
- `test_apply_discount_*`: **3/5 běhů** (různé varianty)

**L2 run1 - outlier analýza:** Nejlepší code coverage (70.96%) i EP coverage (30%), ale nejhorší validity (86.7%) s 4 stale testy. Model v tomto běhu zacílil na 15 unikátních endpointů a 12 error-focused testů, což vedlo k širšímu pokrytí, ale i k většímu počtu selhání.

</details>

<details>
<summary><strong>📊 Úroveň L3 - + Databázové schéma (44 770 tokenů)</strong></summary>

### Charakteristika úrovně

**Nejslabší úroveň experimentu.** Databázové schéma přidává pouhých 853 tokenů, ale výsledky se zhoršují na všech frontách: validity klesá na 90.0%, EP coverage na 25.2%, stale count roste na 3.0. Model vidí unique constraints a foreign keys, což ho svádí ke generování constraint-violation testů (`duplicate_name`, `delete_with_books`), které ale API neimplementuje očekávaným způsobem.

**L3 je nejhorší úroveň v experimentu** - platíte téměř stejně jako za L2, ale dostáváte horší výsledky.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5   |
|---|---|---|---|---|---------|
| **Validity** | ⚠️ 96.7% | ⚠️ 90.0% | ⚠️ 90.0% | ⚠️ 90.0% | ❌ 83.3% |
| **EP Coverage** | 26.0% | 26.0% | 24.0% | 26.0% | 24.0%   |
| **Stale** | 1 | 3 | 3 | 3 | 5       |
| **Iterace** | 3 | 3 | 3 | 3 | 3       |
| **Assertion Depth** | 3.17 | 3.20 | 3.10 | 3.47 | 3.47    |
| **Response Valid.** | 93.3% | 93.3% | 93.3% | 90.0% | 93.3%   |
| **Cena** | $0.0524 | $0.0513 | $0.0530 | $0.0517 | $0.0520 |
| **Code Cov.** | 68.09% | 66.11% | 66.80% | 67.20% | -       |
| **crud.py** | 39.79% | 34.88% | 36.69% | 37.21% | -       |
| **main.py** | 69.73% | 69.39% | 69.39% | 70.07% | -       |

*Poznámka: L3 run5 nemá coverage data v dodaném MD souboru (pouze 4 runy v L3 coverage tabulce).*

**Specifická selhání L3:**
- `test_create_author_duplicate_name` / `test_delete_author_with_books`: Model vidí v DB schématu unique constraint a foreign key, generuje 409 Conflict testy - ale API vrací jiný kód.
- `test_apply_discount_*`: Pokračující problém z L2, model stále nedokáže správně předpovědět discount logiku.
- `test_restore_soft_deleted_book`: 2/4 běhy (run4, run5) - přetrvávající problém.

**L3 run5 - nejhorší běh experimentu:** 83.3% validity (25/30), 5 stale testů, jen 24% EP coverage. Model se pokouší o nejambicióznější scénáře (duplicate ISBN, discount, restore, rate limit) a všechny selhávají.

</details>

<details>
<summary><strong>📊 Úroveň L4 - + Ukázkové testy (53 438 tokenů)</strong></summary>

### Charakteristika úrovně

**Nejširší pokrytí, průměrná stabilita.** Ukázkové testy (25 963 znaků, nekomprimované) fungují jako template: model generuje 8 helperů (vs. 4–6 jinde), včetně `reset_db` a `setup_book_with_deps`. EP coverage roste na 30.8% (max 36% v run2) - nejlepší v experimentu. Validity zůstává na 92.0%.

**Unikátní chování L4:**
- Jako jediná úroveň má compliance score 65 (run1) - model přidává `reset_db()` volání, ale nesprávně.
- Jako jediná úroveň má nenulový self-correction rate (L4 run4: 20%).
- Model v L4 pokrývá endpointy, které jinde nikdy nevidíme: `GET /categories`, `GET /health`, `GET /authors` (list).

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | ⚠️ 93.3% | ⚠️ 96.7% | ⚠️ 93.3% | ⚠️ 86.7% | ⚠️ 90.0% |
| **EP Coverage** | 32.0% | **36.0%** ⭐ | 32.0% | 28.0% | 26.0% |
| **Stale** | 2 | 1 | 2 | 4 | 3 |
| **Iterace** | 3 | 3 | 3 | 3 | 3 |
| **Assertion Depth** | 2.67 | 3.43 | 2.83 | 2.73 | 3.33 |
| **Response Valid.** | 93.3% | 93.3% | 86.7% | 90.0% | 86.7% |
| **Cena** | $0.0655 | $0.0667 | $0.0656 | $0.0664 | $0.0644 |
| **Code Cov.** | 68.78% | 68.38% | 68.29% | 67.39% | 66.01% |
| **crud.py** | 42.38% | 41.34% | 41.60% | 37.73% | 34.88% |
| **main.py** | 68.71% | 68.71% | 68.03% | 70.07% | 69.05% |

**L4 run2 - nejlepší EP coverage experimentu (36%):**
- 18 unikátních endpointů v plánu (nejvíce ze všech 25 běhů)
- Top3 koncentrace jen 26.7% (nejrovnoměrnější distribuce)
- Pokrývá `GET /categories`, `GET /books/{id}/reviews`, `GET /books/{id}/rating`
- Přesto 1 stale test (`test_list_authors_with_pagination` - assertion on sort order)

**L4 run4 - unikátní self-correction:**
- First-shot: 25/30 (83.3%)
- Po opravě: 26/30 (86.7%) - **opravil `test_create_author_valid_data`**
- Ale 4 testy nikdy neopraveny: model špatně kopíroval assertions z ukázkových testů (hardcoded string values)

</details>

---

## 6. Souhrnná zjištění a doporučení

### 6.1 Příběh chování modelu v jedné větě

> Mistral Large 2512 je **spolehlivý generátor jednoduchých testů**, který se s rostoucím kontextem stává ambicióznějším, ale ne chytřejším - vidí víc kódu, pokouší se o sofistikovanější scénáře, ale jeho inferenční schopnosti nestačí na odvození správného chování, a jeho nulová self-correction znamená, že každé špatné rozhodnutí je finální.

### 6.2 Klíčová čísla pro obhajobu

| Zjištění | Hodnota | Implikace |
|---|---|---|
| Nejlepší validity | **L1: 99.3%** | Technická dokumentace je nejcennější kontext |
| Nejhorší validity | **L3: 90.0%** | DB schéma je „toxický kontext" |
| Nejlepší EP coverage | **L4: 30.8%** (max 36%) | Ukázkové testy rozšiřují pokrytí |
| Self-correction rate | **0.0%** (24/25 běhů) | Opravný cyklus je neúčinný |
| Nejlepší code coverage | **L2 run1: 70.96%** | Ale za cenu nejhorší validity v L2 |
| crud.py coverage | **36–40%** stabilně | Business logika zůstává nepokryta |
| Cost efficiency | **L0 > L1 > L2 ≈ L3 > L4** | Více kontextu = méně hodnoty za dolar |
| Celková cena | **$1.12 za 25 běhů** | Nízký náklad, ale nízká návratnost po L1 |

### 6.3 Praktická doporučení

1. **Pro maximální validity:** Použijte L1 (OpenAPI + tech doc). Návratnost dalšího kontextu je negativní.
2. **Pro maximální pokrytí:** Použijte L4, ale počítejte s ~8% failure rate a trojnásobnou cenou.
3. **Eliminujte opravné iterace:** U Mistralu se nevyplatí - 1 iterace je optimum.
4. **Investujte do prompt engineeringu:** Explicitně vyžadujte testování orders, exports a admin modulů - model je systematicky ignoruje.
5. **DB schéma (L3) vynechte:** Přidává náklady bez přínosu - je to čistý šum.