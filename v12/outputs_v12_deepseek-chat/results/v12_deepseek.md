# 🔬 Analytický Report: DeepSeek-Chat (V12) - Vibe Testing Framework

> **Datum analýzy:** 15. dubna 2026  
> **Datový zdroj:** `experiment_diplomka_v12_20260415_165515.json` + `coverage_deepseek_v12.md`  
> **Analyzováno:** 25 experimentálních běhů (5 úrovní × 5 runů)

---

## 1. Konfigurace a Přehled

### 1.1 Konfigurace experimentu

| Parametr | Hodnota                                   |
|---|-------------------------------------------|
| **LLM model** | `deepseek-chat`                           |
| **API / SUT** | `bookstore` (50 endpointů)                |
| **Teplota** | 0.4                                       |
| **Plánovaný počet testů** | 30 na run                                 |
| **Úrovně kontextu** | L0 – L4 (inkrementální přidávání sekcí)   |
| **Počet runů na úroveň** | 5                                         |
| **Max iterací oprav** | 3 (L0–L3), 4 (L4 v některých runech)      |
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

DeepSeek-Chat je v tomto experimentu **spolehlivý, ale konzervativní generátor testů**. Napříč 25 běhy dosahuje průměrné validity **95,6 %** a nikdy neklesá pod 83 %. Klíčový nález: model těží z přidaného kontextu především v **kvalitě testů** (assertion depth, response validation), nikoli v šířce pokrytí endpointů. Endpoint Coverage osciluje kolem 34–42 % a nikdy nepřekročí 50 %. Code Coverage na kritickém souboru `app/crud.py` stoupne z průměrných 39 % (L0) na 53–56 % (L1–L4), ale pak se plateau stabilizuje. Model je extrémně levný ($0,005–$0,013 za run) a nehallucinuje status kódy - ale zároveň se systematicky vyhýbá celým doménám API (kategorie, tagy, objednávky, exporty).

---

## 2. Co se v datech děje (Analýza hlavních metrik)

### 2.1 Validity Rate - Procento úspěšných testů

| Úroveň | Průměr | Min | Max | Runy s 100 % | Stale celkem |
|---|---|---|---|---|---|
| **L0** | **90,67 %** | 83,33 % | 96,67 % | 0/5 | 14 |
| **L1** | **96,67 %** | 93,33 % | 100,0 % | 2/5 | 5 |
| **L2** | **98,00 %** | 96,67 % | 100,0 % | 2/5 | 3 |
| **L3** | **96,67 %** | 90,00 % | 100,0 % | 2/5 | 5 |
| **L4** | **97,33 %** | 96,67 % | 100,0 % | 1/5 | 4 |

**Klíčová zjištění:**

- **L0 je nejslabší** s průměrem 90,67 % a nejvyšším počtem stale testů (14 celkem). Bez kontextu beyond OpenAPI specifikace model "hádá" chování API a často se trefí špatně.
- **L1 přináší dramatický skok** (+6 pp): přidání byznys dokumentace dá modelu vodítka o business logice (objednávky, statusy), takže méně testů selhává na neočekávaných status kódech.
- **L2 je peak validity** (98 %) - zdrojový kód endpointů eliminuje zbylou nejistotu o validačních pravidlech.
- **L3 a L4 mírně osciluji** kolem 96–97 %. Přidání DB schématu a ukázkových testů už validity výrazně nezlepšuje - model je na platou.

### 2.2 Endpoint Coverage

| Úroveň | Průměr pokrytých EP | Průměr (%) | Min | Max |
|---|---|---|---|---|
| **L0** | 20,4 / 50 | **40,8 %** | 19 | 22 |
| **L1** | 18,4 / 50 | **36,8 %** | 16 | 20 |
| **L2** | 17,4 / 50 | **34,8 %** | 17 | 19 |
| **L3** | 18,8 / 50 | **37,6 %** | 16 | 24 |
| **L4** | 22,4 / 50 | **44,8 %** | 18 | 25 |

**Klíčová zjištění - kontraintuitivní vzorec:**

