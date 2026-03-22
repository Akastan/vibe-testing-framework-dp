# Analýza běhu: diplomka_v4 — 2026-03-22

**Konfigurace:** gemini-3.1-flash-lite-preview | bookstore | L0–L4 | 1 run | 3 iterace | 30 testů

**Nové oproti v3:** unified prompt framework (PromptBuilder), `api_rules` + `helper_hints` v YAML, stale detection (threshold=2)

---

## Souhrnná tabulka

| Level | Validity | Failed | Stale | Iterace | EP Cov | Assert | Resp Val | Status Codes | Čas |
|-------|----------|--------|-------|---------|--------|--------|----------|-------------|-----|
| **L0** | 80.0% (24/30) | 6 | 6 | 3 | 58.82% | 1.87 | 73.33% | 4 | 44s |
| **L1** | **100%** (30/30) | 0 | 0 | **1** | 55.88% | 1.43 | 40.0% | 7 | 27s |
| **L2** | 96.67% (29/30) | 1 | 1 | 3 | 61.76% | 2.03 | 100.0% | 6 | 61s |
| **L3** | **100%** (30/30) | 0 | 0 | **1** | 61.76% | 2.03 | 93.33% | 7 | 54s |
| **L4** | **100%** (30/30) | 0 | 0 | **1** | 50.0% | 1.67 | 60.0% | 7 | 55s |

### Srovnání s v3 (průměr per level, v3 = 2 runy × 5 iterací)

| Level | v3 Validity | v4 Validity | v3 EP Cov | v4 EP Cov | v3 Assert | v4 Assert |
|-------|-------------|-------------|-----------|-----------|-----------|-----------|
| L0 | 96.61% | 80.0% | 67.65% | 58.82% | 1.99 | 1.87 |
| L1 | 90.00% | **100%** | 69.12% | 55.88% | 2.27 | 1.43 |
| L2 | 93.33% | 96.67% | 61.77% | 61.76% | 2.05 | 2.03 |
| L3 | 96.67% | **100%** | 58.82% | 61.76% | 1.90 | 2.03 |
| L4 | 93.33% | **100%** | 57.35% | 50.0% | 1.90 | 1.67 |

---

## Vliv helper_hints — klíčová změna

### Co se změnilo

V `experiment.yaml` je nový blok `helper_hints`, injektovaný do generačního promptu přes `PromptBuilder`:

```yaml
helper_hints:
  - 'create_book helper MUSÍ nastavit "stock": 10'
  - 'Pro test discountu na novou knihu vytvoř knihu ROVNOU přes POST s published_year=2026'
```

### Výsledek: stock hint funguje perfektně

Ve v3 byl **chybějící stock hlavní příčinou selhání** (33% runů). Ve v4 **všech 5 levelů** má `"stock": 10` v helperu. Žádný order test nepadá na insufficient stock. Zero kaskádových KeyError selhání.

Důkaz z vygenerovaného kódu — L0 helper:
```python
def create_book(author_id=None, category_id=None, published_year=2026):
    payload = {
        ...
        "stock": 10,  # ← helper_hint funguje
    }
```

### Výsledek: discount hint má vedlejší efekt na L0

Hint "vytvoř knihu ROVNOU přes POST s published_year=2026" měl být pokyn pro specifický discount test. Ale L0 model ho interpretoval jako **default hodnotu** v `create_book` helperu — `published_year=2026`. To znamená:

- Všechny knihy vytvořené přes helper mají rok 2026 (aktuální rok)
- `test_apply_discount_success` vytvoří knihu → rok 2026 → sleva selže (400, kniha příliš nová)
- Test očekává 200, dostane 400 → FAILED

L1–L4 modely tento hint pochopily správně: default rok je 2020, a jen konkrétní discount testy používají 2026. L0 bez kontextu API pravidel nemá jak vědět, že rok 2026 znamená "příliš nová kniha".

---

## Detailní rozbor selhání per level

### L0 — 24/30 passed (80.0%)

Nejhorší výsledek běhu. Ale mechanismus selhání je úplně jiný než ve v3.

**Iterace 1: 21 failing**

Root cause: `create_book` helper vrací 422. Proč? Generovaný ISBN je `unique("ISBN")` → produkuje `ISBN_a3f2b1c8` (14 znaků). API validuje formát ISBN a odmítá. Kaskádový efekt: 18 testů volá `create_book()` → všechny padají na `assert r.status_code == 201` v helperu.

