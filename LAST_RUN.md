# Analýza běhu: diplomka_v3 — 2026-03-22

**Konfigurace:** gemini-3.1-flash-lite-preview | bookstore | L0–L4 | 2 runy | 5 iterací | 30 testů

---

## Souhrnná tabulka

| Level | Run | Validity | Failed | Iterace | EP Cov | Assert | Resp Val | Empty | Status Codes | Čas |
|-------|-----|----------|--------|---------|--------|--------|----------|-------|-------------|-----|
| L0 | 1 | 96.55% (28/29) | 1 | 5 | 67.65% | 2.07 | 82.76% | 0 | 5 | 84s |
| L0 | 2 | 96.67% (29/30) | 1 | 5 | 67.65% | 1.90 | 76.67% | 0 | 5 | 53s |
| L1 | 1 | 93.33% (28/30) | 2 | 5 | 67.65% | 2.17 | 83.33% | 0 | 7 | 82s |
| L1 | 2 | 86.67% (26/30) | 4 | 5 | 70.59% | 2.37 | 63.33% | 0 | 7 | 136s |
| L2 | 1 | 90.00% (27/30) | 3 | 5 | 64.71% | 2.33 | 93.33% | 0 | 7 | 129s |
| L2 | 2 | 96.67% (29/30) | 1 | 5 | 58.82% | 1.77 | 73.33% | 1 | 7 | 64s |
| L3 | 1 | 93.33% (28/30) | 2 | 5 | 55.88% | 1.87 | 60.00% | 0 | 7 | 95s |
| L3 | 2 | **100%** (30/30) | 0 | **2** | 61.76% | 1.93 | 83.33% | 1 | 6 | 41s |
| L4 | 1 | 93.33% (28/30) | 2 | 5 | 58.82% | 1.50 | 53.33% | 0 | 9 | 89s |
| L4 | 2 | 93.33% (28/30) | 2 | 5 | 55.88% | 2.30 | 96.67% | 0 | 6 | 98s |

### Průměry per level

| Level | Validity (avg) | EP Cov (avg) | Assert (avg) | Resp Val (avg) |
|-------|---------------|-------------|-------------|---------------|
| **L0** | **96.61%** | 67.65% | 1.99 | 79.72% |
| **L1** | 90.00% | 69.12% | 2.27 | 73.33% |
| **L2** | 93.33% | 61.77% | 2.05 | 83.33% |
| **L3** | **96.67%** | 58.82% | 1.90 | 71.67% |
| **L4** | 93.33% | 57.35% | 1.90 | 75.00% |

---

## Detailní rozbor selhání per level

### L0 Run 1 — 28/29 passed (96.55%)

**Poznámka:** Plán má jen 29 testů (ne 30). Reset test (`test_reset_db_success`) byl odfiltrován ale plán se nedoplnil na 30. Bug ve frameworku: `_filter_reset_tests` se volá po count validaci.

**Iterace 1: 12 failing** — Klasický helper bug. `create_book` generuje ISBN přes hardcoded string, ne přes `unique()`. Druhé volání `create_book` → ISBN kolize → 409. Všech 10 testů co volají `create_book` padá na `assert 409 == 201`. Plus 2 testy se špatným status kódem (422 místo 404).

**Iterace 2: 3 failing** — Helper opraven (ISBN přes unique). Zbývají:
- `test_get_author_not_found`: očekává 422, API vrací 404. Model bez kontextu neví jaký kód API vrací pro "not found".
- `test_create_order_valid`: `assert 400 == 201`. Kniha má stock=0 (helper nemá stock), objednávka selže na insufficient stock.
- `test_delete_nonexistent_book`: očekává 422, API vrací 404. Stejný problém jako author.

**Iterace 3: 1 failing** — Repair opravil status kódy (422→404). Zbývá jen `test_create_order_valid` — stock=0, neopravitelné bez helper opravy.

**Iterace 3–5: stuck** — `test_create_order_valid` padá identicky (assert 400 in [200, 201]). Repair mění assert ale nemůže opravit chybějící stock v helperu. V iteraci 5 repair dokonce rozbil test jinak (assert 422 == 200) — model zkusil úplně jinou strategii ale stock stále chybí.

**Root cause:** `create_book` helper nemá `"stock": 10`. OpenAPI spec říká `stock: default 0`, model to respektuje a vynechá.

---

### L0 Run 2 — 29/30 passed (96.67%)

