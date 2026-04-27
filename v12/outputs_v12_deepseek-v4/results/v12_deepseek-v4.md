# 🔬 Analytický Report: DeepSeek-V4-Flash (V12) - Vibe Testing Framework

> **Datum analýzy:** 26. dubna 2026  
> **Datový zdroj:** `experiment_diplomka_v12_20260426_220445.json` + `coverage_deepseek-v4.md`  
> **Analyzováno:** 25 experimentálních běhů (5 úrovní × 5 runů)

---

## 1. Konfigurace a Přehled

### 1.1 Konfigurace experimentu

| Parametr | Hodnota                                   |
|---|-------------------------------------------|
| **LLM model** | `deepseek-v4-flash`                       |
| **API / SUT** | `bookstore` (50 endpointů)                |
| **Teplota** | 0.4                                       |
| **Plánovaný počet testů** | 30 na run                                 |
| **Úrovně kontextu** | L0 – L4 (inkrementální přidávání sekcí)   |
| **Počet runů na úroveň** | 5                                         |
| **Max iterací oprav** | 3                                         |
| **Kompresní pipeline** | Ano (48,1 % úspora na L0 -> 22,6 % na L4) |

### 1.2 Struktura kontextu podle úrovní

| Úroveň | Sekce v kontextu | Est. tokenů | Komprese |
|---|---|---|---|
| **L0** | OpenAPI specifikace | ~15 958 | 48,1 % |
| **L1** | + Technická a byznys dokumentace | ~23 783 | 38,8 % |
| **L2** | + Zdrojový kód endpointů | ~43 917 | 26,2 % |
| **L3** | + Databázové schéma | ~44 770 | 25,8 % |
| **L4** | + Existující testy (ukázka stylu) | ~53 438 | 22,6 % |

### 1.3 Celkové shrnutí

DeepSeek-V4-Flash je **silný a vyzrálý generátor testů, který je proti DeepSeek-Chat výrazně schopnější už na L0**. Napříč 25 běhy dosahuje průměrné validity **98,5 %** a od L3 výše dokonce **stabilních 100 % ve všech runech, vždy napoprvé bez jediné opravy**. Klíčový a kontraintuitivní nález: **přidávání kontextu nepřináší prakticky žádné měřitelné zlepšení**. Code coverage zůstává na plateau okolo 70 % napříč všemi úrovněmi (dokonce s mírnou degradací z 71,2 % na L0 na 69,5 % na L4) a endpoint coverage osciluje mezi 36–48 %. Model nehallucinuje status kódy (0× ve 25 bězích), je extrémně levný ($0,002–$0,005 za run) a generuje krátké, ale syntakticky bezchybné testy. Hlavní slabinou je nízký **assertion depth (~2,0–2,5)** - testy jsou "tenké", model preferuje stručnost před hloubkou ověření. Oproti DeepSeek-Chat je tu jiný profil: **vyšší spolehlivost, nižší závislost na kontextu, ale plošší distribuce assertionů**.

---

## 2. Co se v datech děje (Analýza hlavních metrik)

### 2.1 Validity Rate - Procento úspěšných testů

| Úroveň | Průměr | Min | Max | Runy s 100 % | Stale celkem |
|---|---|---|---|---|---|
| **L0** | **95,33 %** | 90,00 % | 100,0 % | 1/5 | 7 |
| **L1** | **98,00 %** | 93,33 % | 100,0 % | 3/5 | 3 |
| **L2** | **99,33 %** | 96,67 % | 100,0 % | 4/5 | 1 |
| **L3** | **100,00 %** | 100,0 % | 100,0 % | **5/5** | **0** |
| **L4** | **100,00 %** | 100,0 % | 100,0 % | **5/5** | **0** |

**Klíčová zjištění:**

- **L0 už začíná velmi vysoko** (95,33 %) - to je o 4,7 pp víc, než DeepSeek-Chat dosáhl na L0 (90,67 %). Model má silné priority a OpenAPI specifikace mu stačí k tomu, aby v 95 % případů uhodl správné chování API.
- **L1 a L2 přinášejí jen drobný posun** (+2,7 pp, +1,3 pp). Žádný "wow" skok jako u DeepSeek-Chat (kde L0->L1 = +6 pp).
- **L3 a L4 dosahují absolutního stropu** (100 %). Žádný test ve 250 testech (5 runů × 30 testů × 2 úrovně + ostatní) v L3 a L4 nezůstal failed. To je ve V12 unikátní.
- **Stale tests klesají monotónně** (7 → 3 → 1 → 0 → 0). Model od L3 nepotřebuje ani jednu repair iteraci.

### 2.2 First-Shot Pass Rate - klíčová silná stránka v4-flash

| Úroveň | Runů s 30/30 napoprvé | Runů s opravou v 1 iteraci | Runů zaseklých (stale) |
|---|---|---|---|
| **L0** | 1/5 (run1 měl 1 fail, opraveno v iteraci 2) | 0/5 | 4/5 |
| **L1** | 3/5 | 0/5 | 2/5 |
| **L2** | 4/5 | 0/5 | 1/5 |
| **L3** | **5/5** | 0/5 | **0/5** |
| **L4** | **5/5** | 0/5 | **0/5** |

Model **nemá problém "začít správně"** - když má dostatečný kontext, generuje rovnou 30/30 funkčních testů. Tohle je dramatický rozdíl oproti DeepSeek-Chat, kde repair loop často skončil zaseklý a běh selhal s iteracemi 3 (stale).

### 2.3 Endpoint Coverage - L0 paradox je tu ještě výraznější