Zbylé 3 failing testy:
- `test_get_author_not_found`: očekává 422, API vrací 404
- `test_create_order_invalid_item`: očekává 422, API vrací 404
- `test_delete_invalid_order`: očekává 422, API vrací 404

**Iterace 1 → 2: helper repair (21 → 6 failing)**

Framework detekuje 21 failing > 10 (MAX_INDIVIDUAL_REPAIRS) → oprava helperů. LLM opraví `create_book`:
- ISBN formát opraven (pravděpodobně truncation nebo jiný formát)
- 15 testů ihned projde

Zbývá 6 failing:

| Test | Chyba | Typ | Root cause |
|------|-------|-----|------------|
| `test_get_author_not_found` | 404 ≠ 422 | Špatný status kód | Model hádá 422 pro "not found" |
| `test_delete_book_success` | 404 ≠ 422 | Špatný status kód | Po DELETE kontroluje GET, očekává 422 místo 404 |
| `test_apply_discount_success` | 400 ≠ 200 | Helper side effect | Kniha má rok 2026 → sleva odmítnuta |
| `test_update_stock_success` | 15 ≠ 5 | Sémantické nepochopení | Helper: stock=10, test: +5, expects 5 but gets 15 |
| `test_create_order_invalid_item` | 404 ≠ 422 | Špatný status kód | Neexistující book → 404, ne 422 |
| `test_delete_invalid_order` | 404 ≠ 422 | Špatný status kód | Neexistující order → 404, ne 422 |

**Iterace 2 → 3: stale detection aktivní**

Všech 6 testů má stejnou chybu jako v iteraci 1 → StaleTracker je označí jako stale. Framework přeskočí opravu. Ušetřeno 6 LLM callů (nebo 1 helper repair call).

Log: `[Repair] Všechny failing testy jsou stale, přeskakuji opravu.`

Iterace 3 produkuje identický výstup jako iterace 2.

**Klasifikace L0 selhání:**
- 4× špatný status kód (422 vs 404) — L0 model bez kontextu neví že API vrací 404 pro not found
- 1× discount helper side effect — published_year=2026 jako default
- 1× stock aritmetika — model neví že quantity je delta, ne absolutní hodnota

**Srovnání s v3 L0:** Ve v3 L0 mělo ~96.6% validity. Ve v4 jen 80%. Proč regrese? Ve v3 model nastavil `published_year=2020` (neutrální default), ve v4 nastavil 2026 (z helper_hints). Navíc ve v3 stock=0 způsobil jiný typ selhání (order testy), ale ty testy co nespoléhaly na stock prošly. Ve v4 stock je OK ale published_year je špatný → discount test padá. Je to trade-off: stock hint opravil 33% selhání z v3, ale discount hint přidal nové selhání na L0.

---

### L1 — 30/30 passed (100%) ✅

**Iterace 1: 30/30 passed.** Žádná oprava potřeba.

Toto je dramatické zlepšení oproti v3 L1 (90.0% průměr, 86.67% worst case). Ve v3 L1 selhávala hlavně na:
1. Chybějící stock → vyřešeno `helper_hints`
2. Discount PATCH/PUT → vyřešeno `helper_hints` (model s byznys docs chápe hint správně)

L1 helper:
```python
def create_book(author_id=None, category_id=None, published_year=2020):
    payload = {
        ...
        "stock": 10,      # ← hint funguje
        "published_year": published_year,  # ← default 2020, ne 2026
    }
```

Discount test:
```python
def test_apply_discount_new_book_fails():
    book = create_book(published_year=2026)  # ← explicitně 2026 jen pro tento test
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", ...)
    assert r.status_code == 400
```

Model s byznys dokumentací pochopil:
- Default rok = 2020 (starší kniha, discounty fungují)
- Rok 2026 = nová kniha (discount selže) — jen pro specifický test
- Stock = 10 (objednávky fungují)
- Status kódy: 400 pro business rules, 404 pro not found, 409 pro conflicts, 422 pro validace

**Test type distribution:** 9 happy_path (30%), 19 error (63.3%), 2 edge_case (6.7%). L1 s byznys docs generuje výrazně více error testů — model chápe byznys pravidla a testuje je.