- **L0 má lepší endpoint coverage než L1–L3.** To je paradox, ale vysvětlitelný: s pouhými 30 testy a jen OpenAPI specifikací model "rozsype" testy široce, protože nemá informace, které endpointy jsou důležitější. Vybírá rovnoměrněji.
- **L1–L3 coverage klesá**, protože byznys dokumentace a zdrojový kód implicitně navedou model k tomu, aby se soustředil na **klíčové CRUD operace** (books, authors) a testoval je hlouběji (více error scénářů), místo aby pokryl šířku.
- **L4 coverage opět roste** (44,8 %) - ukázkové testy dají modelu konkrétní příklady, jak testovat různé endpointy, a model se inspiruje jejich šířkou.
- **30 testů na 50 endpointů je inherentní limit.** Pokrytí 50 % je matematicky reálné, ale vyžadovalo by 1 test = 1 endpoint, což eliminuje error testy.

### 2.3 Staleness a bludné kruhy

**Repair trajectory - klíčový pattern:**

Model DeepSeek vykazuje **výraznou neschopnost opravit vlastní chyby**. V naprosté většině případů platí:

```
iterace 1: 28p/2f -> iterace 2: 28p/2f -> iterace 3: 28p/2f
```

Počet passed/failed testů se mezi iteracemi **nemění**. Repair loop je de facto mrtvý. Ze všech 25 běhů model úspěšně opravil všechny chyby pouze v **7 případech** (kde prošlo 30/30 hned v 1. nebo 2. iteraci). Ve zbylých 18 bězích se stale count rovná počtu failů z první iterace.

| Úroveň | Runů s 100 % po opravě | Typická trajektorie |
|---|---|---|
| L0 | 0/5 | Stagnace od 1. iterace |
| L1 | 2/5 | run2, run4: opraveno v 2. iteraci |
| L2 | 2/5 | run1, run4: prošlo napoprvé (0 oprav potřeba) |
| L3 | 2/5 | run1, run4: prošlo napoprvé |
| L4 | 1/5 | run3: prošlo napoprvé; run2, run4 měly regrese |

**L4 run2 a run4 vykazují regresi** - ve 3. iteraci se počet failů zvýšil (29p/1f -> 27p/3f -> zpět 29p/1f). Model při opravě jednoho testu rozbije jiný. To je unikátní pro L4 a souvisí s velikostí kontextu (53k tokenů), kde model začíná ztrácet konzistenci.

**Nejčastější stale testy:**

| Test | Výskytů | Příčina |
|---|---|---|
| `test_update_order_status_valid` | 5× (L0) | Špatný status code; model nezná state machine objednávek |
| `test_restore_soft_deleted_book` | 5× (L2+L4) | Neví, jak funguje soft-delete/restore mechanismus |
| `test_upload_cover_valid_file` | 3× (L0+L3) | Multipart upload je komplikovaný bez příkladu |
| `test_apply_discount_*` | 4× (L1+L3+L4) | Business logika slev a rate-limitů |

### 2.4 Token Usage, Komprese a Cena

| Úroveň | Ø Celk. tokeny | Ø Prompt | Ø Completion | Ø Cache hit | Ø Cena (USD) | Ø Cena/passed test |
|---|---|---|---|---|---|---|
| **L0** | 35 687 | 28 759 | 6 928 | 24 128 | **$0,006** | $0,00022 |
| **L1** | 53 229 | 45 364 | 7 869 | 37 184 | **$0,007** | $0,00024 |
| **L2** | 81 015 | 73 846 | 7 172 | 73 424 | **$0,008** | $0,00027 |
| **L3** | 82 355 | 75 338 | 7 017 | 73 206 | **$0,006** | $0,00021 |
| **L4** | 100 638 | 93 063 | 7 575 | 85 252 | **$0,008** | $0,00027 |

**Klíčová zjištění:**

- **Celkové tokeny rostou 2,8× z L0 na L4** (35k -> 100k), ale **completion tokeny zůstávají prakticky konstantní** (~7 000–7 900). Model generuje stejně dlouhý výstup bez ohledu na velikost kontextu.
- **Cache hit rate dramaticky roste** - na L4 je 85 % prompt tokenů cachováno, což drží reálnou cenu na absurdně nízké úrovni ($0,005–$0,013 za run).
- **Cena za passed test je prakticky konstantní** napříč úrovněmi ($0,00021–$0,00027). DeepSeek je z cenového hlediska neutrální vůči velikosti kontextu díky agresivnímu cachování.
- **Komprese klesá s kontextem**: L0 šetří 48 % tokenů, ale L4 jen 22,6 %. Zdrojový kód a ukázkové testy se komprimují hůře než strukturovaná OpenAPI spec.