| Úroveň | Průměr pokrytých EP | Průměr (%) | Min | Max |
|---|---|---|---|---|
| **L0** | **23,8 / 50** | **47,6 %** | 21 | 26 |
| **L1** | 19,0 / 50 | **38,0 %** | 17 | 21 |
| **L2** | 20,4 / 50 | **40,8 %** | 17 | 22 |
| **L3** | 19,2 / 50 | **38,4 %** | 17 | 24 |
| **L4** | 18,4 / 50 | **36,8 %** | 16 | 20 |

**Klíčová zjištění:**

- **L0 má JEDNOZNAČNĚ nejvyšší endpoint coverage** - 47,6 %, což je téměř o 10 pp víc než kterákoli jiná úroveň. Přidání jakéhokoli dalšího kontextu **snižuje šířku pokrytí**.
- **L0 run1 dosáhl 26/50 endpointů (52 %)** - to je absolutní rekord celého experimentu, navíc se 100 % validitou a 100 % compliance.
- **Klesající trend od L1**: čím víc kontextu, tím užší fokus modelu. Tohle je stejný jev jako u DeepSeek-Chat, ale u v4-flash je výraznější protože L0 startuje výš.
- **L4 má nejnižší EP coverage** (36,8 %) - oproti DeepSeek-Chat, kde L4 mělo coverage explozi (44,8 %), tu ukázkové testy nepřinesly žádný rozšiřující efekt. Model už má svůj styl pevně daný a nenechá se inspirovat.

### 2.4 Repair Trajectory - "vymření" repair loopu

**Charakteristický vzorec v4-flash:**

```
L0: stagnace (np. 28p/2f -> 28p/2f -> 28p/2f) NEBO oprava v 1 iteraci
L1-L2: většinou 30p/0f napoprvé, jinak stagnace
L3-L4: VŽDY 30p/0f napoprvé, repair se vůbec nespouští
```

| Úroveň | First-shot pass rate (Ø) | Self-correction rate (Ø) | Iterace (Ø) |
|---|---|---|---|
| L0 | 94,67 % | omezený | 2,8 |
| L1 | 97,33 % | omezený | 1,8 |
| L2 | 98,67 % | omezený | 1,4 |
| L3 | **100,00 %** | n/a (není co opravovat) | **1,0** |
| L4 | **100,00 %** | n/a | **1,0** |

**Self-correction je u v4-flash zásadně lepší než u chat.** Když model fail udělá, často (ne vždy) ho dokáže opravit - např. L0 run1 přešel z 29p/1f na 30p/0f v iteraci 2. Ale pokud se zasekne (ostatní runy L0), zaseknutí je trvalé - model opravuje "do prázdna" stejně jako chat.

**Nikdy neopravené testy (8 unikátních):**

| Test | Výskytů | Příčina |
|---|---|---|
| `test_update_order_status_valid` | 2× (L0) | Špatný status code; chybí znalost state machine objednávek |
| `test_update_stock_valid` / `_success` / `_positive_quantity` | 4× (L0) | Stock update logika - model neví, jaké body vrací |
| `test_update_order_status_invalid_transition_returns_400` | 2× (L1, L2) | Stavový automat objednávek - business logika |
| `test_delete_author_with_books_returns_400` | 1× (L1) | Kaskádové mazání - model očekává jiný status |
| `test_create_book_export_success` | 1× (L0) | Export workflow neznámý bez dokumentace |
| `test_list_authors_pagination_returns_correct_slice` | 1× (L1) | Konkrétní hodnoty v paginaci |

**Pozorování:** Většina nikdy-neopravených testů sídlí na **L0–L2** a téměř vždy v doménách, které model nemůže odvodit ze samotné OpenAPI specifikace (state machine, business pravidla). **Od L3 mizí úplně.**

### 2.5 Token Usage, Komprese a Cena

| Úroveň | Ø Celk. tokeny | Ø Prompt | Ø Completion | Ø Cache hit | Ø Cena (USD) | Ø Cena/passed test |
|---|---|---|---|---|---|---|
| **L0** | 34 559 | 28 221 | 6 338 | 20 480 | **$0,0029** | $0,00010 |
| **L1** | 49 544 | 42 209 | 7 335 | 38 093 | **$0,0027** | $0,00009 |
| **L2** | 78 741 | 72 194 | 6 547 | 65 818 | **$0,0029** | $0,00010 |
| **L3** | 79 126 | 72 794 | 6 332 | 69 990 | **$0,0024** | $0,00008 |
| **L4** | 94 878 | 88 534 | 6 344 | 84 198 | **$0,0026** | $0,00009 |

**Klíčová zjištění:**

- **Celkové tokeny rostou 2,7× z L0 na L4**, ale **completion tokeny zůstávají téměř konstantní** (~6 300–7 300). Model generuje konzistentně krátký výstup bez ohledu na šíři kontextu.
- **Cache hit rate je extrémní** - na L4 je 95 % prompt tokenů cachováno (84 198 / 88 534). Díky tomu reálná cena nepřesáhne $0,005 na běh ani u nejvyšší úrovně.
- **Cena dokonce klesá s vyšším kontextem!** L3 ($0,0024) je nejlevnější, protože má nejvyšší cache hit rate v poměru k tokenům a žádné repair iterace. To je matematický důsledek toho, že L0/L1 občas potřebují drahé repair calls.
- **Cena za passed test je absurdně nízká** ($0,00008–$0,00010) - prakticky neutrální vůči kontextu. v4-flash je z cenového hlediska "level-agnostic".
- **Komprese klesá s kontextem** stejně jako u chat: 48,1 % na L0 → 22,6 % na L4. Strukturovaná OpenAPI spec se komprimuje skvěle, ostatní sekce hůř.

### 2.6 Kvalita testů - Assertion Depth a Response Validation

