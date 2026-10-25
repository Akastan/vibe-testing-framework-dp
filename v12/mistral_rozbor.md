# Mistral Large 2512 — Rozbor 25 testovacích sad

**Subjekt analýzy:** `mistral-large-2512`, API `bookstore`, 5 úrovní kontextu × 5 běhů = 25 sad
**Konfigurace:** `temperature=0.4`, `test_count=30`, `max_iterations=7`
**Zdroj:** `merged_test_suites_mistral.py` (9 866 řádků), `merged_test_suites_log_mistral.txt` (4 288 řádků), `experiment_diplomka_v12_20260415_220449.json` (25 záznamů), `coverage_mistral_v12.md` (24 coverage runů)

> Analýza zkoumá strukturní, sémantické a behaviorální charakteristiky vygenerovaných testovacích sad nezávisle na obsahu `ABOUT.md`. Cílem je popsat **co** Mistral testuje, **jak** to testuje a **jak** se jeho strategie mění s úrovní kontextu — připravit srovnávací podklad pro ostatní modely.

---

## 1. Souhrnná tabulka všech 25 sad

| Sada | Řádky | Tříd | Testů | Helpers | Asercí | AsrD | StCodes | Validity% | Iter | Pass | Cost ($) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0_run1 | 287 | **0** | 30 | 4 | 62 | 1.97 | 12 | 100.0 | 1 | ✓ | 0.0207 |
| L0_run2 | 308 | **0** | 30 | 7 | 57 | 1.70 | 12 | 100.0 | 1 | ✓ | 0.0218 |
| L0_run3 | 348 | **0** | 30 | 4 | 75 | 2.40 | 11 | 90.0 | 3 | ✗ | 0.0258 |
| L0_run4 | 296 | **0** | 30 | 5 | 55 | 1.70 | 12 | 93.3 | 3 | ✗ | 0.0259 |
| L0_run5 | 357 | **0** | 30 | 4 | 64 | 2.03 | 11 | 100.0 | 1 | ✓ | 0.0212 |
| L1_run1 | 382 | **0** | 30 | 5 | 84 | 2.67 | 10 | 100.0 | 1 | ✓ | 0.0306 |
| L1_run2 | 468 | **0** | 30 | 5 | 96 | 3.07 | 13 | 96.7 | 3 | ✗ | 0.0339 |
| L1_run3 | 308 | **0** | 30 | 4 | 70 | 2.23 | 10 | 100.0 | 1 | ✓ | 0.0356 |
| L1_run4 | 370 | **0** | 30 | 4 | 75 | 2.40 | 10 | 100.0 | 1 | ✓ | 0.0304 |
| L1_run5 | 369 | **0** | 30 | 4 | 77 | 2.47 | 10 | 100.0 | 1 | ✓ | 0.0304 |
| L2_run1 | 460 | **0** | 30 | 6 | 104 | 3.30 | 13 | 86.7 | 3 | ✗ | 0.0528 |
| L2_run2 | 443 | **0** | 30 | 6 | 103 | 3.27 | 13 | 96.7 | 3 | ✗ | 0.0517 |
| L2_run3 | 393 | **0** | 30 | 4 | 78 | 2.50 | 11 | 93.3 | 3 | ✗ | 0.0504 |
| L2_run4 | 474 | **0** | 30 | 6 | 112 | 3.57 | 13 | 90.0 | 3 | ✗ | 0.0529 |
| L2_run5 | 339 | **0** | 30 | 4 | 80 | 2.57 | 13 | 96.7 | 3 | ✗ | 0.0490 |
| L3_run1 | 524 | **0** | 30 | 5 | 99 | 3.17 | 13 | 96.7 | 3 | ✗ | 0.0524 |
| L3_run2 | 425 | **0** | 30 | 4 | 111 | 3.60 | 13 | 90.0 | 3 | ✗ | 0.0513 |
| L3_run3 | 516 | **0** | 30 | 6 | 110 | 3.50 | 13 | 90.0 | 3 | ✗ | 0.0530 |
| L3_run4 | 415 | **0** | 30 | 4 | 95 | 3.07 | 13 | 90.0 | 3 | ✗ | 0.0517 |
| L3_run5 | 387 | **0** | 30 | 5 | 96 | 3.07 | 13 | 83.3 | 3 | ✗ | 0.0520 |
| L4_run1 | 347 | **0** | 30 | 8 | 98 | 3.07 | 11 | 93.3 | 3 | ✗ | 0.0655 |
| L4_run2 | 453 | **0** | 30 | 5 | 117 | 3.77 | 10 | 96.7 | 3 | ✗ | 0.0667 |
| L4_run3 | 310 | **0** | 30 | 6 | 75 | 2.33 | 11 | 93.3 | 3 | ✗ | 0.0656 |
| L4_run4 | 389 | **0** | 30 | 7 | 102 | 3.23 | 13 | 86.7 | 3 | ✗ | 0.0664 |
| L4_run5 | 323 | **0** | 30 | 4 | 81 | 2.60 | 13 | 90.0 | 3 | ✗ | 0.0644 |

**Legenda:** `Cls` = počet top-level tříd, `AsrD` = průměrná hloubka asercí na test, `StCodes` = počet různých HTTP status kódů ověřovaných, `Iter` = počet iterací repair loopu, `Pass` = sada plně pasuje na konci pipeline.

**Klíčové agregáty:**
- Plan adherence (počet testů): **30/30 ve všech 25 sadách** (100% adherence)
- 100% pass rate na 1. iteraci: **7/25 sad** (28 %)
- Total experiment cost: **$1.122**, total tokens: **1 846 353**, total time: **66.2 min**
- Průměrný cost/sad: **$0.0449**
- L4/L0 cost ratio: **2.85×**

---

## 2. Strukturní analýza — proč Mistral nikdy nepoužívá třídy?

### 2.1 Dominantní pozorování (homogenní napříč všemi sadami)

**0 z 25 sad obsahuje top-level Python třídy.** Všechny testy jsou definovány jako **ploché funkce** na nejvyšší úrovni modulu. Toto je **deterministická** stylistická preference Mistral, naprosto opačná než u Claude (24/25 s třídami).

| Úroveň | Sady s třídami | Avg testů/sadu | Avg helperů/sadu | Avg řádků/sadu |
|---|---:|---:|---:|---:|
| L0 | 0 / 5 | 30 | 4.8 | 319.2 |
| L1 | 0 / 5 | 30 | 4.4 | 379.4 |
| L2 | 0 / 5 | 30 | 5.2 | 421.8 |
| L3 | 0 / 5 | 30 | 4.8 | 453.4 |
| L4 | 0 / 5 | 30 | 6.0 | 364.4 |

### 2.2 Konvence pojmenování testů (signature scenarios)

Bez tříd je jediným strukturním nositelem informace **název testovací funkce**. Mistral používá několik nápadných konvencí:

**Top 25 nejčastějších test names přes všech 25 sad:**

| Frekvence | Test name | Operace |
|---:|---|---|
| 23 | `test_update_author_with_valid_data` | PUT happy path |
| 19 | `test_delete_author_without_books` | DELETE pre-condition |
| 18 | `test_update_author_with_etag_mismatch` | PUT 412 |
| 18 | `test_restore_soft_deleted_book` | restore happy path |
| 17 | `test_get_nonexistent_author` | GET 404 |
| 17 | `test_create_book_with_valid_data` | POST happy path |
| 17 | `test_update_book_with_valid_data` | PUT happy path |
| 16 | `test_get_soft_deleted_book` | GET 410 |
| 15 | `test_get_existing_author` | GET happy path |
| 15 | `test_get_existing_book` | GET happy path |
| 15 | `test_upload_valid_cover_image` | POST cover |
| 15 | `test_apply_discount_to_new_book` | POST discount |
| 14 | `test_create_author_with_valid_data` | POST happy path |
| 14 | `test_restore_non_deleted_book` | restore error |
| 13 | `test_get_author_with_etag_not_modified` | GET 304 |
| 13 | `test_delete_author_with_books` | DELETE 409 |
| 13 | `test_apply_discount_to_eligible_book` | POST discount |
| 13 | `test_create_book_with_duplicate_isbn` | POST 409 |
| 12 | `test_list_books_with_filters` | GET filter |
| 11 | `test_apply_discount_exceeding_rate_limit` | POST 429 |

