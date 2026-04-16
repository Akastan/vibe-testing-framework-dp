# 📊 Analýza experimentu Vibe Testing - Gemini 3.1 Flash Lite Preview (v12)


---

## 1. Konfigurace a Přehled

### 1.1 Konfigurace experimentu

| Parametr | Hodnota                                         |
|---|-------------------------------------------------|
| **LLM model** | `gemini-3.1-flash-lite-preview`                 |
| **Testovaný API ekosystém** | `bookstore` (50 endpointů, FastAPI)             |
| **Teplota** | `0.4`                                           |
| **Úrovně kontextu** | L0, L1, L2, L3, L4                              |
| **Počet běhů per úroveň** | 5 (celkem 25 běhů pro metriky, 25 pro coverage) |
| **Cílový počet testů v plánu** | 30 testů na běh                                 |
| **Datum experimentu** | 2026-04-15                                      |

### 1.2 Celkové shrnutí - příběh modelu v jedné větě

> **Gemini 3.1 Flash Lite je model, který má „sweet spot" na úrovni L1-L2 a trpí informačním přetížením při L4.** Při minimálním kontextu (L0) je nejistý a vyrábí chyby; při středním kontextu (L1) překvapivě excelově ladí plán s realitou; s dalšími vrstvami kontextu (L3, L4) se paradoxně zhoršuje a začíná „tonout ve vlastní dokumentaci".

| Úroveň | Validity % (průměr) | EP Coverage % | Stale testů (průměr) | Cost $ | 100% úspěch / 5 | Status drift |
|---|---|---|---|---|---|---|
| **L0** | 80,00 % (σ 11,79) | 38,8 % | 6,0 | 0,01684 | **0/5** | 2,00 |
| **L1** | **97,34 %** (σ 1,49)  | 39,2 % | **0,8**  | 0,01955 | **1/5** | **1,60**  |
| **L2** | 94,00 % (σ 8,30) | **44,0 %**  | 1,8 | 0,02413 | **2/5**  | 2,60 |
| **L3** | 90,67 % (σ 7,60) | 39,2 % | 4,2 | 0,02438 | 1/5 | 2,80 |
| **L4** | 80,67 % (σ 14,79) | 43,6 % | 5,8 | **0,02984**  | 0/5 | **7,40**  |

**Klíčová zjištění na první pohled:**

- **L1 je nejspolehlivější úroveň** - nejvyšší validity rate, nejnižší rozptyl, nejméně stale testů, nejnižší status code drift.
- **L2 má nejlepší endpoint coverage** (44 %) - přidaný kontext pomohl modelu „objevit" více endpointů.
- **L4 je kontraproduktivní** - nejdražší, nejvyšší rozptyl, nejvíce driftu, nula 100% úspěšných běhů.
- **L0 je loterie** - vysoký rozptyl (σ 11,79) a 0/5 běhů bez chyby, model „střílí naslepo".

---

## 2. Co se v datech děje - Analýza hlavních metrik

### 2.1 Validity rate - kde model exceluje a kde padá

**Validity rate** (% testů, které uspějí v běhu na reálném API) tvoří tvar **převráceného U**:

```
L0 ──► L1 ──► L2 ──► L3 ──► L4
80 %   97 %   94 %   91 %   81 %
 ↑      ↑              ↓     ↓
padá  peak          klesá  padá
```

**Kde model exceluje:**
- **L1 run2, L2 run4/run5, L3 run2** dosáhly **100 % validity** (30/30 testů prošlo). To ukazuje, že model *umí* vyprodukovat bezchybný test suite - ale ne konzistentně.
- **L1 je abnormálně stabilní**: směrodatná odchylka σ = 1,49 % je nejnižší napříč všemi úrovněmi. Model má jasné, ne-přehlcené instrukce.

**Kde padá:**
- **L0 run2** dramaticky propadl (60 %, 12 stale testů) - bez dokumentace o helper funkcích si model vymyslel chování, které neodpovídá realitě.
- **L4 run3** je nejhorší běh experimentu (**56,67 %**, 13 stale testů, 16 failures). V té chvíli dostal model plný kontext a **ztratil se v něm**.

**Pozorování o rozptylu:** Rozptyl (σ) narůstá směrem k L4 (z 1,49 na 14,79). **S více kontextu se chování modelu stává méně předvídatelným.**

### 2.2 Endpoint Coverage - kolik endpointů model reálně trefil

API má **50 endpointů**. Model trefil:

| Úroveň | Covered / 50 | % |
|---|---|---|
| L0 | ~19,4 | **38,8 %** |
| L1 | ~19,6 | 39,2 % |
| L2 | **~22,0** | **44,0 %** |
| L3 | ~19,6 | 39,2 % |
| L4 | ~21,8 | 43,6 % |

**Brutální realita:** **Ani v nejlepším scénáři model netrefí víc než ~46 % endpointů.** Strop je strukturální - v plánu má vždy jen ~30 testů, takže i při maximální diverzitě pokryje ~30 z 50 endpointů. Coverage je **limitovaný velikostí plánu**, ne schopností modelu.

**Které endpointy model konzistentně ignoruje (≥ 24/25 běhů nezahrnulo):**

