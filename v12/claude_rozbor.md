# Claude Haiku 4.5 — Rozbor 25 testovacích sad

**Subjekt analýzy:** `claude-haiku-4-5-20251001`, API `bookstore`, 5 úrovní kontextu × 5 běhů = 25 sad
**Konfigurace:** `temperature=0.4`, `test_count=30`, `max_iterations=7`
**Zdroj:** `merged_test_suites_claude.py` (12 264 řádků), `merged_test_suites_log_claude.txt` (2 229 řádků)

> Analýza zkoumá strukturní, sémantické a behaviorální charakteristiky vygenerovaných testovacích sad nezávisle na obsahu `ABOUT.md`. Cílem je popsat **co** Claude testuje, **jak** to testuje a **jak** se jeho strategie mění s úrovní kontextu — připravit srovnávací podklad pro ostatní modely.

---

## 1. Souhrnná tabulka všech 25 sad

| Sada | Řádky | Tříd | Prázd. tříd | Testů | Helpers | Asercí | AsrD | StCodes | Passed | Iter |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0_run1 | 556 | 15 | 0 | 30 | 5 | 70 | 2.33 | 9 | 28 | 3 |
| L0_run2 | 570 | 18 | 0 | 30 | 5 | 71 | 2.37 | 8 | 30 | 1 |
| L0_run3 | 538 | 14 | 0 | 30 | 5 | 65 | 2.17 | 9 | 30 | 1 |
| L0_run4 | 522 | 19 | 0 | 30 | 5 | 63 | 2.10 | 8 | 30 | 1 |
| L0_run5 | 523 | 18 | 0 | 30 | 5 | 71 | 2.37 | 9 | 30 | 1 |
| L1_run1 | 478 | 24 | **10** | 30 | 6 | 72 | 2.40 | 11 | 29 | 3 |
| L1_run2 | 469 | 15 | 0 | 30 | 5 | 73 | 2.43 | 10 | 30 | 1 |
| L1_run3 | 387 | 15 | 0 | 30 | 5 | 74 | 2.47 | 9 | 30 | 1 |
| L1_run4 | 403 | **0** | 0 | 30 | 5 | 68 | 2.27 | 9 | 30 | 1 |
| L1_run5 | 576 | 21 | **7** | 30 | 6 | 69 | 2.30 | 10 | 30 | 1 |
| L2_run1 | 460 | 14 | 0 | 30 | 4 | 88 | 2.93 | 10 | 30 | 1 |
| L2_run2 | 497 | 15 | 0 | 30 | 6 | 85 | 2.83 | 11 | 29 | 3 |
| L2_run3 | 400 | 14 | 0 | 30 | 4 | 77 | 2.57 | 10 | 30 | 1 |
| L2_run4 | 437 | 13 | 0 | 30 | 4 | 90 | 3.00 | 10 | 30 | 1 |
| L2_run5 | 484 | 20 | **7** | 30 | 7 | 86 | 2.87 | 12 | 30 | 1 |
| L3_run1 | 448 | 14 | 0 | 30 | 5 | 86 | 2.87 | 10 | 30 | 1 |
| L3_run2 | 390 | 14 | 0 | 30 | 5 | 81 | 2.70 | 12 | 30 | 1 |
| L3_run3 | 461 | 15 | 0 | 30 | 6 | 83 | 2.77 | 10 | 30 | 1 |
| L3_run4 | 473 | 26 | **10** | 30 | 5 | 85 | 2.83 | 11 | 30 | 1 |
| L3_run5 | 421 | 12 | 0 | 30 | 5 | 87 | 2.90 | 11 | 29 | 3 |
| L4_run1 | 500 | 14 | 0 | 30 | 6 | 77 | 2.57 | 13 | 29 | 3 |
| L4_run2 | 500 | 17 | 0 | 30 | 6 | 95 | 3.17 | 10 | 30 | 1 |
| L4_run3 | 566 | 17 | 0 | 30 | 6 | 87 | 2.90 | 12 | 30 | 1 |
| L4_run4 | 489 | 15 | 0 | 30 | 6 | 87 | 2.90 | 10 | 30 | 1 |
| L4_run5 | 466 | 15 | 0 | 30 | 6 | 89 | 2.97 | 12 | 30 | 1 |

**Legenda:** `Cls` = počet top-level tříd, `AsrD` = průměrná hloubka asercí na test, `StCodes` = počet různých HTTP status kódů ověřovaných, `Iter` = počet iterací repair loopu.

---

## 2. Strukturní analýza — proč Claude organizuje testy do tříd?

### 2.1 Pozorování (jedinečné napříč modely)

**24 z 25 sad používá top-level Python třídy** k seskupení testů. Pouze jediná výjimka existuje (`L1_run4` s plochou strukturou 30 funkcí). Žádný jiný model v experimentu pravděpodobně tuto strategii nepoužívá tak důsledně, nebo vůbec.

| Úroveň | Sady s třídami | Průměr tříd na sadu | Min–Max | Test/třída |
|---|---:|---:|---:|---:|
| L0 | 5 / 5 | 16.8 | 14–19 | 1.79 |
| L1 | 4 / 5 | 18.8 | 15–24 | 1.65* |
| L2 | 5 / 5 | 15.2 | 13–20 | 1.97 |
| L3 | 5 / 5 | 16.2 | 12–26 | 1.85 |
| L4 | 5 / 5 | 15.6 | 14–17 | 1.92 |

