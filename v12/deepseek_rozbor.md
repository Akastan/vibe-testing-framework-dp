# DeepSeek-V4-Flash — Rozbor 25 testovacích sad

**Subjekt analýzy:** `deepseek-v4-flash`, API `bookstore`, 5 úrovní kontextu × 5 běhů = 25 sad
**Konfigurace:** `temperature=0.4`, `test_count=30`, `max_iterations=7`
**Zdroj:** `merged_test_suites_deepseek.py` (8 957 řádků), `merged_test_suites_log_deepseek.txt` (2 601 řádků), `experiment_diplomka_v12_20260426_220445.json`, `coverage_deepseek-v4.md`

> Analýza zkoumá strukturní, sémantické a behaviorální charakteristiky vygenerovaných testovacích sad nezávisle na obsahu `ABOUT.md`. Cílem je popsat **co** DeepSeek testuje, **jak** to testuje a **jak** se jeho strategie mění s úrovní kontextu — připravit srovnávací podklad pro ostatní modely.

---

## 1. Souhrnná tabulka všech 25 sad

| Sada | Řádky | Tříd | Testů | Helpers | Asercí | AsrD | StCodes | Validity | EpCov | CodeCov | Iter | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0_run1 | 374 | **0** | 30 | 6 | 61 | 1.87 | 12 | 100.00% | 52% | 71.46% | 2 | $0.0039 |
| L0_run2 | 297 | 0 | 30 | 6 | 65 | 2.00 | 7 | 93.33% | 42% | 70.47% | 3 | $0.0027 |
| L0_run3 | 278 | 0 | 30 | 4 | 60 | 1.90 | 8 | 96.67% | 48% | 71.46% | 3 | $0.0025 |
| L0_run4 | 330 | 0 | 30 | 5 | 67 | 2.10 | 6 | 96.67% | 46% | 72.35% | 3 | $0.0026 |
| L0_run5 | 389 | 0 | 30 | 5 | 69 | 2.17 | 12 | 90.00% | 50% | 70.37% | 3 | $0.0028 |
| L1_run1 | 372 | 0 | 30 | 5 | 71 | 2.23 | 10 | 96.67% | 34% | 71.75% | 3 | $0.0027 |
| L1_run2 | 299 | 0 | 30 | 5 | 64 | 2.00 | 10 | 93.33% | 42% | 69.47% | 3 | $0.0045 |
| L1_run3 | 304 | 0 | 30 | 5 | 62 | 1.93 | 10 | 100.00% | 40% | 71.46% | 1 | $0.0021 |
| L1_run4 | 318 | 0 | 30 | 4 | 70 | 2.23 | 10 | 100.00% | 34% | 69.18% | 1 | $0.0021 |
| L1_run5 | 343 | 0 | 30 | 6 | 75 | 2.33 | 10 | 100.00% | 40% | 71.75% | 1 | $0.0022 |
| L2_run1 | 377 | 0 | 30 | 5 | 72 | 2.27 | 10 | 100.00% | 40% | 69.97% | 1 | $0.0047 |
| L2_run2 | 360 | 0 | 30 | 4 | 69 | 2.20 | 10 | 96.67% | 34% | 68.78% | 3 | $0.0026 |
| L2_run3 | 450 | 0 | 30 | 6 | 87 | 2.73 | 8 | 100.00% | 44% | 72.84% | 1 | $0.0025 |
| L2_run4 | 352 | 0 | 30 | 5 | 80 | 2.53 | 9 | 100.00% | 42% | 72.15% | 1 | $0.0024 |
| L2_run5 | 423 | 0 | 30 | 5 | 84 | 2.67 | 11 | 100.00% | 44% | 70.27% | 1 | $0.0024 |
| L3_run1 | 310 | 0 | 30 | 5 | 68 | 2.13 | 10 | 100.00% | 34% | 67.10% | 1 | $0.0024 |
| L3_run2 | 388 | 0 | 30 | 6 | 67 | 2.07 | 12 | 100.00% | 48% | 72.05% | 1 | $0.0024 |
| L3_run3 | 414 | 0 | 30 | 6 | 75 | 2.33 | 10 | 100.00% | 36% | 70.66% | 1 | $0.0024 |
| L3_run4 | 381 | 0 | 30 | 5 | 71 | 2.23 | 9 | 100.00% | 38% | 70.86% | 1 | $0.0023 |
| L3_run5 | 412 | 0 | 30 | 6 | 71 | 2.20 | 8 | 100.00% | 36% | 70.96% | 1 | $0.0023 |
| L4_run1 | 306 | 0 | 30 | 7 | 77 | 2.40 | 10 | 100.00% | 32% | 66.80% | 1 | $0.0037 |
| L4_run2 | 305 | 0 | 30 | 7 | 72 | 2.23 | 9 | 100.00% | 40% | 71.46% | 1 | $0.0023 |
| L4_run3 | 314 | 0 | 30 | 7 | 74 | 2.30 | 8 | 100.00% | 36% | 67.99% | 1 | $0.0025 |
| L4_run4 | 303 | 0 | 30 | 7 | 81 | 2.53 | 9 | 100.00% | 36% | 70.47% | 1 | $0.0023 |
| L4_run5 | 333 | 0 | 30 | 6 | 69 | 2.13 | 11 | 100.00% | 40% | 70.76% | 1 | $0.0023 |

**Legenda:** `Tříd` = počet top-level Python tříd, `AsrD` = průměrná hloubka asercí na test (`assertion_depth`), `StCodes` = počet různých HTTP status kódů ověřovaných, `EpCov` = endpoint coverage v %, `CodeCov` = code coverage v % (ze coverage runs), `Iter` = počet iterací repair loopu, `Cost` = USD náklady na běh.

**Klíčové průměry:**

