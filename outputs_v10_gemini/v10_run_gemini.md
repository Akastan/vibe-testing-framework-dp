# Analýza běhu: diplomka_v10 — 2026-03-31

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM modely | gemini-3.1-flash-lite-preview |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 34 endpointů) |
| Iterací | 5 |
| Runů na kombinaci | **5** |
| Testů na run | 30 |
| Stale threshold | 2 |
| **Temperature** | **0.4** |

### Změny oproti v9

| Parametr | v9 | v10 | Dopad |
|----------|----|----|-------|
| Runy | 3 | **5** | Robustnější statistika, nižší vliv outlierů |
| Temperature | Google default (nezadáno) | **0.4** | Nižší variabilita výstupů, deterministickější generování |
| Stale threshold | 3 | 2 | Agresivnější detekce zamrzlých testů |

---

## RQ1: Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje kvalitu LLM-generovaných API testů?

### Validity rate per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg ± Std |
|-------|-------|-------|-------|-------|-------|-----------|
| L0 | 90.0% | 96.67% | 90.0% | 83.33% | 96.67% | **91.33% ± 5.5** |
| L1 | 96.67% | 100.0% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |
| L2 | 100.0% | 96.67% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |
| L3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0% ± 0.0** |
| L4 | 96.67% | 100.0% | 100.0% | 100.0% | 100.0% | **99.33% ± 1.5** |

### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Validation (avg) |
|-------|--------------------|---------------------------|
| L0 | 1.81 | 56.0% |
| L1 | 1.34 | 30.67% |
| L2 | 1.43 | 41.33% |
| L3 | 1.41 | 39.33% |
| L4 | 1.44 | 46.0% |

### Iterace ke konvergenci a stale testy

| Level | Iterace (avg) | Stale (avg) |
|-------|---------------|-------------|
| L0 | 5.0 | 2.8 |
| L1 | 2.6 | 0.6 |
| L2 | 1.8 | 0.2 |
| L3 | 1.4 | 0.2 |
| L4 | 1.8 | 0.2 |

### Analýza trendu L0→L4

**L0→L1: Konzistentní kvalitativní skok — potvrzení z v9**

Přechod z L0 na L1 je opět nejvýznamnější změna. Validita vzrostla z 91.33 % na 99.33 %, počet selhání v první iteraci klesl z průměrných 9.6 na 0.6. S 5 runy je tento efekt statisticky robustnější než ve v9 (3 runy).

Kauzální mechanismus je stejný jako ve v9: `api_knowledge` odstraňuje tři hlavní kategorie selhání — špatné status kódy (200 vs. 201), špatné formáty requestů (JSON body vs. query param na PATCH /stock), a chybějící prerekvizity (stock default 0). L0 průměrně selhalo v 9.6 testech v první iteraci (rozmezí 3–15), zatímco L1 selhalo jen ve 0.6 testech (rozmezí 0–1).

Paradox assertion depth se potvrdil: L0 má nejvyšší assertion depth (1.81) a response validation (56.0 %), zatímco L1 má nejnižší (1.34 / 30.67 %). Interpretace z v9 platí — model bez kontextu kompenzuje nejistotu defenzivním testováním s více asercemi, z nichž značná část je nesprávná.

**Srovnání s v9:** V v9 činil L0→L1 skok 94.44 % → 100.0 %. Ve v10 je L0 horší (91.33 % vs. 94.44 %) a L1 mírně horší (99.33 % vs. 100.0 %). L0 pokles lze vysvětlit vyšším počtem runů — 5 runů zachytilo Run 4 s 83.33 % (5 never-fixed testů, 6 stale), který by ve v9 se 3 runy nemusel nastat. L1 pokles je způsoben jedním neopravitelným testem v Run 1 (`test_apply_discount_new_book_fails` — stejný discount edge case jako ve v9).

**L1→L2: Zdrojový kód potvrzuje marginální přidanou hodnotu**

Přidání zdrojového kódu (~11 474 tokenů) nezvýšilo validitu — obě úrovně mají 99.33 %. L2 má mírně lepší iterační profil (1.8 vs. 2.6) a nižší stale count (0.2 vs. 0.6), což naznačuje, že zdrojový kód sice nepřináší nové behaviorální informace, ale může mírně usnadnit první iteraci (4/5 runů na L2 prošlo na první pokus vs. 2/5 na L1).

Response validation vzrostla z 30.67 % na 41.33 % (+10.7 p.b.) — model vidí strukturu response objektů (Pydantic modely) a přidává kontroly response body. Assertion depth se mírně zvýšila (1.34 → 1.43). Oba trendy kopírují v9.

**L2→L3: DB schéma — žádný destruktivní outlier, žádné zlepšení**

Toto je nejvýznamnější rozdíl oproti v9. Ve v9 mělo L3 destruktivní outlier (Run 2: 40 % validity, ISBN prefix bug). Ve v10 má L3 **100 % validity ve všech 5 runech** — nejlepší výsledek celého experimentu s nulovou variancí.

Možné vysvětlení absence outlieru:
1. **Temperature 0.4** (vs. Google default ve v9) snížila variabilitu generování. Nižší temperature znamená deterministickější výstupy — model méně pravděpodobně zvolí „ambiciózní" helper architekturu s 6 helpery a neobvyklým ISBN prefixem.
2. **Statistická náhoda** — i při 5 runech nemusí nastat edge case, který má pravděpodobnost ~1/3 (1 outlier ze 3 runů ve v9).
3. **Kombinace obou faktorů** — temperature 0.4 snižuje pravděpodobnost outlieru z ~33 % na pravděpodobně <10 %, a 5 runů tuto sníženou pravděpodobnost nezachytilo.