\* Bez L1_run4 (no-classes anomálie).

### 2.2 Konvence pojmenování tříd

Claude se striktně drží schématu `Test{Resource}{HTTPVerb}` nebo `Test{Resource}{Operation}`. Nejčastější třídy přes všech 25 sad:

| Frekvence | Třída | Doména | Operace |
|---:|---|---|---|
| 24× | `TestBooksGet` | books | GET (list) |
| 23× | `TestAuthorsPost` | authors | POST (create) |
| 23× | `TestAuthorsDelete` | authors | DELETE |
| 23× | `TestBooksPost` | books | POST |
| 23× | `TestBooksDelete` | books | DELETE |
| 23× | `TestBooksRestore` | books | restore (custom action) |
| 22× | `TestAuthorsGet` | authors | GET |
| 22× | `TestAuthorsPut` | authors | PUT |
| 20× | `TestBooksDiscount` | books | discount (custom) |
| 20× | `TestCategoriesPost` | categories | POST |
| 17× | `TestBooksStock` | books | stock |
| 15× | `TestHealth` | health | GET |

**Výklad:** Granularita je velmi jemná — typicky **2 testy na třídu** (medián 2.0). Každá HTTP-akce na zdroji má vlastní třídu. To dává:
- **Sémantické čtení testovací zprávy** (`TestAuthorsPost::test_create_author_missing_name` jasně signalizuje co a kde se zkouší)
- **Logickou izolaci** (každá třída pokrývá jeden endpoint × verb pár)
- **Lepší pytest reporting** (hierarchie v `--verbose` výstupu)

### 2.3 Proč to dělá Claude (a pravděpodobně ne ostatní modely)

Žádný prompt v `prompt_templates.py` to explicitně nepředepisuje. Jde o **emergentní stylistickou preferenci** Claude:

1. **Tréninková data:** Anthropic pravděpodobně přizpůsobil Claude na produkční pytest kód, kde jsou třídy běžné (Django/Flask projekty, `unittest.TestCase` dědictví).
2. **„Plánovací" charakter:** Claude očividně přemýšlí v termínech *kategorií scénářů* před psaním. Třídy jsou strukturní formalizace plánu z fáze 2.
3. **Mentální model OOP:** Pro Claude je třída přirozený *namespace* na rozdíl od ploché funkce.

### 2.4 Slabina tříd: prázdné kostry

**4 z 25 sad obsahují třídy bez testů — kostry, které Claude vytvořil, ale nezaplnil:**

| Sada | Prázdné třídy | Konkrétně |
|---|---:|---|
| L1_run1 | 10 / 24 | TestTags, TestBookTags, TestReviews, TestOrders, TestCover, TestBulkBooks, TestCloneBook, TestExports, TestMaintenance, TestStatistics |
| L1_run5 | 7 / 21 | TestBooksDiscount, TestBooksReviews, TestBooksCover, TestTags, TestBookTags, TestOrders, TestBulkBooks |
| L2_run5 | 7 / 20 | TestReviews, TestTags, TestOrders, TestBulkBooks, TestCloneBook, TestExports, TestMaintenance |
| L3_run4 | 10 / 26 | TestTags, TestReviews, TestOrders, TestMaintenance, TestStatistics, TestDeprecatedCatalog, TestBulkBooks, TestCloneBook, TestExports, TestEdgeCases |

**Diagnóza:** Claude evidentně *přeplánuje* (vytvoří kostry pro většinu domén API), ale dojde mu rozpočet asercí na 30 — čili „obětuje" pokryté domény ve prospěch hloubky v jiných. Limit 30 testů + komplexita 50-endpointového API vede k tomu, že prázdné třídy zůstanou jako *technický dluh*. Pro RQ1 to znamená: **Claude zachová `plan_test_count == 30`, ale plánuje pro mnohem víc** — což lze měřit jako rozpor mezi „intent" (počet tříd) a „realization" (testů ve třídách).

Mimořádně se to vyskytuje na L1 a L3 (vyšší dokumentace/DDL doplňují kontext, ale nejsou ještě "examples" jako L4).

---

## 3. Helper funkce — konzistence jako podpis modelu

### 3.1 Standardizovaná knihovna helperů

Všech **25 sad bez výjimky** definuje stejné základní helpery na top-level:

| Frekvence | Helper | Účel |
|---:|---|---|
| 25 / 25 | `unique(prefix)` | Generování unikátního stringu (`uuid.uuid4().hex[:8]`) |
| 25 / 25 | `create_author()` | POST /authors a vrácení JSON odpovědi |
| 25 / 25 | `create_category()` | POST /categories |
| 25 / 25 | `create_book()` | POST /books (s automatickým vytvořením autora + kategorie) |
| 22 / 25 | `create_tag()` | POST /tags |
| 10 / 25 | `create_order()` | POST /orders |
| 1 / 25 | `create_jpeg_image()` | Generování JPEG bytes pro cover upload (L2_run5) |