### 2.5 Kvalita testů - Assertion Depth a Response Validation

| Úroveň | Ø Assertion Depth | Ø Response Validation | Ø Avg Lines/test | Ø Side-effect checks |
|---|---|---|---|---|
| **L0** | 2,34 | 51,3 % | 9,1 | 11,3 % |
| **L1** | 3,39 | 85,3 % | 12,6 | 24,7 % |
| **L2** | 3,31 | 94,0 % | 11,7 | 31,3 % |
| **L3** | 2,91 | 96,7 % | 11,1 | 18,7 % |
| **L4** | 2,97 | 98,7 % | 10,7 | 10,0 % |

**Příběh kvality je jasný:**

- **L0 testy jsou mělké** - 2,34 assertionů na test, jen polovina kontroluje tělo response.
- **L1 je kvalitativní skok** - assertion depth stoupne o 45 %, response validation skočí z 51 % na 85 %. Byznys dokumentace učí model, *co* v odpovědi ověřovat.
- **L2 je peak kvality** - 94 % response validation, 31 % side-effect checks (nejvíc ze všech úrovní). Zdrojový kód dává modelu přesnou představu o tom, co endpoint vrací.
- **L3–L4 kvalita mírně klesá** v assertion depth (2,9) a side-effect checks (10–19 %). Model je zahlcen kontextem a vrací se k jednodušším testům.

---

## 3. Detailní rozbor Code Coverage

### 3.1 Souhrnná tabulka Coverage podle úrovní

| Úroveň | Celkový Ø | `crud.py` | `main.py` | `__init__`, `database`, `models`, `schemas` |
|---|---|---|---|---|
| **L0** | **68,15 %** | 39,28 % | 70,61 % | Vše 100 % |
| **L1** | **74,45 %** | 56,43 % | 69,66 % | Vše 100 % |
| **L2** | **73,70 %** | 54,83 % | 69,19 % | Vše 100 % |
| **L3** | **73,12 %** | 53,75 % | 68,64 % | Vše 100 % |
| **L4** | **73,50 %** | 53,18 % | 70,68 % | Vše 100 % |

### 3.2 Analýza pokrytí jednotlivých souborů

**`app/__init__.py`, `app/database.py`, `app/models.py`, `app/schemas.py` - vždy 100 %**

Tyto soubory jsou pokryty implicitně - importem a inicializací aplikace. Každý test, který zavolá jakýkoli endpoint, nutně projde těmito soubory. Toto číslo **nemá žádnou diagnostickou hodnotu** pro kvalitu testů.

**`app/main.py` - stabilních 69–71 %**

Soubor obsahuje route definice a middleware. Průměr ~70 % naznačuje, že ~30 % routingového kódu se neprovede - odpovídá to faktu, že model pokrývá jen 35–45 % endpointů. Zbytek jsou nepokryté route handlery pro kategorie, tagy, objednávky atd.

**`app/crud.py` - klíčový differenciátor (39 -> 56 %)**

Toto je jediný soubor, kde se úroveň kontextu projeví dramaticky:

| Úroveň | Ø `crud.py` | Δ vs L0       |
|---|---|---------------|
| L0 | 39,28 % | -             |
| L1 | **56,43 %** | **+17,15 pp** |
| L2 | 54,83 % | +15,55 pp     |
| L3 | 53,75 % | +14,47 pp     |
| L4 | 53,18 % | +13,90 pp     |

L1 je opět inflexní bod. Byznys dokumentace zřejmě popisuje workflow (vytvoření autora -> knihy -> objednávky), což modelu pomáhá generovat testy procházející více CRUD funkcemi. Od L2 výše coverage mírně klesá - model se v bohatším kontextu soustředí na menší počet endpointů, ale testuje je důkladněji.

### 3.3 Které funkce model pokrývá a které ignoruje

**Konzistentně pokryté funkce (odvozeno z endpointového pokrytí):**

Napříč všemi úrovněmi model vždy testuje:

| Funkce / Endpoint | Pokrytí | Proč |
|---|---|---|
| `POST /authors` (create_author) | 25/25 runů | Jednoduchý POST, jasná struktura |
| `GET /authors/{id}` (get_author) | 24/25 runů | Základní CRUD read |
| `POST /books` (create_book) | 25/25 runů | Hlavní entita systému |
| `GET /books/{id}` (get_book) | 25/25 runů | Základní read |
| `DELETE /books/{id}` | 22/25 runů | Jednoduchý delete |
| `DELETE /authors/{id}` | 20/25 runů (L0 ne) | Vyžaduje znalost kaskádního mazání |
| `POST /orders` (create_order) | 25/25 runů | Business-critical |
| `PATCH /orders/{id}/status` | 25/25 runů | Ale často failed! |

**Systematicky ignorované funkce:**

| Funkce / Endpoint | Ignorováno | Pravděpodobná příčina                                                    |
|---|---|--------------------------------------------------------------------------|
| `GET /categories`, `POST /categories`, `PUT /categories/{id}`, `DELETE /categories/{id}` | 25/25 runů ignorováno | Celá doména kategorií je opomíjena - model se soustředí na books/authors |
| `GET /tags`, `GET /tags/{id}`, `PUT /tags/{id}`, `DELETE /tags/{id}` | 25/25 runů | Stejný vzorec jako kategorie - "vedlejší" entity                         |
| `GET /orders`, `GET /orders/{id}`, `GET /orders/{id}/invoice` | 25/25 runů | Model vytváří objednávky, ale nečte je zpět                              |
| `DELETE /orders/{id}` | 22/25 runů | Model neví, zda jsou objednávky mazatelné                                |
| `GET /books/{id}/cover`, `DELETE /books/{id}/cover` | 25/25 runů | Multipart/binary operace = model se jim vyhýbá                           |
| `GET /books/{id}/rating`, `GET /books/{id}/reviews` | 25/25 runů | Odvozená data - model preferuje primární CRUD                            |
| `GET /authors/{id}/books` | 25/25 runů | Nested resource - model testuje entity izolovaně                         |
| `POST /reset` | 25/25 runů | Model endpoint nezná nebo ho nepoužívá jako setup                        |
| `GET /admin/maintenance` | 24/25 runů | Admin endpoint - model ho považuje za out-of-scope                       |
| `GET /catalog` | 23/25 runů | Agregovaný read endpoint - model preferuje jednotlivé GETy               |
| `GET /statistics/summary` | 23/25 runů | Analytický endpoint                                                      |
| `POST /exports/orders`, `GET /exports/{job_id}` | 25/25 runů (orders), 19/25 (job_id) | Asynchronní workflow - vyžaduje multi-step choreografii                  |

### 3.4 Rozptyl Coverage v rámci úrovní

| Úroveň | Min celk. | Max celk. | Spread | Min `crud.py` | Max `crud.py` | Spread |
|---|---|---|---|---|---|---|
| L0 | 67,49 % | 69,57 % | 2,08 pp | 37,47 % | 42,89 % | 5,42 pp |
| L1 | 71,66 % | 75,92 % | 4,26 pp | 50,13 % | 60,21 % | 10,08 pp |
| L2 | 72,65 % | 75,82 % | 3,17 pp | 52,45 % | 58,66 % | 6,21 pp |
| L3 | 71,26 % | 74,63 % | 3,37 pp | 48,84 % | 56,33 % | 7,49 pp |
| L4 | 71,85 % | 75,22 % | 3,37 pp | 49,61 % | 56,07 % | 6,46 pp |

L0 je paradoxně **nejstabilnější** (nejmenší spread) - s minimem kontextu model generuje velmi podobné testy pokaždé. L1 má největší variabilitu v `crud.py` (10 pp spread), což odpovídá tomu, že byznys dokumentace otevírá více možností, ale model nedeterministicky vybírá, které z nich využije.

---

## 4. Proč se to děje? (Kauzalita a obhajoba)

### 4.1 Proč L1 je inflexní bod, ne L4

Hlavní zjištění tohoto experimentu: **nejcennější informací pro DeepSeek není zdrojový kód ani ukázkové testy, ale byznys dokumentace** (přidaná v L1). Proč?