Metriky kvality: EP coverage mírně klesla (52.94 % L2 → 49.41 % L3), assert depth zůstala stabilní (1.43 → 1.41), response validation mírně klesla (41.33 % → 39.33 %). DB schéma nepřináší žádnou přidanou hodnotu pro black-box HTTP testování — potvrzení závěru z v9, tentokrát bez destruktivního outlieru.

**L3→L4: Referenční testy — stabilní forma, mírně vyšší EP coverage**

L4 validita je 99.33 % (1 selhání v Run 1: `test_list_orders_invalid_date_format`). EP coverage vzrostla z 49.41 % na 55.88 % — referenční testy mohou poskytnout vodítka pro výběr endpointů. Response validation vzrostla na 46.0 % (nejvyšší z L1+).

Compliance: 4/5 runů na L4 má compliance 100 (timeout na všech voláních), vs. 0/5 na L0–L3. Potvrzuje závěr z v9 — referenční testy s `timeout=30` jsou účinnější pro vynucení technických pravidel než psané instrukce.

### Shrnutí RQ1

L1 (`api_knowledge`) je opět jednoznačně nejdůležitější kontextová vrstva — přináší skok z 91.33 % na 99.33+ % validity. L2–L4 přinášejí marginální zlepšení. Klíčový rozdíl oproti v9: **L3 nemá destruktivní outlier** díky nižší temperature (0.4). Assertion depth paradox se potvrdil (L0 > L1). Celkový trend je konzistentní s v9, ale s vyšší stabilitou díky temperature a většímu počtu runů.

---

## RQ2: Jak se liší endpoint coverage a code coverage vygenerovaných testů mezi jednotlivými úrovněmi kontextu?

### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| L0 | 67.65% | 70.59% | 67.65% | 76.47% | 67.65% | **70.0%** | 3.8 |
| L1 | 55.88% | 55.88% | 61.76% | 61.76% | 61.76% | **59.41%** | 3.2 |
| L2 | 55.88% | 52.94% | 50.0% | 52.94% | 52.94% | **52.94%** | 2.1 |
| L3 | 47.06% | 52.94% | 50.0% | 50.0% | 47.06% | **49.41%** | 2.4 |
| L4 | 52.94% | 61.76% | 52.94% | 55.88% | 55.88% | **55.88%** | 3.5 |

### Code coverage per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| L0 | 81.3% | 74.0% | 80.9% | 74.3% | 83.9% | **78.9%** | 4.5 |
| L1 | 86.0% | 86.0% | 84.4% | 84.9% | 85.2% | **85.3%** | 0.7 |
| L2 | 84.1% | 85.5% | 84.1% | 84.3% | 85.7% | **84.7%** | 0.7 |
| L3 | 84.3% | 85.8% | 82.4% | 83.3% | 84.1% | **84.0%** | 1.3 |
| L4 | 85.4% | 83.8% | 84.6% | 84.3% | 83.8% | **84.4%** | 0.6 |

### Code coverage breakdown (crud.py vs main.py)

| Level | crud.py Avg | main.py Avg | Gap (main−crud) |
|-------|-------------|-------------|-----------------|
| L0 | 56.5% | 87.2% | 30.7 p.b. |
| L1 | 70.7% | 88.7% | 18.0 p.b. |
| L2 | 70.1% | 87.2% | 17.1 p.b. |
| L3 | 68.5% | 86.7% | 18.2 p.b. |
| L4 | 69.0% | 87.7% | 18.7 p.b. |

### Další metriky kvality

| Level | Happy (avg %) | Error (avg %) | Edge (avg %) | Status Code Diversity (avg) |
|-------|---------------|---------------|--------------|----------------------------|
| L0 | 60.67 | 38.0 | 1.33 | 5.0 |
| L1 | 53.33 | 46.67 | 0 | 6.8 |
| L2 | 53.33 | 46.67 | 0 | 7.0 |
| L3 | 49.33 | 50.67 | 0 | 7.0 |
| L4 | 47.33 | 52.0 | 0.67 | 6.6 |

### Analýza

**Endpoint coverage: potvrzení klesajícího trendu**

EP coverage klesá s kontextem: L0 (70.0 %) → L3 (49.41 %), s mírným nárůstem na L4 (55.88 %). Trend je silnější než ve v9 (58.82 % → 49.02 %) — L0 ve v10 má výrazně vyšší EP coverage (70.0 % vs. 58.82 %), protože L0 bez kontextu „rozhazuje síť" přes co nejvíce endpointů. Run 4 na L0 dokonce dosáhl 76.47 % (26/34 endpointů) — nejvyšší v celém experimentu.

Efekt zaměření potvrzuje distribuce typů testů: L0 generuje 60.67 % happy path (jedno volání na endpoint = širší pokrytí), zatímco L3–L4 generují ~49 % happy path a ~51 % error testů (hlubší testování méně endpointů). S 5 runy je tento trend statisticky robustnější než ve v9.

**Code coverage: L1 opět nejvyšší, L2–L4 plateau**

L1 dosahuje nejvyššího code coverage (85.3 %) navzdory nižší EP coverage (59.41 %) než L0 (70.0 % EP, 78.9 % code coverage). Paradox z v9 se potvrdil — L1 testy pokrývají méně endpointů, ale procházejí hlubšími větvemi kódu díky správnému testování error cases.

L2–L4 tvoří plateau kolem 84–85 % — přidání zdrojového kódu, DB schématu a referenčních testů nemá měřitelný dopad na code coverage. L2 (84.7 %) je mírně nižší než L1 (85.3 %), L3 (84.0 %) je nejnižší z L1+, L4 (84.4 %) se mírně vrací. Rozptyl je minimální (std 0.6–1.3) — coverage je u L1+ velmi stabilní.

**crud.py vs main.py: gap jako indikátor hloubky**