**Response validation: 40%** — nejnižší ze všech levelů. L1 model se zaměřuje na status kódy a error handling, méně na response body. Paradox: 100% validity ale jen 40% testů kontroluje response body.

---

### L2 — 29/30 passed (96.67%)

**Iterace 1: 1 failing**

Jediný failing test: `test_get_author_edge_case_negative_id`
- Posílá `GET /authors/-1`
- Očekává 422 (Pydantic validace záporného ID)
- API vrací 404 (SQLAlchemy nenajde autora s ID=-1, vrátí 404)

**Iterace 2: repair attempt**

LLM opraví test (pravděpodobně změní assert na 404), ale nový kód stále selhává — model osciluje nebo oprava nefunguje.

**Iterace 2 → 3: stale**

StaleTracker detekuje stejnou chybu 2× → stale. Přeskočeno.

**Root cause:** Model se zdrojovým kódem vidí Pydantic schema s `author_id: int` a předpokládá, že záporné ID selže na validaci (422). Ale FastAPI přijme jakýkoli int, předá ho do DB, a CRUD vrátí 404. Toto je typický L2 problém: model halucinuje validační chování ze zdrojového kódu.

**Response validation: 100%** — nejlepší ze všech levelů. L2 se zdrojovým kódem generuje testy co kontrolují response body na každém testu. Model vidí strukturu response objektů v kódu.

**Assertion depth: 2.03** — konzistentně lepší než L0/L1. Zdrojový kód motivuje bohatší aserce.

---

### L3 — 30/30 passed (100%) ✅

**Iterace 1: 30/30 passed.** Žádná oprava potřeba.

L3 helper:
```python
def create_book(author_id=None, category_id=None, published_year=2020):
    data = {
        ...
        "isbn": unique("ISBN")[-13:],  # ← správný formát
        "stock": 10,
        "published_year": published_year,  # ← default 2020
    }
```

Zajímavé testy které L3 vygeneroval a které prošly na první pokus:
- `test_update_stock_success`: assertuje `stock == 15` (10 + 5) — model s DB schématem chápe stock aritmetiku
- `test_apply_discount_too_recent_book`: vytvoří knihu s `published_year=2026` — chápe constraint
- `test_update_status_shipped_to_delivered`: full order lifecycle (pending → confirmed → shipped → delivered)
- `test_remove_tags_success`: assertuje `len(r.json()["tags"]) == 0` po odebrání

**Srovnání s v3 L3:** Ve v3 L3 mělo 96.67% průměr (93.33% a 100%). Ve v4 100% na první iteraci. Klíčový rozdíl: `helper_hints` eliminovaly stock problém a discount PATCH/PUT problém.

---

### L4 — 30/30 passed (100%) ✅

**Iterace 1: 30/30 passed.** Žádná oprava potřeba.

L4 s existujícími testy jako vzorem generuje nejkomplexnější testy:
- `test_update_status_cancel_restores_stock`: vytvoří objednávku (5 ks), zruší ji, ověří že stock se vrátil na 10. Side-effect test.
- `test_delete_shipped_order_error`: full lifecycle (pending → confirmed → shipped), pak DELETE → 400. Multi-step test.
- `test_get_book_details`: assertuje `"tags" in r.json()` — ověřuje strukturu response

**Endpoint coverage: 50%** — nejnižší ze všech levelů. L4 model generuje méně endpointů ale hlubší testy. Nepokryté: GET /authors, GET /categories, PUT endpointy, DELETE /categories, DELETE /tags, GET /health.

**Response validation: 60%** — nižší než L2/L3. Model kopíruje minimalistický styl z referenčních testů (ty mají často jen status code check).

---

## Analýza stale detection

### Efektivita

| Level | Stale testů | Iterace ušetřeny | LLM cally ušetřeny |
|-------|-------------|------------------|---------------------|
| L0 | 6 | 1 (iterace 3) | 6 (nebo 1 helper) |
| L1 | 0 | 0 | 0 |
| L2 | 1 | 1 (iterace 3) | 1 |
| L3 | 0 | 0 | 0 |
| L4 | 0 | 0 | 0 |
| **Celkem** | **7** | **2** | **~7** |

S max_iterations=3 (místo 5 ve v3) je úspora menší. Ale stale detection správně identifikoval všech 7 neopravitelných testů a zabránil zbytečným opravám.

