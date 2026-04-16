# 📊 Vibe Testing Framework v12 - Komparativní analýza tří LLM

> **Datový zdroj:** 3 × JSON experiment files + 3 × analytické reporty (DeepSeek-Chat, Gemini 3.1 Flash Lite Preview, Mistral Large 2512)
> **Rozsah:** 75 experimentálních běhů (3 modely × 5 úrovní × 5 runů)
> **API:** Bookstore (50 endpointů, FastAPI + SQLAlchemy + SQLite)
> **Teplota:** 0.4 · **Cílový počet testů:** 30 / run · **Datum analýzy:** 16. 4. 2026

---

## 0. Úvod - co tento report odpovídá

Diplomový experiment zkoumá, jak rostoucí úroveň kontextu (**L0 -> L4**) ovlivňuje kvalitu a pokrytí automaticky generovaných API testů, a zda se tento vliv liší napříč LLM modely z odlišných ekosystémů (americký ← Gemini od Googlu, čínský ← DeepSeek, evropský ← Mistral).

- **RQ1** a **RQ2** agregují výsledky **přes všechny tři modely** (aritmetický průměr na úrovni model -> level -> metrika, následně průměr přes modely pro každou úroveň). To odpovídá designu výzkumných otázek v ABOUT.md.
- **RQ3** naopak modely **explicitně odlišuje** a zkoumá jejich systematické rozdíly v chování, konvergenci s rostoucím kontextem a nákladovou efektivitu.

### Rekapitulace úrovní kontextu

| Úroveň | Obsah | Odhad tokenů (po kompresi) |
|---|---|---|
| **L0** | OpenAPI specifikace | ~15 958 |
| **L1** | + Byznys/technická dokumentace | ~23 783 |
| **L2** | + Zdrojový kód endpointů | ~43 917 |
| **L3** | + Databázové schéma | ~44 770 |
| **L4** | + Existující testy | ~53 438 |

---

## 1. RQ1 - Validita, kvalita a testovací strategie (průměr 3 modelů)

> **Otázka:** Jak rostoucí úroveň kontextu (L0–L4) ovlivňuje **Test Validity Rate**, **hloubku asercí**, **distribuci testovacích scénářů** a **diverzitu ověřovaných HTTP status kódů**?

### 1.1 Hlavní tabulka - cross-model průměry

| Metrika | L0 | L1 | L2 | L3 | L4 | Trend |
|---|---|---|---|---|---|---|
| **Validity Rate %** | 89,11 | **97,78** ⭐ | 94,89 | 92,44 | 90,00 | Obrácené U, peak L1 |
| **Assertion Depth** | 1,89 | 2,40 | **2,51** ⭐ | 2,47 | 2,42 | Roste, peak L2 |
| **Response Validation %** | 43,11 | 60,22 | 68,00 | 71,33 | **71,78** ⭐ | Monotónně roste |
| **Status Code Diversity** | 11,60 | 12,27 | 12,67 | 12,53 | **13,07** ⭐ | Mírně roste |
| **Stale Tests (ø na run)** | 3,27 | **0,67** ⭐ | 1,53 | 2,73 | 3,00 | U-křivka, minimum L1 |

### 1.2 Distribuce typů testů (průměr 3 modelů)

| Úroveň | Happy Path % | Error % | Edge Case % |
|---|---|---|---|
| **L0** | 48,22 | 47,11 | 4,67 |
| **L1** | 50,44 | 46,44 | 3,11 |
| **L2** | 43,11 | 52,67 | 4,22 |
| **L3** | 42,22 | 54,67 | 3,11 |
| **L4** | **34,89** | **60,22** | 4,89 |

**Posun ve strategii:** S rostoucím kontextem modely systematicky přesouvají váhu od happy-path k error scénářům. Na **L4 tvoří error testy 60 %** (vs. 47 % na L0). Bohatší kontext umožňuje formulovat specifičtější negativní scénáře (rate limits, constraint violations, state-machine tranzice).

### 1.3 Klíčová zjištění RQ1