Mistral má rozpoznatelný **stable mental model** pro CRUD pattern. 64 % sad sdílí ≥10 z těchto signature testů, což připomíná Claude — ale **bez třídního strukturování**.

### 2.3 Granulární test-name styling per úroveň

Test name patterns dramaticky kolísají s úrovní:

| Pattern | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| `_returns_NNN` (např. `_returns_404`) | **54** | 18 | 0 | 0 | 0 |
| `_happy_path` suffix | 0 | 0 | 0 | 0 | **15** |
| `_with_*` pattern | 72 | 80 | 60 | 65 | 38 |
| `_invalid_*` | 11 | 10 | 4 | 11 | 6 |
| `_duplicate_*` | 0 | 8 | 9 | 11 | 9 |
| `_nonexistent_*` | 7 | 6 | 5 | 5 | 5 |

**Klíčová zjištění:**

1. **Dramatický posun stylu pojmenování s kontextem:**
   - **L0:** Mistral preferuje **`_returns_NNN` suffix** (status code v názvu) — 54 výskytů
   - **L1:** Tendence částečně přežívá (18 výskytů)
   - **L2-L3:** Úplně mizí (`_returns_NNN` = 0)
   - **L4:** Místo toho se objevuje **`_happy_path` suffix** (z příkladů v `existing_tests.py`) — 15 výskytů, exkluzivně v L4_run1

2. **L0_run4 je extrém: 30/30 testů má `_returns_NNN` suffix.** Je to úplně dominantní styl bez ohledu na refaktoring.

3. **`_happy_path` exkluzivně v L4_run1** — tj. jen 1 ze 5 L4 sad přijala tento pattern z příkladů. Mistral je na in-context style learning **slabší než Claude**.

### 2.4 Žádné prázdné kostry

Protože Mistral nepoužívá třídy, **nemůže mít prázdné třídy**. Všech 25 sad má **30/30 funkčních testů**, žádné kostry, žádný over-planning. Toto je **strukturní výhoda** oproti Claude, který má 16 % sad s prázdnými třídami.

---

## 3. Helper funkce — striktní jádro + adaptace s kontextem

### 3.1 Standardizovaná knihovna helperů

**Frekvence helperů přes 25 sad:**

| Frekvence | Helper | Účel |
|---:|---|---|
| 25 / 25 | `unique(prefix)` | Generování unikátního stringu (`uuid.uuid4().hex[:8]`) |
| 25 / 25 | `create_author()` | POST /authors |
| 25 / 25 | `create_category()` | POST /categories |
| 25 / 25 | `create_book()` | POST /books (s automatickým vytvořením autora + kategorie) |
| 14 / 25 | `create_tag()` | POST /tags |
| 8 / 25 | `create_order()` | POST /orders |
| 2 / 25 | `reset_db()` | POST /reset (jen L4_run1, L4_run4) |
| 1 / 25 | `create_review()` | POST /books/{id}/reviews (jen L0_run2) |
| 1 / 25 | `setup_book_with_deps()` | Composite helper (jen L4_run1) |

**Klíčová zjištění:**

1. **Univerzální 4-helper jádro** (unique, create_author, create_category, create_book) je shodné s Claude — reprezentuje **konvergentní přístup ke generování testovací knihovny**.

2. **`create_tag` adopce roste s kontextem:** L0 = 2/5, L1-L3 = 2-3/5, L4 = 4/5. Mistral postupně rozpoznává tag jako primární zdroj.

3. **`create_order` má bimodální distribuci:** přítomna v 8/25 sad, ale pouze v některých L2/L3/L4 — Mistral ji zařadí, jen když plánuje testovat orders doménu.

4. **L4_run1 je nejbohatší** (8 helperů) — obsahuje navíc `reset_db()` a `setup_book_with_deps()`. Toto je výsledek in-context learning z `existing_tests.py`.

### 3.2 Asertivní helpery (defensive guards)

**100 % helperů ve všech 25 sadách** končí defenzivním guard assert:

```python
assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
return response.json()
```

Toto je shodné s Claude — sdílený best-practice pattern.

### 3.3 Co Mistral NEPOUŽÍVÁ

| Feature | Výskyt | Komentář |
|---|---:|---|
| `@pytest.fixture` | **0/25** | Žádné fixtures |
| `@pytest.mark.parametrize` | **0/25** | Žádná parametrizace |
| `@pytest.mark.skip` / `xfail` | 0/25 | Žádné skipy |
| `setup_method` / `teardown_method` | 0/25 | Žádné setup/teardown |
| `yield` v testech | 0/25 | Imperativní setup |
| `conftest.py` | 0/25 | Žádné collect-time hooks |
| `pytest.raises` | 0/25 | Žádné except expectations |
| `/reset` endpoint | **1/25** | Pouze L4_run1 (po vzoru existing_tests.py) |

To je **identický pytest non-idiomatický profil** jako Claude — oba modely:
- Preferují **imperativní setup uvnitř každého testu** přes helper-volání
- Dosahují **test independence** přes uuid-based unique identifiers, ne přes fixture cleanup
- Generují **redundantní API volání** (DRY oběť pro jednoduchost)

### 3.4 Type annotations — paradoxní vzorec

Mistral má **U-shaped typing pattern** napříč úrovněmi:

| Úroveň | Typed helpers | Untyped helpers | Pozn. |
|---|---:|---:|---|
| L0 | **20** | 4 | Většina helperů má `-> Dict[str, Any]` |
| L1 | 0 | 22 | Úplně mizí typing |
| L2 | 0 | 26 | Stále bez typing |
| L3 | 0 | 24 | Stále bez typing |
| L4 | 7 | 23 | Částečný comeback (`Optional[str]`) |

**Hypotéza:** L0 vidí pouze OpenAPI specifikaci a snaží se být "produkčně robustní" — proto typing jako defenzivní mechanismus. S přidáním dokumentace L1 si Mistral uvědomí, že stačí prostý styl. L4 importuje `from typing import Optional` z některých příkladů.

---

## 4. Importy — minimalismus s kontextovými rozdíly

| Modul | Frekvence (z 25) | Komentář |
|---|---:|---|
| `uuid` | 25 | Universal |
| `requests` | 25 | Universal |
| `pytest` | **20** | Chybí v 5 sadách (všechny L4 + L4_run3 chybí) |
| `datetime` | **14** | Roste s kontextem (L0=1, L1=5, L2=5, L3=3, L4=0) |
| `time` | 9 | Pro rate-limit testy |
| `typing` | **5** | Pouze L0 a L4 |
| `PIL.Image` | **0** | Mistral nikdy nepoužívá PIL (kontrast s Claude 2/25) |

**Pozoruhodné:**

- **`pytest` v L4 chybí v 5/5 sadách** — Mistral si uvědomí, že žádný pytest decorator nepoužívá, takže import je redundantní. Tato optimalizace je signifikantní (Claude měl pytest v 24/25 sadách).
- **`datetime` peakuje na L1-L2** — Mistral využívá dokumentaci/zdrojový kód k testování `published_year` validace (current year ± offset).
- **`typing` zmizí v L1-L3** — viz sekce 3.4. L4 částečný comeback.
- **Žádný PIL import** — Mistral pro upload testů generuje **inline byte sekvence** nebo zapisuje **fyzické soubory na disk** (`open(...wb...)`), nikdy nepoužívá generování JPEG dat.

---

## 5. Co se testuje — sémantické pokrytí

### 5.1 Doménové pokrytí (kolik z 5 sad na úrovni odkazuje na doménu)