| Úroveň | Validity | EpCov | CodeCov | AsrD | StDiv | Cost (avg) | Iter (avg) | Time (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L0 | 95.33% | 47.6% | 71.22% | 2.01 | 9.0 | $0.0029 | 2.8 | 105.9s |
| L1 | 98.00% | 38.0% | 70.72% | 2.14 | 10.0 | $0.0027 | 1.8 | 105.1s |
| L2 | 99.33% | 40.8% | 70.80% | 2.48 | 9.6 | $0.0029 | 1.4 | 92.2s |
| L3 | 100.00% | 38.4% | 70.33% | 2.19 | 9.8 | $0.0024 | 1.0 | 86.8s |
| L4 | 100.00% | 36.8% | 69.49% | 2.32 | 9.4 | $0.0026 | 1.0 | 87.0s |

---

## 2. Strukturní analýza — proč DeepSeek nikdy nepoužívá třídy?

### 2.1 Pozorování (zcela odlišné od jiných modelů)

**0 z 25 sad používá top-level Python třídy.** Žádná výjimka — všech 25 sad je strukturováno jako **plochá kolekce funkcí** (helpery + 30 testovacích funkcí). Každý test je samostatná modulová funkce: `def test_xyz(): ...`.

To je **diametrálně opačná strategie** vůči modelům, které preferují třídní organizaci. Kde Claude vytváří `class TestAuthorsPost: def test_create_author_success(self): ...`, DeepSeek napíše prostě `def test_create_author_success(): ...`.

| Úroveň | Sady s třídami | Průměr funkcí/test | Test/funkce |
|---|---:|---:|---:|
| L0 | 0 / 5 | 35.2 (5 helperů + 30 testů) | n/a |
| L1 | 0 / 5 | 35.0 | n/a |
| L2 | 0 / 5 | 35.0 | n/a |
| L3 | 0 / 5 | 35.6 | n/a |
| L4 | 0 / 5 | 36.8 | n/a |

### 2.2 Důsledky ploché struktury

1. **Jednodušší pytest discovery** — test runner najde 30 testů v jednom modulu bez introspekce tříd.
2. **Žádné `self`** — eliminuje boilerplate při každé deklaraci.
3. **Nemožnost přirozeného sdílení stavu** — DeepSeek se musí spoléhat výhradně na **explicitní helper volání** a **modulové konstanty** (BASE_URL, TIMEOUT, API_KEY).
4. **Chybí logické seskupení** — pytest `--verbose` výstup je plochý seznam 30 testů. Žádná hierarchie `TestX::test_y`.
5. **Snadnější repair-loop targeting** — opravu konkrétního testu lze provést jako lokální AST-edit funkce, bez nutnosti zachovat třídní kontext.

### 2.3 Konvence pojmenování testů

Bez tříd se DeepSeek spoléhá na **dlouhé, popisné názvy testů**. Úroveň přesnosti se ale liší podle kontextu — viz sekce 5.4 níže.

Žádné prázdné kostry tříd (přirozeně — žádné třídy neexistují). To znamená **0 % over-planning** strukturálního typu, který se může objevit u jiných modelů.

---

## 3. Helper funkce — konzistence a evoluce signatury

### 3.1 Standardizovaná knihovna helperů

| Frekvence | Helper | Účel |
|---:|---|---|
| 25 / 25 | `unique(prefix)` | Generování unikátního stringu (`uuid.uuid4().hex[:8]`) |
| 23 / 25 | `create_author()` | POST /authors |
| 23 / 25 | `create_category()` | POST /categories |
| 23 / 25 | `create_book()` | POST /books |
| 20 / 25 | `create_tag()` | POST /tags |
| 11 / 25 | `create_order()` | POST /orders |
| 5 / 25 | `setup_book_with_deps()` | Vytvoří author + category + book naráz |
| 2 / 25 | `_create_author`, `_create_*` | Privátní (underscore-prefix) varianty (jen L2_run1, L2_run3) |

**Závěr:** DeepSeek má **stabilní jádro helperů** (`unique`, `create_author/category/book`) přítomné téměř ve všech sadách. `create_tag` se objevuje v 80 % sad, `create_order` jen v 44 %. Helper `setup_book_with_deps` je **L4-specifická abstrakce** — objevuje se 5/5 v L4 a vůbec jinde, jasně inspirovaná L4 příklady.

### 3.2 Klíčový architektonický posun: parametr `session`

Mezi sadami se signatura helperů **podstatně mění** mezi úrovněmi:

| Úroveň | Sady s `requests.Session()` | Sady s `session` parametrem v helperech |
|---|---:|---:|
| L0 | **5 / 5** | 5 / 5 |
| L1 | 1 / 5 | 1 / 5 |
| L2 | 2 / 5 | 2 / 5 |
| L3 | 1 / 5 | 1 / 5 |
| L4 | 0 / 5 | **0 / 5** |

Na L0 je signatura pravidelně `create_author(session, name=None, ...)` — DeepSeek vždy vytváří `requests.Session()` *uvnitř každého testu* a předává ji do helperu.

```python
# L0 typický pattern (anti-pattern!):
def test_create_author_valid():
    session = requests.Session()  # nová session v každém testu
    name = unique("author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    ...
```

Toto je **bezvýznamné použití Session** (žádné connection pooling, žádné sdílení cookies napříč testy). DeepSeek se naučil "good practice" pattern (Session) bez znalosti, kdy ho použít. Ve výsledku přidává ~10 řádků boilerplate bez výhody.

S rostoucím kontextem se DeepSeek od tohoto patternu **odpoutá**: na L4 je 0 % sad s Session() a helpery mají signaturu `create_author(name=None, ...)` — přímé `requests.post(...)` volání.

**Hypotéza:** Bez kontextu DeepSeek aplikuje "best-practice" template z trainingu. Příklady v L4 ukazují přímý plain-`requests` styl, což DeepSeek **kopíruje** a opouští Session pattern.

### 3.3 Asertivní helpery (pre-conditions)

Všechny helpery (kromě `unique`) končí defenzivním guard-assertem:

```python
def create_author(session, name=None, bio=None, born_year=None):
    ...
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()
```

Tato defense-in-depth je přítomná **ve všech 23/23 helperech `create_*`** (mimo `unique` a `setup_book_with_deps`). Pokud setup helper selže, test selže s konkrétní chybovou zprávou identifikující selhání pre-condition.

### 3.4 Co DeepSeek NEPOUŽÍVÁ

Podobně jako Claude, ale ještě striktněji:

- **0 fixtures** napříč všemi 25 sadami (žádné `@pytest.fixture`)
- **0 `@pytest.mark.parametrize`** napříč všemi sadami
- **0 `@pytest.mark.skip` / `xfail`**
- **Žádné `setup_method` / `teardown_method`**
- **Žádné `yield`** v helperech
- **Nepoužívá `/reset` endpoint** (žádná z 25 sad — `calls_reset_endpoint=False` všude)
- **0 `time.sleep()`** — nezkouší rate-limit testy s časovými prodlevami
- **0 docstringů** ve **všech 25 sadách** — viz sekce 7.5

Toto je téměř totožné s Claude, ale s jednou klíčovou výjimkou: **0 docstringů u DeepSeek** vs ~5/5 u Claude na L0.

---

## 4. Importy — minimalismus, ale méně než Claude

| Modul | Frekvence (z 25) |
|---|---:|
| `requests` | 25 |
| `uuid` | 25 |
| `time` | 14 |
| `pytest` | **4** |
| `typing` | 3 |
| `io` | 2 |
| `datetime` | 2 |

**Pozoruhodné:**

- **`pytest` import jen ve 4/25 sadách.** DeepSeek používá pouze `assert` syntax — žádné `pytest.raises`, `pytest.fail`, `pytest.skip`. Pytest funguje implicitně přes test_ prefix bez nutnosti importu. Claude měl pytest importovaný ve 24/25.
- `time` ve 14/25 sadách, ale **ani jednou nepoužito pro `time.sleep`** — pravděpodobně import zůstal po dřívějších iteracích bez následného použití.
- Žádný `PIL.Image` přežil v žádné sadě — DeepSeek nezkouší generovat reálné JPEG/PNG bytes (na rozdíl od Claude). Pro cover-upload testy používá hardcoded `b"\x89PNG..."` magic bytes.
- `typing.Optional, Dict, Any` jen ve 3 sadách (L2_run1, L2_run3, L3_run1) — DeepSeek neanotuje typy.

---

## 5. Co se testuje — sémantické pokrytí

### 5.1 Doménové pokrytí (kolik z 5 sad na úrovni testuje doménu)

| Doména | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| `health` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `authors` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `categories` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `books` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `tags` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `orders` | 4/5 | 4/5 | 4/5 | 4/5 | **5/5** |
| `admin` | **1/5** | 0/5 | 0/5 | 0/5 | 0/5 |
| `exports` | **1/5** | 0/5 | 0/5 | 0/5 | 0/5 |

**Klíčová zjištění:**

1. **DeepSeek pokrývá 6 z 8 domén stabilně.** Health/authors/categories/books/tags jsou 5/5 napříč všemi úrovněmi. Orders je 4/5 (s L4 = 5/5).
2. **Admin doména v 1/25 sad** (L0_run5 — má 1 test `test_toggle_maintenance_missing_api_key`). Tento test selhal a byl ve failed listu. Po L0 už admin doménu nikdy netestuje.
3. **Exports v 1/25 sad** — opět L0_run5, opět selhal (`test_create_book_export_success`).
4. **Jediná sada, která zkusila admin/exports/maintenance, je L0_run5 a ALL THESE FAILED.** Po této neúspěšné zkušenosti DeepSeek na vyšších úrovních admin a exports zcela vynechává.
5. **Zlepšené pokrytí orders:** 4/5 už od L0 — DeepSeek si všímá orders endpointu z OpenAPI specifikace bez příkladů.

### 5.2 Pokrytí scénářů (počet sad z 5 na úrovni s ≥ 1 testem na scénář)

| Scénář | L0 | L1 | L2 | L3 | L4 | Komentář |
|---|---:|---:|---:|---:|---:|---|
| ETag conditional GET (304) | 1/5 | 1/5 | 0/5 | 0/5 | 0/5 | **L4 regrese — úplně mizí** |
| ETag mismatch (412) | 2/5 | 4/5 | 2/5 | 2/5 | 0/5 | L1 peak, L4 vymizí |
| Soft delete + restore (410) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno na L0 |
| Pagination | 2/5 | 2/5 | 2/5 | 4/5 | **0/5** | **L4 dramatický kolaps** |
| Duplicate key (409) | 0/5 | 5/5 | 5/5 | 5/5 | 5/5 | **L0→L1 jasný práh** |
| Validation 422 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Rate limit (429) | 3/5 | 1/5 | 0/5 | 1/5 | 0/5 | Klesá s kontextem |
| Idempotency-Key | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | **NIKDY** |
| API key auth (X-API-Key) | 2/5 | 1/5 | 1/5 | 0/5 | **5/5** | L4 jen *deklaruje* konstanty |
| Cover upload (multipart) | 4/5 | 4/5 | 4/5 | 4/5 | 3/5 | Stabilně vysoké |
| Reviews | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Discount logika | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Stock manipulace | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Search/filter | 2/5 | 0/5 | 1/5 | 1/5 | 0/5 | Velmi nízké |
| Concurrent / race | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | **NIKDY** |
| Maintenance mode (503) | 1/5 | 0/5 | 0/5 | 0/5 | 0/5 | Jen L0_run5 (selhal) |
| Order state machine | 3/5 | 1/5 | 3/5 | 4/5 | 3/5 | L1 dip, L3 peak |
| Restore endpoint | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |

### 5.3 X-API-Key autentizace — *deklarovaná, ale nepoužitá*

V 5/5 L4 sad DeepSeek deklaruje konstanty na top-level:

```python
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
```

**Ale tyto konstanty NIKDY nepoužije** — `headers=AUTH` se nevyskytuje ani v jediném testu na L4. Jde o **kopírovaný-ale-nepoužitý** kód: DeepSeek si všiml deklarace v `existing_tests.py` a převzal ji do top-level scope, ale nezreplikoval testy, které ji používají.

To je **podstatná diagnostická distinkce vs Claude**: Claude na L4 *skutečně* používá `headers={"X-API-Key": ...}` při testech `/admin/*` a `/books/bulk` endpointů. DeepSeek deklaruje a zapomene.

Důsledek: L4 sady **úplně vynechávají** všechny endpointy vyžadující API key (`/admin/*`, `/exports/*`, `/books/bulk`, `/admin/maintenance`). Konstanty jsou "dead code".

### 5.4 Konvence pojmenování testů — explicitní status code v názvu

DeepSeek vykazuje **silně bimodální** vzor pojmenování:

| Úroveň | Tests s `_returns_NNN` v názvu | % | Příklady |
|---|---:|---:|---|
| L0 | 5 / 150 | **3.3%** | `test_create_author_valid` (převažuje generický styl) |
| L1 | 77 / 150 | **51.3%** | smíšené — `test_get_soft_deleted_book_returns_410` |
| L2 | 26 / 150 | 17.3% | málo `_returns_*` — generická forma |
| L3 | 29 / 150 | 19.3% | málo `_returns_*` — generická forma |
| L4 | 102 / 150 | **68.0%** | `test_create_book_with_negative_price_returns_422` |

**Pozorování:**

- **L0 (3.3 %)** — DeepSeek "ne-formálně" pojmenovává testy bez status kódu (`test_create_author_valid`).
- **L1 (51.3 %)** — náhlý přechod ke `_returns_NNN` formátu kvůli dokumentaci, která exposuje očekávané status kódy.
- **L2/L3 propad zpět k 17–19 %** — když DeepSeek získá zdrojový kód a DDL, stane se "imperativnější" v testovacím záměru a méně formální v pojmenování.
- **L4 peak 68 %** — silný in-context learning signál. Existující testy v L4 příkladu používají `_returns_NNN` styl, který DeepSeek kopíruje.

Tento U-tvar (51 → 17 → 19 → 68) je **unikátní stylistická vlna** napříč úrovněmi.

### 5.5 Nejčastěji generované testy (signature scenarios)

20 nejčastějších test names přes všech 25 sad:

| # opak. | Název testu |
|---:|---|
| 17 | `test_get_soft_deleted_book_returns_410` |
| 16 | `test_create_author_success` |
| 16 | `test_create_book_success` |
| 15 | `test_create_category_success` |
| 15 | `test_health_check_returns_ok` |
| 13 | `test_create_author_missing_name` |
| 12 | `test_get_author_not_found` |
| 12 | `test_create_review_success` |
| 12 | `test_create_tag_success` |
| 12 | `test_create_order_success` |
| 12 | `test_apply_discount_to_new_book_returns_400` |
| 11 | `test_get_author_by_id_success` |
| 11 | `test_create_author_missing_name_returns_422` |
| 11 | `test_soft_delete_book_success` |
| 10 | `test_upload_cover_unsupported_type` |
| 10 | `test_create_duplicate_category_returns_409` |
| 9 | `test_restore_soft_deleted_book` |
| 8 | `test_create_book_duplicate_isbn_returns_409` |
| 8 | `test_create_book_duplicate_isbn` |
| 7 | `test_list_authors_default_pagination` |

**Důležité:** žádný test se neobjeví ve více než **17 z 25 sad** (Claude měl test s 20 výskyty). To znamená, že DeepSeek je **méně deterministický v test jmenech** — viz Jaccard analýza níže.

---

## 6. Jak se testuje — taktická úroveň

### 6.1 Distribuce HTTP status kódů ověřených v asercích

| Code | L0 | L1 | L2 | L3 | L4 | Význam |
|---:|---:|---:|---:|---:|---:|---|
| 200 | 56 | 56 | 52 | 45 | 41 | OK — postupně klesá |
| 201 | 26 | 31 | 37 | 24 | 24 | Created |
| 202 | **1** | 0 | 0 | 0 | 0 | Accepted (jen L0_run5 export) |
| 204 | 13 | 11 | 11 | 7 | 10 | No Content |
| 304 | **1** | 1 | 0 | 0 | 0 | Not Modified — postupně mizí |
| 400 | **2** | 18 | 18 | 23 | 20 | Bad Request — **L0→L1 skok ×9!** |
| 401 | 3 | 0 | 1 | 0 | 0 | Unauthorized — pouze L0/L2 |
| 403 | 0 | 1 | 3 | 3 | 2 | Forbidden — emerging na L2+ |
| 404 | 8 | 8 | 8 | 9 | 7 | Not Found |
| 409 | **0** | 14 | 15 | 19 | **23** | Conflict — **L0→L1 skok, plynule roste** |
| 410 | 8 | 5 | 6 | 7 | 10 | Gone (soft delete) |
| 412 | 3 | 4 | 1 | 2 | **0** | Precondition Failed — L4 mizí |
| 413 | 0 | 0 | 0 | 0 | **2** | Payload Too Large — pouze L4 |
| 415 | 4 | 4 | 4 | 4 | 3 | Unsupported Media Type |
| 422 | **21** | 7 | 7 | 6 | 11 | Unprocessable — **L0 over-uses** |
| 429 | 3 | 0 | 0 | 1 | 0 | Too Many Requests — klesá |

**Pozorování:**

- **L0 over-uses 422 (21 výskytů) a under-uses 400 (2 výskyty)** — DeepSeek bez dokumentace defaultně používá 422 jako "validation error" status (správně dle FastAPI), ale neumí rozlišit business-rule errors (400). Po dokumentaci na L1 se to obrátí: 422 klesá na 7 a 400 vyskakuje na 18.
- **L0→L1 skok pro 400** (2 → 18) — z OpenAPI specifikace nezná všechny business-rule chyby, dokumentace je odhalí.
- **L0→L1 skok pro 409** (0 → 14) — duplicitní klíče, podobně jako Claude.
- **L4 jediné s 413 (Payload Too Large)** — z příkladů se DeepSeek naučí testovat soubory přes 2 MB.
- **L4 nemá ETag (412 = 0)** — největší regrese, viz dále.
- **Diversity peak:** L0_run1 a L0_run5 mají 12 různých kódů, L4 maxima jsou 11 (L4_run5).

### 6.2 Distribuce testovacích typů (z plánovacího JSON)

| Úroveň | happy_path | edge_case | error |
|---|---:|---:|---:|
| L0 | 19.2 | 2.0 | 10.0 |
| L1 | 18.0 | 0.0 | 12.0 |
| L2 | 17.4 | 0.0 | 12.6 |
| L3 | 15.2 | 0.0 | 14.8 |
| L4 | 14.6 | 0.0 | 15.4 |

**Trendy:**

1. **Happy path klesá** 19.2 → 14.6 (~−24 %).
2. **Error roste** 10.0 → 15.4 (~+54 %).
3. **Edge case se vyparuje** po L0 (2.0 → 0.0). Toto je **specificky DeepSeek**: edge cases jsou pohlceny do "error" kategorie. DeepSeek nepřemýšlí o "boundary conditions" jako oddělené kategorii.
4. Trend: na L4 je distribuce ~50/50 happy/error — agresivní error focus.

### 6.3 Patterny asercí (sum přes všechny sady na úrovni)

| Pattern | L0 | L1 | L2 | L3 | L4 | Trend |
|---|---:|---:|---:|---:|---:|---|
| `status_code ==` | 149 | 160 | 163 | 150 | 153 | Stabilní |
| `status_code in (...)` | 21 | 21 | 20 | 23 | 25 | Mírně roste |
| `"key" in data` | 71 | 56 | **95** | **120** | 73 | **L1→L2 skok +70%, L3 peak 120, L4 propad** |
| `data["key"] == X` | 51 | 54 | **79** | 48 | **81** | L2 peak, L3 dip, L4 peak |
| `isinstance(...)` | 8 | 3 | 3 | 4 | **0** | Klesá k nule |
| `len(...)` | 0 | 1 | 2 | 1 | 2 | Velmi nízké |
| `"detail" in data` | 26 | 0 | 37 | **73** | 40 | **L1 = 0, L3 peak** |
| `>=, <=` srovnání | 2 | 0 | 2 | 0 | 0 | Velmi nízké |

**Klíčové signály využití kontextu:**

1. **`key in data` skok L1→L2: 56 → 95 (+70 %)**. Stejný pattern jako Claude (+84 %). Po zpřístupnění zdrojového kódu DeepSeek zná Pydantic field names a kontroluje je. Skok pokračuje na L3 (+26 %) díky DDL polím.

2. **`isinstance` decline L0 = 8 → L4 = 0.** Defenzivní typové kontroly mizí s rostoucí konkrétností. Stejný pattern jako Claude, ale DeepSeek startuje s nižším počtem (8 vs Claude 17).

3. **`detail in data` divný pattern: L1 = 0, L2 = 37, L3 = 73 (peak).** Bez dokumentace DeepSeek o `detail` poli neví. Při L1 se z nějakého důvodu (pravděpodobně defaultní reset chování po dokumentaci) propadá na 0. Při L2/L3 vrací zpět masivně.

4. **`len()` aserce zůstávají nízké** (0–2 napříč úrovněmi) — DeepSeek nekontroluje délku list odpovědí jako Claude (kde L2 mělo 6 a L3 4).

### 6.4 Velikost testů a celých sad

| Úroveň | Avg lines/sada | Avg lines/test | Avg asercí/sada | Avg helpers |
|---|---:|---:|---:|---:|
| L0 | 333.6 | 7.71 | 64.4 | 5.2 |
| L1 | 327.2 | 7.68 | 68.4 | 5.0 |
| L2 | 392.4 | **9.71** | 78.4 | 5.0 |
| L3 | 381.0 | 9.14 | 70.4 | 5.6 |
| L4 | 312.2 | **7.00** | 74.6 | **6.8** |

**U-shape v délce testů:**

- L0 — krátké testy (7.71 lines), s `requests.Session()` boilerplate
- L2 — peak (9.71 lines), DeepSeek explicitněji testuje pole z Pydantic modelů
- L4 — minimum (7.00 lines), úsporná struktura inspirovaná příklady

**Helper count peak na L4 (6.8 helperů):** L4 sady přidávají `setup_book_with_deps` jako "fixture-equivalent" (5/5 sad). To je **L4-exklusivní pattern**.

### 6.5 Docstrings — totální absence

**0 docstringů ve všech 25 sadách.** Žádná funkce v žádné sadě nemá `"""docstring"""`. To je **diametrálně odlišné** od Claude (kde L0 měl 5/5 sad s ≥30 docstringy).

DeepSeek věří, že **název testu je dokumentace**. Pro `test_create_author_with_negative_born_year_returns_422` nepotřebuje další popis. Tento minimalismus se promítá i do absence type-anotací (`typing.Optional` jen ve 3 sadách).

---

## 7. Validita a repair loop

### 7.1 Souhrnná validita

| Úroveň | Avg validity | 100 % sad | Avg iterací | Sady s repair |
|---|---:|---:|---:|---|
| L0 | **95.33%** | 1/5 | **2.8** | 4/5 (1 fixed, 3 NEVER fixed) |
| L1 | 98.00% | 3/5 | 1.8 | 2/5 (oba NEVER fixed) |
| L2 | 99.33% | 4/5 | 1.4 | 1/5 (NEVER fixed) |
| L3 | **100.00%** | 5/5 | 1.0 | 0/5 |
| L4 | **100.00%** | 5/5 | 1.0 | 0/5 |

**Klíčové rozdíly oproti Claude:**

1. **Validita má jasný monotónní průběh** 95.33 % → 100 %. To je **velmi silný signál pro RQ1** — Claude byl saturován od L0 (98.7 %), DeepSeek **skutečně reaguje na kontext**. Dokumentace (L1) získává +2.7 %, zdrojový kód (L2) získává +1.3 %, DDL/příklady (L3+) dosahují 100 %.

2. **Repair loop je z velké části NEÚČINNÝ.** Z 8 sad, které vstoupily do repair loopu (více než 1 iterace):
   - **Pouze 1 sada (L0_run1) byla úspěšně opravena** — `self_correction_rate = 100 %`
   - **7 sad terminovalo s `all_stale_early_stop`** po 3 iteracích bez zlepšení — `self_correction_rate = 0 %`

3. **17/25 sad (68 %) prošlo na první iteraci.** Claude mělo 80 %.

### 7.2 Anatomie selhání — co se DeepSeek nedaří opravit

Z logu identifikováno **9 unikátních selhání** přes všech 8 problémových sad:

| # výskytů | Test name | Selhání kategorie |
|---:|---|---|
| 6× | `test_update_stock_valid` (L0_run2, L0_run3) | assertion_value_mismatch |
| 6× | `test_update_order_status_valid` (L0_run2, L0_run5) | wrong_status_code |
| 6× | `test_update_order_status_invalid_transition_returns_400` (L1_run1, L2_run2) | wrong_status_code |
| 3× | `test_update_stock_success` (L0_run4) | assertion_value_mismatch |
| 3× | `test_update_stock_positive_quantity` (L0_run5) | assertion_value_mismatch |
| 3× | `test_create_book_export_success` (L0_run5) | wrong_status_code |
| 3× | `test_list_authors_pagination_returns_correct_slice` (L1_run2) | assertion_value_mismatch |
| 3× | `test_delete_author_with_books_returns_400` (L1_run2) | wrong_status_code |
| 1× | `test_update_stock_negative_quantity` (L0_run1) | wrong_status_code (FIXED) |

**Diagnostika selhání:**

- **`/books/{id}/stock` doména je 7/9 selhání** (6 + 3 + 3 unikátních variant). DeepSeek opakovaně nesprávně testuje stock manipulaci. Bug pattern: `test_update_stock_valid` aserce `data["stock"] == 20`, ale dostal 30 (nebo jinou hodnotu).

- **`order status` je 6 selhání** napříč 3 sadami (L0_run2, L0_run5, L1_run1, L2_run2, ...). DeepSeek nezná správné stavové přechody (`pending → confirmed → ...`).

- **Pagination pattern selhává specificky** v L1_run2: `test_list_authors_pagination_returns_correct_slice` — DeepSeek předpokládá konkrétní velikost stránky, kterou API nedeklaruje.

- **L0_run5 je nejhorší sada** s 3 trvalými failures: stock, order status, export. Tato sada paradoxně zkoušela admin/export — což jí přineslo nejvíc selhání. Po této zkušenosti se DeepSeek admin doméně vyhýbá.

### 7.3 Repair-loop strategie

DeepSeek používá tříkrokovou repair eskalaci (z `repair_trajectory`):

| Iterace | Strategie | Účinnost |
|---:|---|---|
| 1 | `isolated` (oprav konkrétní failed test) | Funguje v 1/8 případů |
| 2 | `helper_fallback` (oprav helper signature/logic) | Funguje 0/7 dosud nezfixovaných |
| 3 | `all_stale_early_stop` (vzdá se) | 0/7 |

Pipeline detekuje "stale" stav (žádné zlepšení po 2 iteracích) a předčasně ukončí repair smyčku — proto `iterations_used = 3` u všech selhávajících sad (ne 7). Toto **šetří tokeny**, ale znamená, že DeepSeek nemá víc než 2 šance opravit chybu.

### 7.4 Leaked thinking — *unikátní podpis DeepSeek*

V **6 z 8 repair-aktivovaných sad** (75 %) se v záhlaví finálního souboru objeví **leaked LLM analysis comments**:

```python
# The main error is likely due to ISBN length exceeding the allowed limit (13 characters).
# The unique function generates prefix + 8 hex chars, so "isbn_" + 8 chars = 13 characters,
# but the API might expect exactly 13 characters or less. Also, the unique function generates
# strings like "isbn_abc12345" which is 13 characters total, but the underscore might not be
# valid for ISBN format. Fix: generate ISBN without prefix, just 13 hex characters.
import uuid
import requests
...
```

| Sada | Leaked? | Iterace | Fixed? |
|---|---|---:|---|
| L0_run1 | ne | 2 | ✅ |
| L0_run2 | **ano** | 3 | ❌ |
| L0_run3 | **ano** | 3 | ❌ |
| L0_run4 | **ano** | 3 | ❌ |
| L0_run5 | **ano** | 3 | ❌ |
| L1_run1 | **ano** ("Analysis:") | 3 | ❌ |
| L1_run2 | **ano** | 3 | ❌ |
| L2_run2 | **ano** | 3 | ❌ |

**Diagnóza:** Při repair fázi DeepSeek **přemýšlí nahlas** v kódovém výstupu — analyzuje pravděpodobnou příčinu chyby jako Python komentář na začátku souboru. Tento komentář **přežívá** do finální verze, ale **diagnostika je často správná, fix je špatný nebo chybí**:

- L0_run3 komentář: *"unique function creates strings like 'isbn_abc12345' which is longer than 13 chars"* → Diagnóza správná, ale fix nefunguje, sada selhává v 3 iteracích.
- L0_run5 komentář: *"missing X-API-Key header for authenticated endpoints"* → Diagnóza správná, fix neimplementován.

Toto je **silný diagnostický marker DeepSeek**: leaked comments = repair triggered, ne all-pass-on-first-iter. **Ani jedna sada s 1 iterací neobsahuje leaked comment.**

Implikace pro výzkum: pro detekci "model identity" stačí grep `# The main error is likely` — vlastně by tato fráze mohla sloužit jako fingerprint DeepSeek-V4-Flash repair fáze.

### 7.5 Doba běhu a cost

| Úroveň | Avg time | Avg cost | Avg total tokens | Avg cached % |
|---|---:|---:|---:|---:|
| L0 | 105.9s | $0.0029 | 34 559 | 59.3% |
| L1 | 105.1s | $0.0027 | 49 544 | 76.9% |
| L2 | 92.2s | $0.0029 | 78 741 | 83.6% |
| L3 | 86.8s | $0.0024 | 79 126 | 88.5% |
| L4 | 87.0s | $0.0026 | 94 878 | 88.7% |

**Pozorování:**

- **Náklady jsou monotonně klesající** s úrovní (po L0 spike kvůli repair) díky aggressive caching.
- **L3/L4 cachují ~88 % tokenů** — kontext je z velké části fixní, jen output se mění.
- **Total cost across všech 25 sad: $0.0677**. To je **mimořádně levné** — kompletní experiment běží pod 7 centů. (Pro srovnání by Claude Haiku při podobných objemech a bez stejné cache rate stál o řád víc.)
- **Cost-per-passed-test: $0.00008–0.00010** napříč úrovněmi. Bez statisticky významného rozdílu — DeepSeek je *uniformly* cost-effective.

---

## 8. Variabilita — jak konzistentní je DeepSeek napříč běhy?

### 8.1 Jaccard similarity test names v rámci úrovně

| Úroveň | Avg pairwise Jaccard | Testy společné všem 5 běhům | Sjednocení testů |
|---|---:|---:|---:|
| L0 | **0.144** | 2 | **101** |
| L1 | 0.189 | 1 | 93 |
| L2 | 0.280 | 6 | 78 |
| L3 | 0.266 | 5 | 78 |
| L4 | **0.312** | 4 | **73** |

**Klíčové zjištění: čím víc kontextu, tím KONZISTENTNĚJŠÍ DeepSeek je.** *Inverzní trend vůči Claude.*

- L0: 101 unikátních test names (5 běhů × 30 = 150 možných); Jaccard 0.144 → DeepSeek **bez kontextu vymýšlí v každém běhu jiné testy**.
- L4: 73 unikátních test names; Jaccard 0.312 → DeepSeek **s příklady konverguje k užšímu repertoáru**.

Příčina: **L4 examples slouží jako "anchor"** — DeepSeek bez větší kreativity reprodukuje subset testů z příkladu. Bez kontextu (L0) DeepSeek samplíguje z širšího prostoru "co by se mohlo testovat", což vede k větší rozmanitosti.

### 8.2 Tests společné všem 5 běhům úrovně

| Úroveň | Tests common to all 5 |
|---|---|
| L0 | `test_create_author_missing_name`, `test_list_authors_default_pagination` |
| L1 | `test_get_soft_deleted_book_returns_410` |
| L2 | `test_create_author_success`, `test_create_book_success`, `test_create_category_success`, `test_create_tag_success`, `test_health_check_returns_ok`, `test_soft_delete_book_success` |
| L3 | `test_create_author_success`, `test_create_book_success`, `test_get_author_by_id_success`, `test_health_check_returns_ok`, `test_soft_delete_book_success` |
| L4 | `test_apply_discount_to_new_book_returns_400`, `test_decrease_stock_below_zero_returns_400`, `test_get_soft_deleted_book_returns_410`, `test_health_check_returns_ok` |

L0/L1 mají **prakticky žádný stable core** (jen 1–2 sdílené testy). L2+ vykazuje 4–6 stabilních "core CRUD happy paths".

### 8.3 Příklady scénářů exkluzivních pouze pro L4

Test names objevující se pouze v L4:

- `test_add_nonexistent_tag_to_book_returns_404`
- `test_create_author_with_minimal_data` / `test_create_author_with_valid_data`
- `test_create_book_with_negative_price_returns_422`
- `test_create_book_with_nonexistent_author_returns_404`
- `test_decrease_stock_below_zero_returns_400`
- `test_delete_author_with_books_returns_409`
- `test_increase_stock_successfully`
- `test_upload_file_too_large_returns_413`

**Charakteristika L4 testů:**
- Verbose názvy s explicitními status kódy (`returns_NNN`)
- "Causal" formulace (`with_negative_price`, `with_nonexistent_author`)
- Specific edge cases (`too_large_returns_413`, `below_zero_returns_400`)

Tyto názvy **kopírují strukturu příkladů** z `existing_tests.py` (in-context learning).

### 8.4 Příklady scénářů exkluzivních pouze pro L0

Test names objevující se pouze v L0 (z 67 unikátních):
- `test_apply_discount_rate_limit`, `test_apply_discount_rate_limit_exceeded`
- `test_bulk_create_books_missing_api_key`
- `test_create_author_valid` (generický nikoliv `_returns_201`)
- `test_create_book_export_success`
- `test_toggle_maintenance_missing_api_key`

L0 obsahuje **více "domain-exploring"** testů (rate limit, bulk create, maintenance), ale tyto často **selhávají** (export, maintenance, rate limit testy v L0_run5 byly všechny ve failed list). DeepSeek bez kontextu zkouší exoticky, ale špatně.

---

## 9. Endpoint coverage a Code coverage — paradoxní vztah

### 9.1 Endpoint coverage klesá s kontextem

| Úroveň | Avg EpCov | Min | Max |
|---|---:|---:|---:|
| L0 | **47.6%** | 42% | 52% |
| L1 | 38.0% | 34% | 42% |
| L2 | 40.8% | 34% | 44% |
| L3 | 38.4% | 34% | 48% |
| L4 | **36.8%** | 32% | 40% |

**Endpoint coverage se zhoršuje s rostoucím kontextem!** Anti-intuitivní výsledek:

- L0: ~24 z 50 endpointů pokryto (47.6 %)
- L4: ~18 z 50 endpointů pokryto (36.8 %)

**Hypotéza:** S rostoucím kontextem DeepSeek **plánuje hlubší (více testů na stejný endpoint)** místo **širších** scénářů. L4 příklady ukazují **kvalitativní hloubku** (více edge cases na 1 endpoint), ne **šířku** (mnoho různých endpointů). DeepSeek to napodobuje a koncentruje testy na ~16–20 endpointů.

Top-3 concentration potvrzuje: L0_run1 = 20 %, L4_run1 = 26.7 % (3 nejvíc testované endpointy nesou 27 % testů).

### 9.2 Code coverage je *pozoruhodně stabilní*

| Úroveň | Avg CodeCov | crud.py |
|---|---:|---:|
| L0 | 71.22% | 46.51% |
| L1 | 70.72% | 46.41% |
| L2 | 70.80% | 47.65% |
| L3 | 70.33% | 46.87% |
| L4 | 69.49% | 45.22% |

**Code coverage zůstává prakticky konstantní (~70 %)** napříč úrovněmi — žádný výrazný skok na L2 ani L4. Jednotlivé soubory `app/__init__.py`, `app/database.py`, `app/models.py`, `app/schemas.py` jsou na 100 % saturovány už od L0. `app/crud.py` se drží 45–48 % a `app/main.py` 67–73 %.

**Implikace:** DeepSeek obsahuje **jiné endpointy ne nutně víc kódu**. Šíře pokrytí (více endpointů) na L0 nepřináší proporčně víc code coverage, protože mnoho endpointů sdílí stejné CRUD funkce. Hloubka na L4 ale také nepřináší skok, protože DeepSeek netestuje exotic paths v `crud.py` (admin, exports, statistics). Code coverage tedy NENÍ informativní metrika pro DeepSeek-V4-Flash při tomto API.

### 9.3 Endpointy, které DeepSeek NIKDY nepokryje

Endpointy chybějící ve všech 5 bězích každé úrovně:

| Endpoint | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| `GET /admin/maintenance` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `POST /admin/maintenance` | (1/5) | ✗ | ✗ | ✗ | ✗ |
| `GET /catalog` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `GET /statistics/summary` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `POST /reset` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `POST /exports/books` | (1/5) | ✗ | ✗ | ✗ | ✗ |
| `POST /exports/orders` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `GET /exports/{job_id}` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `POST /books/bulk` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `POST /books/{id}/clone` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `DELETE /books/{id}/cover` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `DELETE /orders/{id}` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `GET /tags` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `PUT /tags/{tag_id}` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `GET /authors/{id}/books` | (1/5) | ✗ | ✗ | ✗ | ✗ |

**Slepá místa DeepSeek:**

1. **Admin doména** — totálně netestována napříč všemi 25 sadami (kromě 1 selhaného pokusu na L0_run5).
2. **Statistics/catalog** — meta-endpointy ignorovány.
3. **Bulk a clone operations** — nikdy netestováno.
4. **`GET` listy pro tags a `GET /authors/{id}/books`** — málo viditelné v doc, DeepSeek se zaměřuje na single-resource operace.
5. **`POST /reset`** — DeepSeek dodržuje framework rule "nekontaktovat reset endpoint" (`calls_reset_endpoint = False` všude).

---

## 10. Slabá místa DeepSeek (pro doktorskou obhajobu / komparace)

### 10.1 Strukturní

1. **0 tříd ve všech 25 sadách** — plochá struktura. To eliminuje nadměrnou komplexnost, ale brání hierarchickému reportingu pytest.
2. **Anti-pattern `requests.Session()` per-test na L0** — boilerplate bez výhody. Mizí s kontextem, ale zatěžuje token budget.
3. **Žádné fixtures, parametrize, ani docstrings** — extrémní minimalismus.

### 10.2 Sémantické

1. **`/admin/*`, `/exports/*`, `/statistics/*`, `/catalog`, `/books/bulk`, `/books/{id}/clone` jsou totální slepá místa** — 24/25 sad tyto endpointy ignoruje.
2. **`Idempotency-Key` mechanismus 0/25** — nikdy netestován.
3. **`Concurrent / race conditions` 0/25** — nikdy netestováno.
4. **`Maintenance mode (503)` 0/25** (kromě L0_run5 selhání).
5. **API key auth deklarován ale nepoužit** na L4 (5/5 sad má `AUTH = {"X-API-Key": ...}` jako mrtvý kód).
6. **Stock manipulace systematicky selhává** — 12 výskytů selhání napříč 4 sadami v L0. DeepSeek nezná, jak interpretovat `quantity` parameter.
7. **Order state machine** — order status transitions selhávají v 9 výskytech napříč 5 sadami.
8. **Rate-limit testy nejsou robustní** — 3/5 sad na L0 → 0/5 na L4. Postupný útěk od scénáře.

### 10.3 Test-engineering

1. **Repair loop má 12.5% úspěšnost** (1 z 8) — extrémně slabý self-correction. Když DeepSeek udělá chybu, většinou ji neopraví ani po 3 iteracích.
2. **Leaked thinking comments** v 6/8 repair-aktivovaných sad — diagnóza je správná, ale fix není aplikován.
3. **L4_run1 má 0% plan adherence** — DeepSeek vygeneruje 30 testů s úplně jinými názvy než v plánu (anomálie).
4. **L1_run2 má 80% plan adherence** — 6 z 30 testů se neshoduje s plánem.
5. **`test_count = 30` adherence je 100% u všech sad**, ale to je výsledek pipeline `validate_test_count` (pipeline ořezává nebo doplňuje).
6. **Endpoint coverage klesá s kontextem** — paradoxní výsledek vlivem koncentrace na hloubku scénářů.

---

## 11. Silné stránky DeepSeek

1. **Dokonalá adherence k `test_count` cíli** — 30/30 testů ve všech 25 sadách (po pipeline zpracování).
2. **Velmi vysoká validita na L3/L4** — 100% napříč 5 běhy. Žádný falešný optimismus jako u Claude.
3. **Výrazná lineární odezva validity na kontext** — 95.3 % → 100 % je čistý kontextový gradient.
4. **Konzistentní helper-knihovna** — `unique`, `create_*`, vždy s defenzivní guard assertion.
5. **Stabilní distribuce 80 % tokenů cachovaných** — pipeline využívá DeepSeek caching efektivně, dramaticky snižuje cost.
6. **Mimořádně levný experiment** — celkem $0.0677 za 25 sad × 30 testů = 750 testů. ~9 ¢ na 1000 testů.
7. **Adaptace na úroveň kontextu**:
   - L0: verbose Session-based, zkouší exotic endpoints (admin, export)
   - L1: explicitní `_returns_NNN` naming
   - L2: peak hloubky (`key in data` + `data["key"] == X` peak)
   - L3: stabilní base, žádné selhání
   - L4: úsporný, mírně regresní u širších scénářů (ETag, pagination)
8. **Status code 400 / 409 jasný L0→L1 práh** — dokumentace umožňuje správné rozlišení Bad Request vs Conflict.
9. **Code coverage je pozoruhodně stabilní (69–71 %)** — DeepSeek pokrývá *jádro* CRUD logiky bez ohledu na kontext.

---

## 12. Implikace pro výzkumné otázky

### RQ1 — Validita, hloubka asercí, distribuce

- **Validity Rate má jasný monotónní průběh** 95.3 % → 100 %, na rozdíl od Claude (saturován od L0). DeepSeek poskytuje **silný RQ1 signál**.
- **Assertion depth roste nelineárně:** L0=2.01, L1=2.14, L2=2.48, L3=2.19, L4=2.32. **Peak na L2** (zdrojový kód), L3 mírný propad, L4 mírný comeback. To je odlišné od Claude (kde AsrD monotonicky roste 2.27 → 2.91).
- **Status code diversity je flat:** L0=9.0, L1=10.0, L2=9.6, L3=9.8, L4=9.4. **Žádný progresivní růst** s kontextem. Claude měl 9 → 13 (+44 %), DeepSeek je víc-méně konstantní.
- **Distribuce typů:** edge_case mizí po L0 (2 → 0), happy klesá, error roste. Stejný směr jako Claude, ale s razantnějším splynutím edge↔error.
- **Response validation roste** 68.7 % → 93.3 % — silný kontextový signál.

### RQ2 — Strukturní pokrytí

- **Endpoint coverage saturuje BRZY a KLESÁ** — L0=47.6 %, L4=36.8 %. To je **opačný trend** než hypotéza saturace na L0. DeepSeek **přesouvá testy z širších k užším** s rostoucím kontextem.
- **Code coverage je flat (69–71 %)** — žádný skok na L2. Toto **vyvrací část RQ2 hypotézy**: code coverage NEROSTE skokem při zpřístupnění zdrojového kódu pro DeepSeek. Sourcecode pomáhá *kvalitativně* (lepší aserce, jiné scénáře), ne *kvantitativně* (víc řádků kódu se neexekuje).

### RQ3 — Mezimodelové rozdíly

- **Strukturní podpis DeepSeek**: 0 tříd (vs Claude 24/25), 0 docstrings (vs Claude L0 5/5), Session() per-test na L0, plochá struktura.
- **Sémantický podpis DeepSeek**: stable test name vocabulary se ~10–15 "signature tests" společných napříč úrovněmi (proti Claude, kde signature je ~15–20).
- **Slabiny pro srovnání**: stock testy systematicky selhávají, order status state machine, admin doména totálně, repair loop má 12.5% úspěšnost.
- **In-context learning kvalitativně slabší**: kopíruje deklarace (API_KEY, AUTH) ale ne použití (header passing). Claude na L4 X-API-Key SKUTEČNĚ POUŽÍVÁ, DeepSeek jen deklaruje jako dead code.
- **Cost-effectiveness**: DeepSeek je **výrazně levnější** než Claude. Celkový experiment $0.0677 vs Claude pravděpodobně >$1.

---

## 13. Doporučení pro komparaci s ostatními modely

### Co měřit pro fair-srovnání

1. **Class usage rate** — DeepSeek 0%, Claude 96%. Extrémní strukturní rozdíl.
2. **Average tests per top-level item** — DeepSeek 30 testů/modul (plochý), Claude ~2 testů/třídu.
3. **Helper consistency** — DeepSeek 23/25 sad má stejný helper core (Claude 25/25). Rozdíl 2 sad u DeepSeek = privatizace (`_create_*`).
4. **`requests.Session()` adoption rate** — DeepSeek L0=5/5, L4=0/5. Claude pravděpodobně 0/25 (Claude používá přímé `requests.X`).
5. **Status code 400 vs 422 ratio** — DeepSeek L0 over-uses 422 (21:2 vs 400), pak se obrátí. Claude začíná balancovaněji.
6. **Plan adherence anomaly rate** — DeepSeek 1/25 anomálií (L4_run1 = 0%). Claude pravděpodobně 0.
7. **Leaked-thinking-in-code rate** — DeepSeek 6/25 (24%, ale 75% repair-aktivovaných). Claude pravděpodobně 0%.
8. **Self-correction rate** — DeepSeek 12.5% (1/8 repaired). Claude 0/5 (žádná repair sada nedosáhla 100%).
9. **Endpoint coverage vs context** — DeepSeek **klesá** L0→L4 (47.6 → 36.8), Claude pravděpodobně roste nebo saturuje.
10. **Jaccard inverze** — DeepSeek L0=0.144, L4=0.312 (KONVERGENCE). Claude L0=0.464, L4=0.148 (DIVERGENCE). **Diametrálně opačný trend.**
11. **Cost-per-passed-test** — DeepSeek $0.00009 average. Klíčový pro RQ3 cost-effectiveness.
12. **L4 X-API-Key actual USAGE rate** — DeepSeek 0/5 (deklarováno, nepoužito). Claude 5/5 (deklarováno A POUŽITO).
13. **Repair iteration distribution** — DeepSeek L0 avg 2.8, L4 avg 1.0 (silně klesá s kontextem). Claude má víc plochou distribuci.
14. **Total unique test names per level** — DeepSeek L0=101, L4=73 (KLESÁ). Claude L0=61, L4=104 (ROSTE).
15. **Docstring rate** — DeepSeek 0/25 napříč všemi sadami. Klíčový strukturní marker.

### Diagnostické otázky pro ostatní modely

1. Generuje top-level třídy nebo plochou strukturu?
2. Používá `requests.Session()` per-test (anti-pattern) nebo přímé volání?
3. Generuje docstringy?
4. Má leaked thinking comments při repair fázi?
5. Self-correction rate v repair loopu?
6. Pokrývá admin doménu vůbec?
7. Distribuce L0 unique test names — šíře explorace bez kontextu?
8. Jaccard trend s kontextem — konvergence (DeepSeek) nebo divergence (Claude)?
9. L4 X-API-Key — deklaruje a používá, jen deklaruje, nebo úplně ignoruje?
10. Endpoint coverage L0→L4 trend?
11. Stock/order status transitions — selhávají systematicky?
12. Status 422 vs 400 distribution na L0 — over-uses 422 (FastAPI default) nebo balanced?

---

## 14. Konkrétní artefakty pro citaci v textu

### Citovatelná čísla

- **0/25 sad používá top-level třídy** — plochá struktura jako podpis DeepSeek
- **0/25 sad obsahuje docstring** — minimalismus
- **30/30 testů ve všech sadách** (perfect adherence to plan, ale 1 anomálie L4_run1 s 0% match)
- **Validity Rate: 95.33% (L0) → 100% (L3/L4)** — monotónní růst
- **17/25 sad pasuje na 1. iteraci** (68 %); Claude měl 80 %
- **8 sad vyžadovalo repair, 1 z nich úspěšně opravena** — self-correction rate 12.5 %
- **6/8 repair-aktivovaných sad obsahuje leaked thinking comments** v hlavičce
- **0 fixtures, 0 parametrize, 0 setup_method, 0 docstrings** napříč 25 sadami
- **Helper functions consistency: 92 %** (`unique` 25/25, `create_author/category/book` 23/25)
- **`requests.Session()` adoption: 5/5 (L0) → 0/5 (L4)** — opuštěno s kontextem
- **Status code diversity: 9.0 (L0) → 9.4 (L4)** — flat (vs Claude 9→13)
- **Assertion depth: 2.01 (L0) → 2.32 (L4)** — peak 2.48 na L2
- **`key in data` aserce: L1→L2 skok +70 %** (56 → 95), L3 peak (120)
- **Jaccard similarity: 0.144 (L0) → 0.312 (L4)** — *konvergence* s kontextem (opačně než Claude)
- **L4 unikátní test names: 73** vs **L0: 101** — užší repertoár s příklady
- **X-API-Key declaration: 0/5 (L0–L3) → 5/5 (L4) — ale 0/5 actual usage**
- **Admin doména: 1/25 sad** (L0_run5 — selhalo)
- **Maintenance mode: 1/25 sad** (L0_run5 — selhalo)
- **Concurrent tests: 0/25**
- **Idempotency-Key: 0/25**
- **Endpoint coverage: 47.6% (L0) → 36.8% (L4)** — klesá
- **Code coverage: 71.22% (L0) → 69.49% (L4)** — flat
- **Total experiment cost: $0.0677**
- **Cached tokens: 1.39M / 1.68M total = 83 %**
- **Cost-per-passed-test: $0.00009** napříč úrovněmi

### Charakteristické úryvky kódu

```python
# DeepSeek L0 typický pattern (Session anti-pattern):
def test_create_author_valid():
    session = requests.Session()  # nová Session v každém testu, žádná výhoda
    name = unique("author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201

# DeepSeek L4 čistý pattern (po opuštění Session):
def test_create_author_with_valid_data():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors",
                      json={"name": name, "bio": "Test bio", "born_year": 1990},
                      timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert data["bio"] == "Test bio"

# DeepSeek L4 dead-code pattern:
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}  # NIKDY se nepoužije v žádném testu

# Standardní helper pattern (23/25 sad):
def create_author(session, name=None, bio=None, born_year=None):  # L0–L3 signature
    if name is None:
        name = unique("author")
    payload = {"name": name}
    ...
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# Repair-fáze leaked thinking pattern (6/8 repair sad):
# The main error is likely due to ISBN length exceeding the allowed limit (13 characters).
# The unique function generates prefix + 8 hex chars, so "isbn_" + 8 chars = 13 characters,
# but the API might expect exactly 13 characters or less. Fix: generate ISBN without prefix.
import uuid
import requests
...
```

---

## 15. Závěr

DeepSeek-V4-Flash produkuje **strukturálně minimalistické** (žádné třídy, žádné docstringy, žádné fixtures), **kvalitativně rostoucí** (validita 95.3 → 100 %) a **velmi cost-efektivní** (~$0.003/sada) testovací sady. Hlavní efekt přírůstku kontextu se projevuje **zejména ve validitě a ve hloubce asercí v polovině spektra** (L2), nikoliv ve šíři pokrytí.

Klíčové unikátní rysy DeepSeek (signatura modelu):

- **0 tříd a 0 docstringů** napříč všemi 25 sadami — extrémní strukturní minimalismus
- **`requests.Session()` per-test anti-pattern** na L0, mizí s kontextem
- **Leaked LLM thinking comments** v hlavičce kódu při repair fázi (75 % repair-aktivovaných sad)
- **Endpoint coverage klesá** s kontextem (anti-intuitivní)
- **Jaccard similarity ROSTE** s kontextem (konvergence místo divergence)
- **In-context learning slabší** — kopíruje deklarace, neaplikuje použití (X-API-Key = dead code na L4)
- **Repair loop má 12.5% self-correction rate** — když selže, většinou se neopraví

Pro mezimodelovou komparaci je DeepSeek **silným kontrastem k Claude**: odlišná strukturní strategie (plochá vs. třídní), opačný trend variability (konvergující vs. divergující), monotónní validity gradient (vs. saturovaný), ale stejné slepé místo na admin doméně a stejné systematické selhání rate-limit testů. Skutečné rozdíly se projeví v **strukturních markerech** (třídy, docstringy), **adopci patternů z příkladů** (in-context learning quality), **repair effectiveness**, a **cost-effectiveness** (DeepSeek je o řád levnější).

L3 je **optimální bod** pro DeepSeek — 100 % validita, žádná potřeba repair, stabilní 70 % code coverage, žádné regrese na pagination/ETag. L4 přidává nové scénáře (decrease/increase stock, file too large 413), ale způsobuje regrese na ETag, pagination a search/filter. Přidání in-context examples pro DeepSeek **přepisuje** existující strategie místo aby je rozšiřovalo.