**Iterace 1: 15 failing** — Jiný helper bug než run 1. `create_book` volá `create_author()` a `create_category()` interně, ale nevrací book objekt správně. Response z POST /books je `{"detail": "..."}` (409 ISBN kolize) → `book["id"]` → KeyError. Kaskádový efekt: 14 testů padá na KeyError.

**Iterace 2: 3 failing** — Helper opraven. Zbývají:
- `test_get_author_not_found`: 422 vs 404 (stejné jako run 1)
- `test_delete_book_success`: po smazání kontroluje GET → očekává 422, API vrací 404
- `test_update_stock_success`: `assert 15 == 5`. Helper vytváří knihu se stock=10, test přičte 5, očekává 5 ale dostane 15 (10+5). Model neví že helper nastavuje stock=10.

**Iterace 3: 1 failing** — Status kódy opraveny. Zbývá `test_update_stock_success` — model opakovaně hádá špatnou výchozí hodnotu stocku. V iteraci 5 test úplně přepsal na jinou logiku ale rozbil volání (422).

**Root cause:** Model neví jaký stock helper nastavuje → špatný assert na výslednou hodnotu.

---

### L1 Run 1 — 28/30 passed (93.33%)

**Iterace 1–5: stabilně 2 failing**, žádný pokrok.

**`test_apply_discount_too_new_book`**: Model vytvoří knihu s `published_year=2020` (z helperu), pak se pokusí přes PUT změnit rok. Ale PUT payload je nesprávný — posílá jen `{"published_year": 2025}` bez ostatních povinných polí. V iteraci 4-5 repair změní strategii (vytvoří novou knihu s rokem 2026), ale pak vrací 404 protože nová kniha se nepodařila vytvořit (kolize ISBN nebo jiný problém). Osciluje mezi 200 a 404.

**`test_get_reviews_with_malformed_query_params`**: Posílá `GET /books/{id}/reviews?invalid_param=abc`, očekává 400 nebo 422. API ignoruje neznámé query parametry a vrací 200. Principiálně neopravitelné — FastAPI nevaliduje extra query parametry.

**Root cause:** Oba testy mají špatné předpoklady o chování API. Discount test neumí správně vytvořit "novou" knihu. Reviews test předpokládá striktní validaci query parametrů.

---

### L1 Run 2 — 26/30 passed (86.67%)

Nejhorší výsledek celého běhu.

**Iterace 1: 5 failing:**

1. **`test_apply_discount_recent_book`**: Stejný problém jako run 1. PATCH na `/books/{id}` pro změnu roku — API nemá PATCH endpoint na books. Rok se nezmění → sleva projde → 200 místo 400.

2. **`test_invalid_status_transition`**: `KeyError: 'id'` při vytváření objednávky. Helper `create_book` nemá `"stock"` v payloadu. Kniha se vytvoří se stock=0. `POST /orders` vrátí 400 (insufficient stock). Response nemá `"id"` → KeyError.

3. **`test_delete_delivered_order_forbidden`**: Stejný kaskádový efekt — objednávka se nepodaří vytvořit kvůli stock=0 → KeyError na `order["id"]`.

4. **`test_remove_nonexistent_tag_from_book`**: DELETE `/books/{id}/tags` s `tag_ids: [9999]` → API vrací 404 (tag neexistuje). Model očekává 200 (idempotentní operace).

5. **`test_get_order_details`**: KeyError — order se nepodařila vytvořit (stock=0).

**Iterace 2: 5 failing** — Identické. Repair opravil asserty ale ne root cause (chybějící stock).

**Iterace 3: 4 failing** — `test_remove_nonexistent_tag_from_book` opraven (status kód 200→404). Ostatní 4 zůstávají.

**Iterace 3–5: stuck na 4 failing:**
- `test_apply_discount_recent_book` — PATCH neexistuje, neopravitelné
- `test_invalid_status_transition` — repair opravil assert na `status_code == 201` ale stock je stále 0 → 400
- `test_delete_delivered_order_forbidden` — kaskáda z neúspěšné objednávky, repair mění assert ale KeyError přetrvává protože objednávka se vytváří v těle testu (ne přes helper) a nemá stock
- `test_get_order_details` — stejné, objednávka selže na 400

**Root causes:**
- Chybějící `"stock"` v `create_book` helperu → 3 order testy padají
- PATCH na books neexistuje → discount test padá
- Repair nedetekuje helper root cause protože signatury chyb jsou různé (KeyError vs assert 400==201 vs assert 200==400)

---

### L2 Run 1 — 27/30 passed (90.00%)