**(1) Validity má tvar obráceného U s peakem na L1.**
Přidání byznys/technické dokumentace (L0 -> L1) přinese **+8,67 pp validity** - nejvyšší kvalitativní skok celého experimentu. Další úrovně (L2 – L4) validity **monotónně snižují** z 94,89 % na 90,00 %. Mechanismus: od L2 výš dostávají modely zdrojový kód a začínají generovat **ambicióznější, ale křehčí testy** (soft-delete, discount logic, state-machine tranzice), jejichž očekávané chování špatně odvodí z kódu.

**(2) Hloubka asercí a validace odpovědí jdou jinými cestami.**
- `assertion_depth` peak na L2 (2,51) a pak klesá - modely mají fixní "attention budget".
- `response_validation_pct` **monotónně roste** z 43 % (L0) na 72 % (L4) - s více kontextem modely konzistentně přechází od "ověřím jen status code" k "ověřím i obsah odpovědi".

**(3) Strategie "breadth -> depth" je viditelná v distribuci testů.**
L0-L1 = vyvážený mix happy/error (~50/50). L4 = posun k error-heavy testům (60 %). Status code diversity roste z 11,6 na 13,1 - modely s více kontextem ověřují širší škálu HTTP kódů (409 Conflict, 422 Unprocessable, 429 Too Many Requests).

**(4) Stale-tests křivka je U-shape s minimem na L1.**
L1 je jediná úroveň s **méně než 1 stale test na run**. Na L0 chybí kontext pro správné odhady (-> wrong status code). Od L3-L4 naopak modely začínají generovat testy předpokládající chování, které API ve skutečnosti nemá (halucinace z bohatého kontextu).

### 1.4 Verdikt RQ1

> **Vztah mezi kontextem a validitou NENÍ monotónní.** Existuje bod nasycení okolo L1-L2, za kterým přidávání kontextu zhoršuje validitu, i když současně mírně zlepšuje hloubku testů (response validation, diverzitu statusů). Optimální kompromis mezi validitou a kvalitou je **L1 pro stabilitu** a **L2 pro nejvyšší hloubku asercí**. Přidání DB schématu (L3) je měřitelně škodlivé. Ukázkové testy (L4) produkují nejkomplexnější testy, ale za cenu nejnižší validity a nejvyššího počtu stale testů.

---

## 2. RQ2 - Strukturální pokrytí (průměr 3 modelů)

> **Otázka:** Jak úroveň kontextu ovlivňuje **endpoint coverage** (pokrytí koncových bodů API) a **code coverage** (pokrytí zdrojového kódu)? Hypotéza: endpoint coverage saturuje brzy (L0), zatímco code coverage vykazuje ostrý skok při zpřístupnění zdrojového kódu (L2).

### 2.1 Hlavní tabulka - cross-model průměry

| Úroveň | Endpoint Coverage % | Code Coverage total % | `crud.py` % | `main.py` % |
|---|---|---|---|---|
| **L0** | 35,87 | 65,78 | 34,75 | 68,44 |
| **L1** | 34,53 | 69,82 | **44,86** ⭐ | 69,01 |
| **L2** | 35,20 | **70,14** ⭐ | 45,13 | **69,76** ⭐ |
| **L3** | 34,00 | 69,35 | 43,65 | 69,00 |
| **L4** | **39,73** ⭐ | 69,05 | 42,74 | 69,14 |

### 2.2 Endpoint Coverage - saturace a oscilace

- Endpoint coverage **od L0 do L3 osciluje v pásmu 34–36 %** - saturace nastává okamžitě, bohatší kontext jejich šířku nezvětšuje.
- **L4 přináší jedinou zřetelnou výjimku (+4 pp na 39,7 %)** - ukázkové testy fungují jako "roadmap" a modely z nich kopírují strukturu testovaných endpointů, včetně těch méně běžných (reviews, ratings, category listy).
- **Strukturální strop je ~50 %** - s 30 testy na 50 endpointů není možné dosáhnout 100 % bez obětování error testů. Nejlepší jednotlivý běh celého experimentu (L2 run1 Gemini) dosáhl 52 %.
- **Hypotéza o časné saturaci endpoint coverage je potvrzena**, ale s korekcí: L4 není "jen další úroveň kontextu", je to **kvalitativně jiná vrstva** (in-context learning exemplářů), která saturaci přerazí.

### 2.3 Code Coverage - skok na L1, ne na L2

Nejvýraznější nález: **Hypotéza o skoku při L2 byla FALSIFIKOVÁNA.** Skok nastává o úroveň dříve - na L1:

| Přechod  | Δ Code Cov total | Δ `crud.py` |
|----------|---|---|
| L0 -> L1 | **+4,04 pp** ⭐ | **+10,11 pp** ⭐ |
| L1 -> L2 | +0,32 pp | +0,27 pp |
| L2 -> L3 | −0,79 pp | −1,49 pp |
| L3 -> L4 | −0,31 pp | −0,91 pp |

**Proč L1, ne L2?**

- **OpenAPI (L0) popisuje povrch** - endpointy, parametry, response schémata. Modely z toho generují syntakticky správné requesty, ale nerozumí business pravidlům.
- **Byznys dokumentace (L1) odemkne business logiku** - vysvětluje workflow (vytvoření autora -> knihy -> objednávky), validační pravidla, chybové stavy. Modely začínají volat **další větve v `crud.py`** (error handling, validace), ne jen happy path.
- **Zdrojový kód (L2) přinese marginální zlepšení** - modely už z L1 vědí, co testovat, kód jim dodá jen implementační detaily (konkrétní validace, hraniční případy).
- **Soubory `__init__.py`, `database.py`, `models.py`, `schemas.py` jsou trvale na 100 %** - pokrývá je už importní čas. **Nemají diagnostickou hodnotu** pro kvalitu testů.

### 2.4 Klíčové neaskové oblasti napříč všemi modely

Napříč všemi 75 běhy 3 modelů **systematicky ignorované** moduly (0 % coverage ve > 90 % runů):

- `POST /reset` - reset database endpoint (**calls_reset = 0/75**)
- Celá doména **exports** (`POST /exports/orders`, `GET /exports/{job_id}`)
- **Admin/maintenance** endpointy
- **List endpointy** (`GET /categories`, `GET /tags`, `GET /orders`) - modely preferují mutace
- **Nested resources** (`GET /authors/{id}/books`, `GET /books/{id}/reviews`)
- **Statistics/analytics** (`GET /statistics/summary`)

### 2.5 Verdikt RQ2

> **Endpoint coverage saturuje okamžitě** (35 % od L0), **strukturální strop tvoří velikost plánu** (30 testů / 50 endpointů). Jediný signifikantní nárůst přichází na L4 díky in-context learning (+4 pp).
> **Code coverage vykazuje ostrý skok na L1, ne L2** - byznys dokumentace je efektivnější "odemykač" business logiky než zdrojový kód. Od L2 coverage stagnuje nebo mírně klesá. **Hypotéza o L2-skoku je falsifikována ve prospěch silnější hypotézy: semantický kontext (business rules) je hodnotnější než syntaktický kontext (zdrojový kód).**

---

## 3. RQ3 - Mezimodelové rozdíly

> **Otázka:** Vykazují LLM modely z odlišných ekosystémů systematické rozdíly v kvalitě generovaných testů? Zkoumá se **konvergence výkonu** s rostoucím kontextem a **nákladová efektivita**.

### 3.1 Modelové vizitky

| Model | Ekosystém | Provider | Role v experimentu |
|---|---|---|---|
| **gemini-3.1-flash-lite-preview** | 🇺🇸 USA | Google | Rychlý, ceněný za kontext; sweet spot na L1-L2 |
| **deepseek-chat** | 🇨🇳 Čína | DeepSeek | Nejlevnější; spolehlivý, ale konzervativní |
| **mistral-large-2512** | 🇪🇺 EU | Mistral AI | Nejdražší; stabilní, bez self-correction |

### 3.2 Kompletní srovnání klíčových metrik

#### 3.2.1 Validity Rate - kdo generuje testy, které projdou?

| Úroveň | DeepSeek | Gemini | Mistral | Cross Avg |
|---|---|---|---|---|
| **L0** | 90,67 % | 80,00 % | **96,67 %** | 89,11 % |
| **L1** | 96,67 % | 97,34 % | **99,33 %** | 97,78 % |
| **L2** | **98,00 %** | 94,00 % | 92,67 % | 94,89 % |
| **L3** | **96,67 %** | 90,67 % | 90,00 % | 92,44 % |
| **L4** | **97,33 %** | 80,67 % | 92,00 % | 90,00 % |
| **Ø celkem** | **95,87 %** ⭐ | 88,53 % | 94,13 % | 92,84 % |