| Doména | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| `health` | 5/5 | 4/5 | 0/5 | 0/5 | 2/5 |
| `authors` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `categories` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `books` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `tags` | 2/5 | 2/5 | 3/5 | 3/5 | 4/5 |
| `orders` | 1/5 | 0/5 | 3/5 | 1/5 | 3/5 |
| `reviews` | 1/5 | 1/5 | 3/5 | 4/5 | 5/5 |
| `admin` | 0/5 | 0/5 | 0/5 | 0/5 | **0/5** |
| `cover` | 4/5 | 1/5 | 4/5 | 5/5 | 2/5 |
| `discount` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| `stock` | 0/5 | 1/5 | 5/5 | 5/5 | 4/5 |
| `restore` | 5/5 | 4/5 | 4/5 | 2/5 | 5/5 |
| `maintenance` | 0/5 | 0/5 | 0/5 | 0/5 | **0/5** |

**Klíčová zjištění:**

1. **Admin doména je completely untested** napříč všemi 25 sadami (shodné s Claude).
2. **Maintenance mode (503) nikdy netestován** napříč 25 sadami (shodné s Claude).
3. **`health` doména paradoxně klesá:** L0/L1 = 5/4, L2-L3 = 0. Mistral si po zpřístupnění zdrojového kódu uvědomí, že `/health` není "podstatný" a vynechá ho. L4 se s 2/5 částečně vrací.
4. **`reviews` plynule roste** L0/L1 = 1, L2 = 3, L3 = 4, L4 = 5/5 — jediná doména s **monotonním zlepšením s kontextem**.
5. **`stock` skok L1→L2 z 1/5 na 5/5** — zpřístupnění zdrojového kódu odhalí PATCH endpoint.
6. **`orders` má erratickou trajektorii** (1/5, 0/5, 3/5, 1/5, 3/5) — Mistral na ni nemá konzistentní strategii.

### 5.2 Pokrytí scénářů (počet sad z 5 na úrovni s ≥ 1 testem na scénář)

| Scénář | L0 | L1 | L2 | L3 | L4 | Komentář |
|---|---:|---:|---:|---:|---:|---|
| ETag conditional GET (304) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno už na L0 |
| ETag mismatch (412) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Soft delete + restore | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Validation 422 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Discount logic | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | Saturováno |
| Pagination | 4/5 | 5/5 | 0/5 | 1/5 | 0/5 | **Klesá od L2** |
| Duplicate key (409) | **0/5** | 5/5 | 5/5 | 5/5 | 5/5 | **L0→L1 skok** |
| Rate limit (429) | 5/5 | 1/5 | 5/5 | 5/5 | 4/5 | L1 dip, comeback |
| Reviews | 1/5 | 1/5 | 3/5 | 4/5 | 5/5 | Plynulý růst |
| Cover upload (multipart) | 4/5 | 1/5 | 4/5 | 5/5 | 2/5 | Erratický |
| Stock manipulace | 0/5 | 1/5 | 5/5 | 5/5 | 4/5 | **L2 skok** |
| Search/filter | 4/5 | 2/5 | 0/5 | 3/5 | 0/5 | Erratický |
| Authentication X-API-Key | 1/5 | 1/5 | 1/5 | 3/5 | **5/5** | Postupný růst |
| Tags M:N | 0/5 | 0/5 | 1/5 | 1/5 | 0/5 | Téměř nikdy |
| Idempotency | 0/5 | 0/5 | 0/5 | 0/5 | **0/5** | Nikdy netestováno |
| Concurrent / race | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | Nikdy netestováno |
| Maintenance mode (503) | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | Nikdy netestováno |

### 5.3 Tři klíčové „kontextové prahy" Mistral

#### Práh L0→L1 (přidání dokumentace):
- **Aktivuje conflict detection (409)** — 0/5 → 5/5 (dramatic shift, jasně z dokumentace)
- **Aktivuje stock manipulaci** (0/5 → 1/5)
- **Deaktivuje rate limit testy** (5/5 → 1/5) — Mistral nahrazuje pokus o testování problematického scénáře jiným
- **Pagination zůstává stabilní** (4/5 → 5/5)

#### Práh L1→L2 (přidání zdrojového kódu):
- **Aktivuje stock manipulaci masivně** (1/5 → 5/5) — endpoint je teď viditelný
- **Aktivuje rate limit zpět** (1/5 → 5/5) — Mistral najde rate limit logiku ve zdrojovém kódu
- **Aktivuje cover upload** (1/5 → 4/5)
- **Aktivuje reviews** (1/5 → 3/5)
- **Pagination paradoxně mizí** (5/5 → 0/5) — vytlačována novějšími scénáři
- **Skok hloubky asercí** AsrD 2.57 → 3.04 (+18 %)

#### Práh L2→L3 (přidání DDL):
- **Reviews dále roste** (3/5 → 4/5)
- **Cover upload se stabilizuje** (4/5 → 5/5)
- **Authentication začíná růst** (1/5 → 3/5)
- **Restore klesá** (4/5 → 2/5) — paradox

#### Práh L3→L4 (přidání in-context examples):
- **Aktivuje X-API-Key autentizaci masivně** — 3/5 → 5/5
- **Reviews konečně 5/5**
- **Stock zůstává vysoký** (4/5)
- **Pagination úplně mizí** (1/5 → 0/5)
- **Cover upload klesá** (5/5 → 2/5) — vytlačován autentizací a orders

### 5.4 Tests exclusive to each level (signal for in-context learning)

| Level | Exclusive count | Vzor |
|---|---:|---|
| L0 | **38** | `_returns_NNN` styl, generic CRUD názvy |
| L1 | 12 | Convergentní (z dokumentace) |
| L2 | 22 | M:N / tags / clone scénáře |
| L3 | 19 | Duplicate name scénáře, clone tests |
| L4 | **47** | `_happy_path` styl, specific status codes |

**Diverzita L4 je vysoká (47 exkluzivních testů)** — Mistral umí vygenerovat širší prostor scénářů s příklady, **ALE** za cenu validity (viz sekce 7).

---

## 6. Jak se testuje — taktická úroveň

### 6.1 Distribuce HTTP status kódů ověřených v asercích

| Code | L0 | L1 | L2 | L3 | L4 | Význam |
|---:|---:|---:|---:|---:|---:|---|
| 200 | 67 | 63 | 53 | 60 | 72 | OK |
| 201 | 9 | 15 | **21** | 23 | 9 | Created |
| 204 | 14 | 10 | 14 | 9 | **20** | No Content |
| 304 | 5 | 5 | 6 | 5 | 5 | Not Modified |
| 400 | 5 | 10 | 13 | 12 | 13 | Bad Request |
| 404 | 8 | 10 | 11 | 11 | 10 | Not Found |
| 405 | **3** | 0 | 0 | 0 | 0 | Method Not Allowed (jen L0!) |
| 409 | **0** | 14 | 13 | 16 | 14 | Conflict — **L0→L1 skok** |
| 410 | 14 | 16 | 17 | 8 | 11 | Gone |
| 412 | 8 | 5 | 5 | 5 | 5 | Precondition Failed |
| 413 | 3 | 1 | 4 | 5 | 2 | Payload Too Large |
| 415 | 2 | 1 | 4 | 5 | 2 | Unsupported Media Type |
| 422 | 20 | 14 | 7 | 16 | 8 | Unprocessable Entity |
| 429 | 6 | 1 | 6 | 5 | 4 | Too Many Requests |
| **Diverzita** | **13** | **13** | **13** | **13** | **13** | Unique codes per level |

**Pozoruhodné:**

- **Diverzita status kódů je naprosto plochá** — 13 unique codes na všech úrovních. **Žádný kontextový gradient v diverzitě** — kontrast s Claude (9 → 13).
- **405 Method Not Allowed pouze v L0** — Mistral hledá "exotické" status kódy bez kontextu, pak je s lepším kontextem opouští.
- **409 Conflict skok L0→L1: 0 → 14** — dramatic jump, dokumentace odhalí unique constraints.
- **422 Validation peakuje na L0 (20)** — bez kontextu Mistral spamuje validation tests, s kontextem rozliší přesnější scénáře.

### 6.2 Distribuce testovacích typů (z metrics JSON)