| Endpoint | Pravděpodobný důvod ignorování                                                     |
|---|------------------------------------------------------------------------------------|
| `GET /admin/maintenance` | Admin-only, vyžaduje oprávnění, nejasný use-case                                   |
| `GET /authors`, `GET /orders`, `GET /tags`, `GET /books/{id}/reviews` | **GET list endpointy** - model je vnímá jako „nudné" a preferuje mutace            |
| `DELETE /categories/{id}`, `DELETE /tags/{id}`, `DELETE /books/{id}/cover` | Vyžaduje setup (vytvořit entitu, pak mazat) - model raději volí jednodušší scénáře |
| `POST /exports/orders`, `POST /reset` | Asynchronní/infrastrukturní endpointy - mimo „happy path" uvažování                |
| `POST /orders/{id}/items` | Vyžaduje nejdřív vytvořit objednávku - model se bojí chainingu                     |

**Které endpointy model naopak spolehlivě pokrývá:**
- `POST /books/{id}/restore` (24/25 běhů) - jednoduchá mutace
- `GET /books/{id}` (22/25) - klasický happy path
- `PATCH /books/{id}/stock` (21/25)
- `POST /books/{id}/reviews` (21/25)

**Doménová zaujatost:** Model **zaostřuje na `books` doménu** (průměrně 16-18 testů z 30 napříč všemi úrovněmi), zatímco `categories` a `tags` dostávají jen 1 test průměrně. To je důsledek toho, že OpenAPI specifikace má nejvíc endpointů pro knihy - model jede po frekvenci výskytu.

### 2.3 Staleness a Chyby - zasekává se model v bludných kruzích?

**Stale testy** = testy, které framework po N iteracích opravy označil za „neopravitelné" a přeskočil.

| Úroveň | Průměr stale | Max stale v jednom běhu |
|---|---|---|
| L0 | **6,0** | 12 (run2) |
| L1 | **0,8**  | 1 |
| L2 | 1,8 | 6 (run2) |
| L3 | 4,2 | 12 (run5) |
| L4 | 5,8 | 13 (run3) |

**Tady je klíčový příběh:** L1 má téměř nulové staleness, L0/L3/L4 ho mají výrazně vyšší. **Model se zasekává v „bludných kruzích" v obou extrémech - když má málo informací i když má jich moc.**

**Failure taxonomy - co přesně padá:**

| Úroveň | wrong_status_code | other (helper/fixture chyby) | timeout |
|---|---|---|---|
| L0 | **20** | 1 | 1 |
| L1 | 5 | 0 | 0 |
| L2 | 9 | **13** | 2 |
| L3 | 3 | **15** | 0 |
| L4 | 7 | **20** | **7** |