1. **OpenAPI spec (L0) říká CO existuje** - endpointy, parametry, response schémata. Model z toho umí vygenerovat syntakticky správné requesty, ale nerozumí *proč* existují a jak spolu souvisí.

2. **Byznys dokumentace (L1) říká PROČ a JAK** - vysvětluje business pravidla (stavový automat objednávek, validace, autorizace). To modelu umožní generovat smysluplné error testy namísto náhodných kombinací parametrů.

3. **Zdrojový kód (L2) přidává implementační detail**, ale marginální přínos klesá - model už z L1 ví, co testovat, a kód mu přidá jen edge-case znalosti (konkrétní validační pravidla, rate limity).

4. **DB schéma (L3) je téměř irelevantní** - přidá jen 844 tokenů a žádný nový testovatelný behaviour. Coverage i validity se prakticky nezmění.

5. **Ukázkové testy (L4) mají ambivalentní efekt** - zlepší endpoint coverage (model se inspiruje šířkou), ale **posunou test type distribuci dramaticky k error testům** (70,7 % error vs 51,3 % happy_path na L0). Model kopíruje styl existujících testů, který je zřejmě error-heavy.

### 4.2 Proč Endpoint Coverage nekoresponduje s Code Coverage

| Metrika | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| EP Coverage | 40,8 % | 36,8 % | 34,8 % | 37,6 % | 44,8 % |
| Code Coverage (crud.py) | 39,3 % | 56,4 % | 54,8 % | 53,8 % | 53,2 % |

EP Coverage klesá L0->L2, zatímco Code Coverage roste. To znamená: **model testuje méně endpointů, ale hlouběji**. Jeden endpoint testovaný s 3 error scénáři pokryje více CRUD kódu než 3 endpointy testované jedním happy-path testem.

### 4.3 Anomálie a jejich vysvětlení

**Anomálie 1: L0 run2 - nejhorší validity (83,33 %)**

Run2 má 5 stale testů, většina na `test_update_order_status_valid` a export-related testech. Bez byznys dokumentace model hádá stavový automat objednávek a export workflow - a hádá špatně. Opravný loop nepomůže, protože model nemá informace potřebné k opravě.

**Anomálie 2: L1 run2 - elapsed time 6 237 s (vs Ø 300 s)**

Run2 na L1 trval **104 minut** místo typických 5. Přitom dosáhl 100 % validity v pouhých 2 iteracích. Pravděpodobně se jedná o **síťový problém nebo rate-limiting** na straně DeepSeek API - samotný model pracoval normálně.

**Anomálie 3: L3 run2 - nejnižší validity na L3 (90 %) ale nejvyšší EP Coverage (24/50)**

Tento run obětoval validitu za šířku. Model se pokusil pokrýt více endpointů, ale na úkor správnosti - 3 testy selhaly. Je to příklad trade-offu **depth vs breadth** v rámci fixního budgetu 30 testů.

**Anomálie 4: L4 - regrese v repair iteracích**

L4 run2 a run4 vykazují unikátní vzorec: ve 3. iteraci oprav se počet failů zvýší (z 1 na 3), pak se v 4. iteraci vrátí na 1. To naznačuje, že s 53k tokeny kontextu model **ztrácí koherenci** při opravách - oprava jednoho testu může rozbít jiný, protože model nedrží celý kontext v "paměti".

**Anomálie 5: L4 dramatický posun k error testům**

L4 runuje generují v průměru 70,7 % error testů (vs 47–50 % na L0–L3). Run4 dokonce 80 % errorů a jen 6,67 % happy-path. Ukázkové testy v kontextu zřejmě obsahují převahu error scénářů, a model tuto distribuci kopíruje. To vysvětluje i vyšší EP Coverage na L4 - error testy různých endpointů pokryjí více routingového kódu.

### 4.4 Kauzální model chování DeepSeek

```
Kontext ↑  ->  Kvalita testů ↑ (assertion depth, response validation)
           ->  Šířka pokrytí ↓ (model se soustředí na méně endpointů)
           ->  Cena ~konstantní (díky cache)
           ->  Repair schopnost se nezlepšuje
           ->  Od L4: ztráta koherence, regrese při opravách
```