| Úroveň | Happy% | Error% | Edge% |
|---|---:|---:|---:|
| L0 (avg) | 56.0 | 41.3 | 2.7 |
| L1 (avg) | 53.3 | 43.3 | 3.3 |
| L2 (avg) | 45.3 | 49.3 | **5.3** |
| L3 (avg) | 48.7 | 48.7 | 2.7 |
| L4 (avg) | 50.7 | 43.3 | **6.0** |

**Trend:** **Happy path klesá, error roste s kontextem.** Mistral se s rostoucím kontextem stává „kritičtější" (shodné s Claude, ale plošší gradient). Edge cases peakují na L2 a L4 (5-6%).

### 6.3 Patterny asercí (raw count přes všechny sady na úrovni)

| Pattern | L0 | L1 | L2 | L3 | L4 | Trend |
|---|---:|---:|---:|---:|---:|---|
| `status_code ==` | 164 | 165 | 174 | 180 | 175 | Stabilní |
| `status_code in (...)` | 19 | 17 | 21 | 19 | 22 | Mírně roste |
| `"key" in <obj>` | 47 | **87** | 87 | **116** | 76 | **L0→L1 +85 %** |
| `<obj>["key"] == X` | 45 | 78 | **116** | **134** | 95 | **Plynulý růst, peak L3** |
| `isinstance(...)` | 11 | 10 | **0** | 3 | 7 | **L1→L2 propad** |
| `len(...)` | 6 | 14 | 4 | 15 | 13 | Erratický |
| `>=, <=, < x, > x` | 8 | 14 | 5 | 9 | 7 | Nestabilní |
| `response.headers` | 6 | 14 | 11 | 8 | 8 | Roste s ETag/Retry-After |
| `response.json()` | 101 | 129 | 157 | 164 | 178 | **Monotonní růst** |
| `.text` | 23 | 17 | 21 | 25 | 22 | Stabilní |

**Mimořádně signifikantní pozorování:**

1. **`key in data` skok L0→L1: 47 → 87 (+85 %)** — již dokumentace stačí Mistralovi k naučení Pydantic field names. To je dramatický kontrast s Claude, kde stejný skok nastal až na L1→L2.

2. **`<obj>["key"] == X` peak na L3 (134)** — DDL přidává konkrétní hodnoty pro testování (např. `is_deleted is False`, `published_year`).

3. **`isinstance(...)` na L2 = 0** — Mistral po zpřístupnění zdrojového kódu úplně opouští defenzivní typové kontroly. Při L4 se 7× vrací (z příkladů?).

4. **`response.json()` monotonní růst** 101 → 178 — Mistral kontextem stále intenzivnější body validation.

### 6.4 Response validation (% testů s body checkem)

| Úroveň | Avg response_validation% |
|---|---:|
| L0 | **44.7 %** |
| L1 | 70.0 % |
| L2 | 89.3 % |
| L3 | **92.7 %** |
| L4 | 90.0 % |

**Toto je nejvýraznější monotonně rostoucí metrika Mistralu.** L0→L3 je +48 procentních bodů — ze 44.7 % na 92.7 %. **L4 mírně klesá** (kvůli refaktoringu pod vlivem příkladů, viz sekce 8.2).

### 6.5 Velikost testů a celých sad

| Úroveň | Avg lines (suite) | Avg lines (test) | Avg asercí | Avg helpers |
|---|---:|---:|---:|---:|
| L0 | 319.2 | **5.5** | 62.6 | 4.8 |
| L1 | 379.4 | 7.0 | 80.4 | 4.4 |
| L2 | 421.8 | **7.9** | 95.4 | 5.2 |
| L3 | **453.4** | 7.0 | 102.2 | 4.8 |
| L4 | 364.4 | 5.7 | 94.6 | 6.0 |

**Inverted-U shape v délce testů:** L0 (terse) → L2 (verbose, peak 7.9 lines/test) → L4 (zpět k 5.7 lines/test).

**Asertivní hloubka monotonně roste do L3:** 62.6 → 102.2 (+63 %), pak mírně klesá v L4.

### 6.6 Variable naming convention switch

Mistral mění **konvenci pojmenování proměnných** s kontextem:

| Úroveň | `response = requests.X(...)` | `r = requests.X(...)` |
|---|---|---|
| L0 (5/5) | **5/5** verbose | 0/5 |
| L1 (5/5) | **5/5** verbose | 0/5 |
| L2 (5/5) | 4/5 | 1/5 (L2_run1) |
| L3 (5/5) | 4/5 | 1/5 (L3_run5) |
| L4 (5/5) | **0/5** | **5/5** terse |

**Toto je strikingly konzistentní stylistický posun:** Při větším kontextu si Mistral uvědomí, že **`r`** je idiomatičtější (vidí to v `existing_tests.py` na L4 a začne to používat). L0/L1 vždy verbose `response = ...`.

### 6.7 TIMEOUT konvence

Mistral má dvě konkurenční konvence pro timeout:
- **Konstanta `TIMEOUT = 30`** + `timeout=TIMEOUT`: 14/25 sad
- **Inline `timeout=30`**: 11/25 sad
- L4 přechází k inline (jen 3/5 L4 sad používá konstantu)

Tento drift je důsledkem **in-context learning** — `existing_tests.py` používá inline timeout.

### 6.8 Side-effect verification (chained GET after write)

| Úroveň | Avg HTTP calls per test | Side-effect check % | Chaining % |
|---|---:|---:|---:|
| L0 | 1.23 | 8.7 | 0.0 |
| L1 | 1.32 | 13.3 | 0.0 |
| L2 | 1.34 | 12.0 | 0.0 |
| L3 | 1.29 | 10.7 | 2.0 |
| L4 | **1.31** | 16.0 | **35.3** |

**L4 má dramatický skok v chaining %:** 0-2 % na L0-L3 → 35.3 % na L4. Mistral vidí v příkladech vzor "vytvoř, modifikuj, ověř GETem" a začne ho replikovat masivně. **L4_run5 dokonce 73.3 % chaining!**

### 6.9 Docstrings — Mistral je zcela bez docstringů

| Úroveň | Sady s ≥1 docstringy |
|---|---:|
| L0 | **0/5** |
| L1 | 0/5 |
| L2 | 0/5 |
| L3 | 0/5 |
| L4 | 0/5 |

**0 docstringů ve všech 25 sadách.** Mistral nikdy nepřipisuje testům docstring — ani na L0, kde Claude jich má 30+. Toto je **silný kontrast** vůči Claude (5/5 sad na L0 měly ≥30 docstringů).

---

## 7. Validita a repair loop

### 7.1 Souhrnná validita

| Úroveň | Avg validity | 100% sad | Avg iterací | Suites s 1-shot pasem |
|---|---:|---:|---:|---:|
| L0 | **96.67 %** | 3/5 | 2.20 | 3/5 |
| L1 | **99.33 %** | 4/5 | 1.40 | 4/5 |
| L2 | 92.67 % | 0/5 | 3.00 | 0/5 |
| L3 | 90.00 % | 0/5 | 3.00 | 0/5 |
| L4 | 92.00 % | 0/5 | 3.00 | 0/5 |

**Klíčová zjištění:**

1. **Validita má inverted-U shape:** **peak na L1** (99.33 %), **propad od L2** (92.67 % → 90.00 % na L3), L4 mírně se zvedá (92 %).
2. **L1 je "sweet spot" pro Mistral** — dokumentace dodá kontext bez příliš mnoha komplikujících detailů.
3. **L2 dramatický propad validity** (99.33 % → 92.67 %) — zpřístupnění zdrojového kódu **paradoxně zhoršuje výsledky**. Mistral si na L2 začne vytvářet testy podle vzorů ze zdroje, které pak v reálu selhávají kvůli edge case detailům.
4. **0/5 sad na L2-L4 dosahuje 100 % validity** — od L2 dál potřebuje **každá** sada repair loop.

### 7.2 Iterations a první-shot pass rate

| Úroveň | First-shot pass rate% | Self-correction rate% | Convergence |
|---|---:|---:|---|
| L0 | 96.7 (avg) | 0 % | 1-3 iter |
| L1 | 99.3 (avg) | 0 % | 1-3 iter |
| L2 | 92.7 (avg) | 0 % | **3 iter všechny** |
| L3 | 90.0 (avg) | 0 % | **3 iter všechny** |
| L4 | 91.9 (avg) | **20 % (1 sada)** | **3 iter všechny** |