`main.py` (routing) je stabilně 86–89 % napříč všemi levely — každé HTTP volání prochází routing vrstvou. Klíčový diferenciátor je `crud.py` (business logika):

- **L0: 56.5 %** — nejnižší, gap 30.7 p.b. Failing testy neprocházejí business logikou.
- **L1: 70.7 %** — skok +14.2 p.b., gap 18.0 p.b. Správné testování error cases aktivuje branching.
- **L2: 70.1 %** — marginální pokles oproti L1. Zdrojový kód nepřidává nové testovatelné větve.
- **L3: 68.5 %** — mírný pokles. DB schéma nepomáhá pokrýt business logiku.
- **L4: 69.0 %** — stabilní. Referenční testy nezlepšují hloubku coverage.

L1 má nejmenší gap (18.0 p.b.) — testy nejefektivněji pronikají do business vrstvy. L0 gap (30.7 p.b.) je téměř dvojnásobný — model bez kontextu „proletí" routing vrstvou, ale neprojde branching logikou.

L0 code coverage je ve v10 nižší než ve v9 (78.9 % vs. 82.2 %). Pravděpodobný důvod: více never-fixed testů na L0 (průměrně 2.6 vs. 1.67 ve v9) znamená, že více testů selhává a neprovádí plný HTTP flow. Run 2 a Run 4 mají shodně 74 % total coverage — oba jsou runy s problematickými helpery.

**Srovnání s v9:**

| Metrika | v9 L0 | v10 L0 | v9 L1 | v10 L1 | v9 L2 | v10 L2 | v9 L3* | v10 L3 | v9 L4 | v10 L4 |
|---------|-------|--------|-------|--------|-------|--------|--------|--------|-------|--------|
| Code Cov | 82.2% | 78.9% | 85.4% | 85.3% | 84.2% | 84.7% | 78.8% | 84.0% | 83.6% | 84.4% |
| crud.py | 63.7% | 56.5% | 71.3% | 70.7% | 68.8% | 70.1% | 57.5%* | 68.5% | 67.6% | 69.0% |

*v9 L3 průměr ovlivněn outlierem (Run 2: crud.py 31.3 %). Bez outlieru by v9 L3 crud.py ≈ 70.6 %.

L0 má ve v10 vyšší EP coverage ale nižší code coverage — důsledek více never-fixed testů, které sice pokrývají více endpointů v plánu, ale ve skutečnosti neprocházejí business logikou kvůli selhání. L3 se ve v10 dramaticky zlepšilo díky absenci outlieru (84.0 % vs. 78.8 %).

---

## RQ3: Jaké typy selhání se vyskytují ve vygenerovaných testech a jak se jejich distribuce mění s rostoucím kontextem?

### Failure taxonomy (první iterace, součet přes 5 runů)

| Typ selhání | L0 (48 failů) | L1 (3 faily) | L2 (1 fail) | L3 (1 fail) | L4 (1 fail) |
|-------------|---------------|-------------|-------------|-------------|-------------|
| wrong_status_code | 15 (31.3%) | 3 (100%) | 1 (100%) | 1 (100%) | 1 (100%) |
| timeout | 24 (50.0%) | 0 | 0 | 0 | 0 |
| other | 8 (16.7%) | 0 | 0 | 0 | 0 |
| assertion_mismatch | 1 (2.1%) | 0 | 0 | 0 | 0 |

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg fixed | Avg never-fixed | Fix rate |
|-------|---------------------|-----------|-----------------|----------|
| L0 | 9.6 | 7.0 | 2.6 | 72.9% |
| L1 | 0.6 | 0.4 | 0.2 | 66.7% |
| L2 | 0.2 | 0 | 0.2 | 0% |
| L3 | 0.2 | 0.2 | 0 | 100% |
| L4 | 0.2 | 0 | 0.2 | 0% |

### Analýza per kategorie

**Timeout (L0: 50 %)**

Timeouty tvoří polovinu všech L0 selhání (24 ze 48). Jsou koncentrovány v Runech 1–3 (10, 7, 7 timeoutů). Mechanismus je identický s v9: model bez `api_knowledge` posílá requesty ve špatném formátu (typicky JSON body místo query parametru na PATCH /stock, nebo chybný formát na discount/tag endpointech). Server na neočekávaný formát reaguje zablokováním, které vyústí v 30s timeout.

Run 4 má 0 timeoutů ale 8× wrong_status_code — model v tomto runu zvolil jiný přístup (jednodušší helpery, ale špatné status kódy). Run 5 má jen 3 selhání (2× wrong_status_code, 1× assertion_mismatch) — nejlepší L0 run, model „uhodl" většinu kontraktů správně.

Na L1+ se timeouty nevyskytují vůbec — `api_knowledge` explicitně specifikuje formáty requestů.

**Wrong status code (L0: 31.3 %, L1+: dominantní zbytková chyba)**

Na L0 tvoří wrong_status_code 15 ze 48 selhání. Nejčastější záměny: 422 vs. 404 (model očekává 422 pro neexistující zdroj, API vrací 404), 200 vs. 204 (DELETE odpovědi), 200 vs. jiný kód na stock/rating endpointech.

Na L1–L4 zůstává wrong_status_code jedinou kategorií selhání. Konkrétní přetrvávající testy:
- `test_apply_discount_new_book_fails` (L1 Run 1, L3 Run 1) — discount boundary edge case
- `test_malformed_json_payload` (L2 Run 2) — model testuje, jak API reaguje na malformed JSON, ale chybně odhaduje status kód
- `test_list_orders_invalid_date_format` (L4 Run 1) — model očekává 422 pro nevalidní formát data

**Other (L0: 16.7 %)**