**Závěr:** Claude rozpoznává transitivní závislosti zdrojů (book vyžaduje author + category) a abstrahuje je do helperů. To je signifikantní — **každý helper redukuje boilerplate** a uvolňuje místo na hlavní aserce.

### 3.2 Dedukce: přechod helper → orderlifecycle

`create_order` se objevuje jen na L4 (pravděpodobně, ale variabilní mezi runy). Test pro `/orders` doménu obecně chybí v L0–L3, viz sekce 5.

### 3.3 Co Claude NEPOUŽÍVÁ

- **0 fixtures** napříč všemi 25 sadami (žádné `@pytest.fixture`)
- **0 `@pytest.mark.parametrize`** napříč všemi sadami
- **0 `@pytest.mark.skip` / `xfail`**
- **Žádné `setup_method` / `teardown_method`**
- **Žádné `yield`** v testech (kromě výjimek)
- **Nepoužívá `/reset` endpoint** (žádná z 25 sad)

To je **silně kontrastní vůči pytest idiomatice**. Claude preferuje **imperativní setup uvnitř každého testu** přes helper-volání, ne deklarativní fixture systém. Hypotézy:

1. **Jednoduchost > DRY:** Každý test je samostatný, snáze čitelný v izolaci. Žádné implicitní fixtures.
2. **Bezstavovost:** Pokud test sám vytváří svá data, nezáleží na pořadí (prevence flaky tests).
3. **Nedůvěra v fixture cleanup:** Claude raději nechá API stav „špinavý" než aby spoléhal na komplikované fixture teardowny.

To má důsledek: **vyšší redundance API volání**. Pokud 3 testy potřebují book, vytvoří se 3 booky (každý se svým author/category). Ale pro výzkum testovací kvality to znamená vyšší **test independence** = méně flakiness.

### 3.4 Asertivní helpery (pre-conditions)

Každý helper končí:
```python
assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
return response.json()
```

To je výjimečně dobrá *defense in depth*: pokud setup helper selže, test selže s **konkrétní zprávou** identifikující selhání pre-condition (ne až v hlavním aserci). Ostatní modely často generují helpery bez tohoto „guard" mechanismu.

---

## 4. Importy — minimalizmus

| Modul | Frekvence (z 25) |
|---|---:|
| `requests` | 25 |
| `uuid` | 25 |
| `pytest` | 24 |
| `time` | 13 |
| `json` | 3 |
| `typing.Dict, Any` | 6 sad |
| `datetime.datetime, timezone` | 6 sad |
| `io.BytesIO` | 5 sad |
| `typing.Optional` | 3 sady |
| **`PIL.Image`** | **2 sady** (L1_run3 dead import, L2_run5 reálně použito) |

**Pozoruhodné:**
- `pytest` chybí v L1_run4 (jediná no-classes sada — protože plochá struktura nepotřebuje import)
- `time` je v 13 sadách — používá se pro `time.sleep()` mezi rate-limit testy nebo `time.time()` pro unique IDs
- **PIL import přežil v 2 sadách**, navzdory `Import Sanitizer` v pipeline. V L2_run5 se reálně volá `Image.new('RGB', (100, 100), color='red')` na generování test JPEG — což znamená, že Claude se *snaží reálně* testovat upload obrázku, ne jen mock

---

## 5. Co se testuje — sémantické pokrytí

### 5.1 Doménové pokrytí (kolik z 5 sad na úrovni testuje doménu)

| Doména | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| `health` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `authors` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `categories` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `books` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `tags` | 5/5 | 5/5 | 2/5 | 5/5 | 5/5 |
| `orders` | 0/5 | 2/5 | 2/5 | 1/5 | **5/5** |
| `admin` | 0/5 | 0/5 | 0/5 | 0/5 | **0/5** |

**Klíčová zjištění:**

1. **Admin doména je completely untested napříč všemi 25 sadami.** Endpointy pod `/admin` (statistika, maintenance mode, exporty) neexistují v generovaných testech ani na L4. Přitom L4 obsahuje příklady — buď tyto příklady admin nezahrnují, nebo Claude vědomě admin zanedbává jako „ne-priority".

2. **Orders domain skok na L4: 1/5 → 5/5.** Toto je **nejvýraznější dopad in-context-learning** — orders je komplexní stavový automat (draft → submitted → approved...) a Claude potřebuje konkrétní příklady, jak ho testovat.

3. **Tags coverage U-shape:** L0/L1 = 5/5, L2 = 2/5, L3 = 5/5, L4 = 5/5. Při zpřístupnění zdrojového kódu (L2) se Claude soustředí na implementační detaily a paradoxně opouští některé povrchové domény. Při L3 (DDL) si všimne tag M:N tabulky a vrací se k testování tagů.

### 5.2 Pokrytí scénářů (počet sad z 5 na úrovni s ≥ 1 testem na scénář)