**Pozorování:**
- **L0 chyby = hallucinations** (wrong_status_code = model hádá). Model bez dokumentace **střílí naslepo**, očekává špatné status kódy.
- **L2-L4 chyby = helper/fixture problémy** („other" = chyby při setup, např. `create_book(stock=...)` když helper nepodporuje `stock` parametr). Model s větším kontextem začíná **psát testy, které přepokládají helpery/chování, jež neexistuje**.
- **L4 má navíc timeouty** (7 - nejvíc ze všech) - testy se zasekávají na endpointech typu `/orders/{id}/invoice`, což znamená že model testuje scénáře, které se reálně „zastaví" na serveru.

**Status code drift** (rozdíl mezi plánovaným a skutečným status kódem):

```
L0: 2.00  ->  L1: 1.60  ->  L2: 2.60  ->  L3: 2.80  ->  L4: 7.40
                                                         4,6× vyšší!
```

**Tohle je nejsilnější kvantitativní důkaz information overload:** při L4 model plánuje jeden status kód, ale generuje kód pro jiný - **jeho plán a implementace se rozcházejí**, protože zpracovává tolik informací, že si je sám plete.

**Self-correction rate** (% chyb, které model sám opraví v iteracích):

| Úroveň | Self-correction % |
|---|---|
| L0 | **0,0 %** |
| L1 | 20,0 % |
| L2 | **80,98 %**  |
| L3 | 13,33 % |
| L4 | 13,75 % |

**L2 má schopnost sebeopravy - ostatní úrovně ne.** Znamená to, že při L2 má model přesně ty správné informace k pochopení vlastních chyb, ale při L3/L4 se ztrácí a nedokáže se opravit stejně efektivně.

### 2.4 Token usage, komprese a cena - vyplatí se vyšší kontext?

| Úroveň | Context tokens (po kompresi) | Komprese % | Total tokens per run | Cost $ | Cena vs. L0 |
|---|---|---|---|---|---|
| L0 | 15 958 | **48,1 %** | 40 869 | 0,01684 | baseline |
| L1 | 23 783 | 38,8 % | 57 700 | 0,01955 | +16 % |
| L2 | 43 917 | 26,2 % | 92 912 | 0,02413 | +43 % |
| L3 | 44 770 | 25,8 % | 100 597 | 0,02438 | +45 % |
| L4 | 53 438 | 22,6 % | 117 132 | 0,02984 | **+77 %** |

**Ekonomika kontextu - brutální ROI:**

- Skok L0 -> L1: cena +16 %, validity **+17 %** (80 % -> 97 %). **Nejlepší investice v experimentu.**
- Skok L1 -> L2: cena +24 %, validity −3 %, EP coverage +5 %. **Okrajová hodnota.**
- Skok L2 -> L3: cena +1 %, validity −3 %, EP coverage −5 %. **Ztráta.**
- Skok L3 -> L4: cena +22 %, validity −10 %, EP coverage +4 %. **Katastrofa - platíte víc za horší výsledek.**

**Efektivita komprese klesá s úrovněmi:** v L0 šetříme 48 % tokenů, v L4 už jen 22,6 %. Přibývající kontexty jsou stále hůře komprimovatelné (přicházejí už „hutné" dokumentace).

**Rozpad nákladů podle fáze (průměr první běh L0):**
- **Planning** - 2 volání, 19 528 tokenů (46 % celkem)
- **Generation** - 1 volání, 17 554 tokenů (41 %)
- **Repair** - 2 volání, 5 238 tokenů (12 %)

Planning spotřebuje nejvíc - a je to právě fáze, kde L1 „trefí" správné rozhodnutí a další úrovně ho už nevylepšují.

---

## 3. Detailní rozbor Code Coverage (úrovňová analýza FastAPI aplikace)

> Data: 24 běhů z `outputs_v12_gemini/coverage_results`. Měří, kolik řádků Python kódu v testované FastAPI aplikaci bylo spuštěno vygenerovanými testy.

### 3.1 Průměrné pokrytí podle souborů a úrovní

| Úroveň | Celkem | `app/__init__.py` | `app/crud.py` | `app/database.py` | `app/main.py` | `app/models.py` | `app/schemas.py` |
|---|---|---|---|---|---|---|---|
| **L0** | 62,32 % | 100 % | **28,32 %** | 100 % | 65,04 % | 100 % | 100 % |
| **L1** | **68,46 %** | 100 % | 40,93 % | 100 % | 69,53 % | 100 % | 100 % |
| **L2** | **68,74 %**  | 100 % | **41,40 %**  | 100 % | 69,87 %  | 100 % | 100 % |
| **L3** | 67,89 % | 100 % | 40,05 % | 100 % | 68,71 % | 100 % | 100 % |
| **L4** | 65,87 % | 100 % | 35,45 % | 100 % | 67,83 % | 100 % | 100 % |

### 3.2 Analýza per soubor

**Soubory s trvalým 100% pokrytím:**
- `app/__init__.py` - triviální inicializace, pokrytá prakticky každým importem.
- `app/database.py` - engine, Session factory. Každý test, který volá API, projde tímto souborem.
- `app/models.py` - SQLAlchemy ORM modely. Pokryté jakýmkoli CRUD voláním.
- `app/schemas.py` - Pydantic validátory. Automaticky pokryté každým požadavkem, který server validuje.

**Důležité zjištění:** 100% pokrytí těchto souborů **neznamená kvalitu testů** - znamená to jen, že tyto soubory jsou *load-time-executed*. Jsou to „falešně 100% zelené" moduly.

**Soubory, které odhalují skutečnou sílu testů:**

#### `app/main.py` - endpoint handlers
- L0: 65,04 % -> L2: 69,87 % -> L4: 67,83 %
- Rozsah 4,8 procentních bodů. **Endpoint logika je pokryta stabilně, ale ne kompletně.** Třetina handlerů zůstává netestovaná napříč všemi úrovněmi - kryje se to s uncovered endpoints (admin, export, maintenance).

#### `app/crud.py` - business logika
- L0: **28,32 %** -> L2: **41,40 %** -> L4: **35,45 %**
- Rozsah 13,1 procentních bodů - **největší variace napříč úrovněmi**.
- **Toto je jediný soubor, kde úroveň kontextu skutečně mění pokrytí.**
- Model nikdy nepřekročil ~42 % pokrytí - CRUD operace pro `categories`, `tags`, `orders` a `authors` zůstávají silně podpokryté.

### 3.3 Proč je `crud.py` „achillova pata" pokrytí?

`crud.py` obsahuje funkce typu `create_X`, `get_X`, `update_X`, `delete_X`, `list_X` pro každou doménu. Model:

1. **Preferuje mutace nad listy** - `create_*` funkce se spouštějí (testy typu `test_create_book_valid`), ale `list_*` funkce (GET kolekce) model ignoruje (viz sekce 2.2).
2. **Nepoužívá reset endpoint** - `calls_reset_endpoint = 0/25` napříč všemi úrovněmi. Model nikdy nevyčistil stav mezi testy, takže `reset_database()` funkce v `crud.py` zůstává nepokrytá.
3. **Ignoruje setup-heavy scénáře** - funkce jako `add_book_to_order`, `clone_book`, `export_orders` vyžadují řetězení více CRUD volání. Model tomu uhýbá (`pct_chaining = 3,3 %` v L0, zůstává nízké).

**Hypotéza proč L2 exceluje v `crud.py` (41,40 %):** L2 má dostatek kontextu, aby model pochopil existenci pokročilých operací (clone, restore, reviews), ale ne tolik, aby se v něm ztratil a začal plánovat ambiciózní řetězené scénáře, které pak selžou (jako v L4).

### 3.4 Funkční mikro-analýza: case study L3 run5 (pokrytí 66,50 %)

> Data: `coverage_gemini-3_1-flash-lite-preview__L3__run5.json`. Tento konkrétní běh je zvlášť hodnotný, protože jde o **tu samou anomálii**, kterou jsme diskutovali v sekci 4.4 - běh se 7 iteracemi oprav a regresí v iteraci 5. Reálné funkční pokrytí tohoto běhu nám říká, **které konkrétní funkce model při chaosu repair loopu stihl otestovat a kterým se vyhnul**.

**Celkové pokrytí L3 run5:** 66,50 % (671 z 1009 statementů). Z tohoto:
- `crud.py`: **34,37 %** (133/387 - pod průměrem L3 40,05 %)
- `main.py`: **71,43 %** (210/294 - nad průměrem L3 68,71 %)
- ostatní soubory: 100 % (load-time pokrytí)

**Rozložení kvality pokrytí v `crud.py`:**

| Kategorie | Počet funkcí | Celkem z 42 |
|---|---|---|
|  100% pokryté | 8 funkcí | 19 % |
|  Částečně pokryté | 8 funkcí | 19 % |
|  0% pokryté (ignorované) | **26 funkcí** | **62 %** |

**Děsivé zjištění:** V `crud.py` je na **0% funkcích 234 z 387 statementů (60,5 %) - model se k nim ani nepřiblížil.**

#### 3.4.1 Funkce, které model spolehlivě pokrývá (100 %)

| Funkce | Řádků | Proč prošla                                                     |
|---|---|-----------------------------------------------------------------|
| `create_author` | 5 | Základní stavební blok - volána helper funkcí `create_author()` |
| `get_author` | 4 | Čte vytvořeného autora po vytvoření                             |
| `create_book` | 9 | Klíčový helper `create_book()` - použit v 83 % testů            |
| `delete_book` | 5 | Součást soft-delete testů (vyvolává `restore_book` scénář)      |
| `create_category` | 85,7 % (6/7) | Helper `create_category()`                                      |
| `create_tag` | 7 | Jedna z mála POST tag operací v plánu                           |
| `apply_discount` | 6 | Model má speciální testy na slevy (happy + invalid value)       |
| `generate_etag` | 1 | Triviální - spustí se při každém GET                            |
| `get_order_response` | 2 | Interní helper volaný po `create_order`                         |

**Vzorec:** Model pokrývá primárně **POST create_X funkce** a jejich nejtěsnější GET doprovod.

#### 3.4.2 Funkce, které model zcela ignoroval (0 %)

Seznam 26 funkcí, seřazený podle velikosti „ztracené plochy":

| Funkce | Řádků  | Kategorie | Proč se model vyhnul                                                                |
|---|--------|---|-------------------------------------------------------------------------------------|
| **`bulk_create_books`** | **26** | Bulk | Vyžaduje znalost multi-status responses (207) a partial success - model to nezvládá |
| `update_book` | 16     | Update | ETag mismatch logika je složitá                                                     |
| `add_item_to_order` | 16     | Chaining | Vyžaduje: author->category->book->order->add_item (pět chainů)                      |
| `get_statistics` | 16     | Agregace | Model generoval test, ale nikdy neprošel (viz L0 failures)                          |
| `get_books` | 15     | List | Paginated list s filtry - model listy ignoruje                                      |
| `update_order_status` | 14     | Update | FSM tranzice (timeouty v L4!)                                                       |
| `get_orders` | 13     | List | Filtrovaný list - ignorován                                                         |
| `update_category`, `update_tag` | po 12  | Update | Generický vzorec update operace                                                     |
| `delete_order` | 10     | Delete | Setup-heavy                                                                         |
| `update_stock` | 9      | Update | Vyžaduje validaci negativního stocku                                                |
| `add_tags_to_book`, `remove_tags_from_book`, `clone_book` | po 8   | Chaining | Multi-entity operace                                                                |
| `update_author`, `delete_author`, `delete_category` | 6-7    | Update/Delete |                                                                                     |
| `create_review`, `get_book_average_rating`, `get_author_books` | po 6   | Aggregation | Vyžaduje větší setup                                                                |
| `delete_tag`, `get_tag` | 4-5    | List/Delete |                                                                                     |
| `get_reviews`, `get_authors`, `get_categories`, `get_tags` | 1-2    | **GET lists** | **Systematicky ignorované**                                                         |

**Taxonomie vyhýbavosti modelu:**

1. **Všechny „GET kolekce" funkce jsou 0 %** (`get_authors`, `get_categories`, `get_books`, `get_orders`, `get_tags`, `get_reviews`). **Model má slepé místo na listing endpointy.**
2. **Všechny „update_X" funkce jsou 0 %** (6 ze 6). Update vyžaduje nejdřív GET pro etag, pak PUT s podmínkami - moc kroků.
3. **Všechny „delete_X" kromě `delete_book` jsou 0 %** (5 ze 6). Delete je neúspěšný, pokud entita má vazby - model se toho bojí.
4. **Bulk, clone a statistics operace 0 %** - pokročilé features mimo core CRUD.

#### 3.4.3 Částečně pokryté funkce (šedá zóna)

| Funkce | Pokrytí | Interpretace                                                  |
|---|---|---------------------------------------------------------------|
| `create_order` | **94,7 %** (18/19) | Model zvládl happy path, minul jednu edge větev               |
| `create_category` | 85,7 % (6/7) | Missed duplicitní name validation                             |
| `get_book` | 83,3 % (5/6) | Missed 404 větev                                              |
| `get_book_include_deleted` | 75,0 % (3/4) | Model ignoruje `include_deleted=true` parametr                |
| `get_category` | 75,0 % (3/4) | Missed 404                                                    |
| `get_order` | 75,0 % (3/4) | Missed 404                                                    |
| `restore_book` | **33,3 %** (3/9) | Pokrývá happy path, ignoruje edge cases (restore-when-active) |
| `generate_invoice` | **27,3 %** (3/11) | Velká funkce - model zavolal jen 1-2 scénáře (pending/paid)   |

**`generate_invoice` je symptomatická**: z 11 statementů pokrytých jen 3 -> model testuje faktury jen povrchně, mine celou validační logiku (forbidden states, pending orders).

#### 3.4.4 Pohled z druhé strany: `main.py` funkční rozbor

`main.py` má jiný profil - endpoint handlery jsou většinou 1-řádkové rutery, takže pokrytí je **binární** (buď volal endpoint, nebo ne).

- **100% pokrytých: 18 handlerů** (reset_database, create_*, health_check, deprecated_catalog, apply_discount, get_invoice, …)
- **0% pokrytých: 33 handlerů** (list_authors, get_cover, delete_cover, update_*, delete_*, get_statistics, get_maintenance_status, …)

**Pozoruhodné:** `reset_database` má 100 % (14/14 statementů) - to ale neznamená, že model volá `POST /reset`! Tato funkce se vykonává jako součást pytest fixture setup/teardown, ne díky testům. **Metrika `calls_reset_endpoint = False` z metrics.json tuto iluzi demaskuje.**

**Speciální pozornost: `deprecated_catalog`** má 100 % (1 řádek). Tenhle endpoint je v plánu pokryt právě proto, že je v OpenAPI specifikaci označený jako deprecated a model k němu přistupuje jako k „nízko visícímu ovoci" pro pokrytí.

#### 3.4.5 Co z toho vyplývá pro obhajobu

Funkční mikro-analýza L3 run5 umožňuje obhájit tři klíčová tvrzení:

1. **„Řádkové pokrytí 67 % nepředstavuje 67 % kvality testů."** Reálně je pokryto 19 % funkcí na 100 % a 62 % funkcí ignorováno. Distribuce kvality je **bimodální**, ne normální.

2. **„Model má systematické slepé skvrny, nikoliv náhodné mezery."** Ignoruje vždy stejné kategorie: list endpointy, update operace, delete operace, bulk/clone operace. Tohle **není náhodou**, je to důsledek plánovacího behavioru modelu.

3. **„Ani při dobrém pokrytí `main.py` (71,4 %) neznamená dobré pokrytí `crud.py` (34,4 %)."** Model „dotkne" endpointu (ruter v main.py), ale nedostane se do hlubší business logiky - nenastavil data tak, aby test vybudil celou kaskádu. **Prozrazuje to mělkost testů.**

---

## 4. Proč se to děje? - Kauzální analýza a obhajoba dat

### 4.1 Hlavní teze: Gemini 3.1 Flash Lite vykazuje klasické **information overload** chování

**Důkaz 1 - Křivka validity** má tvar obráceného U s vrcholem L1:

```
Validity:    80 -> 97 -> 94 -> 91 -> 81  (L0 -> L4)
```

**Důkaz 2 - Status code drift exploduje u L4:** z 1,6 (L1) na 7,4 (L4). Tohle je **přímý otisk toho, že model ztrácí synchronizaci mezi plánem a kódem**. Jeho plán říká „tento test čeká 201", ale v kódu napíše `assert r.status_code == 200`.

**Důkaz 3 - „Other" kategorie chyb roste:** z 0 (L1) na 20 (L4). Model začíná používat helper signatury, které si „pamatuje" špatně (`create_book(stock=10)` - ale helper neumí `stock` parametr!).

**Důkaz 4 - Self-correction klesá:** L2 má 80,98 %, L4 jen 13,75 %. Model s velkým kontextem ani nedokáže sám opravit vlastní chyby, protože se v kontextu ztrácí.

### 4.2 Proč má L0 výrazně horší výsledky než L1?

**Kauzalita:** V L0 má model jen OpenAPI specifikaci (~16 k tokenů), ale **žádnou ukázku helper funkcí** ani info o fixturech. Výsledek:

- **20 z 22 chyb = wrong_status_code** -> model hádá, jaký kód vrátí endpoint.
- **Self-correction = 0 %** -> model nemá co opravit, protože opakuje stejnou chybu.
- **calls_reset_endpoint = 0/5** -> model neví, že `POST /reset` existuje jako izolační mechanismus.

L1 přidává právě těch ~8 k tokenů „minimální nápovědy" (helper signatury) - a validity skočí o 17 procentních bodů.

### 4.3 Proč L4 kolabuje, i když má nejvíc informací?

**Hypotézy (všechny podpořené daty):**

**(a) Context window pollution** - 53 k tokenů samotného kontextu + 2 632 tokenů plánu = 56 k tokenů v promptu. Model musí „navigovat" obrovský prostor a jeho attention mechanism dělá mikro-chyby.

**(b) Helper memorization glitch** - v L4 failure taxonomy vidíme opakovaný vzorec `b = create_book(a["id"], c["id"], stock=10)` - model v kontextu vidí *příklady* volání helperů, ale začne je kombinovat kreativně se *semantickými* přáními (chce knihu se stockem 10, tak napíše `stock=10`, i když helper to neumí).

**(c) Ambition inflation** - L4 má nejvíc „error" testů (20 z 30 průměrně, vs. 15 v L0). Model s velkým kontextem plánuje ambicióznější scénáře (invalid transitions, forbidden states, etag mismatch), které jsou ale křehčí a častěji padají.

**(d) Timeout amplification** - L4 má 7 timeoutů vs. 0 v L1. Model generuje testy pro endpointy, které na serveru reálně visí (např. `PATCH /orders/{id}/status -> delivered` při nevalidní tranzici). Znak toho, že se pouští do území, kterému ne zcela rozumí.

### 4.4 Anomálie a jejich vysvětlení

**Anomálie 1 - L0 run2 (60 %, 12 stale):**
Bez kontextu o helperech se model rozhodl 12 testů založit na předpokladech, které framework nemohl ani opravit („neopravitelné"). **Je to ukázka, jak rychle se model propadne bez základní nápovědy.**

**Anomálie 2 - L3 run5 (7 iterací, 12 stale, not early_stopped):**
Dramatický příběh. Trajektorie oprav:

| Iterace | Passed | Failed | Repair type |
|---|---|---|---|
| 1 | 29 | 1 | isolated |
| 2 | 29 | 1 | helper_fallback |
| 3 | 28 | 2 | isolated (regrese!) |
| 4 | 28 | 2 | helper_fallback |
| 5 | **16** | **14** | isolated **← katastrofa** |
| 6 | 16 | 14 | helper_fallback |
| 7 | 25 | 5 | finální |

**Co se stalo:** V iteraci 5 model při opravě jediného testu **rozbil 12 dalších**. Klasický případ, kdy model v pokusu o „chytrou opravu" změnil společný helper nebo fixture tak, že rozbil předchozí funkční testy. **Toto je *přesně* ten režim, kterého se bát - regrese způsobená repair loopem.**

**Anomálie 3 - L4 run3 (56,67 %, 13 stale, 16 failures):**
Nejhorší běh experimentu. Failure taxonomy ukazuje 13× kategorii „other" = 13 selhání už v setup fázi (create_book volání). **Model v L4 si vytvořil falešný mentální model helperů a nedokázal se z něj vymanit.**

**Anomálie 4 - L1 je abnormálně stabilní (σ = 1,49 %):**
Všech 5 běhů L1 má validity 96,67-100 %. Tohle není náhoda - L1 má „přesně správnou" dávku kontextu: helper signatury + velmi seškrcená OpenAPI. Model nemá prostor na kreativní chyby.

### 4.5 Jak kontext koreluje s Code Coverage

Tabulka korelace:

| Metrika | Korelace se vzrůstajícím kontextem |
|---|---|
| `crud.py` pokrytí | Obrácené U (peak L2) |
| `main.py` pokrytí | Obrácené U (peak L2) |
| EP Coverage | Obrácené U (peak L2) |
| Validity | Obrácené U (peak L1) |
| Náklady | Lineární růst ↑ |
| Status drift | L1 minimum, L4 exploze |

**Kauzální vztah:** Větší kontext -> model plánuje **šířeji** (víc endpointů -> vyšší EP coverage a crud.py coverage) -> ale také **mělčeji** (méně pečlivě -> nižší validity). **Sweet spot je L2 pro šířku, L1 pro hloubku.**

---

## 5. Detailní rozpis jednotlivých úrovní a běhů

<details>
<summary><b>📘 L0 - Minimální kontext (jen OpenAPI, 15 958 tokenů)</b></summary>

**Chování modelu:** Model má k dispozici jen OpenAPI specifikaci. Nemá popis helperů, fixtur ani konvencí. **Střílí naslepo - halucinuje status kódy a selhává na predikci chování serveru.** Každý z 5 běhů skončil early stop (nedokonvergoval).

| Metrika | Hodnota |
|---|---|
| Průměrná validity | 80,0 % (σ 11,79) |
| Průměr stale | 6,0 testů |
| Průměrné náklady | $0,01684 |
| 100% úspěch | 0/5 |
| Hlavní chyba | wrong_status_code (91 %) |
| Coverage app/crud.py | 28,32 % |

| Run | Validity | EP Cov | Stale | Cost $ | Coverage celk. |
|---|---|---|---|---|---|
| 1 | 86,67 % | 42,0 % | 4 | 0,02078 | 63,53 % |
| 2 | **60,00 %**  | 42,0 % | **12** | 0,01927 | 58,47 % |
| 3 | 83,33 % | 42,0 % | 5 | 0,01347 | 62,64 % |
| 4 | 80,00 % | 30,0 % | 6 | 0,01268 | 62,64 % |
| 5 | 90,00 % | 38,0 % | 3 | 0,01799 | 64,32 % |

**Komentář:** L0 je **baseline nejistoty**. Model se opakovaně zasekává na 4 testech, které označí za neopravitelné (`test_apply_discount_invalid_value`, `test_create_order_success`, `test_get_statistics_success`, `test_start_export_success`) - všechny 4 mají wrong_status_code. Jediná halucinace status kódu v celém experimentu (`409`) vznikla v L0 run5.

</details>

<details>
<summary><b>📗 L1 - Minimální kontext + helper signatury (23 783 tokenů)  NEJSTABILNĚJŠÍ</b></summary>

**Chování modelu:** Přidání signatur helper funkcí (`create_book()`, `create_author()`, `create_category()`, `get_unique()`) je **zlom**. Model přestává hádat a začíná skutečně psát testy. Validity vyskakuje na 97 % s minimálním rozptylem.

| Metrika | Hodnota |
|---|---|
| Průměrná validity | **97,34 %** (σ 1,49)  |
| Průměr stale | **0,8** testů  |
| Průměrné náklady | $0,01955 (+16 % vs. L0) |
| 100% úspěch | 1/5 |
| Self-correction | 20,0 % |
| Coverage app/crud.py | 40,93 % (+12,6 p.b.) |

| Run | Validity | EP Cov | Stale | Cost $ | Coverage |
|---|---|---|---|---|---|
| 1 | 96,67 % | 36,0 % | 1 | 0,02450 | 67,20 % |
| 2 | **100,00 %**  | 36,0 % | 0 | 0,01497 | 68,58 % |
| 3 | 96,67 % | 40,0 % | 1 | 0,01934 | 68,09 % |
| 4 | 96,67 % | 38,0 % | 1 | 0,01981 | 69,57 % |
| 5 | 96,67 % | **46,0 %** | 1 | 0,01913 | 68,88 % |

**Komentář:** L1 je **ROI šampion experimentu**. Za 16 % vyšší cenu dostáváte 17 procentních bodů validity a 5× menší rozptyl. Všech 5 běhů je konzistentních. Model ještě nezačíná vymýšlet pokročilé scénáře, drží se konzervativních volání.

</details>

<details>
<summary><b>📙 L2 - Helper + ukázky testů (43 917 tokenů)  NEJLEPŠÍ COVERAGE</b></summary>

**Chování modelu:** Model dostane pravé ukázky existujících testů. **Začíná experimentovat s širším spektrem endpointů a dosahuje nejvyššího endpoint coverage (44 %) a crud.py pokrytí (41,40 %).** Paradoxně ale klesá validity - model je ambicióznější a dělá víc chyb v setup fázích.

| Metrika | Hodnota |
|---|---|
| Průměrná validity | 94,00 % (σ 8,30) |
| Průměr stale | 1,8 testů |
| Průměrné náklady | $0,02413 (+43 % vs. L0) |
| 100% úspěch | **2/5**  |
| Self-correction | **80,98 %**  |
| Coverage app/crud.py | **41,40 %**  |

| Run | Validity | EP Cov | Stale | Cost $ | Coverage |
|---|---|---|---|---|---|
| 1 | 93,33 % | **52,0 %** 🎯 | 2 | 0,02636 | 68,58 % |
| 2 | 80,00 %  | 44,0 % | 6 | 0,02071 | 67,39 % |
| 3 | 96,67 % | 42,0 % | 1 | 0,02858 | 69,87 % |
| 4 | **100,00 %**  | 46,0 % | 0 | 0,02243 | 67,39 % |
| 5 | **100,00 %**  | 36,0 % | 0 | 0,02257 | 70,47 % |

**Komentář:** L2 má **nejvyšší variabilitu v úspěchu** - dva 100% běhy a jeden propad na 80 %. Kontext už dává modelu prostor k experimentu, což někdy vyjde dokonale a jindy propadne. **Self-correction 81 %** ukazuje, že když model selže, často se dokáže opravit - klíčová výhoda L2.

</details>

<details>
<summary><b>📕 L3 - Plný helper + testy + naming conventions (44 770 tokenů)</b></summary>

**Chování modelu:** Jen marginální nárůst kontextu (+850 tokenů vs. L2), ale významný pokles výkonu. Model začíná být **zahlcený** - validity klesá na 90,67 %, stale roste na 4,2. Self-correction propadá z 81 % na 13 %.

| Metrika | Hodnota |
|---|---|
| Průměrná validity | 90,67 % (σ 7,60) |
| Průměr stale | 4,2 testů |
| Průměrné náklady | $0,02438 (+45 %) |
| 100% úspěch | 1/5 |
| Self-correction | 13,33 % |
| Coverage app/crud.py | 40,05 % |

| Run | Validity | EP Cov | Stale | Cost $ | Coverage |
|---|---|---|---|---|---|
| 1 | 83,33 % | 40,0 % | 5 | 0,02470 | 67,89 % |
| 2 | **100,00 %**  | 44,0 % | 0 | 0,01973 | 67,00 % |
| 3 | 90,00 % | 36,0 % | 3 | 0,02517 | 68,68 % |
| 4 | 96,67 % | 38,0 % | 1 | 0,02126 | 67,99 % |
| 5 | 83,33 % | 38,0 % | **12**  | 0,03106 | **66,50 %**  |

**Komentář:** **L3 run5 je anomálie zaslouženého rozboru** - 7 iterací oprav s klasickou regresí (iter 5: 28->16 passed). Model v jedné z oprav „přepsal" helper/fixture a rozbil si dalších 12 testů. Je to **varovný příklad repair loopu**, který je o to zákeřnější, že framework nevyhlásil early stop (pokračoval hádat).

</details>

<details>
<summary><b> L4 - Maximální kontext (53 438 tokenů)  INFORMATION OVERLOAD</b></summary>

**Chování modelu:** Plný kontext, vysoká cena, nejhorší výkon (spolu s L0). **4 z 5 běhů skončily early stop**, žádný nedosáhl 100 %. Status code drift vyskočil na **7,40** - model plánuje jedno a kóduje druhé.

| Metrika | Hodnota |
|---|---|
| Průměrná validity | 80,67 % (σ 14,79) |
| Průměr stale | 5,8 testů |
| Průměrné náklady | **$0,02984**  (+77 % vs. L0) |
| 100% úspěch | 0/5 |
| Status drift | **7,40**  (4,6× vs. L1) |
| Timeouty | 7 (nejvíc) |
| Coverage app/crud.py | 35,45 % |

| Run | Validity | EP Cov | Stale | Cost $ | Coverage |
|---|---|---|---|---|---|
| 1 | 76,67 % | 50,0 % | 7 | 0,02681 | 63,73 % |
| 2 | 90,00 % | 38,0 % | 3 | 0,02275 | 65,51 % |
| 3 | **56,67 %**  | 44,0 % | **13** | 0,03204 | 62,24 % |
| 4 | 93,33 % | 44,0 % | 2 | 0,02704 | 68,29 % |
| 5 | 86,67 % | 42,0 % | 4 | **0,04056**  | 69,57 % |

**Komentář:** L4 je **ekonomicky a kvalitativně worst-case scenario**. L4 run3 je nejhorší běh experimentu - 16 failures, 13 stale, z nichž 13 jsou „other" kategorie (halucinované helper parametry typu `stock=10`). L4 run5 je nejdražší běh vůbec ($0,041). Doporučení: **L4 nepoužívat pro tento model a tento typ úlohy.** Pokud už chcete víc kontextu, řešení není kvantita, ale **kvalita** (selektivní dokumentace).

</details>

---

## 6. Finální závěry a doporučení

### 6.1 Co jsme se naučili o Gemini 3.1 Flash Lite

1. **Sweet spot je L1 pro stabilitu, L2 pro šířku pokrytí.** Obě tyto úrovně dávají nejlepší poměr cena/výkon.
2. **Model má „context overflow threshold" někde mezi L2 a L3** (~45 k tokenů kontextu). Nad tímto prahem začíná plán a kód divergovat.
3. **Model má silnou doménovou zaujatost k `books`** napříč všemi úrovněmi - je to důsledek struktury OpenAPI, kde je tato doména nejbohatší.
4. **Model ignoruje list-style GET endpointy** a setup-heavy scénáře (chaining). Toto je strukturální omezení *plánování*, ne *kódování*.
5. **Reset mechanismus není nikdy využit** (`calls_reset = 0/25`) - slepé místo v přístupu modelu.

### 6.2 Praktická obhajoba dat pro diplomku

- **„Proč L0 měří chování bez opory"** -> L0 má 0 % self-correction, 20/22 chyb wrong_status_code. Je to referenční bod hallucinace.
- **„Proč L1 je nejefektivnější"** -> +16 % cena, +17 procentních bodů validity, σ 1,49 % (nejnižší), 0,8 stale.
- **„Proč L2 má nejvyšší EP coverage"** -> Ukázky testů dodávají modelu „nápady" na širší scénáře. L2 run1 dosáhl 52 % EP coverage (nejvíc v experimentu).
- **„Proč L4 nedoporučujeme"** -> status drift 7,40 vs. 1,60 u L1 (4,6×), 0/5 úspěšných běhů, +77 % cena vs. L0.
- **„Proč crud.py nikdy nepřekročí 42 %"** -> Model pokrývá max ~30 endpointů plánem, preferuje mutace, ignoruje listy a setup-heavy scénáře, nikdy nevolá reset.

### 6.3 Co by pomohlo modelu (doporučení pro další iteraci)

1. **Explicitně instruovat model, aby volal `POST /reset`** - získali byste pokrytí `reset_database()` a stabilnější testy.
2. **Rozšířit plán z 30 na 50 testů** - uvolnilo by to strop endpoint coverage.
3. **Přidat do promptu seznam „povinných doménových slotů"** - donutilo by to model testovat i `tags` a `categories`.
4. **Pro L3/L4 pravděpodobně použít kvalitativní selekci kontextu** místo kumulativního přidávání.

---

*Report vygenerován 2026-04-16 | Analyzovaných běhů: 25 (metriky) + 24 (coverage) | Model: gemini-3.1-flash-lite-preview | API: bookstore (50 endpointů) | Teplota: 0,4*