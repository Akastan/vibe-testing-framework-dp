# 🔬 Analytický Report: Claude Haiku 4.5 (V12) - Vibe Testing Framework

> **Datum analýzy:** 24. dubna 2026  
> **Datový zdroj:** `experiment_diplomka_v12_20260424_160040.json` + `coverage_v12_claude.md`  
> **Analyzováno:** 25 experimentálních běhů (5 úrovní × 5 runů)

---

## 1. Konfigurace a Přehled

### 1.1 Konfigurace experimentu

| Parametr | Hodnota                                      |
|---|----------------------------------------------|
| **LLM model** | `claude-haiku-4-5-20251001`                  |
| **API / SUT** | `bookstore` (50 endpointů)                   |
| **Teplota** | 0.4                                          |
| **Plánovaný počet testů** | 30 na run                                    |
| **Úrovně kontextu** | L0 – L4 (inkrementální přidávání sekcí)      |
| **Počet runů na úroveň** | 5                                            |
| **Max iterací oprav** | 3 (early-stopped ve všech případech selhání) |
| **Kompresní pipeline** | Ano (48,1 % úspora na L0 -> 22,6 % na L4)    |

### 1.2 Struktura kontextu podle úrovní

| Úroveň | Sekce v kontextu | Est. tokenů | Komprese |
|---|---|---|---|
| **L0** | OpenAPI specifikace | ~15 958 | 48,1 % |
| **L1** | + Technická a byznys dokumentace | ~23 783 | 38,8 % |
| **L2** | + Zdrojový kód endpointů | ~43 917 | 26,2 % |
| **L3** | + Databázové schéma | ~44 770 | 25,8 % |
| **L4** | + Existující testy (ukázka stylu) | ~53 438 | 22,6 % |

### 1.3 Celkové shrnutí

Claude Haiku 4.5 je v tomto experimentu **mimořádně spolehlivý first-shot generátor testů**. Průměrná validity napříč 25 běhy činí **99,2 %** a ani jednou neklesne pod 93 %. Klíčový nález: **21 z 25 runů dosáhlo 100 % validity už v 1. iteraci** (bez jediné opravy). To je fundamentálně jiný režim chování, než u DeepSeek-Chat.

Kontext modelu spíše **prohlubuje kvalitu** testů než rozšiřuje jejich záběr. Endpoint Coverage osciluje v úzkém pásmu **27–34 %** a nikdy nepřekročí 38 %. Response validation ale dramaticky stoupá z 50 % (L0) na 91 % (L4). Assertion depth z 2,13 na 2,73. Inflekční bod je tentokrát **L2 (zdrojový kód)**, kde skok v response validation činí +40 p.b.

Kontraintuitivní zjištění v Code Coverage: **L0 má nejvyšší pokrytí `crud.py`** (40,72 %), pak paradoxně klesá na L1–L3 (~36 %) a mírně se vrací na L4 (38 %). Důvod: v základním režimu model testuje širší paletu endpointů, ale mělčeji - což procentuálně pokryje víc kódu. Od L1 se soustředí na méně endpointů s hlubší validací.

Model je **výrazně dražší než DeepSeek** ($0,055–$0,160 za run, tj. 10–15× více), ale za to nabízí first-shot spolehlivost. Systematicky ignoruje celé doménové oblasti API (**objednávky, tagy, admin, exporty**) - ve 25 bězích nepokryl **ani jednou** 23 z 50 endpointů.

---

## 2. Co se v datech děje (Analýza hlavních metrik)

### 2.1 Validity Rate - Procento úspěšných testů

| Úroveň | Průměr | Min | Max | Runy s 100 % | Stale celkem |
|---|---|---|---|---|---|
| **L0** | **98,67 %** | 93,33 % | 100,0 % | 4/5 | 2 |
| **L1** | **99,33 %** | 96,67 % | 100,0 % | 4/5 | 1 |
| **L2** | **99,33 %** | 96,67 % | 100,0 % | 4/5 | 1 |
| **L3** | **99,33 %** | 96,67 % | 100,0 % | 4/5 | 1 |
| **L4** | **99,33 %** | 96,67 % | 100,0 % | 4/5 | 1 |

**Klíčová zjištění:**

- **Validity je konzistentně velmi vysoká** napříč všemi úrovněmi. Rozdíl mezi L0 (98,67 %) a L1–L4 (99,33 %) je statisticky malý (jen 1 test z 30 navíc).
- **L0 je jediná úroveň s runem pod 100 %** kromě jednoho stale případu na vyšších levelech (viz 2.3). Run1 na L0 má validity 93,33 % a 2 stale testy - model hádá chování rate-limited discount endpointu a stock update bez byznys kontextu.
- **Úrovně L1–L4 jsou prakticky identické** v agregované validitě. Všechny mají přesně 1 stale test rozložený vždy do 1 runu (konkrétně: L1 run1, L2 run2, L3 run5, L4 run1). Ostatních 16 runů na L1–L4 projde 30/30 napoprvé.
- **Tohle je unikátní pattern Claude Haiku** - model má tak vysoký baseline, že přidaný kontext už nemá prostor validitu zlepšovat. Namísto toho zlepšuje *kvalitu* testů (viz 2.5).

### 2.2 Endpoint Coverage

| Úroveň | Průměr pokrytých EP | Průměr (%) | Min | Max |
|---|---|---|---|---|
| **L0** | 17,2 / 50 | **34,4 %** | 15 | 19 |
| **L1** | 14,2 / 50 | **28,4 %** | 13 | 15 |
| **L2** | 13,8 / 50 | **27,6 %** | 13 | 15 |
| **L3** | 14,2 / 50 | **28,4 %** | 12 | 16 |
| **L4** | 15,6 / 50 | **31,2 %** | 14 | 17 |