**Self-correction rate je 0 % všude kromě L4_run4** (20 %, 1 fixed test). To znamená, že **repair loop u Mistral téměř neopravuje testy** — jen je validuje, že další iterace nezhoršuje stav.

### 7.3 Anatomie selhání

**Typologie selhání (z `failure_taxonomy`):**

| Kategorie | Total výskyt napříč 25 sadami | Komentář |
|---|---:|---|
| `wrong_status_code` | **21** | Test očekává jiný kód, než API vrátí |
| `other` | 16 | Pestrý mix: KeyError, FileNotFoundError, helper failures |
| `assertion_value_mismatch` | 8 | Aserce na konkrétní hodnotu selže |

**Per-level failure distribution:**

| Level | wrong_status_code | other | assertion_value_mismatch |
|---|---:|---:|---:|
| L0 | 2 | 3 | 0 |
| L1 | 0 | 0 | 1 |
| L2 | 6 | 4 | 1 |
| L3 | 9 | 3 | 3 |
| L4 | 4 | 6 | 3 |

**Top 10 nejvíce selhávajících testů (`never_fixed_tests`):**

| Frekvence | Test name | Pattern selhání |
|---:|---|---|
| 9 | `test_restore_soft_deleted_book` | **`KeyError: 'is_deleted'`** — pole neexistuje v response |
| 5 | `test_apply_discount_exceeding_rate_limit` | Status code mismatch (200 vs 429) |
| 3 | `test_apply_discount_to_eligible_book` | Status code mismatch |
| 3 | `test_apply_discount_rate_limit_exceeded` | Status code mismatch |
| 2 | `test_delete_author_with_associated_books` | Wrong status |
| 2 | `test_apply_discount_to_new_book` | Status mismatch |
| 2 | `test_create_author_duplicate_name` | Status mismatch |
| 2 | `test_delete_author_with_books` | Status mismatch |

**Kritická pozorování:**

1. **`test_restore_soft_deleted_book` selže 9× kvůli `KeyError: 'is_deleted'`** — Mistral konzistentně předpokládá, že restore endpoint vrátí pole `is_deleted` v JSON, ale API jej nevrací. Toto je **systematická hallucinace polí**, kterou Mistral nikdy neopraví.

2. **Rate-limit testy systematicky selhávají** (5+3+3 = 11 výskytů) — shodný pattern jako Claude. Mistral zaměňuje 200 a 429 v assertion.

3. **Conceptual bugs unikátní pro Mistral:**
   - **L4_run4 `test_create_author_valid_data`:** Helper `create_author(name=name, ...)` vrátí dict s `name = unique("...")` (s suffixem), ale test pak asseruje `data["name"] == name`. Ale **`name` proměnná v testu je odlišná hodnota než v helperu** — `name = "George Orwell"` ale helper přidá `_xxxxxxxx`. Selhání: `'George Orwell_0c089e6b' == 'George Orwel...lish novelist'`.
   - **L4_run4 `test_create_book_valid_data`:** `isbn=unique("ISBN")[:13]`, pak `assert book["isbn"] == unique("ISBN")[:13]` — **dvojí volání `unique()` generuje různé hash hodnoty**. Klasický race-condition self-contradicting test.
   - **L3_run5 `test_create_book_with_duplicate_isbn`:** `book2 = create_book(...)` ALE helper `create_book` má guard `assert response.status_code in (200, 201)` — takže 409 conflict je raisován v helperu, ne v testu. Pak test asseruje `book2.status_code == 409` — ale `book2` je dict, ne response. **Helper return-value misuse.**

### 7.4 KeyError 'is_deleted' — systémový bug

Mistral generuje aserce typu `assert data["is_deleted"] is False` v 9 sadách, ale API vrací response **bez** klíče `is_deleted`. Sady s tímto problémem: L2_run1, L2_run3, L2_run4, L2_run5, L3_run4, L3_run5, L4_run1, L4_run3, L4_run4. Toto je **systematická chyba** která přežívá všechny iterace repair loopu.

### 7.5 Doba běhu

Průměrná doba běhu jedné sady (poslední iterace pytestu): **1.5–4.7 sekundy**.

| Úroveň | Avg pytest time | Min-Max |
|---|---:|---|
| L0 | 1.78s | 1.57-2.03 |
| L1 | 1.99s | 1.37-2.57 |
| L2 | **3.65s** | 2.41-4.59 |
| L3 | **3.21s** | 1.81-4.66 |
| L4 | 2.16s | 1.58-2.49 |

**L2 a L3 jsou pomalejší** kvůli rate-limit testům, které musí provést 5+ POST volání s `time.sleep()` na vyvolání 429.

### 7.6 Self-diagnostic comments at file top — Mistral signature

**18 z 19 sad, které potřebovaly repair loop, má NL komentáře na vrcholu souboru** — Mistral „myslí nahlas" a tyto myšlenky se vyleakují do výsledného kódu.

Příklad z **L4_run5**:
```
# The main issues are:
# 1. Missing API key in create_category and create_book helpers (required by some endpoints)
# 2. Potential string length issues with unique() function for ISBN (13 chars max)
# 3. Missing /categories endpoint in the API spec (should be /categories not /categories/)
```

Příklad z **L0_run3**:
```
# Main issues: 1) ISBN generation might exceed length limits 2) Missing required fields ...
# Fixes: 1) Ensure ISBN length is within API limits 2) Add all required fields to payloads ...
```

| Iter count | Sady s NL komentáři | Sady bez komentářů |
|---|---:|---:|
| 1 (no repair) | 0/7 | 7/7 |
| 3 (repair) | **17/18** | 1/18 (L4_run1) |

**Toto je behaviorální podpis Mistralu** — leakage internal reasoning artefaktů do produkovaného kódu. Žádný jiný model v experimentu by to pravděpodobně nedělal (Claude má vždy clean output bez meta-komentářů). Toto je **diagnostický feature** signalizující, že Mistral generuje kód v "thinking aloud" módu, kde myšlenkový proces o předchozí iteraci přežívá do nového výstupu.

---

## 8. Variabilita — jak konzistentní je Mistral napříč běhy?

### 8.1 Jaccard similarity test names v rámci úrovně

| Úroveň | Avg pairwise Jaccard | Testy společné všem 5 běhům | Sjednocení testů |
|---|---:|---:|---:|
| L0 | 0.324 | **1** | 72 |
| L1 | 0.390 | 5 | 63 |
| L2 | 0.355 | 5 | 66 |
| L3 | **0.406** | **9** | 64 |
| L4 | **0.148** | 3 | **82** |

**Klíčové zjištění (kontrast s Claude):**

- **L0 má jen 1 test společný všem 5 běhům** — Mistral má vyšší variabilitu už od L0 než Claude (10 testů společných). Mistral je „kreativnější" bez kontextu, ale méně konzistentní.
- **L3 je naopak NEJVÍCE konvergentní** (9 společných testů, Jaccard 0.406) — DDL přidává jasné cíle (`is_deleted`, `created_at`...) a Mistral se na ně sjednocuje.
- **L4 dramaticky diverguje** (Jaccard 0.148, 82 unique tests) — příklady otevírají velký prostor scénářů (shodné s Claude, který má 0.148 také).
- **Total unique test names: 209** napříč všech 25 sadami (Claude ~150-180?).

### 8.2 L4 a in-context learning — tříbarevný profil

L4 sady se dělí do tří „rodin":

**Rodina 1 (purist):** L4_run1 — masivně používá `_happy_path` suffix (15× v jediné sadě), `setup_book_with_deps` helper, `reset_db()`, perfect mimicry of `existing_tests.py`. **Validity 93.3 %**, žádné self-diagnostic komentáře.

**Rodina 2 (hybrid):** L4_run2, L4_run3 — používají `r = requests.X(...)`, X-API-Key auth, ale ne `_happy_path` styling. Self-diagnostic komentáře přítomné. **Validity 96.7 %, 93.3 %**.