| Úroveň | Ø Assertion Depth | Ø Response Validation | Ø Avg Lines/test | Ø Side-effect checks |
|---|---|---|---|---|
| **L0** | **2,01** | 68,7 % | 7,7 | 2,0 % |
| **L1** | **2,14** | 60,7 % | 7,7 | 8,0 % |
| **L2** | **2,48** | 89,3 % | 9,7 | 7,3 % |
| **L3** | **2,19** | 85,3 % | 9,1 | 5,4 % |
| **L4** | **2,32** | 93,3 % | 7,0 | 7,3 % |

**Příběh kvality - méně optimistický než u DeepSeek-Chat:**

- **Assertion depth je systematicky nízký** (2,01–2,48). Pro srovnání DeepSeek-Chat na L1 dosahuje 3,39. v4-flash píše "minimální" testy se 2 assertiony - typicky `assert status == X` + jeden další check.
- **L1 má paradoxně nižší response validation než L0** (60,7 % vs 68,7 %). Zkoumáno detailněji v sekci 4.3 - run1 a run3 na L1 mají RV jen 40 % a 47 %, což taží průměr dolů.
- **L2 je peak kvality** - assertion depth 2,48, RV 89,3 %. Zdrojový kód umožňuje modelu validovat strukturu odpovědí.
- **L3 má regresí v RV i depth** - DB schéma nepřináší novou informaci pro testy a model se vrátí ke konzervativnějšímu stylu.
- **L4 má nejvyšší RV (93,3 %), ale nejkratší testy** (7,0 řádků!). Ukázkové testy učí model "stručnému stylu" - asserty jsou konkrétní, ale jich je málo.

**Test type distribution - posun směrem k errorům s rostoucím kontextem:**

| Úroveň | Happy Path | Error | Edge Case |
|---|---|---|---|
| **L0** | **64,0 %** | 33,3 % | 2,7 % |
| **L1** | 60,0 % | 40,0 % | 0,0 % |
| **L2** | 58,0 % | 42,0 % | 0,0 % |
| **L3** | 50,7 % | 49,3 % | 0,0 % |
| **L4** | 48,7 % | **51,3 %** | 0,0 % |

S rostoucím kontextem model přidává více error testů na úkor happy-path. Edge cases ale prakticky mizí od L1 výše - model je "vidí" jen v OpenAPI spec, kde jsou explicitně.

---

## 3. Detailní rozbor Code Coverage

### 3.1 Souhrnná tabulka Coverage podle úrovní

| Úroveň | Celkový Ø | `crud.py` | `main.py` | `__init__`, `database`, `models`, `schemas` |
|---|---|---|---|---|
| **L0** | **71,22 %** | 46,51 % | 71,63 % | Vše 100 % |
| **L1** | 70,72 % | 46,41 % | 70,07 % | Vše 100 % |
| **L2** | 70,80 % | 47,65 % | 68,71 % | Vše 100 % |
| **L3** | 70,33 % | 46,87 % | 68,10 % | Vše 100 % |
| **L4** | **69,49 %** | 45,22 % | 67,42 % | Vše 100 % |

### 3.2 Klíčová anomálie: Coverage MÍRNĚ KLESÁ s rostoucím kontextem

Tohle je **největší rozdíl oproti DeepSeek-Chat**, kde L1 přinesla skok +6 pp (68,15 → 74,45 %). U v4-flash:

```
L0: 71,22 %  →  L1: 70,72 %  →  L2: 70,80 %  →  L3: 70,33 %  →  L4: 69,49 %
                  -0,5 pp        +0,1 pp         -0,5 pp         -0,8 pp
```

Coverage **plynule klesá o 1,7 pp** mezi L0 a L4. Příčina: model už na L0 dosahuje skoro maxima (vidíme to i v EP coverage 47,6 % na L0), a s rostoucím kontextem se zužuje na hlubší testy stejných endpointů, místo aby pokryl víc kódu.

### 3.3 Analýza pokrytí jednotlivých souborů

**`app/__init__.py`, `app/database.py`, `app/models.py`, `app/schemas.py` - vždy 100 %**

Stejně jako u DeepSeek-Chat - tyto soubory jsou pokryté implicitně importem aplikace. Žádná diagnostická hodnota.

**`app/main.py` - klesá z 71,6 % (L0) na 67,4 % (L4)**

Routing kód: pokrytí kopíruje EP coverage. Čím víc se model zaměří na úzký výběr endpointů, tím víc routes zůstává nepokrytých.

**`app/crud.py` - flat curve okolo 45–48 %**

| Úroveň | Ø `crud.py` | Δ vs L0    |
|---|---|------------|
| L0 | **46,51 %** | -          |
| L1 | 46,41 % | -0,10 pp   |
| L2 | **47,65 %** | +1,14 pp   |
| L3 | 46,87 % | +0,36 pp   |
| L4 | 45,22 % | **-1,29 pp** |

Tohle je **diametrálně jiný profil** než u DeepSeek-Chat:

| Soubor | DeepSeek-Chat L0→L1 | DeepSeek-V4-Flash L0→L1 |
|---|---|---|
| `crud.py` | **39,28 % → 56,43 %** (+17,15 pp) | 46,51 % → 46,41 % (**-0,10 pp**) |
| Celkem | 68,15 % → 74,45 % (+6,30 pp) | 71,22 % → 70,72 % (**-0,50 pp**) |

V4-flash začíná silně (46,51 % crud na L0 vs chat 39,28 %), ale **na rozdíl od chat ho byznys dokumentace nedostane výš**. Implikace: v4-flash umí business logiku už ze svých priorů, byznys dokumentace mu nepřidá nic nového.

### 3.4 Které funkce model pokrývá a které ignoruje

**Vždy nebo téměř vždy pokrývané endpointy (přes všech 25 runů):**

| Endpoint | Pokrytí | Poznámka |
|---|---|---|
| `POST /tags` | 23/25 | Nečekaně - chat tuto doménu úplně ignoroval! |
| `POST /books/{id}/cover` | 20/25 | Multipart upload model zvládá |
| `POST /orders` | 20/25 | Business-critical |
| `PUT /authors/{id}` | 18/25 | Klasický update |