**Klíčová zjištění - stejný kontraintuitivní vzorec jako u DeepSeek, ale výraznější:**

- **L0 má nejlepší endpoint coverage celého experimentu.** Bez byznys kontextu model "rozpráší" svých 30 testů široce a zasáhne 17 endpointů v průměru. Run1 a run4 dokonce pokryly 19/50.
- **L1–L3 spadnou pod 30 %.** Byznys dokumentace a zdrojový kód vedou model k hlubšímu testování **menšího okruhu endpointů** (zhruba 14). Místo šířky získáváme hloubku - což se pozitivně projeví v assertion depth a response validation (viz 2.5).
- **L4 se vrací na 31,2 %** - ukázkové testy dodají modelu konkrétní vzory pro širší spektrum endpointů, takže se záběr mírně rozšíří.
- **Inherentní limit:** 30 testů dělených mezi happy_path, error a edge_case scénáři na 50 endpointech dává matematické maximum ~60 % coverage. Claude zůstává výrazně pod tímto stropem.
- **Rozptyl na L1–L2 je extrémně nízký** (std = 0,84, spread 2 endpointy). Model velmi konzistentně vybírá přibližně stejnou sadu endpointů. Na L3–L4 se rozptyl zvětší - model má víc vodítek a trochu experimentuje.

### 2.3 Staleness a bludné kruhy

**Repair trajectory - diametrálně odlišný pattern od DeepSeek:**

Claude Haiku vykazuje **extrémně vysokou first-shot pass rate**. Z 25 běhů model ve **21 případech** generuje 30/30 passing testů hned v 1. iteraci bez potřeby jakékoli opravy. To se promítá do této distribuce:

| Úroveň | Runů s 1. iterací OK | Runů s opravným loopem |
|---|---|---|
| L0 | **4/5** | 1 (run1) |
| L1 | **4/5** | 1 (run1) |
| L2 | **4/5** | 1 (run2) |
| L3 | **4/5** | 1 (run5) |
| L4 | **4/5** | 1 (run1) |

**Ve všech 4 případech, kdy repair loop proběhne, model selhává úplně stejně:**

```
iterace 1: 29p/1f (nebo 28p/2f) 
  -> iterace 2: 29p/1f (repair typ: helper_fallback, nic nezměněno) 
  -> iterace 3: 29p/1f (all_stale_early_stop)
```

Stav passed/failed se **ani jednou nezmění**. Metrika `self_correction_rate_pct = 0,0 %` platí **pro všech 25 runů**. Model nikdy během experimentu neopravil svoji chybu - buď uspěl napoprvé, nebo neuspěl vůbec.

**Rozdíl oproti DeepSeek:** DeepSeek se dostává do repair loopu ve většině runů (18/25), kde stagnuje. Claude se do repair loopu dostane jen v 4/25 runů - ale jakmile se tam dostane, chová se stejně (nulová self-correction).

**Seznam stale testů ve všech 6 případech:**

| Test | Úroveň | Kategorie chyby |
|---|---|---|
| `test_apply_discount_rate_limit` | L0 run1, L1 run1 | wrong_status_code |
| `test_update_stock_success` | L0 run1 | assertion_value_mismatch |
| `test_apply_discount_exceeds_rate_limit` | L2 run2 | wrong_status_code |
| `test_restore_deleted_book_success` | L3 run5 | assertion_value_mismatch |
| `test_discount_rate_limit_exceeded` | L4 run1 | wrong_status_code |

**Vzorec v datech jasný:** 4 ze 6 stale testů jsou varianty stejného konceptu - **rate-limit na POST /books/{id}/discount**. Model i s plným kontextem nedokáže správně predikovat chování tohoto jednoho endpointu. Ostatní 2 se týkají soft-delete / restore workflow.

### 2.4 Token Usage, Komprese a Cena

| Úroveň | Ø Celk. tokeny | Ø Prompt | Ø Completion | Ø Cache hit | Ø Cena (USD) | Ø Cena/passed test |
|---|---|---|---|---|---|---|
| **L0** | 37 280 | 28 509 | 8 771 | 9 950 | **$0,0634** | $0,00215 |
| **L1** | 56 943 | 45 835 | 11 107 | 16 912 | **$0,0862** | $0,00290 |
| **L2** | 93 763 | 83 980 | 9 783 | 32 157 | **$0,1040** | $0,00349 |
| **L3** | 95 059 | 85 602 | 9 458 | 32 855 | **$0,1033** | $0,00347 |
| **L4** | 113 279 | 103 892 | 9 387 | 40 102 | **$0,1147** | $0,00386 |

**Klíčová zjištění:**

- **Celkové tokeny rostou 3× z L0 na L4** (37k -> 113k), poháněno hlavně prompt tokeny. Completion tokeny se drží v úzkém pásmu 8 800–11 100 - model generuje konzistentně dlouhé výstupy bez ohledu na velikost kontextu.
- **Cache hit rate je 36–39 %** - výrazně nižší než u DeepSeek (85 % na L4). Claude tak z cachování profituje méně - každý run znovu platí plnou cenu značné části promptu.
- **Cena roste s úrovní kontextu skoro lineárně** ($0,063 -> $0,115, +80 %). Žádný plateau jako u DeepSeek není.
- **Cena za passed test stoupá** z $0,00215 (L0) na $0,00386 (L4). Přidaný kontext **nezlepšuje validity** (ta je plošně ~99 %), ale zvyšuje cenu každého úspěšného testu.
- **Porovnání s DeepSeek:** Claude Haiku je 10–15× dražší. DeepSeek stojí $0,005–0,013 za run, Claude $0,055–0,160. Za passed test: DeepSeek ~$0,00025, Claude ~$0,003 (12×).
- **Phase breakdown:** na všech úrovních ~50 % promptu jde na planning, ~50 % na generation, a jen marginální ~1 300 tokenů na (neúčinný) repair loop.