Kategorie „other" (8 ze 48 selhání) je koncentrována v Run 3 (7 selhání). Z kontextu (`error_summary` obsahuje `"items": [{"book_id": b["id"], "quantity": 1}]`) jde pravděpodobně o order-related testy, kde helper `create_book` nemá dostatečný stock (default 0) a objednávka selže na insufficient stock.

**Halucinace status kódů**

| Level | Kódy v kontextu | Halucinované |
|-------|-----------------|--------------|
| L0 | 200, 201, 204, 422 | 404 ✅ (korektní inference) |
| L1+ | 200, 201, 204, 400, 404, 409, 422 | žádné |

Identický vzorec jako ve v9. L0 „halucinuje" 404 z HTTP konvencí — korektní inference, nikoliv chybná halucinace.

**Vzorec opravitelnosti: potvrzení z v9**

L0 chyby jsou „povrchové" a opravitelné (72.9 % fix rate) — špatné status kódy a formáty requestů, kde pytest error message poskytuje dostatečnou informaci pro opravu. Typický průběh: helper_fallback v 1. iteraci → isolated v dalších → stabilizace.

L1+ zbývající chyby jsou „sémantické" a většinou neopravitelné — discount boundary, malformed JSON handling, date format validation. Error message obsahuje `assert r.status_code == 400` nebo `== 422`, ale model opakovaně generuje stejnou špatnou opravu, protože nepochopí příčinu.

---

## Srovnání v9 vs. v10 — efekt temperature a počtu runů

### Souhrnná tabulka

| Metrika | v9 | v10 | Trend |
|---------|----|----|-------|
| **Temperature** | default (≈1.0?) | **0.4** | Nižší variabilita |
| **Runy** | 3 | **5** | Robustnější statistika |
| **L0 validity** | 94.44% | 91.33% | ▼ (-3.1 p.b.) |
| **L1 validity** | 100.0% | 99.33% | ▼ (-0.7 p.b.) |
| **L2 validity** | 98.89% | 99.33% | ▲ (+0.4 p.b.) |
| **L3 validity** | 80.0% (outlier) | **100.0%** | ▲▲ (+20 p.b.) |
| **L4 validity** | 97.78% | 99.33% | ▲ (+1.6 p.b.) |
| **L3 std** | 34.6 | **0.0** | ▼▼ (eliminace outlieru) |
| **L0 EP coverage** | 58.82% | 70.0% | ▲ (+11.2 p.b.) |
| **L0 stale avg** | 1.67 | 2.8 | ▲ (více zamrzlých) |

### Interpretace

**Temperature 0.4 eliminovala L3 outlier.** Nejdramatičtější změna: L3 přešlo z 80.0 % ± 34.6 (bimodální distribuce s destruktivním outlierem) na 100.0 % ± 0.0 (perfektní stabilita). Nižší temperature výrazně snížila pravděpodobnost, že model zvolí „ambiciózní" 6-helper architekturu s neobvyklým ISBN prefixem. Všech 5 L3 runů zvolilo konzervativní 4-helper strategii.

**L0 se mírně zhoršilo.** 91.33 % vs. 94.44 % ve v9. Nižší temperature na L0 může být kontraproduktivní — bez kontextu model potřebuje „kreativitu" k uhádnutí API kontraktů, a temperature 0.4 může omezit jeho schopnost explorovat alternativní přístupy. Run 4 s 83.33 % (5 never-fixed, 6 stale) je nejhorší L0 run v obou experimentech.

**L1 mírně horší — discount edge case přetrvává.** 99.33 % vs. 100.0 % ve v9. Jeden test (`test_apply_discount_new_book_fails`) zůstává problematický napříč experimenty — discount boundary vyžaduje znalost aktuálního roku vs. `published_year`, kterou `api_knowledge` explicitně nezmiňuje.

**EP coverage na L0 vzrostla.** 70.0 % vs. 58.82 % ve v9. S 5 runy a nižší temperature model konzistentněji generuje široké pokrytí endpointů na L0.

---

## Repair loop analýza

### Efektivita per level

| Level | Avg failing (iter 1) | Avg opraveno | Fix rate | Iterace ke konvergenci | Dominantní strategie |
|-------|---------------------|-------------|----------|------------------------|---------------------|
| L0 | 9.6 | 7.0 | 72.9% | 5.0 (max) | helper_fallback → isolated alternace |
| L1 | 0.6 | 0.4 | 66.7% | 2.6 | isolated |
| L2 | 0.2 | 0 | 0% | 1.8 | isolated → stale |
| L3 | 0.2 | 0.2 | 100% | 1.4 | isolated |
| L4 | 0.2 | 0 | 0% | 1.8 | isolated → stale |

### L0: konzistentní showcase repair loopu

L0 opět demonstruje hodnotu repair loopu. Průběh per run:

- **Run 1:** 11 failing → 8 opraveno (72.7 %). helper_fallback → isolated(10) → isolated(4) → isolated(1) + stale(3). Never-fixed: `test_create_order_success`, `test_delete_pending_order`, `test_remove_tags_from_book_success`.
- **Run 2:** 11 failing → 10 opraveno (90.9 %). helper_fallback → isolated(6) → isolated(1) → stale(1). Never-fixed: `test_update_stock_negative`.
- **Run 3:** 15 failing → 12 opraveno (80 %). helper_fallback → isolated(5) → isolated(3) → stale(3). Never-fixed: `test_delete_order_invalid_status`, `test_update_order_status_success`, `test_update_stock_success`.
- **Run 4:** 8 failing → 3 opraveno (37.5 %). isolated(8) → isolated(6) → stale(6). Never-fixed: 5 testů (nejvíce stale v celém experimentu). **Poznámka:** Run 4 jako jediný L0 run nepoužil `helper_fallback` — šel rovnou na `isolated`, což bylo méně efektivní.
- **Run 5:** 3 failing → 2 opraveno (66.7 %). isolated(3) → isolated(1) → stale(1). Never-fixed: `test_update_stock_quantity`.