**Plus 12 endpointů, které mají 100 % pokrytí ve všech 25 runech (POST/GET/DELETE pro books, authors, atd.).**

**Systematicky ignorované endpointy (0/25 nebo 1/25 runů):**

| Endpoint | Ignorováno | Pravděpodobná příčina |
|---|---|---|
| `DELETE /books/{book_id}/cover` | 25/25 | Subresource - model ji nevidí |
| `DELETE /books/{book_id}/tags` | 25/25 | Tag-relation operace |
| `DELETE /orders/{order_id}` | 25/25 | Model neví, zda jsou objednávky mazatelné |
| `GET /admin/maintenance` | 25/25 | Admin doména - out-of-scope |
| `GET /catalog` | 25/25 | Agregovaný read - model preferuje primární CRUD |
| `GET /exports/{job_id}` | 25/25 | Async workflow |
| `GET /orders` | 25/25 | Listing endpoint - model nevolí |
| `GET /statistics/summary` | 25/25 | Analytický endpoint |
| `GET /tags` | 25/25 | List tags - ignorováno |
| `POST /exports/orders` | 25/25 | Async export |
| `POST /reset` | 25/25 | Setup endpoint - model ho nezná |
| `PUT /tags/{tag_id}` | 25/25 | Update tagu - ignorováno |

**Pozorování:** v4-flash má **stejné slepé skvrny jako chat** (kategorie, tagy, exporty, admin), s drobným rozdílem - `POST /tags` občas otestuje (23/25), což chat dělal vzácně.

### 3.5 Rozptyl Coverage v rámci úrovní

| Úroveň | Min celk. | Max celk. | Spread | Min `crud.py` | Max `crud.py` | Spread |
|---|---|---|---|---|---|---|
| L0 | 70,37 % | 72,35 % | **1,98 pp** | 44,96 % | 49,61 % | 4,65 pp |
| L1 | 69,18 % | 71,75 % | 2,57 pp | 41,34 % | 49,87 % | 8,53 pp |
| L2 | 68,78 % | 72,84 % | 4,06 pp | 43,67 % | 52,45 % | 8,78 pp |
| L3 | 67,10 % | 72,05 % | 4,95 pp | 37,73 % | 50,13 % | **12,40 pp** |
| L4 | 66,80 % | 71,46 % | 4,66 pp | 37,73 % | 50,39 % | **12,66 pp** |

**Paradox:** Stejně jako u chat, **L0 je nejstabilnější** (spread 1,98 pp). Ale u v4-flash je rozptyl na L3/L4 výrazně vyšší (12,4 pp v crud.py!) - model i přes 100 % validitu generuje mezi runy velmi odlišné sady testů. Jeden run může pokrýt 50 % crud.py, jiný jen 37 %.

---

## 4. Proč se to děje? (Kauzalita a obhajoba)

### 4.1 Proč u v4-flash neexistuje "L1 inflexní bod"

Hlavní zjištění tohoto experimentu: **DeepSeek-V4-Flash má oproti DeepSeek-Chat výrazně silnější priors pro REST API testování**. Důsledek:

1. **OpenAPI spec (L0) modelu STAČÍ** - dokáže z ní odvodit nejen syntax, ale i běžnou business logiku (CRUD vztahy, validace, autentizace). Validity 95,33 %, EP coverage 47,6 %, crud.py coverage 46,51 % - všechno startuje vysoko.

2. **Byznys dokumentace (L1) duplikuje co model už ví.** Pro chat byla L1 zjevení (+17 pp v crud.py), pro v4-flash je to **ztráta 0,1 pp**. Model už znal pravidla z OpenAPI + svých interních priorů.

3. **Zdrojový kód (L2) přidá nejmenší možný benefit** - +1,2 pp v crud coverage, +0,2 pp v RV. Ale za cenu 35k extra prompt tokenů.

4. **DB schéma (L3) je úplně irelevantní** stejně jako u chat - 844 tokenů zbytečných, žádné měřitelné zlepšení.

5. **Ukázkové testy (L4) způsobují mírnou regresi** - assertion depth +0,1, ale total coverage -0,84 pp, EP coverage -1,6 pp. Model "se zarovná" na styl ukázkových testů a ztratí svou počáteční šíři.

**Závěr:** Pro v4-flash je **L0 (čistá OpenAPI spec) nejlepší volbou** z hlediska coverage poměru k nákladům. L3 je nejlepší volbou z hlediska validity + 100 % first-shot pass rate. L4 nepřináší nic.

### 4.2 Proč Endpoint Coverage tak dramaticky klesá z L0 (47,6 %) na L4 (36,8 %)

Když model na L0 vidí jen seznam endpointů bez kontextu, nemá žádné "preference" - rozprostře 30 testů široce, často 1 test = 1 endpoint. Na L0 se průměrně dotkne 23,8 endpointů.

Jakmile dostane byznys kontext (L1+), pochopí, že **knihy a autoři jsou "important"**, **tagy a kategorie jsou "side"**, **exporty a admin jsou "out-of-scope"**. Začne soustředit více testů na klíčové entity - testuje stejné endpointy s 2-3 variantami (happy + error), čímž se EP coverage zúží na 19-20 endpointů. To je klasický **breadth/depth trade-off** v rámci fixního test budgetu (30 testů).

### 4.3 Anomálie a jejich vysvětlení

**Anomálie 1: L0 run5 - nejnižší validity (90 %) a nejvyšší EP coverage v L0 (25/50)**