### 2.5 Kvalita testů - Assertion Depth a Response Validation

| Úroveň | Ø Assertion Depth | Ø Response Validation | Ø Avg Lines/test | Ø Side-effect checks | Ø Helper calls/test |
|---|---|---|---|---|---|
| **L0** | 2,13 | 50,0 % | 12,49 | 9,3 % | 1,17 |
| **L1** | 2,22 | 41,3 % | 9,77 | 10,0 % | 1,18 |
| **L2** | 2,71 | **81,3 %** | 10,49 | 12,6 % | 1,27 |
| **L3** | 2,67 | 82,0 % | 9,98 | 10,0 % | 1,23 |
| **L4** | **2,73** | **90,7 %** | 12,04 | **14,7 %** | **2,25** |

**Příběh kvality je dramatický - L2 je inflexní bod:**

- **L0 testy jsou mělké** - 2,13 assertionů na test, polovina ověřuje response body. Testy mají průměrně 12,5 řádků.
- **L1 je paradoxně *horší* v response validation** (41,3 % vs 50,0 % na L0). Přidání byznys dokumentace pomůže modelu upřesnit *co* testovat (plán je lepší), ale přitom zkrátí průměrnou délku testu (9,77 řádku, nejméně ze všech) a model tak dělá méně body-checks. Klasický trade-off: víc informací -> snaha je využít -> kratší, focusednější testy -> méně generických assertionů.
- **L2 je zásadní skok**: response validation skočí z 41 % na 81 % (+40 p.b.), assertion depth z 2,22 na 2,71. **Zdrojový kód modelu ukáže přesnou strukturu response** - model začne ověřovat konkrétní pole v odpovědi. Toto je pro Claude Haiku **klíčový moment** kontextového obohacení.
- **L3 je plateau** - DB schéma nepřidá žádný nový informační obsah pro testování HTTP API. Všechny kvalitativní metriky se pohybují ±1 p.b. oproti L2.
- **L4 je peak kvality** - response validation 90,7 % (nejvíc ze všech), assertion depth 2,73, side-effect checks 14,7 %, **helper calls skočí na 2,25** (oproti 1,23 na L3, téměř zdvojnásobení). Ukázkové testy naučí model těžit z helperů - kde předtím vytvářel entity inline, teď volá `create_book()` a `create_author()` z ukázky.

**Helper calls jsou nejvýraznější efekt L4** - učení z příkladů se zde projeví nejmarkantněji. Pokud je cílem, aby generované testy napodobovaly styl existujícího test-suitu, L4 jasně vyhrává.

---

## 3. Detailní rozbor Code Coverage

### 3.1 Souhrnná tabulka Coverage podle úrovní

| Úroveň | Celkový Ø | `crud.py` | `main.py` | `__init__`, `database`, `models`, `schemas` |
|---|---|---|---|---|
| **L0** | **67,97 %** | **40,72 %** | 68,10 % | Vše 100 % |
| **L1** | **65,63 %** | 35,86 % | 66,47 % | Vše 100 % |
| **L2** | **65,71 %** | 35,60 % | 67,08 % | Vše 100 % |
| **L3** | **66,18 %** | 36,07 % | 68,10 % | Vše 100 % |
| **L4** | **66,98 %** | 38,04 % | 68,23 % | Vše 100 % |

### 3.2 Analýza pokrytí jednotlivých souborů

**`app/__init__.py`, `app/database.py`, `app/models.py`, `app/schemas.py` - vždy 100 %**

Stejně jako u DeepSeek jsou tyto soubory pokryty implicitně - importem a inicializací aplikace při prvním HTTP requestu. Metrika nemá žádnou diagnostickou hodnotu pro kvalitu testů.

**`app/main.py` - stabilních 66–68 %**

Rozpětí pouhých 2 p.b. napříč úrovněmi. Nepokrytých ~32 % kódu odpovídá route handlerům pro endpointy, které model systematicky ignoruje (orders, tags, admin, exports). Zvýšení pokrytí by vyžadovalo testy v těchto doménách - ale žádný level kontextu model k tomu nemotivuje.

**`app/crud.py` - paradoxní inverze oproti DeepSeek (40,72 % -> 35,60 %)**

Toto je nejzajímavější nález celé Coverage analýzy:

| Úroveň | Ø `crud.py` | Δ vs L0 |
|---|---|---|
| **L0** | **40,72 %** | - |
| L1 | 35,86 % | **-4,86 p.b.** |
| L2 | 35,60 % | -5,12 p.b. |
| L3 | 36,07 % | -4,65 p.b. |
| L4 | 38,04 % | -2,68 p.b. |

U DeepSeek byl L1 inflexní bod **nahoru** (39 % -> 56 %). U Claude Haiku je L1 inflexní bod **dolů** (41 % -> 36 %). Proč?

**Mechanismus:** Claude Haiku při L0 generuje testy, které jsou sice mělké (viz assertion depth 2,13), ale pokrývají širší paletu endpointů (17,2/50 oproti 14,2/50 na L1). Širší paleta = víc volaných CRUD funkcí = víc řádek v `crud.py` provedených. Od L1 se model soustředí na méně endpointů s hlubšími testy -> každý test volá méně různých CRUD funkcí, takže celkové pokrytí `crud.py` paradoxně klesá.

**L4 částečně kompenzuje** (38 % vs 36 % na L2–L3) díky širší endpoint coverage a dvojnásobnému využití helperů - helper `create_book()` vnitřně zavolá `create_author()` a `create_category()`, takže každý test nepřímo pokryje 3 CRUD funkce místo 1.

### 3.3 Které endpointy model pokrývá a které ignoruje

**Endpointy pokryté ve všech 25 runech (50 - 44 = 6 endpointů):**

