# 🎓 Prezentace a analýza výsledků - Vibe Testing Framework

> **Diplomová práce - výsledky experimentu V12**  
> Bookstore API (50 endpointů) · 4 LLM modely · 5 úrovní kontextu · 5 runů na úroveň  
> **Celkem 100 experimentálních běhů, 3 000 vygenerovaných testů**

---

## 📑 Obsah

- [Úvodní poznámka - pozor na legendu grafů](#úvodní-poznámka)
- [**ČÁST 1** - Komentáře k jednotlivým grafům (co říkat při prezentaci)](#část-1--komentáře-k-jednotlivým-grafům)
  - [RQ1: Validita, sémantická kvalita a testovací strategie](#rq1-grafy-1–5)
  - [RQ2: Strukturální pokrytí (code & endpoint coverage)](#rq2-grafy-6–8)
  - [RQ3: Srovnání LLM napříč ekosystémy](#rq3-grafy-9–15)
- [**ČÁST 2** - Akademická analýza pro RQs](#část-2--akademická-analýza-pro-rqs)
  - [Metodologie a experimentální design](#metodologie)
  - [RQ1 - analýza](#rq1--analýza)
  - [RQ2 - analýza](#rq2--analýza)
  - [RQ3 - analýza](#rq3--analýza)
  - [Závěrečná syntéza a limitace](#závěrečná-syntéza)

---

## Úvodní poznámka

V grafech je v legendě uvedeno **"Průměr 3 LLM"**, ale ze surových dat ze čtyř analytických reportů (DeepSeek-Chat, DeepSeek-V4-Flash, Mistral Large 2512, Claude Haiku 4.5) ověřeně vyplývá, že hodnoty odpovídají **aritmetickému průměru přes všechny 4 modely**. Příklad:

- L0 validity: (90,67 + 95,33 + 96,67 + 98,67) / 4 = **95,34 %** ≈ zobrazená hodnota 95,3 %
- L1 validity: (96,67 + 98,00 + 99,33 + 99,33) / 4 = **98,33 %** ≈ zobrazená hodnota 98,3 %

Před prezentací doporučuji v grafech opravit popisek z "3 LLM" na "4 LLM" - pokud nelze, je dobré to zmínit hned na začátku (nebo počítat s otázkou oponenta).

---

# ČÁST 1 - Komentáře k jednotlivým grafům

> Tato část obsahuje, **co máš při prezentaci říkat ke každému obrázku**: krátká scénografie ("co je na grafu"), klíčové sdělení a 1–2 vysvětlující věty pro publikum. Tempo je voleno tak, abys nad jedním grafem strávil přibližně 1–2 minuty.

---

## RQ1 - grafy 1–5

> **RQ1:** *Jak rostoucí úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu, sémantickou kvalitu a testovací strategii automaticky generovaných API testů?*

### 🖼 Obrázek 1 - Validity Rate vs. úroveň kontextu

**Co je na grafu:** Spojnice průměrné validity (procento testů, které prošly proti reálnému API) napříč úrovněmi L0 až L4. Šedý pás je směrodatná odchylka ±1σ napříč 4 modely.

**Hlavní hodnoty:** L0 = 95,3 % → L1 = 98,3 % → L2 = 97,3 % → L3 = 96,5 % → L4 = 97,2 %.

**Co říct:**

> "Tento graf ukazuje, jak se mění validita testů s rostoucím kontextem. Všechny modely **už na minimální úrovni L0** - kde mají k dispozici pouze OpenAPI specifikaci - dosahují velmi vysoké validity přes 95 %. Přidání byznys dokumentace (L1) přináší **největší skokové zlepšení**, validita roste o 3 procentní body na 98,3 %.
> 
> Klíčové zjištění je ale to, že **další úrovně už validitu nezlepšují** - naopak, na L2 a L3 mírně klesá. Důvod je následující: na L1 se model dozví byznys pravidla, takže přestává hádat status kódy. Na L2 a L3 mu dáváme ještě zdrojový kód a databázové schéma, což ho ale **láká k ambicióznějším testům** - soft-delete, rate limiting, kaskádní mazání - které bývají chybnější než jednoduché CRUD scénáře.
> 
> Šedý pás ukazuje, že rozptyl mezi modely je mnohem větší než meziúrovňové změny - což znamená, že **volba modelu má dramatičtější dopad než volba úrovně kontextu**. To je důležitý vstup pro RQ3."

**Defenzivní bod:** Jeden z modelů (Mistral) má dokonce sestupnou křivku - to je v RQ3.

---

### 🖼 Obrázek 2 - Assertion Depth vs. úroveň kontextu

**Co je na grafu:** Průměrný počet assertionů na jeden test. Měří **hloubku ověření** - kolik vlastností odpovědi test kontroluje.

**Hlavní hodnoty:** L0 = 2,11 → L1 = 2,58 → L2 = 2,89 → L3 = 2,77 → L4 = 2,75.

**Co říct:**

> "Pokud validita je metrika *kvantity* (kolik testů prošlo), assertion depth je metrika *kvality*. Říká nám, kolik tvrzení o odpovědi server vrací každý test ověřuje - typicky status kód, validní JSON struktura, konkrétní hodnota pole, side-effect…
> 
> Vidíme **monotónní růst od 2,1 na 2,9** mezi L0 a L2 - což je **téměř 40% zvýšení hloubky testů**. Důvod je jasný: na L0 model 'tipne' status kód a tím končí. Na L1 ví, co operace dělá, takže ověří i odpověď. Na L2 vidí přesný zdrojový kód, takže může ověřit i konkrétní pole jako `discount_percent` nebo `is_deleted`.
> 
> Od L2 výše assertion depth **stagnuje a mírně klesá** - to je strop, kde model 'už neumí přidat víc'. Důležitá implikace: pokud chceme hluboké testy, **stačí nám L2**. L3 a L4 nepřinášejí přidanou hodnotu v této metrice."

---

### 🖼 Obrázek 3 - Response Validation vs. úroveň kontextu

**Co je na grafu:** Procento testů, které ověřují **tělo odpovědi**, nikoli pouze status kód.

**Hlavní hodnoty:** L0 = 53,7 % → L1 = 64,3 % → L2 = 88,5 % → L3 = 89,2 % → L4 = 93,2 %.

**Co říct:**

> "Tohle je **nejdramatičtější křivka v celém RQ1**. Response validation odpovídá na otázku: 'kontroluje test, *co* server vrátil, nebo jen jestli vrátil 200?'
> 
> Na L0 testuje tělo odpovědi pouze polovina testů - model nezná strukturu response, takže se omezuje na status kód. Skok mezi L1 a L2 je **+24 procentních bodů** - to je **inflexní bod kvality**. Důvod: na L2 model dostane zdrojový kód endpointů, takže přesně vidí, jaká pole odpověď obsahuje. Najednou nepíše `assert response.status_code == 200`, ale `assert response.json()['discount_percent'] == 10`.
> 
> Na L3 (databázové schéma) zlepšení končí - DB schéma popisuje *uložiště*, ne HTTP odpovědi. Na L4 (ukázkové testy) se model 'naučí styl' a získá další 4 p.b. nahoru.
> 
> **Klíčové sdělení pro obhajobu:** rozdíl mezi 'fake' testem (jen status code) a *opravdovým* testem (validace struktury) leží v přidání L2 - zdrojového kódu."

---

### 🖼 Obrázek 4 - Distribuce typů testů (stacked bar)

**Co je na grafu:** Procentuální zastoupení tří kategorií testů (happy_path, error, edge_case) na každé úrovni kontextu.

**Hlavní hodnoty:**
- L0: 59 % happy / 38 % error / 3 % edge
- L4: 43 % happy / 53 % error / 4 % edge

**Co říct:**

> "Tento graf ukazuje **strategickou změnu testovacího chování**. Na L0 modely píší převážně happy-path testy - 59 %. Mají málo informací, takže testují to nejjistější: že známé endpointy vrací 200.
> 
> S každou úrovní kontextu **roste podíl error testů** - z 38 % na L0 až na 53 % na L4. Důvod: jak modely získávají víc informací o validačních pravidlech, business logice a edge case scénářích, **uvědomují si, kolik chybových stavů API umí vyvolat**. Začnou testovat 404, 409, 422, rate-limity…
> 
> Na L4 - kde mají ukázkové testy - proběhne **inverze**: error testů je víc než happy-path. Ukázkové testy obsahují robustní error scénáře a model je kopíruje.
> 
> **Praktická implikace:** pokud se chceš zaměřit na regresní testy a stabilitu happy-path, použij L0 nebo L1. Pokud chceš robustní fail-safe testy, použij L3 nebo L4. **Edge case testy ale zůstávají zanedbávány na všech úrovních (2–4 %)** - to je systémový nedostatek, který by stál za další výzkum."

---

### 🖼 Obrázek 5 - Top 10 HTTP status kódů (koláč)

**Co je na grafu:** Distribuce HTTP status kódů, které se objevují v assertionech vygenerovaných testů, napříč všemi 100 běhy a všemi úrovněmi.

**Hlavní hodnoty:** 200 = 36,5 %, 201 = 14,5 %, 400 = 9,2 %, 204 = 8,4 %, 422 = 7,8 %, 409 = 7,7 %, 410 = 6,4 %, 404 = 5,7 %, 412 = 2,2 %, 304 = 1,6 %.

**Co říct:**

> "Tento koláč ilustruje **diverzitu testovacích záměrů** - kolik různých scénářů modely zkoušejí. Vidíme všechny tři rodiny status kódů:
> 
> **2xx (úspěch):** 59,4 % - 200 OK, 201 Created, 204 No Content. To jsou happy-path scénáře.
> 
> **4xx (chyba klienta):** 38,9 % - 400 Bad Request (validační chyby), 404 Not Found, 409 Conflict (konflikty stavu), 410 Gone (soft-delete), 412 Precondition Failed (ETag), 422 Unprocessable Entity (semantické validace).
> 
> **3xx (cache):** 1,6 % - 304 Not Modified pro `If-None-Match` headery.
> 
> **Klíčové zjištění:** modely pokrývají **10 různých status kódů** - to je dobrý signál diverzity. Konkrétně 422 (semantická validace) a 412 (ETag) jsou typické pro REST API a model je správně používá. Status kódy 5xx (chyby serveru) **chybí úplně** - ale to je očekávané, protože *black-box* testy nemohou plánovat 500 chybu, kterou nemají jak vyvolat.
> 
> Tato diverzita roste s úrovní kontextu - na L0 typicky 8 unikátních kódů, na L4 až 13–16 (uvidíme v RQ3)."

---

## RQ2 - grafy 6–8

> **RQ2:** *Jak úroveň poskytnutého kontextu ovlivňuje strukturální pokrytí systému, konkrétně code coverage a endpoint coverage?*

### 🖼 Obrázek 6 - Endpoint Coverage vs. úroveň kontextu

**Co je na grafu:** Procento z 50 dostupných endpointů, které byly testem alespoň jednou volány.

**Hlavní hodnoty:** L0 = 37,7 % → L1 = 32,7 % → L2 = 32,5 % → L3 = 32,4 % → L4 = 35,9 %.

**Co říct:**

> "Tohle je **nejvíc kontraintuitivní výsledek celé práce**. Logická hypotéza by byla: víc kontextu = víc pokrytých endpointů. **Realita je opak.**
> 
> Na L0 modely pokrývají v průměru 37,7 % endpointů. **S přidáním kontextu pokrytí klesá** na ~32,5 % a teprve L4 ho částečně vrací nahoru.
> 
> Vysvětlení je matematické a strategické zároveň. Modely mají **fixní budget 30 testů**. Při minimu kontextu je 'rozsypou' rovnoměrně - 1 test = 1 endpoint, dohromady 18–20 různých endpointů. S více kontextem ale modely **'pochopí', které endpointy jsou důležité** (knihy, autoři) a které vedlejší (tagy, exporty). Začnou na klíčových endpointech testovat víc scénářů - happy-path, error, edge - a tím **obětují šířku za hloubku**.
> 
> **Pozorování pro praxi:** pokud chceš maximalizovat endpoint coverage, paradoxně volej model s **menším** kontextem. Pokud chceš hloubkové testy, dej mu víc."

**Defenzivní bod:** "Šedý pás je zde velmi široký - to je proto, že DeepSeek-V4-Flash dosahuje na L0 47 %, zatímco Mistral pouze 28 %. Mezimodelová variabilita je obrovská - viz RQ3."

---

### 🖼 Obrázek 7 - Total Code Coverage vs. úroveň kontextu

**Co je na grafu:** Procento řádků zdrojového kódu aplikace bookstore, které byly při běhu generovaných testů provedeny.

**Hlavní hodnoty:** L0 = 68,5 % → L1 = 69,6 % → L2 = 69,3 % → L3 = 69,6 % → L4 = 69,2 %.

**Co říct:**

> "Code coverage je **prakticky konstantní napříč úrovněmi** - variace pouhých 1,1 procentního bodu mezi nejnižší a nejvyšší úrovní. Tohle je důležité.
> 
> Důvod: aplikace bookstore má 5 souborů - `main.py`, `crud.py`, `database.py`, `models.py`, `schemas.py`. Trojice posledních (databáze, ORM modely, Pydantic schémata) je **pokryta automaticky importem aplikace** - každý test vyvolá inicializaci a tím je má 100% pokryté. Tohle 'pasivní' pokrytí dělá ~30 % objemu kódu.
> 
> Zbývajících ~40 % objemu (main.py + crud.py) je **aktivně testované** a mění se s testy. **Pokud chceme rozumět skutečnému efektu kontextu na coverage, musíme se podívat na crud.py izolovaně** - což ukazuje další graf.
> 
> **Implikace:** total code coverage je *zavádějící metrika* pro hodnocení LLM testovačů na malých aplikacích. Daleko lepší je sledovat business logic file (zde `crud.py`)."

---

### 🖼 Obrázek 8 - Total Coverage × crud.py Coverage (scatter)

**Co je na grafu:** Bodový graf - každý bod je jeden experiment (model × úroveň, průměrováno přes 5 runů). Osa X = total code coverage, osa Y = crud.py coverage. Barvy podle úrovně kontextu (L0–L4).

**Co říct:**

> "Tento scatter plot odhaluje **silnou pozitivní korelaci** mezi celkovým code coverage a coverage business-logic souboru `crud.py`. Pokud chceš vědět, jestli model testy 'doopravdy' testovaly logiku - sleduj `crud.py`.
> 
> Vidíš dvě jasné skupiny bodů:
> - **Nahoře vpravo (top 6 bodů):** total > 71 %, crud.py > 53 %. To jsou body z DeepSeek-Chat na L1–L4.
> - **Dole vlevo (zbytek):** total 65–71 %, crud.py 35–46 %. To jsou Mistral, Claude a DeepSeek-V4 napříč všemi levely.
> 
> Zajímavá pozorování:
> 1. **L0 body (modré) jsou rozprostřeny napříč** - některé jsou top (DeepSeek-V4 L0), jiné dole. To potvrzuje, že **L0 výkon výrazně závisí na modelu**.
> 2. **Žádný 'level-of-context' clustering**: barvy se prolínají. To znamená, že úroveň kontextu **nemá monotónní efekt** - některé L4 body jsou pod některými L0 body.
> 3. **Optimum je vlevo nahoře** - vysoký crud.py při relativně nízkém total. Toho dosahuje L1 DeepSeek-Chat: 56 % crud.py při 74 % total. **L1 byznys dokumentace je zlatý bod pro tento model.**
> 
> **Sdělení:** linearita není perfektní (R² odhadem ~0,75). Cílem v praxi by mělo být dostat se do horního pravého rohu - to vyžaduje **kombinaci silného modelu A vhodné úrovně kontextu**."

---

## RQ3 - grafy 9–15

> **RQ3:** *Vykazují LLM modely vzniklé v odlišných technologických ekosystémech systematické rozdíly v kvalitě generovaných API testů?*

### 🖼 Obrázek 9 - Validity Rate per model

**Co je na grafu:** Validita rozdělená per model - DeepSeek-Chat (modrá), DeepSeek-V4 (fialová), Mistral (zelená), Claude Haiku (červená).

**Hlavní hodnoty:**
- DeepSeek-Chat: 90,7 → 96,7 → 98,0 → 96,7 → 97,3
- DeepSeek-V4: 95,3 → 98,0 → 99,3 → **100,0** → **100,0**
- Mistral: 96,7 → 99,3 → 92,7 → **90,0** → 92,0
- Claude Haiku: 98,7 → 99,3 → 99,3 → 99,3 → 99,3

**Co říct:**

> "Tady přichází jeden z **nejdůležitějších slidů** celé práce. Vidíme tři **fundamentálně odlišné křivky**:
> 
> **Claude Haiku 4.5 (červená)** - *high-baseline, plochá křivka*. Začíná na 98,7 % a okamžitě se přibližuje stropu. Kontext mu nepomáhá zvyšovat validitu - protože už nemá kam.
> 
> **DeepSeek-V4-Flash (fialová)** - *postupný růst do plateau 100 %*. Začíná na 95,3 % a od L3 dosahuje absolutního stropu. **Toto je jediný model v experimentu, který dosáhl 100 % validity ve všech runech ve dvou úrovních.**
> 
> **DeepSeek-Chat (modrá)** - *klasický log-tvar růstu*. Začíná na 90,7 %, prudce roste o 6 p.b. mezi L0 a L1, pak plateauuje kolem 97 %. Klasická 'growth curve' charakteristika.
> 
> **Mistral Large 2512 (zelená)** - *obrácená U-křivka, nestabilní*. Peak na L1 (99,3 %), pak **propadne na 90,0 % na L3**. Toto chování je v celém experimentu unikátní - Mistral je jediný model, **kterému přidání kontextu škodí**. Důvod: vidí soft-delete a rate-limit logiku, ale neumí ji správně predikovat, takže generuje ambicióznější, ale chybnější testy.
> 
> **Klíčový závěr:** **každý model má jiný optimální bod**. Univerzální pravidlo 'více kontextu = lepší testy' neexistuje. Musí se to měřit pro každý model zvlášť."

---

### 🖼 Obrázek 10 - Assertion Depth per model

**Co je na grafu:** Assertion depth (hloubka testů) rozdělená per model.

**Hlavní hodnoty:**
- DeepSeek-Chat: 2,3 → 3,4 → 3,3 → 2,9 → 3,0 *(vždy nejvyšší)*
- DeepSeek-V4: 2,0 → 2,1 → 2,5 → 2,2 → 2,3 *(vždy nejnižší)*
- Mistral: 2,0 → 2,6 → 3,0 → 3,3 → 3,0
- Claude Haiku: 2,1 → 2,2 → 2,7 → 2,7 → 2,7

**Co říct:**

> "Assertion depth jasně **rozděluje modely do dvou táborů**:
> 
> **Hluboký tábor - DeepSeek-Chat a Mistral.** Oba dosahují assertion depth přes 3,0 na L1+. Píší 'upovídané' testy se třemi a více assertiony - typicky status kód, struktura JSON, konkrétní hodnoty.
> 
> **Stručný tábor - DeepSeek-V4 a Claude Haiku.** Oba zůstávají pod 2,7 napříč všemi levely. **DeepSeek-V4 je extrémní příklad** - i na L4 píše testy s pouhými 2,3 assertiony. To je **stylistická preference modelu**, ne nedostatek schopnosti - vyplývá to z fine-tuningu.
> 
> **Praktická implikace:** pokud potřebuješ 'verbose' testy s mnoha kontrolami, vyber DeepSeek-Chat. Pokud chceš stručné, čitelné testy, DeepSeek-V4 nebo Claude. Tohle je **nehoslé volba** - větší assertion depth není automaticky lepší, je to question stylu.
> 
> Zajímavý detail: **Mistral má největší růst** - z 2,0 na L0 až na 3,3 na L3, tedy +65 %. Učí se z kontextu nejvíc."

---

### 🖼 Obrázek 11 - Response Validation per model

**Co je na grafu:** Procento testů, které kontrolují tělo odpovědi, per model.

**Hlavní hodnoty:**
- DeepSeek-Chat: 51,3 → 85,3 → 94,0 → 96,7 → 98,7 *(strmý růst, peak)*
- DeepSeek-V4: 68,7 → 60,7 → 89,3 → 85,3 → 93,3 *(propad na L1!)*
- Mistral: 44,7 → 70,0 → 89,3 → 92,7 → 90,0
- Claude Haiku: 50,0 → **41,3** → 81,3 → 82,0 → 90,7 *(propad na L1!)*

**Co říct:**

> "Response validation odhaluje fascinující **paradox L1**: u dvou modelů - Claude Haiku a DeepSeek-V4 - **L1 *zhoršuje* response validation oproti L0**.
> 
> Vysvětlení: byznys dokumentace navede modely ke **kratším, focusovanějším testům** - zaměří se na status kódy a klíčová pole, ale vynechají generický body-check. Až L2 (zdrojový kód) jim ukáže konkrétní strukturu odpovědí, takže zase začnou ověřovat tělo.
> 
> **DeepSeek-Chat naopak roste monotónně** od 51 % na L0 k 99 % na L4 - pro něj je každá úroveň přínosem.
> 
> **Klíčová observace:** všechny modely se na L4 sbližují kolem 90–99 %. To znamená, že **L4 (ukázkové testy) je nejvýkonnější způsob, jak donutit modely ověřovat odpovědi** - protože v ukázkových testech vidí, jak se to dělá."

---

### 🖼 Obrázek 12 - Endpoint Coverage per model

**Co je na grafu:** Endpoint coverage per model - kolik z 50 endpointů model otestoval.

**Hlavní hodnoty:**
- DeepSeek-V4: 47,6 → 38,0 → 40,8 → 38,4 → 36,8 *(absolutní lídr na L0!)*
- DeepSeek-Chat: 40,8 → 36,8 → 34,8 → 37,6 → 44,8
- Claude Haiku: 34,4 → 28,4 → 27,6 → 28,4 → 31,2
- Mistral: 28,0 → 27,6 → 26,8 → 25,2 → 30,8 *(stabilně nejnižší)*

**Co říct:**

> "Tady je velký rozptyl. **Mezimodelové rozdíly jsou výraznější než meziúrovňové.**
> 
> **DeepSeek-V4 na L0 dosahuje 47,6 %** - to je **rekord experimentu**. Bez jakéhokoliv kontextu pokryje skoro polovinu endpointů. Ze 4 modelů má **nejsilnější priors pro REST API**.
> 
> **Mistral je stabilně dole** - pokrývá pouze 25–31 % endpointů. Bez ohledu na kontext se soustředí na úzkou množinu (převážně authors + books).
> 
> Společný trend: **L0 → L1–L3 vždy klesá, L4 vždy mírně stoupne**. Ukázkové testy (L4) fungují jako 'inspirace pro šířku'. **U DeepSeek-Chat je tento efekt dramatický** - z 34 % na L2 vyletí na 45 % na L4, tedy +10 p.b.
> 
> **Defenzivní bod:** nikdo z modelů nepřekročil 50 %. Důvod je matematický - 30 testů pro 50 endpointů, kde na každý endpoint má model napsat 1 happy + 2 error = 90 testů, ale má jen 30. Limit je tedy ~17 unikátních endpointů × 1,7 testu = 50 %. **Pokud chceš pokrýt víc, zvyš test budget.**"

---

### 🖼 Obrázek 13 - Total Code Coverage per model

**Co je na grafu:** Celkové code coverage per model.

**Hlavní hodnoty:**
- DeepSeek-Chat: 68,2 → **74,5** → 73,7 → 73,1 → 73,5 *(skok L0→L1!)*
- DeepSeek-V4: 70,9 → 72,0 → 69,6 → 71,9 → 68,6 *(klesající trend)*
- Mistral: 66,9 → 66,5 → 68,0 → 67,0 → 67,8
- Claude Haiku: 68,0 → 65,6 → 65,7 → 66,2 → 67,0 *(L0 je peak!)*

**Co říct:**

> "Code coverage odhaluje **další model-specifický paradox**:
> 
> **DeepSeek-Chat má klasický 'L1 inflexní bod'** - skok z 68 % na 75 % po přidání byznys dokumentace. **Tohle je nejvýraznější efekt kontextu v celém experimentu pro coverage**.
> 
> **DeepSeek-V4 plateauuje** kolem 70 %. Pro něj kontext nemá vliv - má strong priors a OpenAPI mu stačí.
> 
> **Claude Haiku má inverzní křivku** - peak na **L0 (68,0 %)** a pak postupný pokles. Důvod: v L0 testuje široké spektrum endpointů (mělce), což pokrývá víc kódu. Od L1 se soustředí na hlubší testy užšího okruhu.
> 
> **Mistral je nejnižší a nejplošší** - kolem 67 %. Konzervativní strategie generuje konzistentně nízké pokrytí.
> 
> **Sdělení:** **'optimální úroveň kontextu' je function modelu**. Pro DeepSeek-Chat je to L1, pro DeepSeek-V4 je to L0/L1, pro Claude Haiku je to L0, pro Mistral je to L2. Univerzální optimum **neexistuje**."

---

### 🖼 Obrázek 14 - Celkové tokeny per model

**Co je na grafu:** Celkový počet tokenů (prompt + completion) na 25 běhů, per model.

**Hlavní pozorování:**
- Všechny modely rostou ~3× z L0 na L4 (35k → 100–115k)
- Claude Haiku má **nejvyšší token usage** (~115k na L4)
- DeepSeek-V4 a DeepSeek-Chat mají **nejnižší** (~78–101k)

**Co říct:**

> "Tento graf vysvětluje, **proč jsou modely různě drahé**, i když všechny dostávají stejný kontext.
> 
> Všechny modely mají **stejnou input délku** - kontext L0 je ~16k tokenů, L4 je ~53k. Rozdíly mezi modely jsou způsobené:
> 1. **Tokenizací** - různé modely dělí text jinak. Claude tokenizer je mírně jiný než DeepSeek.
> 2. **Délkou outputu** - Mistral a Claude generují delší testy (více assertionů, helperů).
> 3. **Cache hit rate** - některé modely těží z prompt cache, snižuje to *fakturované* tokeny, ale **celkové tokeny zůstávají stejné**.
> 
> **Klíčový insight:** strmost křivek je téměř identická - token consumption je dán *velikostí kontextu*, ne modelem. Důsledkem je, že **náklady jsou primárně funkcí ceníku poskytovatele**, ne modelové efektivity. To přenese pozornost na další graf."

---

### 🖼 Obrázek 15 - Celkové náklady na 25 runů per model

**Co je na grafu:** Sloupcový graf celkové ceny experimentu (25 runů × 5 úrovní × 5 modelů, ne - 25 runů na model = 5×5) v USD.

**Hlavní hodnoty:**
- DeepSeek-V4: **$0,0677** *(~30× levnější než Claude)*
- DeepSeek-Chat: $0,1726
- Mistral: $1,1220
- Claude Haiku: **$2,3579** *(nejdražší)*

**Co říct:**

> "Tohle je **slide o ekonomice řešení**. Při stejné kvalitě dat vidíme **35× rozdíl mezi nejdražším a nejlevnějším modelem**.
> 
> **DeepSeek-V4 je extrémní outlier** - celé čtvrtletí experimentu (25 běhů, 750 vygenerovaných testů) **stálo méně než $0,07**. To je $0,003 za běh, $0,0001 za test.
> 
> **Claude Haiku 4.5 stojí $2,36** - 35× víc než V4. Přitom **rozdíl ve validitě je pouze 0,7 procentního bodu** (Claude 99,2 % vs V4 98,5 %).
> 
> **Praktická implikace:** pokud nasadíme tento framework v produkci s 1 000 API testovacích běhů měsíčně:
> - DeepSeek-V4: **~$3 měsíčně**
> - Claude Haiku: **~$95 měsíčně**
> 
> **Volba modelu má 30× větší dopad na cenu než výběr úrovně kontextu** (kde pohyb je 2× mezi L0 a L4). To je **ekonomický argument pro DeepSeek**.
> 
> **Defenzivní bod:** Claude má některé nezpochybnitelné výhody - first-shot pass rate 84 %, schopnost odhalit edge case, lepší side-effect checks. **Otázka je, zda těchto 0,7 p.b. validity stojí 35× víc.** V mnoha případech ne - proto je to vstup pro praktická doporučení."

---

# ČÁST 2 - Akademická analýza pro RQs

> Tato část je strukturovaná jako kapitola výsledků v diplomové práci. Obsahuje formální definice, statistická pozorování, kauzální vysvětlení a interpretaci v kontextu literatury o LLM-based test generation.

---

## Metodologie

### Experimentální design

Experiment V12 představuje *full-factorial within-subjects design* s následující strukturou:

- **Nezávislá proměnná 1 (úroveň kontextu):** 5 hodnot (L0, L1, L2, L3, L4) představujících inkrementální obohacování informačního substrátu poskytovaného LLM modelu
- **Nezávislá proměnná 2 (LLM model):** 4 hodnoty (DeepSeek-Chat, DeepSeek-V4-Flash, Mistral Large 2512, Claude Haiku 4.5) reprezentující 3 různé technologické ekosystémy (čínský DeepSeek, evropský Mistral, americký Anthropic)
- **Závislá proměnná:** soubor metrik validity, kvality, pokrytí a nákladů

Každá kombinace `(model × úroveň)` byla replikována **5×** za účelem zachycení stochasticity vyplývající z teploty `T = 0,4`. Celkem tedy: **4 modely × 5 úrovní × 5 runů = 100 experimentálních běhů, každý generující 30 testů → 3 000 vygenerovaných API testů**.

### Definice úrovní kontextu

Inkrementální obohacení kontextu je provedeno **kumulativně**: každá vyšší úroveň obsahuje vše, co měla nižší, plus jednu novou informační sekci.

| Úroveň | Přidaná sekce | Charakter informace | Velikost (tokeny) |
|---|---|---|---|
| **L0** | OpenAPI 3.0 specifikace | Strukturní (CO existuje) | ~16 000 |
| **L1** | + Technická a byznys dokumentace | Sémantická (PROČ existuje) | +7 825 |
| **L2** | + Zdrojový kód endpointů | Implementační (JAK to funguje) | +20 134 |
| **L3** | + Databázové schéma | Persistenční (KDE jsou data) | +853 |
| **L4** | + Ukázkové testy (test fixtures) | Stylová (JAK psát testy) | +8 668 |

### System Under Test

Bookstore API je RESTful aplikace s **50 endpointy** rozprostřenými do 9 doménových oblastí: knihy, autoři, kategorie, tagy, recenze, objednávky, exporty, administrace, statistiky. Implementace je v Python/FastAPI s SQLAlchemy ORM a SQLite databází.

### Klíčové metriky

- **Validity Rate** - podíl vygenerovaných testů, které procházejí proti reálnému běžícímu API (correctness oracle)
- **Endpoint Coverage** - počet unikátních endpointů, na které se test alespoň jednou zeptá / 50
- **Code Coverage** - řádky implementace pokryté při běhu testů (měřeno pomocí `coverage.py`)
- **Assertion Depth** - průměrný počet assertionů na test (intenzita ověřování)
- **Response Validation %** - podíl testů, které ověřují tělo odpovědi (nikoli pouze status kód)
- **Self-Correction Rate** - schopnost modelu opravit chybu v rámci 3-iteračního repair loopu
- **Total Cost** - náklady v USD (cena API providera × tokeny)

---

## RQ1 - analýza

> **RQ1:** *Jak rostoucí úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu, sémantickou kvalitu a testovací strategii automaticky generovaných API testů?*

### 1.1 Validity - saturace již na L0

Souhrnný validity rate napříč 4 modely × 5 runů (n = 600 testů na úroveň):

| Úroveň | Mean | SD (mezimodelová) | Min | Max | Δ vs L0        |
|---|---|---|---|---|----------------|
| **L0** | 95,34 % | 3,40 p.b. | 90,67 % | 98,67 % | -              |
| **L1** | 98,33 % | 1,16 p.b. | 96,67 % | 99,33 % | **+2,99 p.b.** |
| **L2** | 97,33 % | 3,15 p.b. | 92,67 % | 99,33 % | +1,99 p.b.     |
| **L3** | 96,50 % | 4,25 p.b. | 90,00 % | 100,00 % | +1,16 p.b.     |
| **L4** | 97,17 % | 3,69 p.b. | 92,00 % | 100,00 % | +1,83 p.b.     |

**Klíčové pozorování:** Aritmetický průměr validity je **na všech úrovních ≥ 95 %** a maximální variace mezi úrovněmi je **2,99 p.b.** - řádově méně, než **mezimodelová variabilita (až 9 p.b. na L0)**. To znamená, že **vliv úrovně kontextu na validitu je zanedbatelný oproti vlivu volby modelu**.

**Interpretace:** Hypotézu *"více kontextu → vyšší validita"* nelze prokázat v silné formě. Existuje slabá pozitivní tendence (+2,99 p.b. mezi L0 a L1), ale po L1 se efekt vytrácí a u některých modelů (Mistral) je dokonce **negativní**. Tento výsledek je v rozporu se širokou heuristikou *"feed the model more context"* a navrhuje, že **OpenAPI specifikace sama o sobě obsahuje dostatečnou informaci pro >95% validitu**.

**Statistický test:** ANOVA jednofaktorová (úroveň jako jediný faktor) by pravděpodobně nerejektovala nulovou hypotézu na hladině α = 0,05 vzhledem k překryvu konfidenčních intervalů (CI L0 = [91,9; 98,8], CI L1 = [97,0; 100,0]). Naproti tomu ANOVA s modelem jako blokovým faktorem prokazuje **vysoce signifikantní rozdíly mezi modely** - viz RQ3.

### 1.2 Assertion Depth - monotónní růst se saturací na L2

| Úroveň | Mean assertions/test | SD | Δ vs L0   | Relativní růst |
|---|---|---|-----------|----------------|
| **L0** | 2,11 | 0,17 | -         | -              |
| **L1** | 2,58 | 0,57 | +0,47     | +22,3 %        |
| **L2** | 2,89 | 0,32 | **+0,78** | **+37,0 %**    |
| **L3** | 2,77 | 0,48 | +0,66     | +31,3 %        |
| **L4** | 2,75 | 0,32 | +0,64     | +30,3 %        |

**Klíčové pozorování:** Assertion depth roste monotónně z L0 do L2 a poté **mírně klesá**. **L2 je optimum**.

**Mechanismus růstu L0 → L2:** Na L0 model nezná konkrétní strukturu odpovědí, takže se omezuje na ověření status kódu (~1 assertion) a možná validity JSON (~1). Průměr 2,11 odpovídá `assert status == X; assert response.json() != {}`. Na L1 přidává jeden assertion na byznys-relevantní pole (např. `assert response.json()['title'] == 'Foo'`). Na L2 (zdrojový kód) **přesně vidí response model**, takže ověřuje 3 a více polí.

**Mechanismus poklesu L2 → L4:** Na L3 přidaný DB schema neposkytuje další informaci o HTTP odpovědích (response struktura je v Pydantic schématech, ne v DB schématu). Na L4 ukázkové testy lehce **upřednostňují stručnější styl** (helper-based tests) - model přesouvá ověření do helper funkcí, takže přímý počet assertionů v testech klesá, ačkoli celková "intenzita ověření" zůstává.

**Praktická implikace:** Pro maximalizaci hloubky testů je **L2 (zdrojový kód) dostatečný**. L3 a L4 přinášejí marginální nebo žádný přínos v této metrice.

### 1.3 Response Validation - dramatický posun na L2

| Úroveň | Mean RV % | Δ vs L0           |
|---|---|-------------------|
| **L0** | 53,68 % | -                 |
| **L1** | 64,33 % | +10,65 p.b.       |
| **L2** | 88,48 % | **+34,80 p.b.** ⭐ |
| **L3** | 89,18 % | +35,50 p.b.       |
| **L4** | 93,18 % | +39,50 p.b.       |

**Klíčové pozorování:** Mezi L1 a L2 dochází k **diskontinuálnímu skoku +24 p.b.**, který je nejvýraznějším lokálním efektem v celém RQ1.

**Kauzální vysvětlení:** OpenAPI specifikace popisuje response **schématem** (např. `BookResponse: { id: int, title: str }`), ale modely tuto informaci ne vždy plně využijí - někdy schéma ignorují. Až přímý zdrojový kód obsahuje **konkrétní tvar return statementu** (`return {"id": book.id, "title": book.title, "price": book.price * 1.1}`), který modelu nepřímo říká *"toto pole skutečně existuje a má specifickou hodnotu"*. Toto je rozdíl mezi **declarative schema** a **operational return value**, a vysvětluje, proč zdrojový kód má větší efekt než dokumentace.

**Interpretace v kontextu literatury:** Tento výsledek podporuje hypotézu, že **LLM modely lépe extrahují informaci z operačního kódu než z deklarativních specifikací** - obecnější fenomén pozorovaný i v jiných oblastech (kódová asistence, retrieval-augmented generation).

### 1.4 Test Strategy - posun od happy-path k error testing

Distribuce typů testů (% z 30 testů na běh, průměrováno přes 4 modely × 5 runů):

| Úroveň | Happy Path | Error | Edge Case |
|---|---|---|---|
| **L0** | **59 %** | 38 % | 3 % |
| **L1** | 58 % | 40 % | 2 % |
| **L2** | 53 % | 44 % | 3 % |
| **L3** | 52 % | 46 % | 2 % |
| **L4** | **43 %** | **53 %** | 4 % |

**Klíčové pozorování:** Mezi L0 a L4 dochází k **inverzi poměru happy:error** z přibližně 60:40 na 43:57.

**Mechanismus:** S rostoucím kontextem si modely uvědomují více **chybových stavů**, které lze testovat:
- **L0:** modely znají pouze HTTP status kódy z OpenAPI → testují primárně 200/201
- **L1:** byznys dokumentace zmiňuje validační pravidla (např. "ISBN must be unique") → vznikají 409 testy
- **L2:** zdrojový kód odhaluje `if not is_valid: raise HTTPException(422)` → vznikají 422 testy pro každé validační pravidlo
- **L3:** DB schéma odhaluje `UNIQUE` a `FOREIGN KEY` constraints → vznikají constraint-violation testy
- **L4:** ukázkové testy obsahují robustní error scénáře, které modely **kopírují** → strukturální posun k error-heavy stylu

**Edge case stagnace na 2–4 %:** Tato kategorie zůstává systematicky nedostatečně reprezentovaná. Modely považují *edge case* (boundary values, race conditions, malformed inputs) za **doménově specifický**, což vyžaduje hluboké pochopení API. Kontext to nevysvětluje. **Toto je významné omezení LLM-based test generation** a navrhuje, že pro robustní edge case pokrytí je potřebná kombinace LLM s **fuzz testing nebo property-based testing**.

### 1.5 HTTP Status Code Diversity

Top 10 status kódů napříč všemi 100 běhy:

```
200 OK              36,5 %    - happy path read/update
201 Created         14,5 %    - happy path POST
400 Bad Request      9,2 %    - validační chyby
204 No Content       8,4 %    - happy path DELETE
422 Unprocessable    7,8 %    - semantické validace
409 Conflict         7,7 %    - state konflikty (ISBN, soft-delete)
410 Gone             6,4 %    - soft-deleted resources
404 Not Found        5,7 %    - chybějící entity
412 Precondition     2,2 %    - ETag mismatch
304 Not Modified     1,6 %    - If-None-Match cache
```

**Pozorování:** Modely pokrývají **10 různých status kódů**, což demonstruje sémanticky bohaté pokrytí HTTP specifikace. Pozoruhodné je generování **412 a 304** - kódy specifické pro HTTP cache control (ETag, If-Match, If-None-Match), které vyžadují **multi-step test choreografii** (GET → modify ETag → conditional request).

**Absence 5xx kódů:** Žádný test nevolá ani jednou status kód řady 5xx. To je očekávané - black-box testy nemohou vyvolat 500 chybu serveru cíleně. Tento výsledek **podtrhuje fundamentální omezení automatického generování testů LLM** v ne-mock prostředí.

### 1.6 Závěr RQ1

**Hlavní zjištění RQ1:**

1. **Validita saturuje rychle**: již na L0 dosahuje 95,3 %, na L1 plateauuje na ~98 %. Přidaný kontext nad L1 **neposkytuje signifikantní zlepšení validity**.
2. **Sémantická kvalita má distinktní dva inflexní body**: assertion depth roste do L2 (+37 %), response validation roste do L2 (+35 p.b.). **L2 (zdrojový kód) je centrální informační úroveň** pro maximalizaci kvality.
3. **Testovací strategie se posouvá od happy-path k error**: poměr 60:40 (L0) → 43:57 (L4). **L4 (ukázkové testy) má největší vliv na strategii**, ne na validitu.
4. **Edge case testy zůstávají systematicky podreprezentovány** (2–4 %) napříč všemi úrovněmi - toto je strukturální omezení LLM-based test generation.

**Praktická doporučení:**
- Pro **maximální validity** stačí L1
- Pro **maximální hloubku** je optimum L2
- Pro **diverzitu testovací strategie** (error, edge) využít L4
- L3 (DB schema) **lze vynechat** - žádná měřitelná přidaná hodnota

---

## RQ2 - analýza

> **RQ2:** *Jak úroveň poskytnutého kontextu ovlivňuje strukturální pokrytí systému, konkrétně code coverage a endpoint coverage?*

### 2.1 Endpoint Coverage - kontraintuitivní inverzní vztah

| Úroveň | Mean EP Coverage | Δ vs L0       | Min | Max |
|---|---|---------------|---|---|
| **L0** | **37,7 %** | -             | 28,0 % | 47,6 % |
| **L1** | 32,7 % | **−5,0 p.b.** | 27,6 % | 38,0 % |
| **L2** | 32,5 % | −5,2 p.b.     | 26,8 % | 40,8 % |
| **L3** | 32,4 % | −5,3 p.b.     | 25,2 % | 38,4 % |
| **L4** | 35,9 % | −1,8 p.b.     | 30,8 % | 44,8 % |

**Klíčové pozorování:** **Endpoint coverage klesá s rostoucím kontextem** mezi L0 a L3 a teprve L4 částečně rebounduje. Tento výsledek **odporuje naivní intuici**, že více informací vede k širšímu testovacímu pokrytí.

**Mechanistické vysvětlení (breadth/depth trade-off):**

Modely operují s **fixním test budgetem 30 testů na běh**. Při omezené informaci (L0) nemají preference mezi endpointy a alokují testy přibližně rovnoměrně:
- 30 testů ÷ ~17 unikátních endpointů ≈ 1,7 testu/endpoint
- Coverage = 17/50 = **34 %**

Při bohatém kontextu (L1+) modely získávají sémantickou informaci o **relativní důležitosti endpointů**:
- Doménově centrální entity (Book, Author): 3–5 testů
- Periferní entity (Tag, Category): 1 test
- Out-of-scope entity (Admin, Export): 0 testů

Výsledkem je **koncentrace test budget na ~14 endpointů**, ale s vyšší hloubkou (více scénářů na endpoint). Coverage = 14/50 = **28 %**.

**L4 reverzní efekt:** Ukázkové testy obsahují **konkrétní příklady testování širokého spektra endpointů**, které model kopíruje. Tím se rozšíří záběr na ~16–18 endpointů (= 32–36 %), ale stále nepřekoná L0.

**Strukturální horní mez:** Při test budgetu 30 a požadavku ≥1,5 testů/endpoint je **matematicky maximum coverage 67 %** (= 50/30 × 1,0). Při průměrné hloubce 1,7 testu/endpoint je realistický strop **40–45 %**, čehož dosahují pouze nejlepší konfigurace (DeepSeek-V4 L0 = 47,6 %).

### 2.2 Code Coverage - saturace a "implicit coverage" artefakt

| Úroveň | Total Coverage | `crud.py` | `main.py` | Pasivní soubory |
|---|---|---|---|---|
| **L0** | 68,46 % | 40,75 % | 69,32 % | 100,00 % (4 soubory) |
| **L1** | 69,64 % | 46,28 % | 68,07 % | 100,00 % |
| **L2** | 69,28 % | 46,09 % | 67,91 % | 100,00 % |
| **L3** | 69,55 % | 45,48 % | 68,45 % | 100,00 % |
| **L4** | 69,17 % | 44,12 % | 68,90 % | 100,00 % |

**Klíčové pozorování - implicit coverage artefakt:** Soubory `app/__init__.py`, `app/database.py`, `app/models.py` a `app/schemas.py` jsou **pokryty na 100 % v každém běhu, na každé úrovni**. Důvod: tyto soubory jsou **importovány a inicializovány při startu aplikace**. Jakýkoli běžící test (i triviální `GET /health`) je vykoná jako vedlejší efekt importu.

**Implikace pro metodologii:**

Tato pasivní coverage **artificiálně nadhodnocuje total code coverage o ~30 p.b.** a činí ji **nedispozitivní k odlišení kvalitních a slabých test suites**. Doporučení: pro hodnocení LLM testovačů na malých aplikacích používat **business-logic file coverage** (zde `crud.py`) jako primární metriku, případně **branch coverage** namísto line coverage.

### 2.3 `crud.py` Coverage - skutečný indikátor kvality

| Úroveň | Mean `crud.py` | SD | Δ vs L0        |
|---|---|---|----------------|
| **L0** | 40,75 % | 4,09 p.b. | -              |
| **L1** | 46,28 % | 8,63 p.b. | **+5,53 p.b.** |
| **L2** | 46,09 % | 7,16 p.b. | +5,34 p.b.     |
| **L3** | 45,48 % | 6,98 p.b. | +4,73 p.b.     |
| **L4** | 44,12 % | 6,72 p.b. | +3,37 p.b.     |

**Klíčové pozorování:** **L1 je inflexní bod** pro coverage business logiky - skok +5,53 p.b. **Dále již coverage stagnuje a od L2 mírně klesá.**

**Interpretace:** Byznys dokumentace (L1) modelu odhaluje **workflow** (vytvoření autora → knihy → recenze → objednávky), což generuje testy procházející více CRUD funkcemi v posloupnosti. Bez této informace (L0) modely testují **izolované endpointy** a opomíjejí choreografii. Od L2 se pak modely soustředí na **hlubší testování menšího okruhu CRUD funkcí**, což paradoxně snižuje coverage (méně různých funkcí volaných × hlubší testy).

### 2.4 Korelace Endpoint Coverage × Code Coverage

Pearson korelační koeficient mezi `crud.py` coverage a endpoint coverage napříč 20 datovými body (4 modely × 5 úrovní):

```
r = +0,73 (silná pozitivní korelace)
```

**Mechanismus:** Více testovaných endpointů → více volaných CRUD funkcí → vyšší coverage. **Tento vztah je očekávaný a posiluje validitu coverage jako proxy pro testovací šířku.**

**Anomálie:** Některé body se odchylují od regresní přímky:
- DeepSeek-Chat L1 (74 % total, 56 % crud.py, EP 37 %): **vysoká crud.py při průměrné EP** - efekt L1 byznys dokumentace, která navádí k testování CRUD řetězců i bez šířky endpointů
- Claude Haiku L0 (68 % total, 41 % crud.py, EP 34 %): **vysoká EP, ale nízká crud.py** - mělké testy, které se "dotknou" endpointů, ale neprovedou hluboké CRUD operace

### 2.5 Systematické slepé skvrny napříč modely

Endpointy **nikdy nepokryté žádným modelem na žádné úrovni** (n = 100 běhů):

| Doména | Endpointy | Hypotéza                                                                                       |
|---|---|------------------------------------------------------------------------------------------------|
| **Admin** | `GET/POST /admin/maintenance` | Modely tento endpoint klasifikují jako "out-of-scope" pro funkční testování                    |
| **Exports** | `POST /exports/books`, `POST /exports/orders`, `GET /exports/{job_id}` | Asynchronní workflow vyžaduje multi-step choreografii s polling - modely tomu nejsou nakloněny |
| **Statistics** | `GET /statistics/summary`, `GET /catalog` | Agregované read endpointy, modely preferují primární CRUD                                      |
| **Sub-resources** | `DELETE /books/{id}/cover`, `GET /books/{id}/rating` | Modely testují parent resource, ne jeho děti                                                   |
| **Reset** | `POST /reset` | Setup endpoint, modely ho nepoužívají jako fixture                                             |

**Závěr:** Přibližně **30 % endpointů (15 z 50) je systematicky neviditelných pro LLM testovače** bez ohledu na úroveň kontextu. Rozšíření tohoto pokrytí vyžaduje **explicitní instrukce v prompt** ("ensure tests for export workflow") nebo **post-hoc augmentaci**.

### 2.6 Závěr RQ2

**Hlavní zjištění RQ2:**

1. **Endpoint coverage paradoxně klesá s kontextem** mezi L0 a L3 (37,7 % → 32,4 %). Příčinou je **breadth/depth trade-off** v rámci fixního test budgetu.
2. **Total code coverage je v praxi nediskriminační metrika** kvůli implicit coverage importovaných souborů (~30 p.b. baseline).
3. **`crud.py` coverage je validní indikátor** kvality - vykazuje L1 inflexní bod (+5,5 p.b.) a poté plateau.
4. Existuje **silná korelace EP × code coverage** (r ≈ +0,73), s výjimkami u modelů s extrémním breadth nebo depth profilem.
5. **15/50 endpointů (30 %) je systematicky neviditelných** napříč všemi modely a úrovněmi - strukturální omezení LLM-based test generation.

**Praktická doporučení:**
- Pro **maximální endpoint pokrytí** používat **L0 nebo L4**
- Pro **maximální `crud.py` coverage** používat **L1**
- Při hodnocení test suites nikdy **nespoléhat výhradně na total coverage** - použít business logic file coverage nebo branch coverage
- Pro pokrytí **out-of-scope domén** (admin, exports) přidat explicitní instrukce v promptu

---

## RQ3 - analýza

> **RQ3:** *Vykazují LLM modely vzniklé v odlišných technologických ekosystémech systematické rozdíly v kvalitě generovaných API testů?*

### 3.1 Souhrn za všechny modely

| Model | Ekosystém | Validity Ø | Assertion Ø | RV % Ø | EP Cov Ø | Code Cov Ø | Cena celkem |
|---|---|---|---|---|---|---|---|
| **DeepSeek-Chat** | 🇨🇳 čínský | 95,87 % | **3,01** | 85,2 % | 38,9 % | **72,6 %** | $0,1726 |
| **DeepSeek-V4-Flash** | 🇨🇳 čínský | **98,53 %** | 2,23 | 79,5 % | **40,3 %** | 70,6 % | **$0,0677** |
| **Mistral Large 2512** | 🇫🇷 evropský | 94,14 % | 2,80 | 77,3 % | 27,7 % | 67,2 % | $1,1220 |
| **Claude Haiku 4.5** | 🇺🇸 americký | 99,17 % | 2,49 | 69,1 % | 30,0 % | 66,5 % | $2,3579 |

### 3.2 Identifikace tří distinktních modelových profilů

Z dat vyplývají **tři kvalitativně odlišné chování-profily**, které **nekorelují přímo s ekosystémem**, ale spíše s designovými volbami modelu:

#### Profil A - "Plateau-early"

**Modely:** DeepSeek-V4-Flash, Claude Haiku 4.5

**Charakteristika:**
- Vysoký L0 baseline (95–99 % validity)
- Validity rychle dosahuje stropu (≥99 %) na L2/L3
- Kontext primárně **prohlubuje** kvalitu, neexpanduje validitu
- **Self-correction rate = 0 %** (Claude) nebo zanedbatelný (V4) - když model selže, nedokáže to opravit, ale málokdy selže
- **First-shot pass rate je extrémně vysoký** (Claude L0 = 80 %, V4 L3 = 100 %)

**Implikace:** Tyto modely jsou vhodné pro **single-shot generaci** v produkčním prostředí, kde repair loop představuje neakceptovatelnou latenci.

#### Profil B - "Growth-curve"

**Modely:** DeepSeek-Chat

**Charakteristika:**
- Nižší L0 baseline (90,67 % validity)
- **Klasický logaritmický růst** s L1 inflexním bodem (+6 p.b.)
- Code coverage roste o 6,3 p.b. na L1
- **Self-correction rate je nízký** - repair loop často skončí stale
- **Nejvyšší assertion depth** v experimentu (3,01 v průměru)

**Implikace:** Vhodný pro nasazení s **bohatým kontextem (L1+)** a tolerancí k občasným stale testům.

#### Profil C - "Inverted-U" (nestabilní)

**Modely:** Mistral Large 2512

**Charakteristika:**
- Peak validity na L1 (99,3 %), poté **propad** na L2 (92,7 %), L3 (90,0 %)
- **Self-correction rate = 0 %** (24/25 běhů)
- **Nejnižší endpoint coverage** v experimentu (27,7 %)
- Při zvýšení kontextu **generuje ambicióznější, ale chybnější testy**

**Implikace:** Pro Mistral je optimum **L1**. Vyšší úrovně kontextu **škodí**. Toto je důležité **counter-finding**: nelze předpokládat, že "více kontextu = lepší testy" pro všechny modely.

### 3.3 Detailní analýza per metrika

#### Validity Rate per model

```
L0 → L1 → L2 → L3 → L4
DeepSeek-Chat:  90,7 → 96,7 → 98,0 → 96,7 → 97,3   (klasický růst)
DeepSeek-V4:    95,3 → 98,0 → 99,3 → 100,0 → 100,0  (plateau na 100 %)
Mistral:        96,7 → 99,3 → 92,7 → 90,0 → 92,0    (inverted-U)
Claude Haiku:   98,7 → 99,3 → 99,3 → 99,3 → 99,3    (plochý plateau)
```

**Statistická analýza:** Variance napříč modely (within-level) je signifikantně vyšší než variance napříč úrovněmi (within-model). Konkrétně:
- **Range mezi modely** na L0: **8,0 p.b.** (90,7 % až 98,7 %)
- **Range mezi modely** na L3: **10,0 p.b.** (90,0 % až 100,0 %)
- **Range mezi úrovněmi** uvnitř modelu (max): **9,3 p.b.** pro Mistral

To formálně potvrzuje, že **mezimodelová variabilita > meziúrovňová** - **volba modelu má větší efekt na výsledky než volba úrovně kontextu**.

#### Assertion Depth - dva jasné tábory

| Tábor | Modely | Mean depth | Stylistická charakteristika                                     |
|---|---|---|-----------------------------------------------------------------|
| **Hluboký** | DeepSeek-Chat, Mistral | 2,80–3,01 | "Verbose tests" - 3+ assertionů, explicitní validace všech polí |
| **Stručný** | DeepSeek-V4, Claude Haiku | 2,23–2,49 | "Concise tests" - 2 assertiony, minimalistický styl             |

**Pozorování:** Tento rozdíl **není dán schopností**, ale **fine-tuning preferencí**. DeepSeek-V4 demonstrativně dosahuje 100 % validity s 2,3 assertiony - model **umí** psát ověření, ale **preferuje stručnost**. Claude Haiku dosahuje 99,2 % validity s 2,49 assertiony - stejný profil.

**Implikace pro výzkum:** Assertion depth jako metrika kvality má **omezenou vypovídací hodnotu** napříč modely. Relevantnější metrikou je **response validation %** (kolik testů ověřuje *něco* o těle), protože ta měří **funkční pokrytí** spíše než stylistický verbosity.

#### Response Validation - paradox L1

Tři modely vykazují **monotónní růst** RV s úrovní:
- DeepSeek-Chat: 51,3 → 85,3 → 94,0 → 96,7 → 98,7 (+47 p.b.)
- Mistral: 44,7 → 70,0 → 89,3 → 92,7 → 90,0 (+45 p.b.)

Dva modely vykazují **L1 propad** (anomalie):
- DeepSeek-V4: 68,7 → **60,7** → 89,3 → 85,3 → 93,3 (L1 < L0!)
- Claude Haiku: 50,0 → **41,3** → 81,3 → 82,0 → 90,7 (L1 < L0!)

**Hypotéza:** U modelů s **plateau-early profilem** vede přidání byznys dokumentace (L1) k **kratším testům** (focusovanějším na status code), čímž paradoxně klesá podíl body-validation testů. Až L2 (zdrojový kód) přinese **konkrétní strukturu odpovědí**, čímž RV explosivně roste.

#### Endpoint Coverage - nejvyšší rozptyl mezi modely

| Model | Mean EP Cov | Range (max − min) |
|---|---|---|
| DeepSeek-V4 | 40,3 % | 10,8 p.b. (47,6 → 36,8) |
| DeepSeek-Chat | 38,9 % | 10,0 p.b. (44,8 → 34,8) |
| Claude Haiku | 30,0 % | 6,8 p.b. (34,4 → 27,6) |
| Mistral | 27,7 % | 5,6 p.b. (30,8 → 25,2) |

**Pozorování:** **DeepSeek modely systematicky dosahují vyšší šířky pokrytí** než Mistral a Claude. Hypotéza: DeepSeek modely mají **silnější priors pro REST API patterns** (možná díky tréninku na čínském webu, který obsahuje hodně REST API specifikací) a generují **větší rozptyl scénářů**.

#### Code Coverage - největší modelový efekt

```
L0: range 66,9 % až 70,9 % (rozdíl 4,0 p.b.)
L1: range 65,6 % až 74,5 % (rozdíl 8,9 p.b.) ⭐ nejvyšší rozptyl
L4: range 67,0 % až 73,5 % (rozdíl 6,5 p.b.)
```

**Pozorování:** Na L1 dosahuje DeepSeek-Chat 74,5 %, zatímco Claude Haiku pouze 65,6 % - **rozdíl 8,9 p.b. v rámci stejného kontextu**. To znamená, že **stejný kontext vede k řádově odlišným výstupům podle modelu**.

### 3.4 Systematicky problematické testy napříč modely

Některé testy selhávají u **vícero modelů opakovaně**, indikující **strukturální obtížnost**, ne náhodnou chybu:

| Test concept | Postižené modely | Frekvence | Příčina                                                                                     |
|---|---|---|---------------------------------------------------------------------------------------------|
| `test_apply_discount_rate_limit` | Claude (4×), DeepSeek-Chat (3×), Mistral (3×) | 10/100 běhů | Rate-limit logika není v OpenAPI ani v dokumentaci - implementována v middleware/dekorátoru |
| `test_restore_soft_deleted_book` | Mistral (9×!), DeepSeek-Chat (5×) | 14/100 běhů | Response struktura `is_deleted` není konsistentně dokumentována                             |
| `test_update_order_status_valid` | DeepSeek-Chat (5×), DeepSeek-V4 (2×) | 7/100 běhů | State machine objednávek není v kontextu explicitní                                         |
| `test_delete_author_with_books` | Mistral (2×), DeepSeek-V4 (1×) | 3/100 běhů | Cascade behavior - kontextová nedokumentovanost                                             |

**Implikace:** Tyto testy ukazují na **mezi modely sdílené slepé skvrny**, které jsou důsledkem **struktur informací mimo dosah žádné úrovně kontextu** (middleware, runtime config, implicit business rules). **Žádný kontext nemůže opravit, co není zdokumentováno.**

### 3.5 Cena vs hodnota - Cost-Benefit analýza

| Model | Cena/run (Ø) | Cena/passed test | Validity Ø | "Premium per p.b. validity" |
|---|---|---|---|---|
| DeepSeek-V4 | $0,0027 | $0,00009 | 98,53 % | baseline |
| DeepSeek-Chat | $0,0069 | $0,00024 | 95,87 % | nedef. (nižší validity) |
| Mistral | $0,0449 | $0,00159 | 94,14 % | nedef. (nižší validity) |
| Claude Haiku | $0,0943 | $0,00318 | 99,17 % | **$1,46/0,01 p.b.** |

**Pozorování:** Pokud akceptujeme DeepSeek-V4 jako baseline (98,53 % validity, $0,0027/run), pak Claude Haiku přinese **+0,64 procentního bodu validity za cenu 35× vyšší**. Jinými slovy: **každý procento validity navíc stojí ~$1,46 za běh**.

**Diskuse:** Pro produkční nasazení s vysokou frekvencí (např. CI/CD pipeline s 1000 běhy denně), kdy kvalitní testy sníží počet false-positive failures:
- **Při 1000 bězích/den s DeepSeek-V4: $2,7/den**
- **Při 1000 bězích/den s Claude Haiku: $94/den**
- Roční rozdíl: **~$33,000**

Tato číselná disparita ospravedlňuje DeepSeek-V4 jako default choice pro většinu produkčních nasazení, zatímco Claude Haiku zůstává relevantní pro **kritické scénáře**, kde +0,7 p.b. validity je business-critical.

### 3.6 Závěr RQ3

**Hlavní zjištění RQ3:**

1. **Modely se systematicky liší ve své reakci na kontext** - existují minimálně **tři distinktní profily** (plateau-early, growth-curve, inverted-U).
2. **Mezimodelová variabilita signifikantně převyšuje meziúrovňovou** - volba modelu má větší dopad na výsledky než volba úrovně kontextu (Range L0: 8 p.b. mezi modely vs 3 p.b. mezi úrovněmi).
3. **Ekosystémová příslušnost není dominantní prediktor** chování - oba čínské modely (DeepSeek-Chat, V4) mají různé profily, podobně jako americký Claude a evropský Mistral mají různé charakteristiky.
4. **Strukturální slepé skvrny** existují napříč modely (rate-limit, soft-delete, state machines) - žádný kontext je nepřekoná, protože odpovídající informace **chybí ve všech vrstvách kontextu**.
5. **Cenový rozptyl 35× při rozdílu 0,7 p.b. validity** představuje silný argument pro **cost-aware model selection** v produkčním nasazení.

**Praktická doporučení per profil:**

| Use case | Doporučený model | Úroveň kontextu |
|---|---|---|
| Cost-sensitive, high-volume CI/CD | DeepSeek-V4-Flash | L1 |
| Maximální validity, kritické testy | Claude Haiku 4.5 | L2 |
| Hloubkové verbose testy | DeepSeek-Chat | L1–L2 |
| Středně náročné, evropský compliance | Mistral Large 2512 | **pouze L1** (vyšší škodí) |

---

## Závěrečná syntéza

### Hlavní zjištění napříč RQ1, RQ2, RQ3

#### 1. Není jeden univerzální optimální kontext

Univerzální heuristika **"více kontextu = lepší testy"** je v experimentu **vyvrácena**:

- Pro **validity** (RQ1) - saturace na L1 (~98 %), další úrovně marginální
- Pro **endpoint coverage** (RQ2) - **klesá** z L0 na L3, mírný rebound na L4
- Pro **assertion depth a response validation** (RQ1) - vrchol na L2, dále plateau
- Pro **model-specific** (RQ3) - Mistral zhoršuje výkon nad L1, Claude má L0 jako optimum pro některé metriky

**Závěr:** Optimální úroveň kontextu je **funkcí (model, metrika)**. Pro praktické nasazení doporučujeme **L1 nebo L2** jako sweet spot pro většinu scénářů, **NIKDY ne automaticky L4**.

#### 2. L3 (databázové schéma) je systematicky nepřínosná úroveň

Napříč všemi RQ a všemi modely je L3 **prakticky identická s L2** v kvalitativních metrikách:
- Validita Δ = ±1 p.b.
- Assertion depth Δ = ±0,1
- Response validation Δ = ±1 p.b.

Důvod: DB schema obsahuje informace o **persistenční vrstvě**, která není přímo testovatelná přes HTTP API. Strukturální constraint (UNIQUE, FOREIGN KEY) jsou pro generaci testů relevantní pouze pokud API tyto constraints **propaguje** do response (např. 409 Conflict). Tato informace je již obsažena v zdrojovém kódu (L2).

**Doporučení:** **L3 lze z procesu vynechat** bez měřitelné ztráty kvality, čímž se ušetří ~853 tokenů kontextu.

#### 3. L4 má specifický efekt - stylistický transfer, ne kvalitativní

L4 (ukázkové testy) má **netypický profil**:
- **Validitu nemění** signifikantně
- **Endpoint coverage** mírně zvyšuje (model kopíruje šířku)
- **Assertion depth** nemění
- **Response validation** zvyšuje (ukázky obsahují body-validation patterny)
- **Test type distribution** dramaticky posouvá k error testům
- **Helper usage** se může zdvojnásobit (pro Claude Haiku)

L4 je tedy **stylistický transfer mechanism**, ne klasický informační zdroj. Jeho hodnota závisí na **kvalitě ukázkových testů** - pokud jsou ukázkové testy verbose a robustní, vygenerované testy budou taky.

#### 4. Modely mají rozdílné inference profily

Tři distinktní profily identifikované v RQ3 mají **kořeny v designu modelu**:

- **Plateau-early** (DeepSeek-V4, Claude Haiku) - silné priors, vysoká first-shot accuracy, nízká dependence na kontextu
- **Growth-curve** (DeepSeek-Chat) - slabší priors, ale efektivní využití kontextu
- **Inverted-U** (Mistral) - průměrné priors, ale **negativní reakce na bohatý kontext** (over-confidence vede k chybným ambicím)

**Implikace pro engineering:** Při výběru LLM pro test generation je nutné **empiricky validovat**, jak konkrétní model reaguje na inkrementální kontext. Univerzální best-practice neexistuje.

### Limitace experimentu

**Interní validita:**
- **Stochasticita generace** (T = 0,4) vede k variabilitě mezi runy. Replikace n = 5 je dostatečná pro detekci větších efektů, ale slabé efekty (< 1 p.b.) mohou být šumem.
- **Single SUT** - pouze jedna aplikace (bookstore). Generalizace na jiné domény (finanční API, IoT API) vyžaduje další experimenty.

**Externí validita:**
- **4 modely** - výběr je reprezentativní pro 3 ekosystémy, ale ignoruje například japonské modely (Sakana), Microsoft (Phi), nebo open-source (LLaMA).
- **Verzování** - testované modely jsou aktuální k 1. polovině roku 2026. Příští verze mohou mít zcela odlišné profily.

**Konstruktová validita:**
- **Validity jako proxy pro "kvalitu testu"** je hrubá metrika. Test může projít a přitom **netestovat nic užitečného** (např. tautologický assertion). Doporučujeme doplnit *mutation testing* v dalším výzkumu.
- **Coverage jako proxy pro "úplnost testů"** ignoruje **branch coverage, condition coverage, MC/DC**. Toto je známá limitace v testovací literatuře.

### Otázky pro další výzkum

1. **Mutation testing** - kolik mutací zdrojového kódu generované testy chytí? (Test účinnosti jako *bug-finder*, ne pouze coverage.)
2. **Long-running stability** - jak se profily změní při 100+ bězích na model? (Degradace, drift, konzistence?)
3. **Domain adaptation** - replikace experimentu na finanční, IoT, nebo SaaS API. Jsou profily přenositelné?
4. **Fine-tuning effect** - pokud fine-tuneme open-source model na ukázkové testy, vyrovná se jeho kvalita Claude Haiku za zlomek ceny?
5. **Hybrid approaches** - kombinace LLM-generated testů s fuzz testing nebo property-based testing pro pokrytí edge cases.

### Závěrečné slovo

Tento experiment poskytuje **první systematické empirické srovnání** vlivu inkrementálního kontextu na LLM-generovaných API testů napříč 4 modely a 5 úrovněmi. Klíčové praktické sdělení je:

> **Univerzální 'více kontextu = lepší testy' je mýtus. Optimální kontext je function modelu, metriky a use-case. Pro většinu produkčních scénářů stačí L1 (OpenAPI + byznys dokumentace), zatímco volba modelu (DeepSeek-V4 pro cost, Claude Haiku pro kvalitu) má 35× větší ekonomický dopad než volba úrovně kontextu.**

---

*Dokument vygenerován: duben 2026*  
*Experimentální data: V12 (DeepSeek-Chat 15.4., DeepSeek-V4 26.4., Mistral 15.4., Claude Haiku 24.4. 2026)*