Run5 na L0 obětoval validitu za šířku - 3 stale testy zahrnuly `test_create_book_export_success` (export workflow se na L0 nedá uhodnout), `test_update_order_status_valid` a `test_update_stock_positive_quantity`. Bez kontextu o stavovém automatu objednávek a stock logice se model "trefil" špatně a v repair loopu nenašel cestu ven.

**Anomálie 2: L1 run1 a run3 - propad response validation na 40 % a 47 %**

| Metrika | L1 run1 | L1 run3 | Pozn. |
|---|---|---|---|
| Validity | 96,67 % | 100,0 % | OK |
| Response Validation | **40,0 %** | **46,7 %** | propad |
| Avg lines/test | 9,2 | 7,0 | krátké testy |

Tyto dva runy generovaly **velmi krátké testy** s jen status code assertem (bez kontroly těla). To stahuje L1 RV průměr na 60,7 %, paradoxně **pod L0** (68,7 %). Příčina není jasná - jiné L1 runy (run4, run5) mají RV 83 %. Pravděpodobně náhodný vzorec - model na teplotě 0,4 občas spadne do "minimálního" stylu.

**Anomálie 3: L1 run2 - elapsed time 177,6 s (vs Ø 105 s)**

Stejný jev jako u DeepSeek-Chat L1 run2 (104 minut tam!) - velmi pravděpodobně **rate-limiting nebo dočasný API problém**. Validity (93,33 %) i pass rate (28/30) byly normální, jen latence 1,7× vyšší. Není to chyba modelu.

**Anomálie 4: Compliance score 80 % na L3 run1, run5 a L4 run1, run5**

| Run | Compliance | Příčina |
|---|---|---|
| L3 run1 | 80 | 40 HTTP volání bez timeout |
| L3 run5 | 80 | 44 HTTP volání bez timeout |
| L4 run1 | 80 | 5 z 40 volání bez timeout |
| L4 run5 | 80 | Nepoužívá unique_helper, 0 timeout violations |

Většina případů: model **přestal používat helper funkci s timeoutem** a začal volat `requests.get()` přímo. Toto se děje od L3 - hypotéza: ve velkém kontextu model "zapomene" na coding conventions a vrátí se k základnímu Python stylu. Není to bug v testech (pořád projdou), ale porušení framework guidelines.

**Anomálie 5: L3 run1 - nejnižší code coverage celého experimentu (67,10 %)**

Tento run pokryl jen 17/50 endpointů (34 %) a `crud.py` jen 37,73 %. I přes 100 % validitu a first-shot pass model **soustředil všechny testy na velmi úzký výběr** (16 happy / 14 error / 0 edge), který nepokryl typické crud cesty. To je důsledek nedeterminismu v plánovači - jiný "seed" by zvolil jinou strategii.

**Anomálie 6: L4 run5 - 9 happy / 21 error testů**

Jediný L4 run, kde error testy dramaticky převažují. Model se inspiroval ukázkovými testy a posunul distribuci. Status code diversity dosáhla 11 (nejvíc v L4). Je to opačný jev než L4 run1, kde poměr je vyrovnaný 15/15.

### 4.4 Status Code Hallucinations - žádné

| Metrika | Hodnota |
|---|---|
| Runů s halucinovaným status kódem | **0/25** |
| Runů se status code drift | 2/25 (L0 run2, L1 run4) |

**v4-flash nikdy nepoužije status kód, který by nebyl v kontextu.** To je velmi silná stránka - DeepSeek-Chat měl podobný profil, ale v4-flash to potvrdil ještě výrazněji. Drift (rozdíl mezi plánem a kódem) se objevil jen ve 2 případech a vždy v rámci validních HTTP kódů.

### 4.5 Kauzální model chování DeepSeek-V4-Flash

```
Kontext ↑  ->  Validity ↑ (až do plateau 100 % od L3)
           ->  Šířka pokrytí ↓ (model se soustředí na "důležité" endpointy)
           ->  Code coverage ~konstantní (mírná degradace L0->L4)
           ->  Cena ~konstantní (díky 95% cache hit rate)
           ->  Repair loop se VYPÍNÁ od L3 (není co opravovat)
           ->  Test depth zůstává nízký (assertion depth ~2,2 nezávisle na úrovni)
```

Klíčový insight: **v4-flash má "ceiling" už na L0**. Přidávání kontextu jen mění **distribuci kvality** (víc validity, míň šířky), ne celkovou hodnotu. Pro tento model je optimální strategie:

- **Optimalizace nákladů + šířky:** L0 (47,6 % EP, 71,2 % cov, $0,003)
- **Optimalizace spolehlivosti:** L3 (100 % validity, 100 % first-shot, $0,002)
- **L4 nedoporučuji** - žádný benefit, vyšší náklady, mírná regrese coverage

### 4.6 Srovnání s DeepSeek-Chat - profilová matice

| Charakteristika | DeepSeek-Chat | DeepSeek-V4-Flash |
|---|---|---|
| L0 validity | 90,67 % | **95,33 %** |
| Peak validity | 98,0 % (L2) | **100,0 % (L3, L4)** |
| L0 EP coverage | 40,8 % | **47,6 %** |
| L0 crud.py coverage | 39,28 % | **46,51 %** |
| L1 inflexion | **+17 pp v crud.py** | -0,1 pp v crud.py |
| L1 assertion depth jump | **2,34 → 3,39** | 2,01 → 2,14 |
| Stale tests celkem | 33 napříč úrovněmi | **11 napříč úrovněmi** |
| Repair loop efektivita | Slabá (18/25 zaseklých) | Silná (4/25 zaseklých) |
| Hallucinace status kódů | 0 | 0 |
| Cena typického runu | $0,005–$0,013 | **$0,002–$0,005** |
| L4 regrese | Ano (29p/1f → 27p/3f) | Ne (vždy 30p/0f) |
| Závislost na kontextu | Vysoká | **Nízká** |
| Assertion depth typický | 2,3–3,4 | 2,0–2,5 |