| Endpoint | Počet runů | Proč |
|---|---|---|
| `GET /health` | 25/25 | Triviální smoke test |
| `POST /authors` | 25/25 | Hlavní setup helper |
| `GET /authors/{id}` | 25/25 | Základní read, testuje ETag |
| `PUT /authors/{id}` | 25/25 | Update + If-Match header testy |
| `POST /books` | 25/25 | Hlavní entita systému |
| `GET /books/{id}` | 25/25 | Základní read, soft-delete ověření |

**Endpointy pokryté často, ale ne vždy:**

| Endpoint | Pokrytí | Poznámka |
|---|---|---|
| `DELETE /authors/{id}` | 24/25 | Téměř universal |
| `POST /books/{id}/restore` | 24/25 | Soft-delete workflow |
| `DELETE /books/{id}` | 24/25 | Soft delete |
| `POST /books/{id}/discount` | 23/25 | Často cíl stale testů! |
| `POST /categories` | 22/25 | Krok v helper create_book |
| `PATCH /books/{id}/stock` | 20/25 | Adjust stock |
| `GET /books` | 19/25 | List s filtry |
| `GET /authors` | 15/25 | List |
| `GET /categories` | 12/25 | List |
| `POST /books/{id}/reviews` | 10/25 | Recenze - sporadicky |
| `POST /books/{id}/cover` | 7/25 | Multipart upload - komplexní |
| `PUT /books/{id}` | 5/25 | Update s ETag |

**Systematicky ignorované endpointy (0/25 pokrytí napříč všemi úrovněmi):**

| Doména | Endpointy | Komentář |
|---|---|---|
| **Orders** (6 endpointů) | `POST /orders`, `GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}/status`, `DELETE /orders/{id}`, `GET /orders/{id}/invoice`, `POST /orders/{id}/items` | **Celá doména objednávek je pro Claude neviditelná.** To je klíčový rozdíl oproti DeepSeek, který POST /orders a PATCH /orders/{id}/status testoval ve všech 25 runech. |
| **Tags** (4 endpointy) | `GET /tags`, `GET /tags/{id}`, `PUT /tags/{id}`, `DELETE /tags/{id}` | Celá doména tagů ignorována ve všech 25 runech. |
| **Admin** (2 endpointy) | `GET /admin/maintenance`, `POST /admin/maintenance` | Out-of-scope pro model |
| **Exports** (3 endpointy) | `POST /exports/books`, `POST /exports/orders`, `GET /exports/{job_id}` | Asynchronní workflow - vyžaduje choreografii |
| **Bulk/Clone** (2 endpointy) | `POST /books/bulk`, `POST /books/{id}/clone` | Pokročilé operace |
| **Reset/Catalog** | `POST /reset`, `GET /catalog`, `GET /statistics/summary` | Agregované / setup endpointy |
| **Cover GET/DELETE** | `GET /books/{id}/cover`, `DELETE /books/{id}/cover` | Pouze POST cover částečně testován |

**Celkem 23 z 50 endpointů (46 %) není pokryto ani v jednom z 25 runů.** Žádná úroveň kontextu tuto slepou skvrnu neodstraní.

### 3.4 Rozptyl Coverage v rámci úrovní

| Úroveň | Min celk. | Max celk. | Spread | Min `crud.py` | Max `crud.py` | Spread |
|---|---|---|---|---|---|---|
| L0 | 66,80 % | 69,08 % | 2,28 p.b. | 38,50 % | 43,15 % | 4,65 p.b. |
| L1 | 64,72 % | 66,20 % | 1,48 p.b. | 34,11 % | 36,95 % | 2,84 p.b. |
| L2 | 65,31 % | 66,70 % | 1,39 p.b. | 33,33 % | 38,24 % | 4,91 p.b. |
| L3 | 65,11 % | 66,90 % | 1,79 p.b. | 33,07 % | 37,47 % | 4,40 p.b. |
| L4 | 65,51 % | 68,68 % | 3,17 p.b. | 34,37 % | 42,89 % | 8,52 p.b. |

**L1 je extrémně stabilní** (spread jen 1,48 p.b.). Od L4 se rozptyl zvětšuje - ukázkové testy vnášejí do modelu víc variability, takže jeden run může trefit širší set endpointů než jiný. L4 run2 dosáhne 68,68 % (téměř na úrovni L0 nejlepšího), zatímco L4 run1 jen 65,51 %.

---

## 4. Proč se to děje? (Kauzalita a obhajoba)

### 4.1 Proč má Claude Haiku fundamentálně jiný profil než DeepSeek

Hlavní zjištění tohoto experimentu: **Claude Haiku 4.5 je "high baseline" model, kde přidaný kontext primárně prohlubuje kvalitu testů, zatímco DeepSeek je "growth curve" model, kde kontext zlepšuje téměř vše.**

| Aspekt                    | DeepSeek-Chat | Claude Haiku 4.5 |
|---------------------------|---|---|
| Baseline validity (L0)    | 90,67 % | **98,67 %** |
| First-shot pass rate (L0) | ~40 % (odhad z repair traj.) | **80 %** |
| L0 -> L1 skok ve validity | +6 p.b. | +0,66 p.b. |
| L0 -> L1 skok v crud.py   | +17 p.b. | **-5 p.b.** |
| L0 -> L2 skok v resp_val  | +43 p.b. | +31 p.b. |
| Inflexní bod kvality      | L1 (byznys doc) | **L2 (zdrojový kód)** |
| Cena za úspěšný test      | ~$0,0002 | ~$0,0030 (15× více) |

### 4.2 Proč L2 je inflexní bod (ne L1 jako u DeepSeek)

Model má vysoký baseline díky **kvalitnějšímu planning kroku**. Plán na L0 už pokrývá 30 různých testových scénářů se správně zvolenými status kódy (hallucinated codes = 0 ve všech runech). Takže:

1. **OpenAPI spec (L0)** stačí modelu k úspěšnému vygenerování **syntakticky i sémanticky správných requestů**. Validity 98,67 % znamená, že model "trefí" všechno zásadní už z OpenAPI.

2. **Byznys dokumentace (L1)** přidá 7 825 tokenů, ale tyto informace model implicitně už "umí" - Claude z pretrenovaných dat zná typické REST API vzory (ETag, If-Match, soft-delete, atd.). Result: validity se zvýší marginálně, coverage *klesne* protože model se "soustředí".

3. **Zdrojový kód (L2)** přidá +20 134 tokenů a s ním **konkrétní struktury response bodies**. Tohle je první informace, kterou model z OpenAPI ani z prozy nezíská - přesné JSON keys, konkrétní hodnoty computed polí (např. `discounted_price`, `discount_percent`). Response validation skočí z 41 % na 81 % - model teprve teď ověřuje `data["discount_percent"] == 10` místo jen status kódu.

4. **DB schéma (L3)** je tentokrát **skutečně mrtvá úroveň** (+853 tokenů, ±0 zlepšení).

5. **Ukázkové testy (L4)** přinášejí největší efekt v **helper usage** (×2) a v **edge-case pokrytí** - model okopíruje vzor `test_get_author_not_modified` s If-None-Match headerem a status 304, což na L0–L3 obvykle nedělá.

### 4.3 Proč Endpoint Coverage klesá L0 -> L1–L2

Stejný mechanismus jako u DeepSeek, ale výraznější:

| Metrika | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| EP Coverage | 34,4 % | 28,4 % | 27,6 % | 28,4 % | 31,2 % |
| Avg helper calls | 1,17 | 1,18 | 1,27 | 1,23 | 2,25 |
| Response validation | 50 % | 41 % | 81 % | 82 % | 91 % |

Model s fixním budgetem 30 testů musí mezi **breadth** (víc endpointů × mělké testy) a **depth** (málo endpointů × hluboké testy) volit. Bez dalšího kontextu preferuje breadth (L0 = 34,4 % EP, resp_val = 50 %). S kontextem výrazně posune k depth (L2 = 27,6 % EP, resp_val = 81 %). L4 nabídne oba - obsah ukázkových testů model inspiruje k širšímu záběru *bez* obětování hloubky.

### 4.4 Anomálie a jejich vysvětlení

**Anomálie 1: L0 run1 - jediný run s validity pod 96 %**

Run1 má 93,33 % validity a 2 stale testy (`test_apply_discount_rate_limit`, `test_update_stock_success`). Je to jediný run, kde Claude při první generaci netrefil správně rate-limit chování discount endpointu a zároveň špatně predikoval response stock hodnotu. Bez byznys dokumentace model tipuje status 200 pro rate-limit překročení (správně má být 429). V runech 2–5 už Claude stejný problém nedělá - teploty 0.4 pravděpodobně vede k šťastnější volbě na prvním pokusu.

**Anomálie 2: L1 run1 - cena $0,118 vs Ø $0,076 na ostatních L1 runech**

Run1 na L1 stál o 55 % víc než ostatní runy. Důvod: je to první run v celém levelu (cache miss - `cached_tokens = 0`), zatímco run2–5 profitují z prompt cache (21 140 tokenů cachováno). Toto pravidlo platí **ve všech úrovních** - první run vždy platí plnou cenu, zbývající runy profitují z cache.

**Anomálie 3: L1 je *horší* v response validation než L0 (41 % vs 50 %)**

Neintuitivní, ale vysvětlitelné. Průměrná délka testu na L1 je **9,77 řádků** (nejkratší ze všech úrovní), zatímco L0 má 12,49. Byznys dokumentace vede Claude ke stručnějším, "profesionálnějším" testům s méně opakovaných assertionů. Kvalita plánu se zvýší, ale každý test má méně řádků = méně bodu-check assertionů. Mechanismus se obrátí až na L2, kde znalost response struktury dotlačí model k explicitnímu ověřování polí.

**Anomálie 4: L4 run1 - outlier cenou i iteracemi**

L4 run1 stál $0,160 (oproti Ø $0,103 zbylých L4 runů) a jako jediný L4 run potřeboval 3 iterace (stale test). Cache miss + stale test kombinace dělá z tohoto runu nejdražší běh celého experimentu. Přesto ostatní L4 runy jsou pozoruhodně stabilní (100 % validity, prošly napoprvé).

**Anomálie 5: L4 run3 má nejvyšší avg_lines (14,07) ze všech 25 runů**

Ukázkové testy vedou tento konkrétní run k obzvlášť robustním testům - 14 řádek na test znamená každý test má setup, 1–2 requesty, 3–4 assertiony. Tohle je nejblíž "produkčnímu" stylu testů v celém experimentu.

### 4.5 Kauzální model chování Claude Haiku

```
L0 (OpenAPI)        -> vysoká validity (98,67 %) + široká breadth (34 %)
                    -> mělké testy (assert 2,13, resp_val 50 %)
                    -> 4/5 runů prochází napoprvé

L1 (+ byznys doc)   -> validity plateau (99,33 %) + úzká breadth (28 %)
                    -> kratší, focusovanější testy (9,77 řádků)
                    -> paradox: resp_val klesne (-9 p.b.)

L2 (+ zdrojový kód) -> validity plateau (99,33 %) + úzká breadth (27 %)
                    -> DEPTH SKOK: resp_val 81 %, assert 2,71
                    -> model vidí response strukturu
                    -> inflexní bod kvality

L3 (+ DB schéma)    -> plateau: žádná změna proti L2
                    -> DB schéma irelevantní pro HTTP testování

L4 (+ ukázky)       -> validity plateau (99,33 %) + mírně rostoucí breadth (31 %)
                    -> helper usage se ZDVOJNÁSOBÍ (1,23 -> 2,25)
                    -> resp_val = 91 % (peak), side-effect = 15 % (peak)
                    -> cena +8 % oproti L3, variabilita roste
```