Model má **fixní "attention budget"**: s více kontextem ho věnuje hlubšímu testování menšího počtu endpointů. L4 částečně tento trend narušuje díky explicitním ukázkovým testům, které model "nakopnou" k širšímu pokrytí.

---

## 5. Detailní rozpis jednotlivých úrovní a běhů

<details>
<summary><strong>📊 L0 - Pouze OpenAPI specifikace (Ø validity 90,67 %, Ø EP 40,8 %, Ø coverage 68,15 %)</strong></summary>

### Komentář k L0

Model má k dispozici pouze komprimovanou OpenAPI specifikaci (~16k tokenů). Generuje **široce rozptýlené, ale mělké testy** - assertion depth je nejnižší (2,34) a response validation jen 51 %. Všech 5 runů skončí early-stopped se stale testy, které model nedokáže opravit. Nejproblematičtější oblasti jsou objednávkové workflow a file upload, kde bez dokumentace model hádá chování API.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 93,33 % | **83,33 %** | 93,33 % | **96,67 %** | 86,67 % |
| **Passed/Total** | 28/30 | 25/30 | 28/30 | 29/30 | 26/30 |
| **EP Coverage** | 20/50 | 19/50 | **22/50** | 19/50 | **22/50** |
| **Stale tests** | 2 | **5** | 2 | **1** | 4 |
| **Assertion Depth** | 2,40 | 2,27 | 1,83 | 2,07 | **3,13** |
| **Resp. Validation** | 46,67 % | 60,0 % | 36,67 % | 46,67 % | **66,67 %** |
| **Cena (USD)** | $0,011 | $0,005 | $0,005 | $0,005 | $0,005 |
| **Celk. tokeny** | 36 409 | 35 735 | 35 400 | 34 705 | 36 188 |
| **Iterace** | 3 (stale) | 3 (stale) | 3 (stale) | 3 (stale) | 3 (stale) |
| **Code Cov. celk.** | 67,79 % | 67,69 % | 67,49 % | 68,19 % | 69,57 % |
| **Code Cov. crud.py** | 38,76 % | 38,76 % | 37,47 % | 38,50 % | **42,89 %** |

**Nejčastější chyby L0:** `wrong_status_code` (12×), `test_update_order_status_valid` (stale v každém runu).

</details>

<details>
<summary><strong>📊 L1 - + Byznys dokumentace (Ø validity 96,67 %, Ø EP 36,8 %, Ø coverage 74,45 %)</strong></summary>

### Komentář k L1

Přidání byznys dokumentace (+7 825 tokenů) přináší **největší kvalitativní skok celého experimentu**. Validity stoupne o 6 pp, assertion depth o 45 %, response validation skočí z 51 % na 85 %. Model poprvé generuje testy ověřující tělo odpovědi, ne jen status kód. Dva runy (run2, run4) dosáhnou 100 % validity - to se na L0 nestalo ani jednou.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 93,33 % | **100,0 %** | 93,33 % | **100,0 %** | 96,67 % |
| **Passed/Total** | 28/30 | **30/30** | 28/30 | **30/30** | 29/30 |
| **EP Coverage** | 18/50 | 16/50 | 20/50 | 19/50 | 19/50 |
| **Stale tests** | 2 | **0** | 2 | **0** | 1 |
| **Assertion Depth** | 3,07 | 2,80 | 3,73 | **3,93** | 3,40 |
| **Resp. Validation** | 66,67 % | 86,67 % | **90,0 %** | **93,33 %** | 90,0 % |
| **Cena (USD)** | $0,010 | $0,005 | $0,009 | $0,005 | $0,006 |
| **Celk. tokeny** | 52 421 | 49 319 | 62 114 | 50 040 | 52 251 |
| **Iterace** | 3 (stale) | **2 (OK)** | 3 (stale) | **2 (OK)** | 3 (stale) |
| **Code Cov. celk.** | 74,03 % | 71,66 % | **75,92 %** | 75,62 % | 75,02 % |
| **Code Cov. crud.py** | 55,56 % | 50,13 % | 58,91 % | **60,21 %** | 57,36 % |

**Posun chyb:** Z `wrong_status_code` (L0) na `assertion_value_mismatch` (L1). Model už trefuje správné status kódy, ale občas špatně odhadne konkrétní hodnotu v response body - kvalitnější typ chyby.

</details>