**Vzorec:** Runy s `helper_fallback` v první iteraci (Run 1–3) mají vyšší fix rate (72.7–90.9 %) než runy bez něj (Run 4: 37.5 %). helper_fallback efektivně řeší kaskádové chyby v prvním kroku. Run 4 měl jen 8 selhání (všechno wrong_status_code, ne timeout/other), proto se neaktivoval helper_fallback práh (potřebuje ≥70 % stejnou chybu) — šly rovnou na isolated opravy.

**Srovnání s v9:** L0 fix rate je nižší ve v10 (72.9 % vs. 84.8 %). Hlavní příčina je Run 4 (37.5 %), který táhne průměr dolů. Bez Run 4 by průměr byl 77.5 % — bližší v9.

### Never-fixed testy na L0 — vzorce

Nejčastěji never-fixed endpointy na L0:

| Endpoint/oblast | Počet never-fixed (z 5 runů) |
|-----------------|------------------------------|
| `update_stock` | 3 (Run 2, 3, 5) |
| `order_status` | 2 (Run 1, 3) |
| `delete_order` | 2 (Run 1, 3) |
| `create_order` | 1 (Run 1) |
| `remove_tags` | 1 (Run 1) |
| `list_reviews` | 1 (Run 4) |
| `get_book_rating` | 1 (Run 4) |

`update_stock` je konzistentně problematický — PATCH /stock vyžaduje query parametr (ne JSON body) a quantity je delta (ne absolutní hodnota). Bez `api_knowledge` model opakovaně selhává na tomto endpointu.

### StaleTracker

| Level | Stale (avg) | Max stale v jednom runu |
|-------|-------------|------------------------|
| L0 | 2.8 | 6 (Run 4) |
| L1 | 0.6 | 1 |
| L2 | 0.2 | 1 |
| L3 | 0.2 | 1 |
| L4 | 0.2 | 1 |

StaleTracker s prahem 2 (vs. 3 ve v9) je agresivnější — označí test jako stale po 2 po sobě jdoucích neúspěšných opravách. To vede k vyššímu průměrnému stale count na L0 (2.8 vs. 1.67 ve v9), ale šetří LLM tokeny tím, že dříve ukončí marné opravy.

---

## L0 Run 4 — hloubková analýza (nejhorší L0 run)

### Fakta

- **Validity:** 83.33 % (25/30) — nejnižší v celém experimentu
- **5 never-fixed testů**, 6 stale, 0 % fix rate na 5 persistentních selhání
- **EP Coverage:** 76.47 % (26/34) — paradoxně nejvyšší v experimentu
- **Code Coverage:** 74.3 % (nejnižší), crud.py 46.7 % (nejnižší)
- **Helpery:** pouze 1 (`unique`) — model negeneroval `create_author`/`create_category`/`create_book`
- **Compliance:** 80 (timeout na všech voláních — model přidal timeout ale ne přes helper vzor)

### Root cause: absence helperů

Model v tomto runu vygeneroval pouze jednu helper funkci (`unique`). Každý test musí vytvářet data inline — autora, kategorii, knihu — přímým voláním POST endpointů. Bez sdílených helperů s korektními parametry (stock=10, published_year=2020) se výrazně zvyšuje pravděpodobnost chyb:

1. **`test_update_stock_success`** — inline vytváří knihu s `{"title": unique("book"), "author": "Author", "stock": 0}` — špatný formát (chybí `isbn`, `author_id`, `category_id`, `published_year`). API vrací 422, test dělá `.json()["id"]` → `KeyError: 'id'`. Tato chyba se opakuje identicky v iteracích 2–5.

2. **`test_remove_tags_success`** — inline vytváří knihu s `{"title": unique("book"), "tag_ids": [tag_id]}` — opět špatný formát. API vrací 422. `.json()["id"]` → `KeyError: 'id'`.

3. **`test_get_book_rating_success`** a **`test_list_reviews_success`** — posílají `"id": book_id` kde `book_id` je string z `unique("book")`, ale API očekává auto-increment integer ID. Volání `POST /books` s neexistujícími poli selhává, další volání na `/books/{book_id}/rating` vrací 422/404.

4. **`test_create_order_invalid_email`** — posílá `"items": [{"book_id": 1, "quantity": 1}]`, ale po DB resetu neexistuje kniha s ID 1. API vrací 404 (not found) místo očekávaného 422 (validation error). Model neví, že pro testování email validace musí nejprve vytvořit knihu.

### Proč model nevygeneroval helpery

L0 kontext obsahuje pouze OpenAPI specifikaci (~20 737 tokenů). Temperature 0.4 snižuje kreativitu generování. V tomto konkrétním runu model zvolil „minimalistický" přístup — přímé inline volání místo helper abstrakcí. Bez `api_knowledge` neví, jaké povinné parametry vyžadují POST endpointy, a inline přístup exponuje tuto neznalost v každém testu.

Paradox: Run 4 má **nejvyšší EP coverage** (76.47 %, 26/34 endpointů) — model pokrývá více endpointů, protože bez helperů píše jednodušší, kratější testy (avg 5.73 řádků) a „stihne" pokrýt víc. Ale **nejnižší code coverage** (74.3 %) — testy sice volají více endpointů, ale 5 z nich selhává na setup (inline data jsou špatná), takže neprocházejí business logikou.

### Evoluce selhání přes iterace