| Scénář | L0 | L1 | L2 | L3 | L4 | Komentář |
|---|---:|---:|---:|---:|---:|---|
| ETag conditional GET (304) | 1/5 | 5/5 | 5/5 | 5/5 | 5/5 | **L0→L1 skok**: dokumentace odhalí `If-None-Match` |
| ETag mismatch (412) | 5/5 | 5/5 | 4/5 | 5/5 | 5/5 | Odvozeno z OpenAPI již na L0 |
| Soft delete + restore (410) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno už na L0 |
| Pagination | 5/5 | 5/5 | 4/5 | 3/5 | 3/5 | **Klesá** s kontextem (vytlačováno složitějšími scénáři) |
| Duplicate key (409) | 0/5 | 4/5 | 5/5 | 5/5 | 5/5 | **L0→L1 skok**: dokumentace odhalí unique constraints |
| Validation 422 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno na L0 |
| Rate limit (429) | 3/5 | 1/5 | 1/5 | 0/5 | 1/5 | **Klesá** — viz analýza failures |
| Idempotency | 0/5 | 0/5 | 0/5 | 0/5 | 1/5 | Pouze L4 a jen 1 sada |
| Authentication (X-API-Key) | 0/5 | 0/5 | 0/5 | 0/5 | **5/5** | **Exkluzivně L4** — viz níže |
| Cover upload (multipart) | 0/5 | 0/5 | 1/5 | 3/5 | 3/5 | **L2 práh** — odhalí endpoint v kódu |
| Tags M:N | 0/5 | 0/5 | 0/5 | 0/5 | 2/5 | Jen L4 |
| Reviews | 5/5 | 0/5 | 1/5 | 0/5 | 4/5 | **U-shape** — opouštěné na L1–L3 |
| Discount logika | 4/5 | 4/5 | 5/5 | 5/5 | 5/5 | Stabilně vysoké |
| Stock manipulace | 2/5 | 5/5 | 3/5 | 5/5 | 5/5 | L1 skok, L2 dip |
| Search/filter | 5/5 | 5/5 | 4/5 | 4/5 | 1/5 | **L4 dramatický pokles** |
| Edge max/min length | 3/5 | 3/5 | 2/5 | 0/5 | 3/5 | Nestabilní |
| Concurrent / race | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | Nikdy netestováno |
| Maintenance mode (503) | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | Nikdy netestováno |

### 5.3 Tři klíčové „kontextové prahy" Claude

#### Práh L0→L1 (přidání dokumentace):
- Aktivuje **conditional GET (304)** — 1/5 → 5/5
- Aktivuje **conflict detection (409)** — 0/5 → 4/5
- Aktivuje **stock manipulace** (2/5 → 5/5)
- **Deaktivuje rate limit testy** (3/5 → 1/5) — Claude nahrazuje pokus o testování problematického scénáře jiným

#### Práh L1→L2 (přidání zdrojového kódu):
- Aktivuje **cover upload** (0/5 → 1/5) — endpoint je teď viditelný
- **Skok hloubky asercí** (AsrD 2.40 → ~2.85)
- Skokový růst `json_dict_keys` asercí (74 → 136 — model zná názvy polí)
- Začínají se objevovat `len()` aserce (nový pattern)

#### Práh L3→L4 (přidání in-context examples):
- **Aktivuje X-API-Key autentizaci** — 0/5 → 5/5 (jediné místo, kde Claude pochopí auth!)
- **Aktivuje orders doménu** 1/5 → 5/5
- **Aktivuje idempotency** 0/5 → 1/5 (jen 1 sada — slabě)
- **Aktivuje tags M:N** 0/5 → 2/5
- Reviews comeback (0/5 → 4/5)

### 5.4 Top opakovaně generované testy (signature scenarios)

20 nejčastějších test names přes všech 25 sad:

| # opak. | Název testu |
|---:|---|
| 20 | `test_create_author_with_all_fields` |
| 19 | `test_restore_non_deleted_book` |
| 18 | `test_create_author_missing_name` |
| 18 | `test_create_book_invalid_isbn_length` |
| 16 | `test_health_check_success` |
| 16 | `test_create_category_success` |
| 16 | `test_apply_discount_to_old_book` |
| 14 | `test_update_author_etag_mismatch` |
| 14 | `test_list_books_with_search_filter` |
| 14 | `test_create_book_duplicate_isbn` |
| 14 | `test_restore_soft_deleted_book` |
| 14 | `test_apply_discount_to_new_book` |
| 13 | `test_update_author_success` |
| 13 | `test_get_soft_deleted_book` |
| 12 | `test_get_author_not_found` |
| 12 | `test_delete_author_success` |
| 11 | `test_list_authors_default_pagination` |
| 11 | `test_soft_delete_book_success` |
| 11 | `test_get_nonexistent_author` |
| 11 | `test_create_category_duplicate_name` |

To naznačuje, že Claude má **stabilní mentální model "co se má testovat na CRUD endpoint"** — happy path + missing required + validation error + 404 not found + duplicate conflict + etag mismatch.

---

## 6. Jak se testuje — taktická úroveň

### 6.1 Distribuce HTTP status kódů ověřených v asercích