Claude Haiku má **fixní budget attention na ~14 endpointů** a 30 testových scénářů - víc kontextu tento budget nerozšíří, ale přesouvá ho do hlubšího testování méně endpointů.

---

## 5. Detailní rozpis jednotlivých úrovní a běhů

<details>
<summary><strong>📊 L0 - Pouze OpenAPI specifikace (Ø validity 98,67 %, Ø EP 34,4 %, Ø coverage 67,97 %)</strong></summary>

### Komentář k L0

Model má k dispozici pouze komprimovanou OpenAPI specifikaci (~16k tokenů). Překvapivě dosahuje **průměrné validity 98,67 %** a pokrývá **nejvyšší počet endpointů celého experimentu (17,2/50)**. Generuje relativně mělké testy (assert depth 2,13, response validation jen 50 %), ale jejich status kódy jsou správné v 98 % případů. Čtyři z pěti runů projdou 30/30 napoprvé. Jediný problematický run je run1 se dvěma stale testy na rate-limited discount a stock update.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **93,33 %** | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| **Passed/Total** | **28/30** | 30/30 | 30/30 | 30/30 | 30/30 |
| **EP Coverage** | 15/50 | **19/50** | 15/50 | **19/50** | 18/50 |
| **Stale tests** | **2** | 0 | 0 | 0 | 0 |
| **Assertion Depth** | 2,20 | 2,23 | 2,03 | 1,97 | 2,23 |
| **Resp. Validation** | 53,33 % | 53,33 % | 43,33 % | 46,67 % | 53,33 % |
| **Cena (USD)** | $0,0809 | $0,0580 | $0,0585 | $0,0642 | $0,0554 |
| **Celk. tokeny** | 42 317 | 35 848 | 35 915 | 37 052 | 35 269 |
| **Iterace** | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Code Cov. celk.** | 66,80 % | 69,08 % | 67,10 % | 68,68 % | 68,19 % |
| **Code Cov. crud.py** | 38,50 % | 42,12 % | 38,50 % | **43,15 %** | 41,34 % |
| **H/E/Ed testy** | 17/13/0 | 21/8/1 | 18/9/3 | 21/8/1 | 20/10/0 |
| **Status Diversity** | 9 | 8 | 9 | 8 | 9 |

**Nejčastější problém L0:** `test_apply_discount_rate_limit` - model nezná existenci rate-limitu a očekává status 200 místo 429. Stejný test selže i na L1 run1 (viz dále).

</details>

<details>
<summary><strong>📊 L1 - + Byznys dokumentace (Ø validity 99,33 %, Ø EP 28,4 %, Ø coverage 65,63 %)</strong></summary>

### Komentář k L1

Přidání byznys dokumentace (+7 825 tokenů) **nezlepší validity** (98,67 % -> 99,33 %, +0,66 p.b.), ale dramaticky změní chování modelu. Endpoint Coverage klesne z 34,4 % na 28,4 %, protože model se v bohatším kontextu soustředí na menší počet endpointů. Paradoxně **Response Validation klesne o 9 p.b.** (50 % -> 41 %) - model generuje kratší testy (9,77 řádků, minimum experimentu) s méně opakovanými body-check assertiony. Code Coverage crud.py klesne o -5 p.b. oproti L0. Čtyři z pěti runů projdou 30/30 napoprvé.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **96,67 %** | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| **Passed/Total** | **29/30** | 30/30 | 30/30 | 30/30 | 30/30 |
| **EP Coverage** | 14/50 | 15/50 | 15/50 | 13/50 | 14/50 |
| **Stale tests** | **1** | 0 | 0 | 0 | 0 |
| **Assertion Depth** | 2,23 | 2,30 | 2,33 | 2,13 | 2,13 |
| **Resp. Validation** | 46,67 % | 36,67 % | 46,67 % | 40,00 % | 36,67 % |
| **Cena (USD)** | $0,1177 | $0,0691 | $0,0672 | $0,0890 | $0,0878 |
| **Celk. tokeny** | 63 562 | 53 482 | 53 080 | 57 400 | 57 190 |
| **Iterace** | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Code Cov. celk.** | 66,20 % | 66,20 % | 66,01 % | 65,01 % | 64,72 % |
| **Code Cov. crud.py** | 36,43 % | 36,95 % | 36,43 % | 34,11 % | 35,40 % |
| **H/E/Ed testy** | 14/12/4 | 19/11/0 | 20/9/1 | 19/11/0 | 18/11/1 |
| **Status Diversity** | 11 | 10 | 9 | 9 | 10 |

**Run1 outlier ceny:** $0,1177 oproti Ø $0,078 zbylých runů (+51 %). Cache miss efekt - první run úrovně nemá předchozí cache. Bez cache by každý run stál ~$0,12; s cachí jen ~$0,07.

**Run1 stale:** `test_apply_discount_rate_limit` - model i s byznys dokumentací selhává ve stejném místě jako na L0 run1. Byznys dokumentace tuto konkrétní rate-limit logiku patrně nepopisuje dost explicitně.

</details>

<details>
<summary><strong>📊 L2 - + Zdrojový kód endpointů (Ø validity 99,33 %, Ø EP 27,6 %, Ø coverage 65,71 %) - inflexní bod kvality</strong></summary>

### Komentář k L2