- **Iterace 1:** 8 selhání, všechna `wrong_status_code` (classifier). `isolated` repair (ne `helper_fallback` — chyby nejsou ≥70 % identické).
- **Iterace 2:** Opraveny 2 testy (`test_get_nonexistent_author`: 422→404, `test_delete_book_success`: 422→404). Zbývá 6. Nové `KeyError: 'id'` na `test_update_stock_success` a `test_remove_tags_success` — repair zhoršil inline kód.
- **Iterace 3:** Opraven `test_delete_order_invalid_id` (422→404). Zbývá 5. Stale threshold (2) dosažen pro 6 testů.
- **Iterace 4–5:** Identické — 5 selhání, všechna stale. Repair loop přeskočen.

**Masking Effect (varianta L0):** Na L0 Run 4 není masking přes helper assertion (jako L3 Run 2 ve v9), ale přes **absenci správného setup**. Model vidí `KeyError: 'id'` a pokouší se opravit přístup k response, ale root cause je v tom, že POST request s neúplnými daty vrací error JSON bez klíče `id`. Model by musel kompletně přepsat inline setup — přidat `isbn`, `author_id`, `category_id` — ale z error message `KeyError: 'id'` to není zřejmé.

### Srovnání s L3 Run 2 (v9 outlier)

| Aspekt | v9 L3 Run 2 | v10 L0 Run 4 |
|--------|-------------|--------------|
| Validity | 40.0 % | 83.33 % |
| Root cause | ISBN prefix 1 znak moc | Absence helperů |
| Failing | 18/30 | 5/30 |
| Fix rate | 0 % | 37.5 % (3/8 fixed) |
| Masking | assert v helperu skrývá response body | KeyError skrývá neúplný setup |
| Příčina | DB schéma → ambiciózní architektura | Temperature 0.4 + L0 → minimalistická architektura |

L0 Run 4 je méně destruktivní (83 % vs. 40 %), ale ilustruje opačný problém: v9 L3 Run 2 selhal na **příliš komplexní** helper architektuře, v10 L0 Run 4 selhal na **příliš jednoduché** (žádné helpery). Obě extrémy vedou k neopravitelným chybám.

### Význam pro diplomovou práci

1. **Helper architektura jako kritický faktor:** Runy se standardními 4 helpery (`unique`, `create_author`, `create_category`, `create_book`) konzistentně dosahují vyšší validity. Absence helperů (Run 4) nebo nadměrné helpery (v9 L3 Run 2) zvyšují riziko selhání.
2. **EP coverage ≠ kvalita:** Run 4 má nejvyšší EP coverage ale nejnižší validity — varování před interpretací EP coverage jako indikátoru kvality.
3. **Inline testy exponují neznalost:** Bez helperů je neznalost API kontraktu viditelná v každém testu, místo aby byla izolována v jednom helperu.

---

## Instruction compliance

### Compliance score per level

| Level | Missing timeout (avg %) | Compliance score (avg) |
|-------|------------------------|------------------------|
| L0 | 100% (5/5 runů) | 80 |
| L1 | 100% (5/5) | 80 |
| L2 | 100% (5/5) | 80 |
| L3 | 100% (5/5) | 80 |
| L4 | **20%** (1/5) | **96** |

L4 compliance je silnější než na L0–L3: 4 z 5 runů má timeout na všech HTTP voláních (compliance 100). Jediný run bez timeoutu je Run 2 (missing_timeout=40). Ve v9 mělo L4 100 % compliance ve všech 3 runech — ve v10 s 5 runy se ukázalo, že compliance není 100% garantovaná ani s referenčními testy.

L0–L3 mají konzistentně 0 % timeout compliance (všech 20 runů) — model nikdy nepřidal `timeout=30` bez vzoru v referenčních testech. Toto je silnější evidence než ve v9 (kde L0 Run 3 a L3 Run 2 měly compliance 100 — pravděpodobně náhoda při vyšší temperature).

**Interpretace:** Nižší temperature (0.4) paradoxně snížila pravděpodobnost „náhodného" dodržení timeout pravidla na L0–L3. Model se determinističtěji drží svého defaultního vzoru (bez timeout), pokud nemá explicitní příklad. Referenční testy na L4 jsou téměř nutnou podmínkou pro timeout compliance.

---

## Shrnutí, vzory a limity

### Hlavní zjištění — RQ1

`api_knowledge` (L1) zůstává klíčovou kontextovou vrstvou: skok z 91.33 % na 99.33+ % validity. Temperature 0.4 eliminovala destruktivní L3 outlier z v9 — L3 dosáhlo 100 % validity ve všech 5 runech. Assertion depth paradox se potvrdil (L0: 1.81 > L1: 1.34). Celkový trend je konzistentní s v9, s vyšší stabilitou a bez bimodálního chování na L3.

### Hlavní zjištění — RQ2

EP coverage klesá s kontextem (70.0 % L0 → 49.41 % L3), code coverage zůstává stabilní (L0: 78.9 %, L1: 85.3 %, L2–L4 plateau 84–85 %). L0 má ve v10 výrazně vyšší EP coverage (70.0 % vs. 58.82 % ve v9) — nižší temperature vede k konzistentnějšímu široce rozloženému pokrytí na L0. L1 code coverage je prakticky identická s v9 (85.3 % vs. 85.4 %). Klíčový nález: `crud.py` gap (rozdíl main.py − crud.py) je na L0 30.7 p.b. a na L1+ stabilně ~18 p.b. — L1 testy pronikají do business vrstvy o řád efektivněji.

### Hlavní zjištění — RQ3

Distribuce selhání na L0 se posunula: timeout tvoří 50 % (vs. 39.4 % ve v9), wrong_status_code 31.3 % (vs. 18.2 %). Kategorie „other" klesla na 16.7 % (vs. 39.4 %) — lepší diagnostika díky konzistentnějším chybám při nižší temperature. Selhání na L1+ jsou téměř výhradně wrong_status_code kolem discount boundary a edge case validací.

### Neočekávané vzory