**Rodina 3 (broken):** L4_run4, L4_run5 — conceptual bugs (unique() race conditions), self-contradicting asserts. **Validity 86.7 %, 90 %**.

To znamená, že **stejný kontext L4 produkuje 3 různé výstupní strategie** — Mistral je málo deterministický.

### 8.3 Příklady scénářů exkluzivních pouze pro L4

Test names výhradně v L4 (z 47 unikátních):

- `test_apply_discount_happy_path`
- `test_apply_discount_rate_limit_exceeded`
- `test_create_author_happy_path`
- `test_create_book_happy_path`
- `test_restore_book_happy_path`
- `test_update_stock_happy_path`
- `test_decrease_stock_below_zero_bad_request`

Tyto názvy obsahují přesný status code (`bad_request`) nebo `_happy_path` suffix — kopírují styl `existing_tests.py`. **Kvalitativní stopa in-context learning**, ale je to jen **1/5 L4 sad** (vs Claude, kde je adoption širší).

### 8.4 Příklady scénářů exkluzivních pouze pro L0

Z 38 unikátních L0-only testů:

- `test_apply_discount_exceeding_rate_limit_returns_429` (verbose `_returns_NNN`)
- `test_create_author_with_invalid_born_year_returns_422`
- `test_create_book_missing_required_field`
- `test_apply_valid_discount_to_book`

Většinou s `_returns_NNN` suffixem nebo generičtěji formulované — **bez konkrétních příkladů Mistral cílí na status codes přímo v názvu**.

---

## 9. Endpoint coverage — analýza pokrytí API

### 9.1 Endpoint coverage per level

| Úroveň | Avg covered_endpoints | Range | Pokrytí % |
|---|---:|---|---:|
| L0 | **14/50** | 14-14 | 28.0 % |
| L1 | 13.8/50 | 13-14 | 27.6 % |
| L2 | 13.4/50 | 12-15 | 26.8 % |
| L3 | 12.6/50 | 12-13 | 25.2 % |
| L4 | **15.4/50** | 13-18 | 30.8 % |

**Pozoruhodný U-shape:** L0 = 28 %, dna na L3 (25.2 %), peak na L4 (30.8 %). Toto je **opačný trend** než u Claude (kde endpoint coverage saturuje brzy).

**Pravděpodobné vysvětlení:** Mistral se s každou další úrovní kontextu **soustředí na hloubku** (více asercí na endpoint) místo šířky (víc endpointů). L4 příklady ho přimějí pokrýt širší prostor.

### 9.2 Endpointy nikdy netestované (25/25 sad)

26 endpointů nepokrytých nikdy:

```
DELETE /books/{book_id}/cover, DELETE /books/{book_id}/tags
DELETE /orders/{order_id}, DELETE /tags/{tag_id}
GET /admin/maintenance, GET /authors/{author_id}/books
GET /books/{book_id}/cover, GET /catalog
GET /categories/{category_id}, GET /exports/{job_id}
GET /orders, GET /orders/{order_id}, GET /orders/{order_id}/invoice
GET /statistics/summary, GET /tags, GET /tags/{tag_id}
PATCH /orders/{order_id}/status, POST /admin/maintenance
POST /exports/books, POST /exports/orders, POST /orders
POST /orders/{order_id}/items, POST /reset
POST /tags, PUT /categories/{category_id}, PUT /tags/{tag_id}
```

**Slepá místa:**
- **Admin** (statistika, maintenance, exports) — **0 % pokrytí**
- **Orders** — Mistral občas **vytvoří helper** `create_order`, ale neprovádí GET/DELETE/PATCH na orders endpointy
- **Tags** — referencuje `/books/{id}/tags`, ale netestuje POST/PUT/GET/DELETE na samotné `/tags`
- **Categories** — má pouze POST a vzácně PUT/DELETE
- **Catalog** — deprecated endpoint nikdy netestován

### 9.3 Endpoints podmíněně pokryté

Endpoints s nestabilním pokrytím:

| Endpoint | Pokryto v % sad |
|---|---:|
| POST /books/{book_id}/restore | 80 % (20/25) |
| PUT /books/{book_id} | 80 % |
| DELETE /books/{book_id} | 76 % |
| GET /books | 72 % |
| POST /books/{book_id}/cover | 64 % |
| PATCH /books/{book_id}/stock | 60 % |
| GET /authors | 56 % |
| POST /books/{book_id}/reviews | 52 % |
| POST /categories | 52 % |
| GET /health | 44 % |

---

## 10. Code coverage analýza (z `coverage_mistral_v12.md`)

24 coverage runů (chybí L3_run5).

### 10.1 Průměrné pokrytí podle úrovní

| Úroveň | Celkový průměr | `app/crud.py` | `app/main.py` |
|---|---:|---:|---:|
| L0 | 66.86 % | 36.64 % | 69.66 % |
| L1 | 66.54 % | 37.21 % | 67.83 % |
| L2 | **67.99 %** | **39.17 %** | **70.21 %** |
| L3 | 67.05 % | 37.14 % | 69.64 % |
| L4 | 67.77 % | **39.59 %** | 68.91 % |

**Klíčová zjištění:**

1. **`__init__.py`, `database.py`, `models.py`, `schemas.py` mají 100 % coverage napříč všemi 24 runs** — testy efektivně inicializují aplikaci a používají DB.

2. **Code coverage je v podstatě plochá** — rozdíl L0 vs L2 je jen +1.13 procentního bodu (66.86 → 67.99). Hypotéza RQ2 o ostrém skoku na L2 **NENÍ podpořena** Mistralem.

3. **`crud.py` coverage rostou s kontextem do L2 a L4** — peak L4 (39.59 %), L0 nejnižší (36.64 %). Nárůst +3 procentní body, ale stále pod 40 %.

4. **`main.py` coverage erratický** — peak na L0 (69.66 %), dno na L1 (67.83 %). Mistral na L1 paradoxně pokrývá méně main.py.

5. **Celkový coverage 65-71 %** — strop daný API doménami, které Mistral nikdy netestuje (admin, orders, tags, exports, maintenance).

### 10.2 Maximální výkonnost code coverage

L2_run1 dosáhl **70.96 % overall, 44.70 % crud.py, 73.13 % main.py** — to je nejvyšší výkon z 24 runs. Kontextové L2 (zdrojový kód) přidá max performance, ale **standardní deviace je vysoká** (66.70 % - 70.96 %).

---

## 11. Nákladová efektivita

### 11.1 Token usage per úroveň

| Úroveň | Avg prompt | Avg completion | Avg total | Avg cost ($) | Cost L4/Lx |
|---|---:|---:|---:|---:|---:|
| L0 | 26 252 | 6 631 | 32 883 | **$0.0231** | 2.85× |
| L1 | 41 258 | 7 698 | 48 956 | $0.0322 | 2.04× |
| L2 | 77 570 | 8 387 | 85 957 | $0.0514 | 1.28× |
| L3 | 79 119 | 8 347 | 87 466 | $0.0521 | 1.26× |
| L4 | **105 303** | **8 707** | **114 010** | **$0.0657** | 1.0× |

**Pozoruhodná zjištění:**

1. **Cost roste 2.85× z L0 na L4**, ale zlepšení jiných metrik (validity, code coverage) je marginální.
2. **Completion tokens jsou téměř konstantní** (6 600 - 8 700) přes všechny úrovně — Mistral generuje podobně dlouhý kód bez ohledu na kontext.
3. **Prompt tokens dramaticky rostou** (26K → 105K) — všechen marginal cost pochází z větších promptů.

### 11.2 Token efficiency score

```
score = (tests_passed * assertion_depth) / cost_usd
```

| Úroveň | Avg score |
|---|---:|
| L0 | **2 484** |
| L1 | 2 386 |
| L2 | 1 638 |
| L3 | 1 702 |
| L4 | **1 260** |

**Token efficiency klesá s kontextem** o 49 % (L0 → L4). I když L4 má vyšší assertion depth, dvojnásobný cost ji devalvuje. **L0 je z hlediska efficiency optimální** pro Mistral.