Přidání zdrojového kódu (+20 134 tokenů) přinese **dramatický skok v response validation** (41 % -> 81 %, +40 p.b.) a assertion depth (2,22 -> 2,71). Model čte implementaci endpointů a teprve teď ví, jaká *konkrétní pole* response obsahuje. Endpoint Coverage lehce klesne (27,6 %, minimum experimentu) - model se soustředí na ještě méně endpointů, ale testuje je důkladně. Čtyři z pěti runů projdou napoprvé, jen run2 má stale test na rate-limit discount.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 100,0 % | **96,67 %** | 100,0 % | 100,0 % | 100,0 % |
| **Passed/Total** | 30/30 | **29/30** | 30/30 | 30/30 | 30/30 |
| **EP Coverage** | 14/50 | 15/50 | 14/50 | 13/50 | 13/50 |
| **Stale tests** | 0 | **1** | 0 | 0 | 0 |
| **Assertion Depth** | 2,83 | 2,67 | 2,47 | **2,90** | 2,70 |
| **Resp. Validation** | 83,33 % | 83,33 % | 66,67 % | **86,67 %** | **86,67 %** |
| **Cena (USD)** | $0,1284 | $0,1026 | $0,0895 | $0,0924 | $0,1069 |
| **Celk. tokeny** | 92 014 | 98 400 | 91 480 | 92 010 | 94 912 |
| **Iterace** | **1 (OK)** | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Code Cov. celk.** | 65,31 % | 66,70 % | 65,31 % | 65,91 % | 65,31 % |
| **Code Cov. crud.py** | 34,88 % | **38,24 %** | 34,88 % | 36,69 % | 33,33 % |
| **H/E/Ed testy** | 17/12/1 | 16/13/1 | 19/11/0 | 16/14/0 | 13/16/1 |
| **Status Diversity** | 10 | 11 | 10 | 10 | **12** |

**Run2 stale:** `test_apply_discount_exceeds_rate_limit`. I se zdrojovým kódem model nedokáže v `crud.apply_discount` identifikovat rate-limit logiku - ta je pravděpodobně implementována v middleware nebo dekorátoru, který v kontextu zdrojového kódu chybí.

**Run3 je outlier kvality v opačném směru:** Response validation jen 66,67 % (nejnižší L2 run) a zároveň assertion depth 2,47 (nejnižší L2 run). Model v tomto konkrétním případě vygeneroval kratší a jednodušší testy než ostatní L2 runy.

</details>

<details>
<summary><strong>📊 L3 - + Databázové schéma (Ø validity 99,33 %, Ø EP 28,4 %, Ø coverage 66,18 %) - mrtvá úroveň</strong></summary>

### Komentář k L3

DB schéma přidá pouhých **853 tokenů** a **žádnou měřitelnou změnu** v žádné klíčové metrice oproti L2. Validity, assertion depth, response validation i code coverage se pohybují v rámci statistického šumu L2. Čtyři z pěti runů projdou napoprvé, jen run5 má stale test. **L3 je nejvíce předvídatelná úroveň experimentu** - pro Claude Haiku je databázové schéma irelevantní, protože testuje HTTP endpointy, ne SQL dotazy.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 100,0 % | 100,0 % | 100,0 % | 100,0 % | **96,67 %** |
| **Passed/Total** | 30/30 | 30/30 | 30/30 | 30/30 | **29/30** |
| **EP Coverage** | 14/50 | 14/50 | 15/50 | **16/50** | 12/50 |
| **Stale tests** | 0 | 0 | 0 | 0 | **1** |
| **Assertion Depth** | 2,73 | 2,57 | 2,60 | 2,70 | **2,77** |
| **Resp. Validation** | 83,33 % | **86,67 %** | 76,67 % | 80,00 % | 83,33 % |
| **Cena (USD)** | $0,1286 | $0,0911 | $0,0906 | $0,1085 | $0,0979 |
| **Celk. tokeny** | 93 460 | 93 354 | 93 244 | 96 830 | 98 409 |
| **Iterace** | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** | 3 (stale) |
| **Code Cov. celk.** | 66,01 % | 66,50 % | 66,40 % | 66,90 % | 65,11 % |
| **Code Cov. crud.py** | 36,69 % | 36,18 % | 37,47 % | 36,95 % | 33,07 % |
| **H/E/Ed testy** | 18/11/1 | 15/14/1 | 19/11/0 | 16/11/3 | 15/15/0 |
| **Status Diversity** | 10 | 12 | 10 | 11 | 11 |

**Run5 stale:** `test_restore_deleted_book_success` s kategorií `assertion_value_mismatch`. Model vygeneroval test, který očekává určitou hodnotu v response po restore, ale API vrací jinou strukturu. DB schéma tuto response nestrukturu nepopisuje (ta je definovaná v schémech Pydantic, ne v DB).

**Run4 má nejvyšší EP Coverage L3** (16/50) a také 3 edge-case testy - jediný L3 run s nenulovým edge-case počtem. Vygeneroval si široký plán.

</details>

<details>
<summary><strong>📊 L4 - + Ukázkové testy (Ø validity 99,33 %, Ø EP 31,2 %, Ø coverage 66,98 %) - peak helper usage</strong></summary>

### Komentář k L4