**Pozorování:**

- **DeepSeek je nejkonzistentnější napříč všemi úrovněmi** - jeho minimum je 90,7 % (L0), maximum 98,0 % (L2). Úzké rozpětí 7,3 pp.
- **Mistral má abnormálně silný start** - jako jediný začíná na L0 na 96,7 %, ale od L2 klesá (92-90 %). Generuje velmi konzervativní testy s nízkou assertion depth, které "neambicují -> neselhávají".
- **Gemini trpí nejvíc information overload** - rozpětí 80-97 %, L4 kolabuje zpět na 80,7 %. Z třech modelů nejcitlivější na velikost kontextu.

#### 3.2.2 Endpoint Coverage - kdo pokryje nejširší spektrum API?

| Úroveň | DeepSeek | Gemini | Mistral | Cross Avg |
|---|---|---|---|---|
| **L0** | **40,80 %** | 38,80 % | 28,00 % | 35,87 % |
| **L1** | 36,80 % | **39,20 %** | 27,60 % | 34,53 % |
| **L2** | 34,80 % | **44,00 %** | 26,80 % | 35,20 % |
| **L3** | 37,60 % | **39,20 %** | 25,20 % | 34,00 % |
| **L4** | **44,80 %** | 43,60 % | 30,80 % | 39,73 % |
| **Ø celkem** | 38,96 % | **40,96 %** ⭐ | 27,68 % | 35,87 % |

**Pozorování:**

- **Gemini je "explorer"** - průměrná coverage 41,0 %, maximum 52 % (L2 run1). Generuje plány s širší distribucí endpointů.
- **Mistral je "exploiter"** - stabilně 25-31 %, vždy se soustředí na authors + books. Naprosto nejnižší variance (na L0 všech 5 běhů = přesně 28 %).
- **DeepSeek je mezi nimi** (39 %), ale vykazuje zajímavý vzor: nejširší coverage na L0 a L4 (40,8 %, 44,8 %), nejužší na L2 (34,8 %). Na L2 přetočí na "depth" místo "breadth".

#### 3.2.3 Code Coverage (`crud.py` - klíčový diferenciátor)

| Úroveň | DeepSeek | Gemini | Mistral |
|---|---|---|---|
| **L0** | 39,28 % | 28,32 % | 36,64 % |
| **L1** | **56,43 %** ⭐ | 40,93 % | 37,21 % |
| **L2** | 54,83 % | **41,40 %** | 39,17 % |
| **L3** | 53,75 % | 40,05 % | 37,14 % |
| **L4** | 53,18 % | 35,45 % | **39,59 %** |
| **Range** | 17,15 pp | 13,08 pp | **2,95 pp** |

**Pozorování:**

- **DeepSeek nejlépe využívá kontext** - jeho `crud.py` coverage skočí o +17,15 pp z L0 na L1. Žádný jiný model tak ostrý skok nemá.
- **Mistral je vůči kontextu téměř "hluchý"** - `crud.py` coverage osciluje v pásmu 36,6-39,6 %, rozpětí jen 2,95 pp. Model se drží vždy přibližně stejné sady CRUD operací.
- **Gemini má obrácené U s peakem L2** (41,4 %), pak padá na L4 (35,5 %) - klasický information-overload signatura.

#### 3.2.4 Nákladová efektivita

| Úroveň | DeepSeek | Gemini | Mistral | Cross   |
|---|---|---|---|---------|
| **L0 cena/run** | $0,0061 | $0,0168 | $0,0231 | $0,0153 |
| **L4 cena/run** | $0,0078 | $0,0298 | **$0,0657** | $0,0344 |
| **Ø cena/run** | **$0,0069** ⭐ | $0,0229 | $0,0449 | $0,0249 |
| **Ø tokens/run** | ~70 585 | ~81 842 | ~73 880 | ~75 435 |
| **100 %-runs** | **7/25** | 4/25 | **7/25** | -       |
| **Ø cena / úspěšný test** | ~$0,00024 | ~$0,00086 | ~$0,00159 | -       |

**Dramatický rozdíl:**