<details>
<summary><strong>📊 L2 - + Zdrojový kód endpointů (Ø validity 98,0 %, Ø EP 34,8 %, Ø coverage 73,70 %)</strong></summary>

### Komentář k L2

Přidání zdrojového kódu (+20 123 tokenů) přinese **peak validity** (98 %) a nejvyšší procento side-effect checks (31,3 %). Model čte implementaci a ví přesně, jak endpointy validují vstupy. EP Coverage ale klesá na minimum (34,8 %) - se znalostí kódu model soustředí veškerou pozornost na důkladné testování menšího setu endpointů. Dva runy projdou napoprvé bez jediné opravy.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | 96,67 % | 96,67 % | **100,0 %** | 96,67 % |
| **Passed/Total** | **30/30** | 29/30 | 29/30 | **30/30** | 29/30 |
| **EP Coverage** | 17/50 | 17/50 | 17/50 | **19/50** | 17/50 |
| **Stale tests** | **0** | 1 | 1 | **0** | 1 |
| **Assertion Depth** | 2,83 | 3,17 | 3,27 | **4,00** | 3,27 |
| **Resp. Validation** | **96,67 %** | 93,33 % | 93,33 % | 93,33 % | 93,33 % |
| **Cena (USD)** | $0,013 | $0,007 | $0,006 | $0,006 | $0,006 |
| **Celk. tokeny** | 77 143 | 83 621 | 82 559 | 78 645 | 83 105 |
| **Iterace** | **1 (OK)** | 3 (stale) | 3 (stale) | **1 (OK)** | 3 (stale) |
| **Code Cov. celk.** | 73,84 % | 73,34 % | 72,84 % | **75,82 %** | 72,65 % |
| **Code Cov. crud.py** | 54,52 % | 54,78 % | 53,75 % | **58,66 %** | 52,45 % |

**Typická chyba L2:** `test_restore_soft_deleted_book` (stale 3×) - assertion_value_mismatch. Model vidí v kódu restore funkci, ale špatně predikuje response strukturu.

</details>

<details>
<summary><strong>📊 L3 - + Databázové schéma (Ø validity 96,67 %, Ø EP 37,6 %, Ø coverage 73,12 %)</strong></summary>

### Komentář k L3

DB schéma přidá pouhých 844 tokenů a **nepřinese měřitelné zlepšení** v žádné klíčové metrice. Validity se dokonce vrátí z 98 % na 96,67 %, code coverage mírně klesne. Databázové schéma je pro generování API testů irelevantní - model testuje HTTP endpointy, ne SQL dotazy. L3 je "mrtvá úroveň" experimentu.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | **100,0 %** | 90,0 % | 96,67 % | **100,0 %** | 96,67 % |
| **Passed/Total** | **30/30** | 27/30 | 29/30 | **30/30** | 29/30 |
| **EP Coverage** | 19/50 | **24/50** | 16/50 | 17/50 | 18/50 |
| **Stale tests** | **0** | **3** | 1 | **0** | 1 |
| **Assertion Depth** | 3,07 | 2,77 | 2,93 | 2,83 | 2,97 |
| **Resp. Validation** | 96,67 % | **100,0 %** | 93,33 % | 96,67 % | 96,67 % |
| **Cena (USD)** | $0,006 | $0,007 | $0,006 | $0,005 | $0,006 |
| **Celk. tokeny** | 79 203 | 85 131 | 84 320 | 78 805 | 84 318 |
| **Iterace** | **1 (OK)** | 3 (stale) | 3 (stale) | **1 (OK)** | 3 (stale) |
| **Code Cov. celk.** | 74,63 % | 71,26 % | 71,56 % | 73,93 % | 74,23 % |
| **Code Cov. crud.py** | 55,81 % | 48,84 % | 51,94 % | 56,33 % | 55,81 % |

**Run2 anomálie:** Nejnižší validity (90 %) ale nejvyšší EP Coverage (24/50). Model se pokusil o široký záběr a 3 testy selhaly - klasický breadth/depth trade-off.

</details>

<details>
<summary><strong>📊 L4 - + Ukázkové testy (Ø validity 97,33 %, Ø EP 44,8 %, Ø coverage 73,50 %)</strong></summary>

### Komentář k L4