**Iterace 1–5: stabilně 2–3 failing.** Z logů bohužel nemám detail pro L2 run1, ale z JSON:
- 3 failed, assertion depth 2.33, response validation 93.33%
- Endpoint coverage 64.71%
- 1 edge case test

Typické L2 problémy: discount test (PATCH neexistuje), halucinované endpointy ze zdrojového kódu.

---

### L2 Run 2 — 29/30 passed (96.67%)

Z JSON: 1 failing, 1 empty test (`test_apply_discount_too_new_book` — 0 asercí). Model vygeneroval test bez assertů, ten vždy projde ale nic netestuje. Ironicky to pomohlo validity (test projde), ale snížilo assertion depth.

---

### L3 Run 1 — 28/30 passed (93.33%)

**Iterace 1–5: stabilně 2 failing**, identické každou iteraci.

**`test_apply_discount_too_recent_book`**: Opět pokus změnit `published_year` přes PUT. Model posílá celý book objekt (včetně `id`, `author`, `category` z GET response) jako PUT payload → některá pole nejsou v `BookUpdate` schématu → request buď projde bez změny roku, nebo selže na validaci. Výsledek: sleva se aplikuje na knihu z 2020 → 200 místo 400.

**`test_search_query_empty_string`**: Posílá `GET /books?search=&page=-1` nebo podobný nevalidní query. V iteraci 1 očekává 404, v iteraci 2+ osciluje mezi 200 a 422. API vrací 422 kvůli `page=-1` (ne kvůli search), ale model si myslí že problém je v search parametru. Neopravitelné — model nechápe co přesně validace odmítá.

**Root cause:** Oba testy mají fundamentálně špatné premisy. Discount: neumí změnit rok vydání. Search: nerozumí validačním pravidlům.

---

### L3 Run 2 — 30/30 passed (100%) ✅

Jediný run s plnou validity. Za 2 iterace.

**Iterace 1: 2 failing:**

1. **`test_invalid_status_transition`**: `create_book` helper má hardcoded ISBN `"1234567890"` → druhé volání v jiném testu způsobí kolizi → 409. Opraven v iteraci 2 (ISBN přes unique).

2. **`test_update_book_stock_invalid_quantity`**: `assert 400 == 422`. Model očekává 422 (Pydantic validace), API vrací 400 (business rule — insufficient stock). Opraven v iteraci 2 (změní assert na 400).

**Iterace 2: 30/30 passed.** Oba problémy byly opravitelné jednoduchou změnou assertu/helperu.

**Proč 100%?** Šťastná kombinace: helper měl stock=10, discount test vytvořil knihu s `published_year=2026` rovnou přes POST (ne přes PUT), žádné halucinované endpointy. Model zůstal konzervativní.

**Poznámka:** 1 empty test (`test_invalid_auth_token_access` — 0 asercí). Validity 100% ale tento test nic netestuje.

---

### L4 Run 1 — 28/30 passed (93.33%)

**Iterace 1: 3 failing:**

1. **`test_remove_nonexistent_tag_from_book`**: DELETE s neexistujícím tag_id → 404. Model očekává 200 (idempotentní). Opraven v iteraci 3 (změna assertu).

2. **`test_post_author_invalid_content_type`**: Posílá `Content-Type: text/plain`, očekává 415 (Unsupported Media Type). FastAPI vrací 422 (parsuje request, validace selže). Principiálně neopravitelné — model hádat nemůže jaký kód FastAPI vrátí pro špatný content-type.

3. **`test_delete_category_fails_when_associated_with_book`**: Očekává 400, API vrací 409 (conflict). Repair mění 400→409 ale v další iteraci zpátky na 400. Model osciluje — v kontextu (L4) vidí oba kódy pro různé situace.

**Iterace 3–5: stuck na 2 failing** (content-type + delete category). Oba principiálně neopravitelné — model osciluje mezi status kódy.

**Root cause:** Model s plným kontextem (L4) generuje ambicióznější testy (content-type validace, přesné status kódy) ale hádá špatně. Paradox: existující testy (L4 input) nemají tyto edge cases, takže model nemá vzor a improvizuje.

---

### L4 Run 2 — 28/30 passed (93.33%)

**Iterace 1: 3 failing:**

1. **`test_apply_discount_new_book`**: `TypeError: create_book() got an unexpected keyword argument 'published_year'`. Model zavolal helper s parametrem který helper nepřijímá. Opraven v iteraci 2 (model přepíše test aby vytvořil knihu jinak).