- **Mistral je ~6,5× dražší než DeepSeek** při srovnatelné validity. Důvod: DeepSeek má agresivní prompt-caching (~85 % hit rate na L4), což reálnou cenu drží nízko bez ohledu na velikost kontextu.
- **Mistral navíc škáluje nejhůř** - jeho cena roste z $0,023 (L0) na $0,066 (L4), tj. **+184 %**, zatímco DeepSeek jen **+28 %**.

#### 3.2.5 Self-correction (repair loop)

| Model | Self-correction rate | Stale tests avg | Popis chování                                                                                                  |
|---|---|---|----------------------------------------------------------------------------------------------------------------|
| **DeepSeek** | ~20 % (7/25 perfektní) | 1,24 | Repair je převážně mrtvý - model opakuje stejnou chybu. Ale startuje nejčistší kód, takže repair není potřeba. |
| **Gemini** | **L2: 81 %**, jinde 0-20 % | 3,72 | **Nejvyšší self-correction na L2** - a zároveň kolaps na L4 (regrese v iteraci 5 -> ztráta koherence).         |
| **Mistral** | **0 %** (24/25 runů) | 1,76 | **Téměř nulová** - opravil pouze 1 test v celém experimentu (L4 run4). Každá iterace po první je čistá ztráta. |

### 3.3 Konvergence napříč úrovněmi - konvergují modely s rostoucím kontextem?

**Validity (standardní odchylka 3 modelů na každé úrovni):**

| Úroveň | σ (validity) | Interpretace                                                  |
|---|---|---------------------------------------------------------------|
| L0 | **8,48 pp** | Největší rozptyl - každý model reaguje na holou OpenAPI jinak |
| L1 | **1,38 pp** | **Nejmenší rozptyl - modely konvergují** ⭐                    |
| L2 | 2,75 pp | Divergence začíná                                             |
| L3 | 3,53 pp | Divergence se prohlubuje                                      |
| L4 | **8,66 pp** | Návrat k divergenci (Gemini padá)                             |

**Klíčové zjištění:** Modely **konvergují nejvíc na L1** (ø validity rozpětí 96,7-99,3 %). Od L2 výš jejich chování opět diverguje - každý model reaguje na "information overload" jinak (Gemini kolabuje, DeepSeek zůstává stabilní, Mistral mírně klesá). **L1 lze interpretovat jako "univerzální sweet spot"** napříč ekosystémy.

### 3.4 Kauzální profily modelů - jak se liší jejich "rozhodovací styl"

**🇨🇳 DeepSeek-Chat - "Konzervativní specialista"**
- Generuje úzký, ale hluboký plán (34-45 % EP coverage, 53-56 % `crud.py`).
- **Nejlepší ROI na L1** - +17 pp `crud.py` coverage z L0. Byznys dokumentace mu dává přesně tu informaci, kterou potřebuje.
- Repair loop je ale **mrtvý** - model se zasekává na stejných chybách (`test_restore_soft_deleted_book`, `test_update_order_status_valid`).
- Aggressive prompt caching -> cena nerezonuje s velikostí kontextu.
- **Silné stránky:** cena, hloubka CRUD testů, stabilita napříč úrovněmi.
- **Slabé stránky:** systematicky ignoruje 60+ % endpointů, nerozumí multi-step workflow (exporty, order state machine).

**🇺🇸 Gemini 3.1 Flash Lite Preview - "Ambiciózní explorer s information overload"**
- Nejvyšší endpoint coverage (41 %), dosáhne maximum 52 %.
- **Nejsilnější self-correction na L2 (81 %)** - v některých úrovních umí opravit vlastní chyby.
- **Ale nejcitlivější na overload** - L4 validity kolabuje na 80,7 %, status-code drift vyskočí z 1,6 (L1) na 7,4 (L4).
- Repair regression na L3 run5 a L4 (model "opravou" rozbije další testy).
- **Silné stránky:** šíře pokrytí, self-correction na střední kontextu, coverage variance.
- **Slabé stránky:** information overload, vysoký rozptyl, kolaps na L4.