1. **Temperature jako stabilizátor:** 0.4 eliminovala L3 outlier a snížila variabilitu napříč levely, ale mírně zhoršila L0 (model méně kreativně hádá API kontrakty).
2. **EP coverage–validity trade-off na L0:** Vyšší EP coverage (70 %) koreluje s nižší validity (91.33 %) — model pokrývá více endpointů, ale méně kvalitně.
3. **Timeout compliance binární na úrovni modelu:** 0/20 runů na L0–L3, 4/5 na L4 — referenční testy jsou téměř nutnou podmínkou.
4. **Run 4 anomálie na L0:** Nejhorší L0 run (83.33 %, 6 stale) zvolil odlišnou strategii (pouze `unique` helper, žádné `create_author`/`create_category`/`create_book` helpery) — bez standardních helperů musel každý test vytvářet data inline, což vedlo k více chybám.
5. **Discount edge case je cross-level problém:** `test_apply_discount_new_book_fails` selhává na L1 (Run 1), L3 (Run 1), i L4 (v9). Discount boundary vyžaduje znalost, která není v žádné kontextové vrstvě explicitně.

### Limity experimentu

1. **Jeden model:** Závěry platí pro gemini-3.1-flash-lite-preview. Větší modely mohou mít jiné chování.
2. **Jedna API:** Bookstore API je jednoduchá CRUD + orders.
3. **5 runů:** Lépe než 3 (v9), ale pro L0 s high variance stále nedostatečné pro robustní CI.
4. **Fixní 30 testů:** Limituje EP coverage ceiling při 34 endpointech.
5. **Chybějící coverage L2–L4:** Code coverage data budou doplněna.
6. **Stale threshold 2 vs. 3:** Nižší threshold zvyšuje stale count na L0 (2.8 vs. 1.67) — nemusí být lepší pro fix rate.

### Threats to validity

**Internal validity:**
- Temperature 0.4 snižuje variabilitu, ale L0 Run 4 ukazuje, že variabilita není eliminována.
- Stale threshold 2 může předčasně ukončit opravy, které by s threshold 3 uspěly.
- L0 Run 4 s neobvyklou helper architekturou (1 helper) naznačuje, že i při temperature 0.4 model občas zvolí radikálně odlišný přístup.

**External validity:**
- Shodné s v9 — single API, single model.

**Construct validity:**
- Assertion depth neměří kvalitu asercí — L0 stále nejvyšší, ale nejnižší validity.
- Compliance je binární (timeout ano/ne) — nízká granularita.

**Conclusion validity:**
- 5 runů zlepšuje statistickou sílu oproti v9.
- L3 100 % ± 0.0 může být artefakt temperature 0.4 — s default temperature by outlier mohl nastat i s 5 runy.

---

## Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1 (90.0%)</summary>

```
Validity: 90.0% (27/30)
EP Coverage: 67.65% (23/34)
Assert Depth: 2.03
Response Validation: 63.33%
Stale: 3 (test_create_order_success, test_delete_pending_order, test_remove_tags_from_book_success)
Iterations: 5
Helpers: 7 (unique, api_get, api_post, api_put, api_delete, create_resource, delete_resource)
Plan adherence: 100%
Compliance: 80 (timeout missing on all 34 calls)
Failure taxonomy (iter 1): timeout 10, other 1 (11 total)
Repair: iter1=11F→helper_fallback, iter2=11F→isolated(10), iter3=4F→isolated, iter4=3F→isolated+stale(3), iter5=3F
Never-fixed (3): test_create_order_success, test_delete_pending_order, test_remove_tags_from_book_success
Fixed (8): test_add_review_valid, test_add_tags_to_book_success, test_apply_excessive_discount,
  test_apply_valid_discount, test_delete_book_success, test_get_book_average_rating,
  test_update_book_stock, test_update_stock_quantity
Status codes hallucinated: 404
```
</details>

<details>
<summary>L0 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 70.59% (24/34)
Assert Depth: 1.57
Response Validation: 40.0%
Stale: 1 (test_update_stock_negative)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book [no stock field])
Plan adherence: 100%
Compliance: 80 (timeout missing on all 35 calls)
Failure taxonomy (iter 1): wrong_status_code 4, timeout 7 (11 total)
Repair: iter1=11F→helper_fallback, iter2=6F→isolated(6), iter3=1F→isolated, iter4=1F→stale(1), iter5=1F
Never-fixed (1): test_update_stock_negative
Fixed (10): test_add_tags_empty_list, test_apply_discount_too_high, test_create_review_invalid_rating,
  test_delete_author_invalid_id, test_delete_book_success, test_delete_order_invalid_id,
  test_get_book_rating_success, test_get_category_not_found, test_get_nonexistent_author, test_remove_tags_valid
Status codes hallucinated: 404
```
</details>

<details>
<summary>L0 — Run 3 (90.0%)</summary>

```
Validity: 90.0% (27/30)
EP Coverage: 67.65% (23/34)
Assert Depth: 1.80
Response Validation: 63.33%
Stale: 3 (test_delete_order_invalid_status, test_update_order_status_success, test_update_stock_success)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book [has stock])
Plan adherence: 100%
Compliance: 80 (timeout missing on all 42 calls)
Failure taxonomy (iter 1): wrong_status_code 1, timeout 7, other 7 (15 total)
Repair: iter1=15F→helper_fallback, iter2=5F→isolated(5), iter3=3F→isolated(3), iter4=3F→stale(3), iter5=3F
Never-fixed (3): test_delete_order_invalid_status, test_update_order_status_success, test_update_stock_success
Fixed (12): test_add_tags_to_book_success, test_apply_discount_success, test_apply_discount_too_high,
  test_create_order_success, test_create_review_invalid_rating, test_create_review_success,
  test_delete_book_success, test_get_author_not_found, test_get_book_rating_success,
  test_get_order_details, test_update_book_price_negative, test_update_order_status_invalid