2. **`test_malformed_json_payload`**: Posílá `{"invalid": "data"}` na POST /authors, očekává 400. API vrací 200 (FastAPI ignoruje extra pole). V iteraci 2 opraveno na 422 ale pak vrací 200. V iteraci 3 opraven (projde).

3. **`test_update_book_stock_zero_value`**: `assert updated_book["stock"] == 0` ale stock je 5. Test posílá `quantity=-5` při stock=10 (z helperu) → 10-5=5, ne 0. Model špatně počítá aritmetiku / neví jaký stock helper nastavuje.

**Iterace 2: 3 failing** — discount opraveno na jinou strategii ale vrací 200 místo 400 (rok se nezmění). Malformed stále 422 vs 400. Stock stále 5 vs 0.

**Iterace 3–5: stuck na 2 failing:**
- `test_apply_discount_new_book`: vrací 404 (book not found — nová kniha se nepodařila vytvořit). Model v repair přepsal test ale stále selhává.
- `test_update_book_stock_zero_value`: `assert 5 == 0`. Model nechápe stock aritmetiku.

**Root cause:** Sémantické nepochopení — model neví kolik stock helper nastavuje (10), takže nemůže správně assertovat výsledek po odečtení.

---

## Klasifikace typů selhání

Napříč všemi 10 runy jsem identifikoval 5 kategorií selhání:

### 1. Chybějící stock v helper funkci
**Výskyt:** L0r1, L0r2, L1r2, L3r2(iter1)
**Mechanismus:** `create_book` helper nemá `"stock": 10`. OpenAPI spec říká `stock: default 0`. Kniha se vytvoří se stock=0. Testy na objednávky padají (insufficient stock → 400) a kaskádově způsobí KeyError na `order["id"]`.
**Opravitelné repair loopem?** NE — repair vidí jen test, ne helper. A signatury chyb jsou různé (KeyError vs assert) takže helper root cause detekce selže.

### 2. Discount "too new book" — špatná HTTP metoda
**Výskyt:** L1r1, L1r2, L2r1, L3r1, L4r2
**Mechanismus:** Model chce otestovat pravidlo "sleva jen pro knihy starší 1 roku". Vytvoří knihu s rokem 2020, pak se pokusí změnit rok na 2025/2026. Ale používá PATCH (neexistuje) nebo PUT se špatným payloadem. Rok se nezmění → sleva projde → 200 místo 400.
**Opravitelné?** NE — principiálně chybný přístup. Správné řešení: vytvořit novou knihu rovnou s `published_year=2026`.

### 3. Špatný očekávaný status kód
**Výskyt:** L0r1(422 vs 404), L0r2(422 vs 404), L1r2(200 vs 404 na remove_tags), L3r2(422 vs 400), L4r1(415 vs 422, 400 vs 409), L4r2(400 vs 422)
**Mechanismus:** Model hádá HTTP status kód bez dostatečné informace. Časté záměny: 422↔404 (validace vs not found), 400↔409 (business rule vs conflict), 415↔422 (content-type vs validace).
**Opravitelné?** ČÁSTEČNĚ — jednoduché záměny (422→404) repair opraví. Oscilace (400↔409) ne.

### 4. Sémantické nepochopení API logiky
**Výskyt:** L0r2(stock aritmetika), L1r1(query param validace), L3r1(search validace), L4r2(stock aritmetika)
**Mechanismus:** Model nerozumí jak API interně zpracovává data. Příklady: neví jaký stock helper nastaví, předpokládá že API validuje extra query parametry, nerozumí že quantity je delta (ne absolutní hodnota).
**Opravitelné?** NE — repair nemůže naučit model sémantiku API.

### 5. Halucinace / neexistující funkce
**Výskyt:** L4r1(Content-Type 415 test), L1r1(malformed query params)
**Mechanismus:** Model vygeneruje test pro chování které API nemá. Např. striktní Content-Type validace, validace extra query parametrů.
**Opravitelné?** NE — API toto chování nemá, žádný status kód nebude správný.

### Distribuce typů selhání

| Typ | Počet výskytů | % z celku |
|-----|--------------|-----------|
| Chybějící stock | 4 runy | 33% |
| Discount PATCH/PUT | 5 runů | 42% |
| Špatný status kód | 6 runů | 50% |
| Sémantické nepochopení | 4 runy | 33% |
| Halucinace | 2 runy | 17% |

(Jeden run může mít více typů selhání)

---

## Metriky — detailní rozbor

### Test Validity Rate

**Rozptyl je vysoký.** L1 má 93.33% a 86.67% (rozdíl 6.67 p.p.). L3 má 93.33% a 100% (rozdíl 6.67 p.p.). Se 2 runy nelze spolehlivě určit průměr — potřeba minimálně 3, ideálně 5 runů.