**🇪🇺 Mistral Large 2512 - "Neflexibilní bezpečná volba"**
- **Nejvyšší validity na L0 (96,7 %) a L1 (99,3 %)** - konzervativní plán, jednoduché asserce.
- Ale **téměř imunní vůči kontextu** - `crud.py` coverage se pohybuje v pásmu 36,6-39,6 % napříč všemi 5 úrovněmi.
- **0 % self-correction** ve 24 z 25 běhů - repair loop je úplně marný.
- Nejdražší - žádný prompt caching, cena lineárně roste s kontextem.
- **Silné stránky:** nejvyšší validita na malém kontextu, prediktabilita (nejnižší variance EP coverage).
- **Slabé stránky:** cena, absence self-correction, neutilizace bohatého kontextu (L3-L4 je mrtvá investice).

### 3.5 Tabulka systematických rozdílů - who wins where

| Kategorie | 🏆 Winner | Runner-up | Loser |
|---|---|---|---|
| **Nejvyšší avg validity** | 🇨🇳 DeepSeek (95,9 %) | 🇪🇺 Mistral (94,1 %) | 🇺🇸 Gemini (88,5 %) |
| **Nejvyšší peak validity** | 🇪🇺 Mistral L1 (99,3 %) | 🇨🇳 DeepSeek L2 (98,0 %) | 🇺🇸 Gemini L1 (97,3 %) |
| **Nejnižší validity rozpětí** | 🇨🇳 DeepSeek (7,3 pp) | 🇪🇺 Mistral (9,3 pp) | 🇺🇸 Gemini (17,3 pp) |
| **Nejvyšší EP coverage** | 🇺🇸 Gemini (41,0 %) | 🇨🇳 DeepSeek (39,0 %) | 🇪🇺 Mistral (27,7 %) |
| **Nejvyšší code coverage** | 🇨🇳 DeepSeek (L1: 74,5 %) | 🇺🇸 Gemini (L2: 68,7 %) | 🇪🇺 Mistral (~67 %) |
| **Nejlepší self-correction** | 🇺🇸 Gemini (L2: 81 %) | 🇨🇳 DeepSeek (~20 %) | 🇪🇺 Mistral (~0 %) |
| **Nejlevnější provoz** | 🇨🇳 DeepSeek ($0,007/run) | 🇺🇸 Gemini ($0,023/run) | 🇪🇺 Mistral ($0,045/run) |
| **Nejlepší ROI z kontextu** | 🇨🇳 DeepSeek (+17 pp crud) | 🇺🇸 Gemini (+13 pp crud) | 🇪🇺 Mistral (+3 pp crud) |
| **Nejodolnější vůči overload** | 🇨🇳 DeepSeek | 🇪🇺 Mistral | 🇺🇸 Gemini |

### 3.6 Verdikt RQ3

> **Ano, mezi modely z různých ekosystémů existují systematické rozdíly, které jsou strukturální, ne náhodné.**
>
> - **DeepSeek (🇨🇳)** se profiluje jako "depth specialist" - vysoká validita, excelentní code coverage v `crud.py`, nejlevnější, ale se systematicky ignorovanými doménami.
> - **Gemini (🇺🇸)** je "breadth explorer" s nejvyšším endpoint coverage a nejlepší self-correction schopností na L2, ale extrémně citlivý na information overload na L4.
> - **Mistral (🇪🇺)** je "safe choice" s nejvyšší peak validity na L1, ale bez schopnosti využít bohatší kontext nebo se opravit - a 6× dražší než DeepSeek.
>
> **Konvergence:** Všechny tři modely dosahují **maximální shody na L1** (ø rozptyl validity 1,4 pp). L1 je univerzální sweet spot napříč ekosystémy - byznys dokumentace odemyká nejvíc business logiky za nejmenší kontextovou cenu.
>
> **Divergence** se zvětšuje od L2 výš - každý model reaguje na "příliš mnoho kontextu" jinak (Gemini kolabuje, DeepSeek stagnuje, Mistral je indiferentní). Tato divergence je **ekosystémově specifická** a pravděpodobně souvisí s rozdílnými tréninkovými strategiemi a architekturou attention mechanismu jednotlivých modelů.

---

## 4. Shrnutí a implikace pro praxi

### 4.1 Tři klíčové teze experimentu

1. **Optimum kontextu je L1, ne L4.** Cross-model průměry ukazují peak validity, minimum stale testů a nejvyšší code-coverage ROI právě na L1. Každá další úroveň je už v zóně diminishing returns (L2) nebo negativního výnosu (L3, L4).