### Threshold=2 je správný

L0 iterace 1→2: helper repair opraví 15 testů. Zbylých 6 má identickou chybu v iteraci 1 i 2. Threshold=2 je správně aktivuje jako stale v iteraci 2, takže iterace 3 nepřichází s dalším zbytečným repairem.

L2 iterace 1→2: repair pokus neuspěje (model osciluje). Threshold=2 správně detekuje stale v iteraci 2.

---

## Klasifikace typů selhání (v4)

Celkem 7 failing testů (6 L0 + 1 L2):

| Typ selhání | Počet | Testy |
|-------------|-------|-------|
| Špatný status kód (422 vs 404) | 5 | L0: author_not_found, delete_book, order_invalid, delete_order; L2: negative_id |
| Discount helper side effect | 1 | L0: apply_discount_success |
| Stock aritmetika | 1 | L0: update_stock_success |

### Srovnání s v3 klasifikací

| Typ selhání | v3 (10 runů) | v4 (5 runů) | Změna |
|-------------|-------------|-------------|-------|
| Chybějící stock | 33% runů | **0%** | ✅ Eliminováno helper_hints |
| Discount PATCH/PUT | 42% runů | **0%** | ✅ Eliminováno helper_hints |
| Špatný status kód | 50% runů | 40% (2/5) | ~ Bez změny |
| Sémantické nepochopení | 33% runů | 20% (1/5) | ↓ Zlepšení |
| Halucinace | 17% runů | 20% (1/5) | ~ Bez změny |
| **Nový: Helper hint side effect** | 0% | 20% (1/5) | ⚠️ Nový typ |

**Hlavní zjištění:** `helper_hints` eliminovaly 2 největší kategorie selhání z v3 (stock + discount), ale zavedly nový typ (hint side effect na L0). Čistý efekt je pozitivní: 3 levely dosáhly 100% na první iteraci (vs 1 level ve v3).

---

## Metriky — detailní rozbor

### Test Validity Rate

| Level | v4 | Komentář |
|-------|----|----------|
| L0 | 80.0% | Regrese kvůli discount hint side effect |
| L1 | **100%** | Dramatické zlepšení (v3: 90%) |
| L2 | 96.67% | Stabilní (v3: 93.33%) |
| L3 | **100%** | Zlepšení (v3: 96.67%) |
| L4 | **100%** | Zlepšení (v3: 93.33%) |

### Endpoint Coverage

Trend z v3 se potvrzuje: **klesá s kontextem**.

| Level | EP Cov | Nepokryté endpointy (výběr) |
|-------|--------|-----------------------------|
| L0 | 58.82% | GET /books/{id}, GET /categories, GET /tags, PUT endpointy |
| L1 | 55.88% | GET /authors/{id}, GET /books/{id}, PUT endpointy, GET /orders/{id} |
| L2 | 61.76% | DELETE /books, GET /reviews, PUT endpointy |
| L3 | 61.76% | DELETE /books, GET /authors, GET /books/{id}, PUT authors/categories |
| L4 | 50.0% | GET /health (!), GET /authors, GET /categories, všechny PUT, DELETE /categories, DELETE /tags |

L4 nepokrývá ani `/health` endpoint — model s existujícími testy se soustředí na složitější scénáře a "nudné" endpointy vynechává.

### Assertion Depth

| Level | Depth | Komentář |
|-------|-------|----------|
| L0 | 1.87 | Slušné, ale mnoho testů má jen 1-2 asserty |
| L1 | 1.43 | Nejnižší — model s docs se zaměřuje na status kódy |
| L2 | **2.03** | Nejlepší — zdrojový kód motivuje bohatší asserce |
| L3 | **2.03** | Shodné s L2 |
| L4 | 1.67 | Kopíruje minimalistický styl referenčních testů |

### Response Validation

| Level | Resp Val | Komentář |
|-------|----------|----------|
| L0 | 73.33% | Solidní |
| L1 | **40.0%** | Nejhorší — model kontroluje jen status kódy |
| L2 | **100%** | Perfektní — zdrojový kód ukazuje response struktury |
| L3 | 93.33% | Téměř perfektní |
| L4 | 60.0% | Kopíruje styl referenčních testů (ne všechny kontrolují body) |