Přidání ukázkových testů (+8 654 tokenů) má **překvapivý a ambivalentní efekt**. EP Coverage skočí na maximum (44,8 %) a status code diversity dosahuje rekordních 16 unikátních kódů. Model se inspiruje stylem existujících testů a pokrývá širší spektrum endpointů. Zároveň ale dramaticky posune test type distribuci k error testům (71 % errorů), sníží side-effect checks na 10 %, a vykazuje jako jediná úroveň **regrese v repair loop** (testy se opravou rozbijí). Compliance score stoupne na 100 ve všech runech - model kopíruje coding conventions z ukázek.

| Metrika | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| **Validity** | 96,67 % | 96,67 % | **100,0 %** | 96,67 % | 96,67 % |
| **Passed/Total** | 29/30 | 29/30 | **30/30** | 29/30 | 29/30 |
| **EP Coverage** | 23/50 | 23/50 | 18/50 | **25/50** | 23/50 |
| **Stale tests** | 1 | 1 | **0** | 1 | 1 |
| **Assertion Depth** | 2,40 | 2,80 | **3,73** | 2,37 | 3,53 |
| **Resp. Validation** | **100,0 %** | **100,0 %** | 96,67 % | 96,67 % | **100,0 %** |
| **Cena (USD)** | $0,011 | $0,008 | $0,006 | $0,007 | $0,007 |
| **Celk. tokeny** | 99 818 | 103 770 | 95 463 | 103 245 | 100 893 |
| **Iterace** | 3 (stale) | **4 (regrese!)** | **1 (OK)** | **4 (regrese!)** | 3 (stale) |
| **Status Diversity** | 14 | 14 | 11 | **16** | 13 |
| **Happy/Error/Edge** | 4/25/1 | 7/21/2 | **18/12/0** | 2/24/4 | 5/24/1 |
| **Code Cov. celk.** | 73,54 % | 71,85 % | 74,53 % | **75,22 %** | 72,35 % |
| **Code Cov. crud.py** | 53,49 % | 49,61 % | 56,07 % | 54,01 % | 52,71 % |

**Run3 je outlier:** Jako jediný na L4 má vyvážený happy/error poměr (60/40 %), dosáhne 100 % validity napoprvé, a má nejvyšší assertion depth (3,73). Ostatní runy jsou dominantně error-testové.

**Regrese v run2 a run4:** Repair trajektorie: 29p/1f -> 29p/1f -> **27p/3f** -> 29p/1f. Model při opravě jednoho testu rozhodí kontext a rozbije další dva. Toto se děje výhradně na L4 (53k tokenů) - indikátor ztráty koherence ve velkém kontextu.

</details>

---

## Závěrečné shrnutí pro obhajobu

### Hlavní příběh dat

**DeepSeek-Chat je cost-effective, spolehlivý, ale konzervativní generátor API testů.** Klíčové zjištění je, že **byznys dokumentace (L1) má největší ROI** - z pohledu validity, assertion depth, response validation i code coverage přináší největší zlepšení za nejmenší přírůstek kontextu. Zdrojový kód (L2) přidá marginální přínos ve validity, DB schéma (L3) je irelevantní, a ukázkové testy (L4) zlepší šířku pokrytí za cenu kvality a stability oprav.

### Čísla pro obhajobu

| Tvrzení | Podpora v datech                                                           |
|---|----------------------------------------------------------------------------|
| Přidání kontextu zlepšuje kvalitu testů | Assertion depth: 2,34 (L0) -> 3,39 (L1); Response validation: 51 % -> 85 % |
| Byznys dokumentace je nejcennější kontext | L0->L1: +6 pp validity, +17 pp crud coverage, +34 pp response validation   |
| Existuje diminishing returns od L2 | L2->L3->L4: validity stagnuje na 96–98 %, coverage osciluje ±2 pp          |
| Model se zasekává při opravách | 18/25 běhů má stale testy; repair loop je neúčinný                         |
| Velký kontext může škodit | L4: regrese v repair, ztráta koherence, bias k error testům                |
| DeepSeek je extrémně levný | $0,005–$0,013 za run; $0,00025 za úspěšný test                             |
| Model systematicky ignoruje celé domény | Kategorie, tagy, exporty, admin - 0 % pokrytí ve všech 25 runech           |