2. **Hypotéza o skoku code coverage na L2 je falsifikována.** Skok přichází na L1 (+10,11 pp na `crud.py`). **Byznys dokumentace je hodnotnější než zdrojový kód** pro generování efektivních API testů.

3. **Volba LLM matter, ale méně než volba kontextové úrovně.** Rozdíl mezi modely na jedné úrovni je typicky 5-15 pp, rozdíl mezi úrovněmi téhož modelu 10-25 pp. **Optimalizace kontextu je větší pákou než optimalizace modelu.**

### 4.2 Praktická doporučení

**Pro výběr kontextu:**
- Default = **L1** (OpenAPI + byznys dokumentace).
- Přidat L2 (zdrojový kód) jen pokud chci maximální assertion depth.
- **Vyhnout se L3** - DB schéma je "toxický kontext" pro všechny tři modely.
- **L4 použít opatrně** - zvyšuje endpoint coverage, ale zhoršuje validitu a je nejdražší.

**Pro výběr modelu:**
- **Cost-sensitive, reliable CRUD testing:** DeepSeek-Chat.
- **Breadth coverage / exploratory testing:** Gemini na L2 (kde má nejlepší self-correction).
- **Safety-first, conservative tests on minimal context:** Mistral na L1.

**Pro framework design:**
- Repair loop je efektivní jen u Gemini na L2. **Default max_iterations = 1** pro Mistral, **2-3** pro DeepSeek, **3-5** pro Gemini.
- Explicitně instruovat modely k volání `POST /reset` - žádný model to nedělá spontánně.
- **Rozšířit plán z 30 na 50 testů** - odstranilo by strukturální strop endpoint coverage (~35 % -> ~50 %).
- Přidat do promptu "povinné doménové sloty" - donutit modely testovat ignorované oblasti (orders, exports, admin).

### 4.3 Omezení platnosti výsledků

- **Jediné API** (Bookstore, FastAPI). Generalizace na GraphQL, gRPC, event-driven API nebyla validována.
- **5 runů / level** -> statistická robustnost je omezená. Doporučuje se ≥10 runů pro confidence intervaly < 3 pp.
- **Jedna teplota (0,4)** - chování při teplotě 0,0 (deterministické) vs 1,0 (divergentní) není známé.
- **Jeden dotaz na každý model ve třídě velikosti** - malý Mistral, střední DeepSeek a malý Gemini by mohly mít jiné profily než testované varianty.
- **Coverage dat:** pro Mistrala některé hodnoty odvozeny ze souhrnných reportů, ne přímo z JSON (JSON obsahuje endpoint coverage, ale ne code coverage - ta vzniká samostatným `run_coverage_manual.py`).

---

## 5. Dodatek - metodologie agregace

### 5.1 Jak byly počítány průměry RQ1 a RQ2

Pro každou dvojici (model, úroveň) byl spočítán aritmetický průměr přes 5 runů. Následně byly tyto tři hodnoty (po jedné za model) zprůměrovány na úroveň. Tento postup je **robustnější než vážený průměr všech 75 runů**, protože:

1. Každý model přispívá stejnou vahou - nepřeváží se více-runový outlier jednoho modelu.
2. Odpovídá designu experimentu: zajímá nás chování "typického LLM", ne populace runů.
3. V souladu s ABOUT.md: *"výsledky jsou agregovány přes všechny testované modely"*.

### 5.2 Proč není k dispozici konfidenční interval

Pro 3 modely × 1 úroveň máme jen 3 body -> σ je velmi nestabilní odhad. Konfidenční intervaly jsou smysluplné až při N ≥ 8-10 modelů. Tento report uvádí průměry a mezimodelové rozpětí (range) místo CI.

### 5.3 Zdrojové soubory

| Soubor | Obsah |
|---|---|
| `experiment_diplomka_v12_20260415_165515.json` | DeepSeek-Chat, 25 runů |
| `experiment_diplomka_v12_20260416_073106.json` | Gemini 3.1 Flash Lite, 25 runů |
| `experiment_diplomka_v12_20260415_220449.json` | Mistral Large 2512, 25 runů |
| `v12_deepseek.md`, `v12_gemini.md`, `v12_mistral.md` | Per-model analytické reporty |
| `ABOUT.md` | Popis frameworku, definice RQ1-RQ3 |