Přidání ukázkových testů (+8 668 tokenů) má **významný a pozitivní efekt** na kvalitu i šířku. Endpoint Coverage se vrací z plateau na 31,2 %, Response Validation dosáhne peak 90,7 %, **helper calls se zdvojnásobí** (1,23 -> 2,25) - model se inspiruje stylem ukázek a masivně volá helper funkce místo inline setupu. Side-effect checks 14,7 % (peak experimentu). Čtyři z pěti runů projdou napoprvé, jen run1 má stale test (cache miss + rate-limit discount).

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **96,67 %** | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| **Passed/Total** | **29/30** | 30/30 | 30/30 | 30/30 | 30/30 |
| **EP Coverage** | 14/50 | **17/50** | **17/50** | 15/50 | 15/50 |
| **Stale tests** | **1** | 0 | 0 | 0 | 0 |
| **Assertion Depth** | 2,40 | **3,00** | 2,73 | 2,73 | 2,80 |
| **Resp. Validation** | 90,00 % | 90,00 % | 90,00 % | 90,00 % | **93,33 %** |
| **Cena (USD)** | $0,1599 | $0,1025 | $0,1041 | $0,1036 | $0,1036 |
| **Celk. tokeny** | 118 300 | 111 785 | 112 199 | 112 053 | 112 059 |
| **Iterace** | 3 (stale) | **1 (OK)** | **1 (OK)** | **1 (OK)** | **1 (OK)** |
| **Avg Helper Calls** | **2,27** | **2,30** | **2,33** | **2,27** | 2,10 |
| **Side-effect %** | 10,0 % | **20,0 %** | 13,3 % | **16,7 %** | 13,3 % |
| **Code Cov. celk.** | 65,51 % | **68,68 %** | 67,59 % | 66,30 % | 66,80 % |
| **Code Cov. crud.py** | 34,37 % | **42,89 %** | 38,24 % | 37,21 % | 37,47 % |
| **H/E/Ed testy** | 12/17/1 | 17/12/1 | 15/13/2 | 14/15/1 | 12/16/2 |
| **Status Diversity** | **13** | 10 | 12 | 10 | 12 |

**Run2 je star L4:** nejvyšší code coverage celk. (68,68 %), nejvyšší crud.py (42,89 %), nejvyšší side-effect % (20,0 %), assertion depth 3,00 (peak). Tento run nejlépe využil ukázky - model dramaticky rozšířil scope o více side-effect ověření (status -> requery -> compare).

**Run1 je star ceny:** $0,1599 (nejdražší run celého experimentu). Cache miss (první L4 run) + 3 iterace repair loopu. Bez cache a se stale testem je to nejhorší kombinace.

**Run1 stale:** `test_discount_rate_limit_exceeded` - 4. výskyt stejného konceptu (rate-limit discount) napříč experimentem. Potvrzuje, že rate-limit logika je **systematicky obtížná** pro Claude bez ohledu na úroveň kontextu.

**L4 má v průměru více error testů** než happy_path (Ø 14,6 error vs Ø 14 happy_path). Tento posun ale není tak dramatický jako u DeepSeek L4 (kde poměr error:happy byl 71:17). Claude zůstává vyváženější.

</details>

---

## Závěrečné shrnutí pro obhajobu

### Hlavní příběh dat

**Claude Haiku 4.5 je "high-baseline, quality-deepening" model.** Už při minimálním kontextu (L0) dosahuje téměř ideální validity (98,67 %) a nejširšího endpoint záběru (34,4 %). Přidaný kontext nevede k růstu validity (ta je již na stropě), ale systematicky prohlubuje kvalitu testů - zejména response validation (50 % -> 91 %) a assertion depth (2,13 -> 2,73). Klíčovým inflexním bodem je **L2 (zdrojový kód)**, kde model získá konkrétní strukturu response bodies a začne dělat skutečné body-check assertiony místo jen status-code ověřování.

Model má ale **jasnou slepou skvrnu**: celé domény API (objednávky, tagy, admin, exporty - 23 z 50 endpointů) nejsou pokryty ani v jednom z 25 runů bez ohledu na úroveň kontextu. Žádná forma přidaného kontextu tuto systematickou tendenci nepřekoná.

Repair loop je **de facto nefunkční** - self-correction rate je 0 % ve všech 25 runech. Model buď uspěje napoprvé (21/25 runů), nebo neuspěje vůbec. Naštěstí díky vysoké first-shot pass rate je toto omezení v praxi málo znatelné.

**Cena je výrazně vyšší než u DeepSeek** - $0,06–$0,16 za run vs $0,005–$0,013, tedy 10–15× dražší. Cache hit rate (~38 %) je horší než u DeepSeek (~72 % na L4), což vysvětluje část cenového rozdílu.

### Čísla pro obhajobu

| Tvrzení | Podpora v datech                                                                |
|---|---------------------------------------------------------------------------------|
| Claude Haiku má extrémně vysoký baseline | L0 validity = 98,67 %; 4/5 runů 30/30 napoprvé bez oprav                        |
| Přidaný kontext prohlubuje kvalitu, nerozšiřuje validity | L0->L4: validity +0,66 p.b., resp. validation +40,7 p.b.                        |
| L2 (zdrojový kód) je inflexní bod kvality | L1->L2: resp_val 41 % -> 81 %, assertion 2,22 -> 2,71                           |
| L3 (DB schéma) je mrtvá úroveň | L2->L3: všechny metriky se mění ±1 p.b.                                         |
| L4 dramaticky mění stylistiku testů | Helper calls 1,23 -> 2,25 (×1,83); side-effect 10 -> 15 %                       |
| Endpoint Coverage klesá s kontextem, pak rebounduje | L0: 34,4 % -> L2: 27,6 % -> L4: 31,2 %                                          |
| `crud.py` coverage se u Claude chová inverzně k DeepSeek | Claude: L0 = 40,72 %, L4 = 38,04 % (DeepSeek: L0 = 39 %, L1 = 56 %)             |
| Model se zasekává při opravách | self_correction_rate = 0 % napříč 25 runy; 4/4 repair loopy skončily early-stop |
| Rate-limit discount endpoint je konzistentně obtížný | 4 z 6 stale testů napříč experimentem                                           |
| Claude má jasné slepé skvrny | 23/50 endpointů (46 %) nepokryto v žádném runu                                  |
| Claude je 10–15× dražší než DeepSeek | Claude: $0,003/passed test; DeepSeek: $0,00025/passed test                      |
| Cache hit rate je u Claude nižší než u DeepSeek | Claude L4: 39 % cached vs DeepSeek L4: 85 % cached                              |