| Code | L0 | L1 | L2 | L3 | L4 | Význam |
|---:|---:|---:|---:|---:|---:|---|
| 200 | 90 | 87 | 78 | 83 | 79 | OK |
| 201 | 38 | 43 | 39 | 41 | **47** | Created (roste mírně s L) |
| 204 | 11 | 9 | 10 | 12 | 6 | No Content |
| 304 | **1** | 5 | 5 | 5 | 5 | Not Modified — L0→L1 práh |
| 400 | 5 | **13** | 13 | 13 | **15** | Bad Request — L1 skok |
| 404 | 5 | 12 | 11 | 9 | 6 | Not Found |
| 409 | **0** | 8 | **15** | 13 | **17** | Conflict — graduálně roste |
| 410 | 12 | 9 | 10 | 10 | 11 | Gone (soft delete) — saturováno |
| 412 | 6 | 5 | 5 | 5 | 5 | Precondition Failed (ETag) |
| 413 | 0 | 0 | 1 | 1 | 3 | Payload Too Large — L2+ |
| 415 | 0 | 0 | 1 | 3 | 3 | Unsupported Media Type — L2+ |
| 422 | 23 | 15 | 16 | 15 | **17** | Unprocessable Entity |
| 429 | 2 | 1 | 1 | 0 | 1 | Too Many Requests — klesá |
| **Diverzita** | **9** | **11** | **13** | **12** | **13** | Unique codes per level |

**Pozorování:**
- Diverzita status kódů roste ze 9 (L0) na 13 (L4) — nárůst o 44 %
- 409 Conflict je **nejdramaticky rostoucí kód** (0 → 17). To přímo koreluje s pokrytím duplicate-name scénářů
- 304 a 412 (ETag headers) jsou „discovery" kódy — bez dokumentace L0 jen 1 výskyt 304
- 413/415 (multipart errors) jsou exkluzivně L2+ — vyžadují source-code context

### 6.2 Distribuce testovacích typů (heuristická klasifikace podle názvu)

| Úroveň | Happy path | Error | Edge | Other |
|---|---:|---:|---:|---:|
| L0 (avg) | ~14 | ~10 | ~5 | ~1 |
| L1 (avg) | ~13 | ~11 | ~5 | ~1 |
| L2 (avg) | ~12 | ~12 | ~5 | ~1 |
| L3 (avg) | ~12 | ~12 | ~6 | ~0 |
| L4 (avg) | ~12 | ~13 | ~5 | ~0 |

Trendy: **happy path mírně klesá, error roste**, edge stabilní. Claude se s rostoucím kontextem stává „kritičtější" — víc cíli na chyby a méně na pozitivní cesty.

### 6.3 Patterny asercí (raw count přes všechny sady na úrovni)

| Pattern | L0 | L1 | L2 | L3 | L4 | Trend |
|---|---:|---:|---:|---:|---:|---|
| `status_code ==` | 153 | 163 | 167 | 168 | 165 | Stabilní (každý test 1×) |
| `status_code in (...)` | 20 | 22 | 19 | 21 | 25 | Mírně roste |
| `"key" in data` | 78 | 74 | **136** | 125 | 129 | **L1→L2 skok +84 %** |
| `data["key"] == X` | 67 | 73 | 77 | 80 | **90** | Plynulý růst +34 % |
| `isinstance(...)` | 17 | 15 | 7 | 7 | **2** | **Klesá** (z defenze na konkrétnost) |
| `len(...)` | 0 | 1 | 6 | 4 | 4 | **L1→L2 práh** |
| `>=, <=, < x, > x` | 20 | 7 | 19 | 11 | 13 | Nestabilní |

**Mimořádně signifikantní pozorování — `key in data` skok L1→L2:**

Před L2 Claude netuší přesné názvy polí v API odpovědích a používá defenzivně `isinstance(data, dict)` nebo `assert "id" in data` jen pro několik známých polí. Po L2 (zdrojový kód) zná všechna pole z Pydantic modelů a kontroluje jejich přítomnost masivně — odtud skok ze 74 na 136 výskytů.

**`isinstance` decline:** L0 = 17 výskytů, L4 = 2. Bez znalosti modelu se Claude zajistí typem (`isinstance(data, list)`), s kontextem rovnou kontroluje obsah pole.

### 6.4 Velikost testů a celých sad

| Úroveň | Avg lines | Avg test lines | Avg asercí | Avg helpers |
|---|---:|---:|---:|---:|
| L0 | 541.8 | **12.5** | 68.0 | 5.0 |
| L1 | 462.6 | 9.8 | 71.2 | 5.4 |
| L2 | 455.6 | 10.5 | 85.2 | 5.0 |
| L3 | 438.6 | 10.0 | 84.4 | 5.2 |
| L4 | 504.2 | **12.1** | 87.0 | **6.0** |

**U-shape v délce testů:** L0 (verbose, neznalý) → L1–L3 (úsporný, sebevědomý) → L4 (znova verbose, ale **bohatší o sofistikované scénáře**).

**Asertivní hloubka monotonně roste**: 68 → 87 (+28 %).

### 6.5 Docstrings — neočekávaný pattern

| Úroveň | Sady s ≥30 docstringy | Sady bez docstringů |
|---|---:|---:|
| L0 | **5/5** | 0/5 |
| L1 | 3/5 | 2/5 |
| L2 | 1/5 | 4/5 |
| L3 | 0/5 | 5/5 |
| L4 | 0/5 | **5/5** |

Na L0 každý test má vlastní docstring (popis scénáře). Postupně to vymizí — od L3 dál je v testech 0 docstringů. **Hypotéza:** se zvyšujícím se kontextem se Claude soustředí na implementaci a názvy testů samy vyjadřují záměr, takže docstring je redundantní. Také to může souviset s úsporou tokenů.