**Shrnutí:** v4-flash je **vyzrálejší, spolehlivější, levnější, ale "tencí"** - generuje minimalistické testy s nižší assertion density. Chat dělá hlubší testy, ale za cenu vyšší míry chyb a stale testů.

---

## 5. Detailní rozpis jednotlivých úrovní a běhů

<details>
<summary><strong>📊 L0 - Pouze OpenAPI specifikace (Ø validity 95,33 %, Ø EP 47,6 %, Ø coverage 71,22 %)</strong></summary>

### Komentář k L0

L0 je u v4-flash **paradoxně nejlepší úroveň pro endpoint coverage** (47,6 %, peak 52 % v run1). Model dostává jen ~16k tokenů komprimované OpenAPI specifikace a generuje široce rozprostřené testy. Validita je už zde 95,33 %, což je podobně jako chat dosáhne až na L1. Hlavní slabost: čtyři z pěti runů skončí early-stopped se stale testy v doméně order/stock workflow, které model nedokáže odvodit ze samotné spec.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | 93,33 % | 96,67 % | 96,67 % | 90,0 % |
| **Passed/Total** | **30/30** | 28/30 | 29/30 | 29/30 | 27/30 |
| **EP Coverage** | **26/50** | 21/50 | 24/50 | 23/50 | 25/50 |
| **Stale tests** | **0** | 2 | 1 | 1 | 3 |
| **Assertion Depth** | 1,87 | 2,00 | 1,90 | 2,10 | **2,17** |
| **Resp. Validation** | 50,0 % | 73,3 % | 66,7 % | **76,7 %** | **76,7 %** |
| **Cena (USD)** | $0,0039 | $0,0027 | $0,0025 | $0,0026 | $0,0028 |
| **Celk. tokeny** | 32 696 | 35 142 | 34 190 | 34 976 | 35 791 |
| **Iterace** | **2 (OK)** | 3 (stale) | 3 (stale) | 3 (stale) | 3 (stale) |
| **Status Diversity** | 12 | 7 | 8 | 6 | 12 |
| **Happy/Error/Edge** | 12/15/3 | 21/9/0 | 23/7/0 | 23/6/1 | 17/13/0 |
| **Code Cov. celk.** | 71,46 % | 70,47 % | 71,46 % | **72,35 %** | 70,37 % |
| **Code Cov. crud.py** | 46,25 % | 45,48 % | 46,25 % | **49,61 %** | 44,96 % |

**Run1 je referenční:** Jediný L0 run s 30/30 a navíc rekordní 26/50 EP coverage - **52 %, absolutní rekord celého experimentu**. Validita opravena z 29p/1f napoprvé.

**Nejčastější chyby L0:** `wrong_status_code` (3×), `assertion_value_mismatch` (3×). Stale testy konzistentně v `test_update_stock_*` a `test_update_order_status_*` - obě domény vyžadují business logiku, která v OpenAPI není.

</details>

<details>
<summary><strong>📊 L1 - + Byznys dokumentace (Ø validity 98,00 %, Ø EP 38,0 %, Ø coverage 70,72 %)</strong></summary>

### Komentář k L1

Přidání byznys dokumentace (+7 825 tokenů) přináší **mírné zlepšení validity** (95,33 → 98 %), ale **regresi v EP coverage** (47,6 → 38 %) a **regresi v code coverage** (71,22 → 70,72 %). Tři z pěti runů dosáhnou 100 % validity a procházejí napoprvé. Paradoxně **L1 má nejnižší response validation** (60,7 %) díky run1 a run3, kde model vygeneroval velmi krátké testy.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 96,67 % | 93,33 % | **100,0 %** | **100,0 %** | **100,0 %** |
| **Passed/Total** | 29/30 | 28/30 | **30/30** | **30/30** | **30/30** |
| **EP Coverage** | 17/50 | **21/50** | 20/50 | 17/50 | 20/50 |
| **Stale tests** | 1 | 2 | **0** | **0** | **0** |
| **Assertion Depth** | 2,23 | 2,00 | 1,93 | 2,23 | **2,33** |
| **Resp. Validation** | **40,0 %** | 50,0 % | 46,7 % | **83,3 %** | **83,3 %** |
| **Cena (USD)** | $0,0027 | $0,0045 | $0,0021 | $0,0021 | $0,0022 |
| **Celk. tokeny** | 51 161 | 58 620 | 45 984 | 45 893 | 46 062 |
| **Iterace** | 3 (stale) | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Status Diversity** | 10 | 10 | 10 | 10 | 10 |
| **Happy/Error/Edge** | 16/14/0 | 21/9/0 | 20/10/0 | 17/13/0 | 16/14/0 |
| **Code Cov. celk.** | 71,75 % | 69,47 % | 71,46 % | 69,18 % | **71,75 %** |
| **Code Cov. crud.py** | 49,87 % | 43,93 % | 48,06 % | 41,34 % | **48,84 %** |

**Run2 anomálie elapsed time:** 177,6 s vs průměr 79–106 s. Pravděpodobně API rate-limit nebo dočasný problém na straně DeepSeek - model fungoval normálně, jen latence třikrát vyšší.

**Stagnace stale testů:** L1 run1 - `test_update_order_status_invalid_transition_returns_400` (3 iterace beze změny). L1 run2 - `test_delete_author_with_books_returns_400` a paginační test - i s byznys dokumentací model neuhodne přesnou hodnotu nebo cascading rule.

</details>

<details>
<summary><strong>📊 L2 - + Zdrojový kód endpointů (Ø validity 99,33 %, Ø EP 40,8 %, Ø coverage 70,80 %)</strong></summary>

### Komentář k L2