### 11.3 Kompresní účinnost

Compression savings (orig → compressed):

| Úroveň | Savings % | Original chars | Compressed chars |
|---|---:|---:|---:|
| L0 | 48.1 % | 92 223 | 47 874 |
| L1 | 38.8 % | 116 630 | 71 349 |
| L2 | 26.2 % | 178 461 | 131 752 |
| L3 | 25.8 % | 181 024 | 134 312 |
| L4 | **22.6 %** | 207 028 | 160 316 |

OpenAPI specifikace má největší kompresi (48.1 %), zdrojový kód a DDL minimum (2.3 %, 0.1 %), existing_tests žádnou (0 %, schválně).

---

## 12. Slabá místa Mistral (pro doktorskou obhajobu / komparace)

### 12.1 Strukturní

1. **Nikdy nepoužívá třídy** — opačný extrém vůči Claude. Pro pytest reporting to znamená plochou strukturu bez hierarchie.
2. **0 docstringů ve všech sadách** — testy bez popisných komentářů (Claude měl 30+ na L0).
3. **Self-diagnostic NL komentáře vyleakovány** v 17/18 repair sad — produkční kód obsahuje meta-komentáře typu „Main issues: ...". Estetická slabina.
4. **Variable naming inconsistency** — `response` na L0-L3, `r` na L4. Drift kvůli příkladům.

### 12.2 Sémantické

1. **`KeyError: 'is_deleted'` systémový bug** — 9 sad selhává na neexistujícím poli. **Repair loop nikdy neopravuje.**
2. **Rate-limit testy systematicky selhávají** (11 výskytů) — stejný problem jako Claude.
3. **Admin doména totálně vynechána** napříč všemi 25 sadami.
4. **Maintenance mode (503) nikdy netestován**.
5. **Concurrent / race condition tests** — 0 výskytů.
6. **Idempotency-Key** mechanismus nikdy testován (0/25), kontrast s Claude (1/25).
7. **Pagination klesá s kontextem** (L0=4/5 → L4=0/5) — vytlačována komplexnějšími scénáři.
8. **Tags M:N** téměř nikdy testován (max 1/5 na L2-L3).
9. **Self-contradicting tests** — L4_run4 obsahuje `assert book["title"] == "Test Book"` po `title=unique("Test Book")`. Conceptual bug exklusivní pro Mistral.
10. **Helper return-value misuse** — L3_run5 `book2 = create_book(...); assert book2.status_code == 409`. Mistral občas zaměňuje dict a response object.

### 12.3 Test-engineering

11. **Žádné `pytest.fixture`** — DRY je obětována jednoduchosti, což zvyšuje API call traffic.
12. **Žádné `parametrize`** — 5 zvlášť pojmenovaných testů místo 1 parametrizovaného.
13. **Žádné `pytest.raises`** — Mistral nikdy testuje exceptions přes pytest.
14. **Žádný cleanup** (try/finally) — jen 0/25 sad používá explicitní cleanup.
15. **Validity má inverted-U trend** — peak L1 (99.3 %), propad L2-L3 (90 %), L4 mírně 92 %. **Více kontextu paradoxně horší výsledky.**

---

## 13. Silné stránky Mistral

1. **Dokonalá adherence k `test_count` cíli** — 30/30 ve všech 25 sadách (shodné s Claude).
2. **Žádné prázdné kostry** — všechny testy implementované (kontrast s Claude 16 % sad s prázdnými třídami).
3. **Univerzální helper jádro** — `unique`, `create_author`, `create_category`, `create_book` ve všech 25 sadách.
4. **Defensive guard asserts v helperech** — `assert response.status_code in (200, 201)`.
5. **Response validation roste monotonně** L0 = 44.7 % → L3 = 92.7 % (+48 procentních bodů). **Nejvýraznější monotonní metrika Mistralu**.
6. **Conflict detection (409) okamžitý L0→L1 skok** 0/5 → 5/5 — dokumentace je dostatečná pro learning.
7. **Stock manipulace skok L1→L2** 1/5 → 5/5 — zdrojový kód odhalí PATCH endpoint.
8. **0 hallucinated status codes** — všechny status code asserce odpovídají reálným API codes.
9. **0 hallucinated endpoints** — context_endpoints_found vždy z reálné API specifikace.
10. **Reviews doména plynule roste** (1/5 → 5/5).
11. **Self-diagnostic komentáře** — neestetické, ale **kvalitativní indikátor učícího procesu** (může to být i výhoda pro debugovatelnost).
12. **Plan adherence 100 %** ve všech sadách (planned == actual == matched).

---

## 14. Implikace pro výzkumné otázky

### RQ1 — Validita, hloubka asercí, distribuce

- **Validity NEsaturuje monotonně** — má inverted-U s peakem na L1. **Více kontextu může škodit validity** u Mistralu.
- **Assertion depth roste** L0 = 1.96 → L3 = 3.28 (+67 %), L4 mírně klesá na 3.00. To je **mnohem strmější růst** než u Claude (2.27 → 2.91, +28 %).
- **Status code diversity je plochá** — 13 unique kódů na všech úrovních. Bez kontextového gradientu (kontrast s Claude 9 → 13).
- **Distribuce typů**: error stoupá, happy path klesá, edge mírně roste — slabší trend než u Claude.
- **Response validation skokový růst** L0 = 44.7 % → L3 = 92.7 %. **Dramatický kontextový efekt**.

### RQ2 — Strukturní pokrytí

- **Endpoint coverage je U-shape** (L0 = 28 % → L3 = 25.2 % → L4 = 30.8 %) — **NEsaturuje brzy**, kontrast s Claude.
- **Code coverage je téměř plochá** (66.86 % L0 → 67.77 % L4) — žádný ostrý skok na L2 (jen +1.13 p.b.). **Hypotéza o L2 skoku NENÍ podpořena** pro Mistral.
- **`crud.py` coverage roste**: L0 = 36.64 %, L4 = 39.59 % (+2.95 p.b.) — slabý trend.

### RQ3 — Mezimodelové rozdíly

- **Strukturní podpis Mistral:** žádné třídy (0/25), žádné fixtures, žádné parametrize, žádné docstringy, vlastní helper library + self-diagnostic NL komentáře.
- **Sémantický podpis Mistral:** stable test name vocabulary (~10-20 signature tests napříč úrovněmi), `_returns_NNN` styl na L0/L1, `_happy_path` jen na L4_run1.
- **Slabiny pro srovnání:** rate-limit handling, total-misses (admin, maintenance, concurrent), `is_deleted` hallucination.
- **In-context learning slabší než Claude:** L4 přijme jen některé features (variable naming `r`, X-API-Key 5/5, ale `_happy_path` jen 1/5).
- **Cost-effectiveness:** Mistral je nákladově efektivní na L0 ($0.023/sad), neefektivní na L4 ($0.066/sad), bez proporcionálního výkonostního nárůstu.

---

## 15. Doporučení pro komparaci s ostatními modely

### Co měřit pro fair-srovnání

1. **Class usage rate** — Mistral 0/25, Claude 24/25. Extreme mezimodelová polarita.
2. **Empty-class rate** — Mistral 0 % (nemá kostry), Claude 16 %.
3. **Helper consistency** — Mistral 100 % na 4-helper jádro (shodné s Claude).
4. **Self-diagnostic NL comments** — Mistral 17/18 repair sad, Claude 0/25. Silně diskriminativní.
5. **Variable naming convention drift** — Mistral L0-L3 = `response`, L4 = `r`. Claude konzistentně.
6. **Validity inverted-U** — Mistral peak L1, propad L2-L3. Claude flat.
7. **L0→L1 jump in `key in data` asserts** — Mistral +85 %, Claude pravděpodobně menší.
8. **Status code diversity gradient** — Mistral plochý (13), Claude rostoucí (9 → 13).
9. **L4 X-API-Key adoption** — Mistral 5/5 (shodné s Claude).
10. **Run-to-run Jaccard similarity** — Mistral L0 = 0.32, L3 = 0.41, L4 = 0.15. Claude L0 = 0.46, L4 = 0.15.
11. **Repair iterations distribution** — Mistral 7/25 = 1 iter, 18/25 = 3 iter. Claude 80 % = 1 iter.
12. **Total unique test names per level** — Mistral L0 = 72, L4 = 82. Claude L0 = 61, L4 = 104.
13. **Response validation %** — Mistral L0 = 44.7 %, L4 = 90 %. Mistralův hlavní RQ1 indikátor.
14. **`KeyError: 'is_deleted'` výskyt** — Mistral 9/25, Claude 0/25 (pravděpodobně). Diskriminativní failure pattern.
15. **Token efficiency score** — Mistral L0 = 2484, L4 = 1260 (klesá). Compare s Claude.
16. **Cost per sad** — Mistral $0.023 (L0) → $0.066 (L4), 2.85× nárůst.