---

## 7. Validita a repair loop

### 7.1 Souhrnná validita

| Úroveň | Avg validity | 100% sad | Avg iterací | Suite s opravou |
|---|---:|---:|---:|---|
| L0 | **98.67%** | 4/5 | 1.40 | L0_run1 (skončil 28/30 po 3 it.) |
| L1 | 99.33% | 4/5 | 1.40 | L1_run1 (29/30 po 3 it.) |
| L2 | 99.33% | 4/5 | 1.40 | L2_run2 (29/30 po 3 it.) |
| L3 | 99.33% | 4/5 | 1.40 | L3_run5 (29/30 po 3 it.) |
| L4 | 99.33% | 4/5 | 1.40 | L4_run1 (29/30 po 3 it.) |

**Validita je extrémně vysoká** (98.67–99.33 %), ale **konstantní** přes úrovně — paradoxně ne rostoucí. Nejvyšší riziko falešného optimismu pro RQ1: Claude je tak „good by default", že přírůstek kontextu se neprojeví na validitě, jen na hloubce a šířce.

**Je 20/25 sad pasovalo na první iteraci.** Repair loop se aktivoval jen u 5 sad, **vždy přesně po 3 iteracích** — což odpovídá situaci, kdy se po 3 iteracích zlepšení zastaví a pipeline se rozhodne ukončit (early-stopping podle gradient detection v `phase3+4_repair`).

### 7.2 Anatomie selhání — co se Claude nedaří opravit

Z logu identifikováno **6 unikátních selhání** přes všech 5 problémových sad:

| Sada | Selhání | Pattern |
|---|---|---|
| L0_run1 | `test_apply_discount_rate_limit` | assertion `==200`, ale dostal `429` |
| L0_run1 | `test_update_stock_success` | assertion `data["stock"] == 20`, ale dostal `30` |
| L1_run1 | `test_apply_discount_rate_limit` | tentýž pattern jako L0 |
| L2_run2 | `test_apply_discount_exceeds_rate_limit` | tentýž pattern |
| L3_run5 | `test_restore_deleted_book_success` | (nezjištěno z logu) |
| L4_run1 | `test_discount_rate_limit_exceeded` | tentýž pattern |

**4 z 6 selhání = stejný koncepční bug s rate limitingem na endpointu `/discount`.** 

Vzor: Claude ví, že existuje rate limit, vytvoří test který ho má vyvolat, ale **assertuje 200 místo 429 nebo naopak**. Bug přežívá repair loop — modelu se nedaří se „přepnout" mezi mentálními modely („test, že rate limit existuje" vs. „test, že request prošel"). Toto je **systémová slabina** Claude pro konkrétní API: rate-limit logika je jediný vzor, který Claude opakovaně mylně testuje a *opakovaně se neopraví*.

**Druhé selhání** — `test_update_stock_success` v L0_run1 — je **stavový bug**: Claude předpokládal stock == 20 (po `+10` na initial 10), ale dostal 30, protože nějaký předchozí test uvnitř téže sady upravil stav. To poukazuje na **slabinu test-independence** v plochém imperativním stylu (žádné fixtures = žádný cleanup).

### 7.3 Doba běhu

Průměrná doba běhu jedné sady (poslední iterace): **1.5–2.2 sekundy**.
- L0: 1.9s
- L1: 1.7s
- L2: 1.8s
- L3: 1.7s
- L4: 1.8s

Konzistentní a velmi rychlé — žádný `time.sleep()` test trvající minuty. 30 testů × ~60ms = realistické pro lokální server.

---

## 8. Variabilita — jak konzistentní je Claude napříč běhy?

### 8.1 Jaccard similarity test names v rámci úrovně

Měříme, do jaké míry se testy mezi 5 běhy stejné úrovně překrývají:

| Úroveň | Avg pairwise Jaccard | Testy společné všem 5 běhům | Sjednocení testů |
|---|---:|---:|---:|
| L0 | **0.464** | 10 | 61 |
| L1 | 0.386 | 4 | 64 |
| L2 | 0.278 | 6 | 79 |
| L3 | 0.213 | **0** | 85 |
| L4 | **0.148** | 2 | **104** |

**Klíčové zjištění: čím víc kontextu, tím víc různorodých testů.**

- L0: Claude má jeden „default" repertoár (10 testů jádrových) → vysoká podobnost
- L4: Claude má rozsáhlý prostor scénářů → každý běh jde jinou cestou, jen 2 testy jsou společné všem 5 běhům
- L3 je extrémní — **žádný test není společný všem 5 běhům** (pravděpodobně každý běh akcentuje jinou DB-schema-derived feature)

To je důležité pro **statistickou robustnost RQ3**: pro L3/L4 je třeba více běhů, aby se aproximovala „typická" sada.

### 8.2 Příklady scénářů exkluzivních pouze pro L4

Test names, které se objevují **jen v L4 sadách** (z 67 unikátních):