Přidání zdrojového kódu (+20 123 tokenů) přináší **peak před plateau** - 4/5 runů 100 % validity (rekord), peak response validation (89,3 %) a peak assertion depth (2,48). Code coverage se ale prakticky nepohne (70,80 % vs L1 70,72 %). Model čte implementaci a generuje hlubší assertce, ale stále se drží úzkého výběru endpointů.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | 96,67 % | **100,0 %** | **100,0 %** | **100,0 %** |
| **Passed/Total** | **30/30** | 29/30 | **30/30** | **30/30** | **30/30** |
| **EP Coverage** | 20/50 | 17/50 | **22/50** | 21/50 | **22/50** |
| **Stale tests** | **0** | 1 | **0** | **0** | **0** |
| **Assertion Depth** | 2,27 | 2,20 | **2,73** | 2,53 | 2,67 |
| **Resp. Validation** | 83,3 % | **93,3 %** | **93,3 %** | 83,3 % | **93,3 %** |
| **Cena (USD)** | $0,0047 | $0,0026 | $0,0025 | $0,0024 | $0,0024 |
| **Celk. tokeny** | 78 356 | 81 399 | 78 143 | 77 944 | 77 861 |
| **Iterace** | **1 (OK)** | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Status Diversity** | 10 | 10 | 8 | 9 | **11** |
| **Happy/Error/Edge** | 20/10/0 | 14/16/0 | 21/9/0 | 21/9/0 | 11/19/0 |
| **Code Cov. celk.** | 69,97 % | 68,78 % | **72,84 %** | 72,15 % | 70,27 % |
| **Code Cov. crud.py** | 43,67 % | 44,44 % | **52,45 %** | 48,58 % | 49,10 % |

**Run3 je referenční:** Highest assertion depth (2,73), 22/50 EP coverage, 100 % validity napoprvé, peak crud.py coverage (52,45 %). Optimální L2 výstup.

**Run2 - jediný stale na L2:** `test_update_order_status_invalid_transition_returns_400`. Stejný test, který se zasekl i na L1 run1. **State machine objednávek je systematická slepá skvrna** - ani zdrojový kód model nedovede k její opravě.

</details>

<details>
<summary><strong>📊 L3 - + Databázové schéma (Ø validity 100,00 %, Ø EP 38,4 %, Ø coverage 70,33 %)</strong></summary>

### Komentář k L3

L3 je **nejvýznamnější bod experimentu pro v4-flash** - **všech 5 runů dosáhne 100 % validity napoprvé bez jediné repair iterace**. Žádný stale test, žádné fail-loops. Cena je nejnižší ze všech úrovní ($0,0024) díky 88% cache hit rate a absenci repair calls. Code coverage paradoxně mírně klesne (70,33 % vs L2 70,80 %) - DB schéma nepřináší novou informaci pro testy. **L3 je zlatý bod** experimentu pro tento model.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | **100,0 %** | **100,0 %** | **100,0 %** | **100,0 %** |
| **Passed/Total** | **30/30** | **30/30** | **30/30** | **30/30** | **30/30** |
| **EP Coverage** | 17/50 | **24/50** | 18/50 | 19/50 | 18/50 |
| **Stale tests** | **0** | **0** | **0** | **0** | **0** |
| **Assertion Depth** | 2,13 | 2,07 | **2,33** | 2,23 | 2,20 |
| **Resp. Validation** | 80,0 % | 83,3 % | **93,3 %** | 86,7 % | 83,3 % |
| **Cena (USD)** | $0,0024 | $0,0024 | $0,0024 | $0,0023 | $0,0023 |
| **Celk. tokeny** | 78 917 | 79 240 | 79 347 | 79 080 | 79 047 |
| **Iterace** | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Status Diversity** | 10 | **12** | 10 | 9 | 8 |
| **Happy/Error/Edge** | 16/14/0 | 8/22/0 | 17/13/0 | 17/13/0 | 18/12/0 |
| **Compliance** | **80** | 100 | 100 | 100 | **80** |
| **Code Cov. celk.** | **67,10 %** | **72,05 %** | 70,66 % | 70,86 % | 70,96 % |
| **Code Cov. crud.py** | **37,73 %** | **50,13 %** | 48,06 % | 49,10 % | 49,35 % |

**Run2 anomálie - error-heavy distribuce:** 8 happy / 22 error / 0 edge - jediný L3 run s tak silným error fokusem. Důsledek: nejvyšší EP coverage L3 (24/50), nejvyšší crud.py coverage L3 (50,13 %), nejvyšší status code diversity (12). Když model jde do šířky errorů, pokryje víc kódu.

**Run1 anomálie - nejnižší coverage celého experimentu:** 67,10 % total, 37,73 % crud.py. Model má 100 % validity, ale soustředil se na 17/50 endpointů a vyhnul se klíčovým CRUD cestám. Compliance navíc 80 % (40 HTTP volání bez timeout). Klasický příklad **"correct but narrow"** běhu.

**Compliance score 80 % na run1 a run5:** Model přestává používat helper funkci s timeoutem - 40+ čistých `requests.get()` bez timeout. Hypotéza: ve velkém kontextu (44k+ tokenů) se ztrácí coding conventions z system promptu.

</details>

<details>
<summary><strong>📊 L4 - + Ukázkové testy (Ø validity 100,00 %, Ø EP 36,8 %, Ø coverage 69,49 %)</strong></summary>

### Komentář k L4