Status codes hallucinated: 404
```
</details>

<details>
<summary>L0 — Run 4 (83.33%) ⚠️ Nejhorší L0 run</summary>

```
Validity: 83.33% (25/30)
EP Coverage: 76.47% (26/34) — nejvyšší v experimentu
Assert Depth: 1.83
Response Validation: 46.67%
Stale: 6 (test_create_order_invalid_email, test_delete_order_invalid_id, test_get_book_rating_success,
  test_list_reviews_success, test_remove_tags_success, test_update_stock_success)
Iterations: 5
Helpers: 1 (pouze unique!) — model negeneroval create_author/create_category/create_book helpery
Plan adherence: 100%
Compliance: 80 (timeout missing on all 45 calls)
Failure taxonomy (iter 1): wrong_status_code 8 (8 total)
Repair: iter1=8F→isolated(8), iter2=6F→isolated(6), iter3=5F→stale(6), iter4=5F→stale(6), iter5=5F
Never-fixed (5): test_create_order_invalid_email, test_get_book_rating_success, test_list_reviews_success,
  test_remove_tags_success, test_update_stock_success
Fixed (3): test_delete_book_success, test_delete_order_invalid_id, test_get_nonexistent_author
Status codes hallucinated: 404

POZNÁMKA: Tento run má pouze 1 helper (unique). Model generoval data inline v každém testu.
Absence create_book helperu znamená, že každý test musí ručně vytvořit autora, kategorii i knihu,
což zvyšuje pravděpodobnost chyb v datech (chybějící stock, špatný formát).
```
</details>

<details>
<summary>L0 — Run 5 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 67.65% (23/34)
Assert Depth: 1.80
Response Validation: 66.67%
Stale: 1 (test_update_stock_quantity)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book [has stock])
Plan adherence: 100%
Compliance: 80 (timeout missing on all 38 calls)
Failure taxonomy (iter 1): wrong_status_code 2, assertion_value_mismatch 1 (3 total)
Repair: iter1=3F→isolated(3), iter2=1F→isolated(1), iter3=1F→stale(1), iter4=1F→stale(1), iter5=1F
Never-fixed (1): test_update_stock_quantity
Fixed (2): test_delete_author_success, test_get_author_nonexistent
Status codes hallucinated: 404
```
</details>

### L1

<details>
<summary>L1 — Run 1 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.33
Response Validation: 33.33%
Stale: 1 (test_apply_discount_new_book_fails)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book [has stock, year=2020])
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Never-fixed (1): test_apply_discount_new_book_fails
```
</details>

<details>
<summary>L1 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.33
Response Validation: 30.0%
Stale: 0
Iterations: 1
Helpers: 1 (pouze unique!) — model generoval data inline, ale správně
Plan adherence: 100%
Compliance: 80 (missing timeout on all 98 calls!)
Failure taxonomy (iter 1): 0 failures

POZNÁMKA: Pouze 1 helper (unique), 98 HTTP volání — model generoval testy bez sdílených helperů.
Přesto 100% validity v 1. iteraci. avg_http_calls=3.27 (nejvyšší v experimentu).
```
</details>

<details>
<summary>L1 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.47
Response Validation: 36.67%
Stale: 1 (test_update_book_malformed_json — opraveno v iter 3)
Iterations: 3
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Fixed (1): test_update_book_malformed_json
```
</details>

<details>
<summary>L1 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.30
Response Validation: 30.0%
Stale: 1 (test_apply_discount_new_book_fails — opraveno v iter 3)
Iterations: 3
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Fixed (1): test_apply_discount_new_book_fails
```
</details>

<details>
<summary>L1 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.27
Response Validation: 23.33%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

### L2

<details>
<summary>L2 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.47
Response Validation: 40.0%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_author, create_category, create_book stock=10 year=2020, create_tag)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L2 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.40
Response Validation: 40.0%
Stale: 1 (test_malformed_json_payload)
Iterations: 5
Helpers: 4 (unique, create_author has_assertion, create_category has_assertion, create_book has_assertion)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Never-fixed (1): test_malformed_json_payload
```
</details>

<details>
<summary>L2 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 50.0% (17/34)
Assert Depth: 1.40
Response Validation: 40.0%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L2 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.43
Response Validation: 40.0%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L2 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.47
Response Validation: 46.67%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

### L3

<details>
<summary>L3 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 47.06% (16/34)
Assert Depth: 1.43
Response Validation: 40.0%
Stale: 1 (test_apply_discount_new_book_fails — opraveno v iter 3)
Iterations: 3
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Fixed (1): test_apply_discount_new_book_fails
```
</details>

<details>
<summary>L3 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.40
Response Validation: 36.67%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L3 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 50.0% (17/34)
Assert Depth: 1.40
Response Validation: 40.0%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L3 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 50.0% (17/34)
Assert Depth: 1.40
Response Validation: 43.33%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L3 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 47.06% (16/34)
Assert Depth: 1.43
Response Validation: 36.67%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

### L4

<details>
<summary>L4 — Run 1 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.47
Response Validation: 46.67%
Stale: 1 (test_list_orders_invalid_date_format)
Iterations: 5
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 41 calls)
Failure taxonomy (iter 1): wrong_status_code 1
Never-fixed (1): test_list_orders_invalid_date_format
```
</details>

<details>
<summary>L4 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.40
Response Validation: 46.67%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 80 (missing timeout on all 40 calls!)
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L4 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.47
Response Validation: 46.67%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 43 calls)
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L4 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.40
Response Validation: 43.33%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 42 calls)
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L4 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.47
Response Validation: 46.67%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 42 calls)
Failure taxonomy (iter 1): 0 failures
```
</details>