Paradox: L1 má 100% validity ale jen 40% response validation. L2 má 96.67% validity ale 100% response validation. **Vyšší response validation nekoreluje s vyšší validity** — ale koreluje s lepším code coverage (ověření v manuálním měření).

### Status Code Diversity

| Level | Unique kódy | Kódy |
|-------|-------------|------|
| L0 | 4 | 200, 201, 204, 422 |
| L1 | 7 | 200, 201, 204, 400, 404, 409, 422 |
| L2 | 6 | 200, 201, 400, 404, 409, 422 |
| L3 | 7 | 200, 201, 204, 400, 404, 409, 422 |
| L4 | 7 | 200, 201, 204, 400, 404, 409, 422 |

L0 nezná 400 (business rule), 404 (not found specificky), 409 (conflict). Od L1+ model chápe všechny status kódy API.

### Test Type Distribution

| Level | Happy | Error | Edge |
|-------|-------|-------|------|
| L0 | 70.0% | 26.7% | 3.3% |
| L1 | 30.0% | **63.3%** | 6.7% |
| L2 | 16.7% | **76.7%** | 6.7% |
| L3 | 43.3% | 56.7% | 0% |
| L4 | 53.3% | 46.7% | 0% |

L2 generuje nejvíce error testů (76.7%) — zdrojový kód odhaluje error handling cesty. L0 generuje převážně happy path (70%) — bez kontextu model testuje hlavně "jde to zavolat?".

---

## Pozorování o repair loop

### Konvergence (v4, max 3 iterace)

| Level | Iter 1 failing | Iter 2 failing | Iter 3 failing |
|-------|----------------|----------------|----------------|
| L0 | 21 | 6 | 6 (stale) |
| L1 | 0 | — | — |
| L2 | 1 | 1 | 1 (stale) |
| L3 | 0 | — | — |
| L4 | 0 | — | — |

**Max 3 iterace je dostatečných.** Ve v3 s 5 iteracemi se po iteraci 3 nic nezlepšilo. Ve v4 stale detection v iteraci 2 zabrání zbytečné iteraci 3 (ale ta proběhne kvůli logice — stale se přeskočí ale testy se stejně spustí).

**Potenciální optimalizace:** pokud jsou VŠECHNY failing testy stale, přeskočit i spuštění testů v další iteraci (early exit). Ušetří ~2s per iteraci.

---

## Klíčové závěry

1. **helper_hints eliminovaly 2 hlavní kategorie selhání z v3.** Stock (33% → 0%) a discount PATCH/PUT (42% → 0%). Tři levely (L1, L3, L4) dosáhly 100% na první iteraci.

2. **helper_hints mají vedlejší efekt na L0.** Model bez kontextu interpretuje hint "published_year=2026" jako default hodnotu v helperu. Řešení: buď hint upřesnit ("default published_year=2020, pro discount test použij 2026"), nebo hint dát jen do generačního promptu pro L1+.

3. **L1 je nejefektivnější kontext pro validity.** 100% na první iteraci, 27s. V3: 90% průměr. Byznys dokumentace + helper_hints = optimální kombinace.

4. **L2 generuje nejkvalitnější testy** (100% response validation, 2.03 assertion depth), ale 1 stale test snižuje validity na 96.67%.

5. **L4 endpoint coverage klesá na 50%.** Model s referenčními testy testuje hlouběji ale užší spektrum endpointů.

6. **Stale detection funguje správně** — identifikuje principiálně neopravitelné testy a šetří LLM cally. Threshold=2 je vhodný.

7. **Špatný status kód (422 vs 404) zůstává hlavní příčinou selhání** — 5 ze 7 failing testů. Toto je inherentní problém L0 (model bez kontextu hádá) a částečně L2 (model halucinuje validaci).

---

## Doporučení pro další běh

1. **Upřesnit discount hint:** "Helper create_book má mít default published_year=2020. Pro test discountu na NOVOU knihu vytvoř knihu s published_year aktuálního roku (2026) PŘÍMO V TESTU, ne v helperu."

2. **Spustit 3 runy** pro statistickou validitu — tento běh je jen 1 run, variance může být vysoká (viz v3 kde L1 mělo 93.33% a 86.67%).

3. **Snížit max_iterations na 3** — potvrzeno že iterace 4-5 nepřináší zlepšení.

4. **Přidat early exit** — pokud všechny failing testy jsou stale, přeskočit zbývající iterace.