L4 udržuje **100 % validitu ve všech runech**, ale přináší **mírnou regresi všech ostatních metrik**: nejnižší EP coverage (36,8 %), nejnižší celkové code coverage (69,49 %), nejkratší testy (avg 7,0 řádků). Model se "zarovná" na styl ukázek a ztratí svou počáteční šíři. **Žádný benefit oproti L3** - jen větší prompt, vyšší cena, horší coverage. Pozitivum: response validation je nejvyšší (93,3 %) - model se z ukázek naučil, jak ověřovat odpovědi.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | **100,0 %** | **100,0 %** | **100,0 %** | **100,0 %** |
| **Passed/Total** | **30/30** | **30/30** | **30/30** | **30/30** | **30/30** |
| **EP Coverage** | **16/50** | 20/50 | 18/50 | 18/50 | 20/50 |
| **Stale tests** | **0** | **0** | **0** | **0** | **0** |
| **Assertion Depth** | 2,40 | 2,23 | 2,30 | **2,53** | 2,13 |
| **Resp. Validation** | 93,3 % | 90,0 % | 93,3 % | **96,7 %** | 93,3 % |
| **Cena (USD)** | $0,0037 | $0,0023 | $0,0025 | $0,0023 | $0,0023 |
| **Celk. tokeny** | 95 566 | 94 430 | 95 211 | 94 487 | 94 694 |
| **Iterace** | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Status Diversity** | 10 | 9 | 8 | 9 | **11** |
| **Happy/Error/Edge** | 15/15/0 | 20/10/0 | 15/15/0 | 14/16/0 | 9/21/0 |
| **Compliance** | **80** | 100 | 100 | 100 | **80** |
| **Code Cov. celk.** | **66,80 %** | **71,46 %** | 67,99 % | 70,47 % | 70,76 % |
| **Code Cov. crud.py** | **37,73 %** | **50,39 %** | 42,89 % | 47,29 % | 47,80 % |

**Run1 je nejhorší celého experimentu:** Pokrytí 16/50 EP (jen 32 %!), code coverage 66,80 % - nejnižší L4. Compliance 80 %. Model zde nejvíc zúžil scope a "podlehl" stylu ukázkových testů. I přes 100 % validitu je to nejméně užitečný výstup.

**Run5 je extrém v error-heavy stylu:** 9 happy / 21 error - opačný profil než run2 (20/10). Status diversity 11 (nejvíc L4). Inspirace ukázkovými testy v error-prone stylu.

**Run2 dosahuje nejlepšího L4 výsledku:** 71,46 % coverage (na úrovni L0 maxima!), 50,39 % crud.py, 20/50 EP. Ukazuje, že L4 *může* fungovat, ale je to lottery.

**Compliance regrese:** Run1 (5 timeout violations z 40), Run5 (přestal používat unique_helper úplně). Stejný problém jako L3 - velký kontext zhoršuje dodržování coding conventions.

</details>

---

## Závěrečné shrnutí pro obhajobu

### Hlavní příběh dat

**DeepSeek-V4-Flash je vyzrálý, vysoce spolehlivý model, jehož chování je téměř nezávislé na velikosti přidaného kontextu.** Klíčové zjištění je, že **na rozdíl od DeepSeek-Chat zde neexistuje "L1 inflexní bod"** - model dosahuje silných výsledků už na L0 (95 % validity, 47,6 % EP coverage, 71,2 % code coverage) a další úrovně přinášejí jen marginální zlepšení validity (až do plateau 100 % na L3) za cenu zúžení šířky pokrytí. **Optimální strategie pro tento model: L0 pro maximalizaci coverage/cena poměru, L3 pro maximalizaci spolehlivosti, L4 nedoporučeno.**

### Čísla pro obhajobu

| Tvrzení | Podpora v datech                                                           |
|---|----------------------------------------------------------------------------|
| Model má silné priors a OpenAPI spec mu stačí | L0: 95,33 % validity, 47,6 % EP coverage, 46,5 % crud.py - výrazně lepší než chat na L0 |
| Přidávání kontextu má diminishing returns | Coverage L0→L4: 71,22 % → 69,49 % (mírná **regrese**); EP coverage 47,6 % → 36,8 % (-22 %) |
| L3 je optimální bod pro spolehlivost | 100 % validity ve všech 5 runech, 0 stale tests, 100 % first-shot pass rate |
| Repair loop je u v4-flash funkční (oproti chat) | L0 run1: 29p/1f → 30p/0f v iteraci 2; ale od L3 vůbec není potřeba |
| Model nehallucinuje | 0/25 runů s halucinovaným status kódem; jen 2/25 runů s drift |
| Cena je extrémně nízká a level-agnostic | $0,002–$0,005 za run; cena/passed test ≈ $0,00009 napříč úrovněmi |
| Slabina: nízký assertion depth | 2,01–2,48 (vs DeepSeek-Chat 2,34–3,39); minimalistický styl testů |
| Stejné slepé skvrny jako chat | 12 endpointů 0 % pokrytí napříč všemi runy: kategorie, tagy, exporty, admin |
| L4 nemá benefit pro v4-flash | Žádné zlepšení validity (100 % už od L3), regrese coverage (-0,84 pp) a EP (-1,6 pp) |
| Velký kontext zhoršuje compliance | Compliance 80 % v 4/10 runů na L3-L4 (timeout missing, helper neused) |

### Doporučení pro budoucí experimenty

1. **Pro v4-flash používat L0 nebo L3** - mezi tím není výrazný benefit, jen narůstající náklady.
2. **Zvýšit test budget z 30 na 50+** - aktuálně model "naráží" na 30-test limit a obětuje šířku za hloubku. Vyšší budget by ukázal skutečnou kapacitu.
3. **Doplnit explicitní instrukce pro pokrytí "side" domén** (kategorie, tagy, exporty) - tyto entity jsou systematicky ignorované, model je nepovažuje za testovatelné.
4. **Otestovat assertion depth boost** - dodat instrukci typu "min 3 assertions per test" a sledovat, zda se assertion depth posune nahoru bez ztráty validity.
5. **Vyšetřit compliance regresi na L3-L4** - je to systematický problém s prompt engineeringem (coding conventions se ztrácí ve velkém kontextu) nebo náhoda?