- `test_add_tags_to_book` / `test_add_tags_to_book_idempotent`
- `test_apply_discount_invalid_percentage_validation_error`
- `test_create_author_born_year_out_of_range`
- `test_create_book_duplicate_isbn_conflict` / `..._returns_409`
- `test_create_book_isbn_too_short_returns_422`
- `test_create_review_on_soft_deleted_book_gone`
- `test_decrease_stock_below_zero_bad_request`

Tyto názvy jsou **výrazně přesnější**: obsahují přesný status code (`returns_409`, `validation_error`, `bad_request`) — kopírují styl referenčních testů z `existing_tests.py`. To je kvalitativní stopa **in-context learning**.

### 8.3 Příklady scénářů exkluzivních pouze pro L0

Z 25 unikátních L0-only testů jsou nejzajímavější:

- `test_apply_discount_exceeds_max`
- `test_apply_discount_valid_percentage`
- `test_create_review_with_rating_and_comment`
- `test_list_book_reviews_success`

Většinou **generičtější, méně specifické** názvy. Bez konkrétních příkladů Claude vymýšlí „selský" jazyk.

---

## 9. Slabá místa Claude (pro doktorskou obhajobu / komparace)

### 9.1 Strukturní

1. **Prázdné třídy** — ~16 % sad má 25 % – 40 % tříd nezaplněných. Plánovací schopnost převyšuje implementační rozpočet.
2. **L1_run4 anomálie** — jedna sada bez tříd. Vysvětlení: pravděpodobně něco v kontextu vyvolalo „flat" mode. Není to deterministický bug, ale ukazuje, že struktura **není garantována** (i když je 24/25 silně preferovaná).

### 9.2 Sémantické

3. **Rate-limit testy systematicky selhávají a nelze je repaire-loopem opravit** — *nejzávažnější jediné API selhání*.
4. **Admin doména totálně vynechána** napříč všemi 25 sadami.
5. **Maintenance mode (503) nikdy netestován** napříč 25 sadami.
6. **Concurrent / race condition tests** — 0 výskytů. Claude netestuje konkurentní přístup.
7. **Idempotency-Key** mechanismus testován jen 1× v L4.
8. **Pagination klesá** s úrovní kontextu (L0 5/5 → L4 3/5) — vytlačována komplexnějšími scénáři.

### 9.3 Test-engineering

9. **Žádné `pytest.fixture`** — DRY je obětována jednoduchosti, což zvyšuje API call traffic.
10. **Žádné `parametrize`** — místo 1 parametrizovaného testu se 5 vstupy se generuje 5 zvlášť pojmenovaných testů. Plus pro čitelnost, mínus pro pokrytí vstupních prostorů.
11. **Stavové aserce bez izolace** — `test_update_stock_success` selhal kvůli stavu sdílenému s jiným testem. Bez fixtures Claude občas předpokládá globální stav.

---

## 10. Silné stránky Claude (oproti potenciálním konkurentům)

1. **Dokonalá adherence k `test_count` cíli** — 30/30 ve všech 25 sadách.
2. **Stabilně vysoká validita** — 98.7–99.3 %, žádný drop pod 93 %.
3. **Velmi rychlá konvergence** — 80 % sad pasuje na první iteraci.
4. **Sofistikovaná hierarchická struktura tříd** — jedinečně mezi modely (předpokládám).
5. **Konzistentní helper-knihovna** — `unique`, `create_*`, vždy s asserts na response.status_code.
6. **Adaptace stylu na úroveň kontextu**:
   - L0 verbose s docstringy
   - L1–L3 úsporný
   - L4 verbose ale s extrémně specifickými názvy testů
7. **Naučí se X-API-Key auth z příkladů** — bez příkladů na L0–L3 by to nikdy neudělal.
8. **Generuje validní JPEG bytes** pro cover upload (L2_run5) — místo aby mockoval.
9. **Defenzivní guard asserts v helperech** — (`assert response.status_code in (200, 201)`).
10. **Diverzita roste s kontextem** — L4 generuje 104 unikátních test names (vs 61 na L0). To dává **organicky širší pokrytí** scénářů při více bězích.

---

## 11. Implikace pro výzkumné otázky

### RQ1 — Validita, hloubka asercí, distribuce

- **Validity Rate je nasycen** už na L0 (98.7 %). Není zde co měřit přírůstkově. **Silný signál pro Claude jako "high baseline" model.**
- **Assertion depth roste lineárně** 2.27 → 2.91 (~+28 %). To je nejlepší kontinuum metrika.
- **Status code diversity roste** 9 → 13 (~+44 %). Druhý nejlepší kontinuum signal.
- **Distribuce typů**: error stoupá, happy path klesá. Claude se s kontextem stává „kritičtější".

### RQ2 — Strukturní pokrytí

- **Endpoint coverage saturuje brzy** (5/5 domén od L0 kromě orders/admin) — potvrzuje hypotézu o saturaci.
- **Code coverage by měl skokově růst na L2** (kdy Claude vidí zdrojový kód a začíná hojně používat `key in data` aserce odvozené z Pydantic schémat — viz +84% skok). Toto je proxy ukazatel pro skutečné code coverage.

### RQ3 — Mezimodelové rozdíly