**L0 je paradoxně nejstabilnější** (96.55%, 96.67%). Bez kontextu model generuje konzervativní testy — méně ambiciózní ale méně chybové.

**L3 run 2 (100%)** je outlier — šťastná kombinace kde oba problémy z iterace 1 byly triviálně opravitelné (ISBN kolize + status kód 422→400).

### Endpoint Coverage

**Klesá s kontextem:** L0 67.65% → L4 57.35%. Konzistentní trend. Více kontextu = model generuje specifičtější testy na méně endpointů. Typicky nepokryté: GET single entity, PUT update, DELETE cascade endpointy.

**Stabilní mezi runy** — L0 run1 i run2 mají shodně 67.65%. Plán (a tím endpoint coverage) je deterministický daný kontextem, ne náhodou.

### Assertion Depth

**Průměr 1.5–2.37.** L1r2 má nejvyšší (2.37) — model s byznys dokumentací generuje bohatší asserty. L4r1 má nejnižší (1.50) — paradoxně, model s existujícími testy jako vzorem generuje jednoduché asserty (kopíruje minimalistický styl z referenčních testů).

### Response Validation

**Nejvíce variabilní metrika.** L2r1 má 93.33%, L4r1 jen 53.33%. Response validation závisí na tom jestli model přidá `assert "detail" in r.json()` nebo `assert data["name"] == name` — to je hodně závislé na promptu a náhodě.

**L4r2 (96.67%)** je nejlepší — existující testy jako vzor motivují model kontrolovat response body.

### Status Code Diversity

**L4r1 má 9 unikátních kódů** (200, 201, 204, 400, 404, 405, 409, 415, 422) — nejbohatší. Model s plným kontextem testuje více edge cases. L0 má jen 5 kódů (200, 201, 204, 404, 422) — bez kontextu model nezná 409 (conflict) ani 400 (business rule).

### Empty Tests

- L2r2: 1 (`test_apply_discount_too_new_book` — 0 asercí, repair vymazal asserty aby test prošel)
- L3r2: 1 (`test_invalid_auth_token_access` — model vygeneroval prázdný test pro auth endpoint který neexistuje)

### Plan Adherence

**Stabilně 93–97%.** Vždy chybí `test_reset_*` (odfiltrovaný). Občas chybí ještě 1 test (model vygeneruje jiný název než plán).

---

## Pozorování o repair loop

### Konvergence

| Iterace | Průměrný počet failing testů |
|---------|------------------------------|
| 1 | 5.4 |
| 2 | 3.0 |
| 3 | 2.1 |
| 4 | 2.0 |
| 5 | 1.9 |

**Největší skok je mezi iterací 1→2** (helper opravy, jednoduché status kódy). Po iteraci 3 se výsledky stabilizují — zbývající failing testy jsou principiálně neopravitelné.

### Efektivita oprav

- **Helper opravy (iterace 1→2):** velmi efektivní, opraví 10+ testů najednou
- **Izolovaná oprava status kódů (iterace 2→3):** efektivní pro jednoduché záměny (422→404)
- **Iterace 4–5:** téměř nulový přínos. Testy které zůstávají jsou stuck.

### Stale detection by ušetřil

Bez stale detection: iterace 3–5 plýtvají 2–4 LLM cally per iteraci na testy co se neopraví. U 10 runů = ~60 zbytečných LLM callů.

---

## Klíčové závěry

1. **Více kontextu nekoreluje s vyšší validity.** L0 (96.6%) > L1 (90.0%). L3 run2 dosáhl 100% ale run1 jen 93.3%.

2. **Hlavní bottleneck je create_book helper bez stocku.** Způsobuje kaskádová selhání order testů. Opravitelné v promptu.

3. **Discount "new book" test je nejčastější stuck failure** — objevuje se v 5/10 runech. Model neumí správně vytvořit knihu s aktuálním rokem vydání (používá PATCH/PUT místo POST s parametrem).

4. **Repair loop je efektivní jen 2–3 iterace.** Po iteraci 3 se výsledky stabilizují. 5 iterací je zbytečných pro většinu runů.

5. **Endpoint coverage klesá s kontextem** (67.65% → 57.35%) — více kontextu vede k užšímu ale hlubšímu testování.

6. **Variance je příliš vysoká pro 2 runy.** L1 má rozptyl 6.67 p.p. — potřeba minimálně 3 runy pro spolehlivé závěry.