### Diagnostické otázky pro ostatní modely

1. Generuje plochou strukturu funkcí jako Mistral nebo třídy jako Claude?
2. Zanechává self-diagnostic komentáře jako Mistral?
3. Mění variable naming convention (`response` → `r`) pod vlivem L4 příkladů?
4. Má `is_deleted` hallucination problém?
5. Má rate-limit dead-zone (jak Claude tak Mistral mají)?
6. Adaptuje se na X-API-Key z příkladů (oba ano)?
7. Pokrývá admin doménu (oba ne)?
8. Má `_returns_NNN` test naming styl nebo jiný?
9. Má L4 více "rodin" výstupních strategií (Mistral má 3)?

---

## 16. Konkrétní artefakty pro citaci v textu

### Citovatelná čísla

- **0/25 sad používá top-level třídy** (extreme: opačný extrém Claude 24/25)
- **30/30 testů ve všech sadách** (perfect plan adherence 100 %)
- **Validity Rate inverted-U: 96.7 % (L0) → 99.3 % (L1) → 92.7 % (L2) → 90.0 % (L3) → 92.0 % (L4)**
- **7/25 sad pasovalo na 1. iteraci** (28 %), 18/25 = 3 iterace (72 %)
- **0 fixtures, 0 parametrize, 0 setup_method, 0 pytest.raises, 0 docstringů** ve všech 25 sadách
- **Helper functions consistency: 100 %** (`unique`, `create_author`, `create_category`, `create_book`)
- **Status code diversity: 13 (konstantní)** napříč všemi úrovněmi
- **Assertion depth: 1.96 (L0) → 3.28 (L3) → 3.00 (L4)**, peak na L3, +67 %
- **Response validation: 44.7 % (L0) → 92.7 % (L3) → 90.0 % (L4)** — +48 procentních bodů
- **`key in data` asserts: L0→L1 skok +85 %** (47 → 87)
- **Jaccard similarity: 0.324 (L0) → 0.406 (L3) → 0.148 (L4)**
- **L4 unikátní test names: 82** vs **L0: 72**
- **X-API-Key adoption: 1/5 (L0) → 1/5 (L1-L2) → 3/5 (L3) → 5/5 (L4)** — postupný in-context learning
- **Admin doména pokryta: 0/25 sad** (slepé místo)
- **Maintenance mode pokryt: 0/25 sad**
- **Concurrent tests: 0/25 sad**
- **Idempotency: 0/25 sad** (kontrast s Claude 1/25)
- **Self-diagnostic NL komentáře: 17/18 repair sad** — Mistral signature
- **`KeyError: 'is_deleted'` failure: 9/25 sad** — systémový bug
- **Total experiment cost: $1.122**, total tokens: **1 846 353**
- **Cost L4/L0 ratio: 2.85×**
- **Code coverage L0=66.86 %, L4=67.77 %** — téměř plochá, kontrast s hypotézou RQ2

### Charakteristické úryvky kódu

```python
# Standardní helper pattern přítomný ve všech 25 sadách:
def create_book(title=None, isbn=None, price=29.99, ...):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:10]}"
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    payload = {...}
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

# Mistral signature: NL komentáře na vrcholu souboru po repair iteracích (17/18 sad):
# Main issues: 1) ISBN generation might exceed length limits 2) Missing required fields ...
# Fix: Ensure ISBN is exactly 13 chars, add proper validation error handling in helpers

# L0/L1 styl test name (verbose):
def test_apply_discount_exceeding_rate_limit_returns_429():
    ...

# L4_run1 only: _happy_path styl (z příkladů):
def test_apply_discount_happy_path():
    ...

# L4 only: API key auth (1/5 → 5/5)
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

# L4 only: variable naming r= (vs response= elsewhere)
r = requests.post(f"{BASE_URL}/authors", json={...}, headers=AUTH, timeout=30)
assert r.status_code == 201

# Conceptual bug exklusivní pro Mistral L4_run4:
def test_create_book_valid_data():
    book = create_book(author["id"], category["id"], title=unique("Test Book"),
                       isbn=unique("ISBN")[:13], ...)
    assert book["title"] == "Test Book"          # FAILS: actual title je "Test Book_xxxxxxxx"
    assert book["isbn"] == unique("ISBN")[:13]   # FAILS: dvojí volání unique() generuje různé hashe

# Helper return-value misuse, L3_run5:
def test_create_book_with_duplicate_isbn():
    book1 = create_book()
    book2 = create_book(isbn=book1["isbn"])      # Helper raisuje na 409
    assert book2.status_code == 409              # NEDOSAŽENO; book2 je dict, ne response

# Systémový bug 'is_deleted' (9 sad):
def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}")
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["is_deleted"] is False    # KeyError: 'is_deleted' (pole neexistuje)
```

---

## 17. Závěr

Mistral Large 2512 produkuje **strukturálně minimalistické** (žádné třídy, žádné docstringy, žádné fixtures), **sémanticky proměnlivé** (3 různé „rodiny" L4 výstupů) a **inverted-U validní** (peak L1, propad L2-L3, comeback L4) testovací sady s **monotonně rostoucí response validation** napříč úrovněmi kontextu — ale s **kvazi-konstantní status code diversity** a se **systematickými slepými místy na rate-limit logice, admin doméně a `is_deleted` field hallucination**.

Hlavní efekt přírůstku kontextu se neprojevuje v *zda* testy prochází (validity má inverted-U, ne monotonní růst), ani ve *strukturní variabilitě status kódů* (plochá), ale v **hloubce body validation** (44.7 % → 92.7 %) a **assertion depth** (1.96 → 3.28). **L1 (přidání dokumentace) je sweet spot** pro Mistral co se týče validity a cost-effectiveness — další kontext zhoršuje validity a zvyšuje cost bez proporcionálního přínosu.

**L4 (in-context examples) je pro Mistral dvojsečný** — částečně se naučí styling (`_happy_path`, `r =`, X-API-Key), ale **generuje conceptual bugs** (unique() race conditions, helper return-value misuse) v 2/5 sad. **In-context learning u Mistral je nedostatečně robustní** — generuje strukturně rozdílné výstupy ze stejného L4 kontextu (3 rodiny strategií).

Pro mezimodelovou komparaci je Mistral **strukturně opačným pólem** vůči Claude (0 vs 24 sad s třídami; 0 vs 25+ docstringů na L0; self-diagnostic NL komentáře vs clean output). Sdílí s Claude **adminstrativní slepá místa** (admin, maintenance, concurrent), **rate-limit dead-zone** a **L4 X-API-Key adoption**. **Differentiátorem** je: Mistralova **inverted-U validity**, jeho **monotonní response validation growth**, jeho **`KeyError: 'is_deleted'` systémový bug**, a jeho **`r =` vs `response =` variable naming drift** s úrovní kontextu.

Skutečné rozdíly v testovací kvalitě se objeví v **assertion depth gradient**, **response validation %**, **structural patterns** (třídy vs ploché funkce, docstring presence), **NL comment leakage**, **in-context style adoption rate**, **failure taxonomy** (`is_deleted` hallucination jako Mistral signature) a **cost-effectiveness profilu** (Mistral je optimální na L1, neefektivní na L4).