- **Strukturní podpis Claude:** třídy (24/25), žádné fixtures, žádné parametrize, vlastní helper library.
- **Sémantický podpis Claude:** stable test name vocabulary se ~10–20 „signature tests" společných napříč úrovněmi.
- **Slabiny pro srovnání:** rate-limit handling, total-misses (admin, maintenance, concurrent).
- **In-context learning čitelný:** test-name styling kopíruje formát příkladů (`_returns_409`, `_validation_error`).

---

## 12. Doporučení pro komparaci s ostatními modely

### Co měřit pro fair-srovnání

1. **Class usage rate** — % sad s ≥1 top-level třídou. Předpokládám, že Claude bude mít 96 %, GPT/Gemini možná 0–30 %.
2. **Average tests per class** — granularity organizace.
3. **Helper consistency** — počet sad používajících stejnou helper library.
4. **Empty-class rate** — Claude má 16 %, ostatní modely možná méně (necítí potřebu plánovat předem).
5. **Status code diversity** — Claude L4 = 13 unique codes.
6. **L1→L2 jump in `key in data` asserts** — proxy pro využití source code.
7. **L4 X-API-Key adoption** — Claude přechází z 0 % na 100 % díky příkladům.
8. **Run-to-run Jaccard similarity** — Claude L0 = 0.46 (konzistentní), L4 = 0.15 (kreativní).
9. **Repair iterations distribution** — Claude má 80 % sad na 1 iteraci, 20 % na 3 iterace.
10. **Total unique test names per level (cardinality)** — Claude L0 = 61, L4 = 104. Porovnání rozšiřitelnosti exploračního prostoru.

### Diagnostické otázky pro ostatní modely

1. Generuje stejné typy „signature tests" (CRUD pattern × verb) jako Claude?
2. Používá fixtures (Claude ne)?
3. Má rate-limit dead-zone (Claude ano)?
4. Adaptuje se na X-API-Key z příkladů (Claude ano)?
5. Prázdné třídy/over-planning (Claude občas)?
6. Distribuce assertion patterns — chová se isinstance jinak?
7. Pokrývá admin doménu (Claude vůbec)?
8. Ad-hoc generování binárních dat (PIL.Image — Claude ano v 1 sadě)?

---

## 13. Konkrétní artefakty pro citaci v textu

### Citovatelná čísla

- **24/25 sad používá top-level třídy** (1 anomálie L1_run4)
- Průměr **16.5 tříd na sadu** s **2.0 testy/třída**
- **30/30 testů** ve všech sadách (perfect adherence to plan)
- **Validity Rate 98.7–99.3 %**, **80 % sad pasuje na 1. iteraci**
- **5 sad vyžadovalo repair**, vždy přesně 3 iterace, 4 z nich kvůli rate-limit bugu
- **0 fixtures, 0 parametrize, 0 setup_method** ve všech 25 sadách
- **Helper functions consistency: 100 %** (`unique`, `create_author`, `create_category`, `create_book`)
- **Status code diversity: 9 (L0) → 13 (L4)**, 44 % nárůst
- **Assertion depth: 2.27 (L0) → 2.91 (L4)**, 28 % nárůst
- **`key in data` asserts: L1→L2 skok +84 %** (74 → 136)
- **Jaccard similarity: 0.46 (L0) → 0.15 (L4)** — variabilita roste
- **L4 unikátní test names: 104** vs **L0: 61**
- **X-API-Key adoption: 0 % (L0–L3) → 100 % (L4)** — exemplary in-context learning signal
- **Admin doména pokryta: 0/25 sad** (slepé místo)
- **Maintenance mode pokryt: 0/25 sad**
- **Concurrent tests: 0/25 sad**
- **Orders doména: 0/5 (L0) → 5/5 (L4)**

### Charakteristické úryvky kódu

```python
# Standardní helper pattern přítomný ve všech 25 sadách:
def create_book(title=None, isbn=None, price=29.99, ...):
    if title is None:
        title = unique("book")
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    payload = {...}
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {...}"
    return response.json()

# Standardní třídní organizace (24/25 sad):
class TestAuthorsPost:
    def test_create_author_success(self):
        ...
    def test_create_author_missing_name(self):
        ...

# L4-only pattern: API key auth (0 → 5/5)
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
```

---

## 14. Závěr

Claude Haiku 4.5 produkuje **strukturálně neobvyklé** (třídy, žádné fixtures), **sémanticky konzistentní** (stable signature tests) a **vysoce validní** (98.7–99.3 %) testovací sady s **kvalitativně rostoucí hloubkou** napříč úrovněmi kontextu — ale s **konstantní validitou** a se **systematickým slepým místem na rate-limit logice a admin doméně**.

Hlavní efekt přírůstku kontextu se neprojevuje v *zda* testy prochází (validity je vysoká od L0), ale v *kolik různých scénářů a status kódů* sada pokryje a *jak hluboko* asertuje. **L4 (in-context examples) je zlomový bod** pro adopci X-API-Key, orders domény a stylistických detailů (specifické názvy s kódy v suffixu).

Pro mezimodelovou komparaci je Claude **silným baseline** (high default validity, structured output) ale s **omezenou citlivostí na nárůst kontextu pro validity-based metriky**. Skutečné rozdíly se objeví v **assertion depth**, **status code diversity**, **scenario breadth** a **structural patterns** (tříd vs. funkce, fixtures vs. helpery).