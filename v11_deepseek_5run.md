# Analýza běhu: diplomka_v11 — DeepSeek Chat

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM model | deepseek-chat |
| Provider | DeepSeek (OpenAI-kompatibilní API) |
| Ekosystém | Čína |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 50 endpointů v11 counting) |
| Max iterací | 5 |
| Runů na kombinaci | 5 |
| Testů na run | 30 |
| Temperature | 0.4 |
| max_tokens | 8192 |
| Stale threshold | 2 (1× isolated + 1× helper se stejnou normalizovanou chybou) |

---

## RQ1: Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu a sémantickou kvalitu LLM-generovaných API testů?

### Validity rate per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| **L0** | 100.0% | 100.0% | 96.67% | 100.0% | 96.67% | **98.67%** | 1.6 |
| **L1** | 100.0% | 96.67% | 100.0% | 96.67% | 100.0% | **98.67%** | 1.6 |
| **L2** | 96.67% | 100.0% | 96.67% | 100.0% | 100.0% | **98.67%** | 1.6 |
| **L3** | 100.0% | 96.67% | 93.33% | 100.0% | 93.33% | **96.67%** | 3.0 |
| **L4** | 100.0% | 96.67% | 96.67% | 93.33% | 100.0% | **97.33%** | 2.5 |

### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Validation (avg %) |
|-------|--------------------|----------------------------|
| L0 | 2.17 | 54.0 |
| L1 | 3.25 | 90.0 |
| L2 | 3.31 | 95.33 |
| L3 | 3.07 | 95.33 |
| L4 | 3.37 | 97.34 |

### Iterace ke konvergenci a stale testy

| Level | Iterace (avg) | Stale (avg) | Early stopped (z 5) |
|-------|---------------|-------------|----------------------|
| L0 | 1.8 | 0.4 | 2/5 |
| L1 | 2.2 | 0.4 | 2/5 |
| L2 | 1.8 | 0.4 | 2/5 |
| L3 | 2.2 | 1.0 | 3/5 |
| L4 | 2.6 | 0.8 | 2/5 |

### Analýza trendu L0→L4

**Celkový vzorec: vysoká baseline, plateau od L0**

DeepSeek vykazuje výrazně odlišný vzorec od Gemini — validity je vysoká (≥96.67 %) již na L0 a zůstává stabilní napříč všemi úrovněmi. L0–L2 dosahují shodného průměru 98.67 % s identickou variancí (std 1.6). L3 a L4 mají paradoxně mírně nižší průměr (96.67 % a 97.33 %) s vyšší variancí.

Toto je **antitetický vzorec vůči H1a** (monotónní růst TVR s kontextem) — DeepSeek kontext nepotřebuje pro vysokou validity, ale kontext mírně zvyšuje riziko stale testů na L3–L4.

**L0: 98.67 % — robustní bez kontextu**

DeepSeek na L0 generuje funkční testy ze samotné OpenAPI specifikace. 3/5 runů dosáhly 100 %. Dva failing runy (Run 3, Run 5) měly každý jen 1 stale test:
- Run 3: `test_update_order_status_valid` — wrong_status_code (model hádal špatný přechodový stav objednávky)
- Run 5: `test_create_order_with_invalid_email_format` — wrong_status_code (API nevaliduje email formát, model očekával 422)

Obě selhání jsou **sémantické** — model neví jak API interně funguje, ale technicky generuje validní kód. Žádné helper kaskádové selhání.

**L1: 98.67 % — dokumentace nemá vliv na validity**

Identický výsledek jako L0. Selhávající testy na L1 jsou jiného typu:
- Run 2: `test_apply_discount_rate_limit_429` — wrong_status_code (timing-dependent rate limit)
- Run 4: `test_apply_discount_to_old_book_200` — assertion_value_mismatch (špatná kalkulace discounted_price)

Klíčový rozdíl L0→L1 je v **response validation**: 54 % → 90 % (+36 p.b.). Dokumentace naučila model kontrolovat response body, ne jen status kódy.

**L2: 98.67 % — zdrojový kód nemění validity, zlepšuje assertion depth**

Validity zůstává na 98.67 %. Assertion depth roste mírně (3.25 → 3.31). Response validation dosáhla 95.33 % (+5 p.b. oproti L1). Selhání:
- Run 1: `test_restore_soft_deleted_book` — assertion_value_mismatch (`data["is_deleted"]` místo `data["is_deleted"] == False`)
- Run 3: `test_upload_valid_cover_image` — NameError: `Image` (model použil `from PIL import Image`, knihovna není dostupná)

Run 3 je jediný případ nedostupné knihovny v celém DeepSeek experimentu.

**L3: 96.67 % — DB schéma přidává komplexitu a riziko**

L3 má nejnižší průměrnou validity (96.67 %) a nejvyšší varianci (std 3.0). Paradoxně, DB schéma s explicitními CHECK a UNIQUE constrainty inspirovalo model k ambicióznějším testům, které pak častěji selhávají:
- Run 3: 2 stale (restore + rate_limit) → 93.33 %
- Run 5: 2 stale (discount_new_book + bulk_partial) → 93.33 %

Specifický problém: `test_apply_discount_rate_limit` — model generuje 5 requestů a čeká 429, ale timing na API není deterministický. Rate limit endpoint je **cross-level stale magnet** pro DeepSeek.

**L4: 97.33 % — referenční testy stabilizují, ale neeliminují rate limit problém**

L4 Run 4 je nejhorší run (93.33 %, 5 iterací, 2 stale) kvůli rate limit testu + bulk partial. Referenční testy zajišťují konzistentní helper architekturu (6 helperů, `create_book(author_id, category_id, ...)` s explicitními parametry), ale nepomáhají s timing-dependent testy.

### Klíčový nález: rate limit jako systematický problém

`test_apply_discount_rate_limit*` je stale v **7 z 25 runů** (28 %) napříč L1–L4:
- L1 Run 2, L3 Run 2, L3 Run 3, L3 Run 5 (jako discount_new_book), L4 Run 2, L4 Run 3, L4 Run 4

Root cause: model posílá 5 discount requestů a pak 6. request, ale rate limit window (10s) může expirovat mezi requesty. Test je nedeterministický. Repair loop nemůže opravit timing problém — izolovaná oprava mění assertion, helper oprava mění setup, ale ani jedno neřeší race condition.

### Srovnání assertion depth a response validation: skoky

| Přechod | Assert Depth Δ | Resp. Validation Δ | Interpretace |
|---------|----------------|---------------------|--------------|
| L0→L1 | +1.08 | +36.0 p.b. | **Největší skok** — dokumentace naučí model co ověřovat |
| L1→L2 | +0.06 | +5.33 p.b. | Marginální — zdrojový kód přidává detaily |
| L2→L3 | −0.24 | 0.0 p.b. | **Pokles** — DB schéma nezvyšuje assertion kvalitu |
| L3→L4 | +0.30 | +2.01 p.b. | Mírný růst — referenční testy ukazují styl |

Assertion depth **neroste monotónně** — L3 je nižší než L2. DB schéma přidává endpoint coverage (model testuje víc endpointů z constraintů) ale ne hloubku asercí.

---

## RQ2: Testovací strategie — distribuce scénářů a pokrytí

### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg (%) |
|-------|-------|-------|-------|-------|-------|---------|
| L0 | 34.0 | 40.0 | 42.0 | 46.0 | 42.0 | **40.8** |
| L1 | 32.0 | 30.0 | 32.0 | 34.0 | 34.0 | **32.4** |
| L2 | 34.0 | 34.0 | 32.0 | 34.0 | 34.0 | **33.6** |
| L3 | 42.0 | 32.0 | 38.0 | 34.0 | 48.0 | **38.8** |
| L4 | 34.0 | 32.0 | 44.0 | 40.0 | 34.0 | **36.8** |

**Paradox: L0 má nejvyšší EP coverage (40.8 %).** Na L0 model bez kontextu „rozhazuje" testy široce přes specifikaci (17–23 endpointů). Na L1 se fokusuje na menší sadu endpointů (15–17), které dokumentace popisuje detailněji, a testuje je hlouběji (vyšší assertion depth). L3 má druhou nejvyšší EP coverage (38.8 %) díky DB constraintům, které model mapuje na endpointy.

Toto podporuje **H1c** — EP coverage je vysoká na L0 a neroste lineárně s kontextem, zatímco assertion depth a response validation rostou strmě.

### Test type distribution (avg %)

| Level | Happy Path | Error | Edge Case |
|-------|-----------|-------|-----------|
| L0 | 49.3 | 43.3 | 7.3 |
| L1 | 52.7 | 45.3 | 2.0 |
| L2 | 55.3 | 44.0 | 0.7 |
| L3 | 40.7 | 52.7 | 6.7 |
| L4 | 37.3 | 58.0 | 4.7 |

**Posun od happy path k error scénářům:** L0–L2 mají nadpoloviční podíl happy path testů (49–55 %). Na L3 se poměr obrací — error testy dominují (52.7 %) díky DB constraintům, které model přeloží do error scénářů. L4 má nejvyšší podíl error testů (58 %) — referenční testy demonstrují error-first přístup.

Toto **částečně podporuje H2a** — happy path klesá z ~50 % (L0) na ~37 % (L4), i když ne pod 40 % jak hypotéza předpokládala. Klíčový přechod nastává na L3 (ne L2 jak očekáváno).

Edge cases jsou nejvyšší na L0 (7.3 %) a L3 (6.7 %). Na L0 model experimentuje bez znalosti API, na L3 DB constrainty inspirují hraniční scénáře (CHECK, UNIQUE).

### Status code diversity (avg)

| Level | Avg unique codes | Min | Max |
|-------|-----------------|-----|-----|
| L0 | 10.4 | 10 | 12 |
| L1 | 10.6 | 9 | 12 |
| L2 | 10.2 | 10 | 11 |
| L3 | 12.2 | 10 | 14 |
| L4 | 13.6 | 11 | 16 |

Diverzita roste výrazně na L3 (+2.0 oproti L2) a L4 (+1.4 oproti L3). L3 DB schéma odhaluje constrainty vedoucí k novým kódům (207 Multi-Status, 304 Not Modified). L4 referenční testy obsahují širokou paletu status kódů. **Největší skok L2→L3 (+2.0) podporuje H2b.**

### Avg test length (řádky)

| Level | Avg lines | Interpretace |
|-------|-----------|--------------|
| L0 | 9.15 | Krátké, status-code-only testy |
| L1 | 13.52 | Delší díky response body checks |
| L2 | 11.41 | Kompaktnější — helper reuse |
| L3 | 11.30 | Stabilní |
| L4 | 11.63 | Stabilní |

L1 má nejvyšší průměrnou délku (13.52) kvůli outlieru Run 5 (21.97 řádků — viz outlier analýza níže). Bez outlieru by L1 avg byl ~10.7.

---

## Failure Analysis

### Failure taxonomy — poslední iterace (stale + failing)

| Level | Total failing | wrong_status_code | assertion_value_mismatch | other | Stale total |
|-------|---------------|-------------------|--------------------------|-------|-------------|
| L0 | 2 | 2 (100%) | 0 | 0 | 2 |
| L1 | 2 | 1 (50%) | 1 (50%) | 0 | 2 |
| L2 | 2 | 0 | 1 (50%) | 1 (50%) | 2 |
| L3 | 5 | 4 (80%) | 0 | 1 (20%) | 5 |
| L4 | 4 | 3 (75%) | 0 | 1 (25%) | 4 |

**Dominantní vzorec: wrong_status_code, NE helper kaskádové selhání.**

Na rozdíl od Gemini, DeepSeek nemá problém s helper kaskádovými chybami. Kategorie "other" je marginální (0–1 per level) a nikdy se nejedná o helper cascade — jde o specifické assertion chyby (`is_deleted` field name, PIL import).

**Hlavní selhávající vzorce:**
1. **Rate limit timing** (7/15 = 47 % všech selhání): `test_apply_discount_rate_limit*` — nedeterministický test
2. **Discount boundary** (3/15 = 20 %): `test_apply_discount_*_new_book*` — model neví přesný rok boundary
3. **Bulk partial success** (2/15 = 13 %): `test_bulk_create_books_partial_success` — 207 Multi-Status handling
4. **Restore assertion** (2/15 = 13 %): `test_restore_soft_deleted_book*` — `is_deleted` vs. `deleted` field name
5. **PIL import** (1/15 = 7 %): `test_upload_valid_cover_image` — nedostupná knihovna

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg never-fixed | Fix rate |
|-------|---------------------|-----------------|----------|
| L0 | 0.4 | 0.4 | 0% |
| L1 | 0.8 | 0.4 | 50% |
| L2 | 0.4 | 0.4 | 0% |
| L3 | 1.0 | 1.0 | 0% |
| L4 | 0.6 | 0.8* | — |

*L4 avg never-fixed je vyšší než avg failing iter 1, protože Run 4 měl regresi (1 failing v iter 1, 2 na konci).

**Nízký fix rate je paradoxní výsledek vysoké výchozí kvality.** DeepSeek generuje tak málo failing testů (0.4–1.0 per run), že ty které selžou, jsou typicky principiálně neopravitelné (timing, boundary edge cases). Repair loop opraví triviální chyby (assertion_value_mismatch na discounted_price kalkulaci — opraveno v 3/4 případech na L1), ale timing-dependent a boundary testy jsou stale materiál.

### Per-level never-fixed vzorce

**L0 never-fixed (2 z 25 runů):**

| Test | Výskyty | Root cause |
|------|---------|------------|
| test_update_order_status_valid | 1 | Model hádá transition pending→confirmed, ale posílá špatný payload |
| test_create_order_with_invalid_email_format | 1 | API nevaliduje email formát — model halucinuje validaci |

**L1 never-fixed (2 z 25 runů):**

| Test | Výskyty | Root cause |
|------|---------|------------|
| test_apply_discount_rate_limit_429 | 1 | Timing-dependent — 5 req/10s window |
| test_apply_discount_to_old_book_200 | 1 | `discounted_price == price * (1 - 10/100)` vs. `round(price * 0.9, 2)` |

**L3 never-fixed (5 z 25 runů):**

| Test | Výskyty | Root cause |
|------|---------|------------|
| test_apply_discount_rate_limit* | 2 | Timing-dependent |
| test_restore_soft_deleted_book* | 1 | `data["is_deleted"]` — field neexistuje v response |
| test_apply_discount_new_book_error | 1 | published_year boundary — model neví přesný rok |
| test_bulk_create_books_partial_success | 1 | ISBN generování pro duplicate detection |

**L4 never-fixed (4 z 25 runů):**

| Test | Výskyty | Root cause |
|------|---------|------------|
| test_apply_discount_rate_limit_exceeded | 3 | Timing-dependent — nejčastější stale test celého experimentu |
| test_bulk_create_books_partial_success | 1 | ISBN setup pro 207 Multi-Status |

---

## Repair Loop Analýza

### Efektivita repair strategií per level

| Level | Runy s repair | Helper repair | Isolated fix | All-stale early stop |
|-------|---------------|---------------|--------------|----------------------|
| L0 | 2/5 | 2/2 (fallback) | Nepomohl (obě stale) | 2/2 |
| L1 | 4/5 | 2× fallback, 2× isolated fix | 2/4 fixed | 2/4 |
| L2 | 2/5 | 2/2 (fallback) | Nepomohl | 2/2 |
| L3 | 3/5 | 3/3 (fallback) | Nepomohl | 3/3 |
| L4 | 3/5 | 3/3 (fallback) | 1× regression! | 2/3 |

**DeepSeek repair pattern:** Téměř všechny failing testy skončí jako stale po 2 iteracích (isolated → helper → stale). Fix rate je nízký protože zbývající chyby jsou principiálně neopravitelné (timing, boundary). Repair loop efektivně funguje jen na L1, kde opravuje assertion_value_mismatch na discount kalkulaci.

### L4 Run 4 — regrese v repair loopu

```
Iter 1: 29p/1f → isolated (1 opraveno)
Iter 2: 29p/1f → helper_fallback (1 attempted)
Iter 3: 28p/2f → isolated (1 opraveno, 1 stale)  ← REGRESE: +1 failing
Iter 4: 28p/2f → helper_fallback (1 attempted, 1 stale)
Iter 5: 28p/2f → max iterací
Never-fixed: 2 (rate_limit + bulk_partial)
```

Helper repair v iter 2 zavedl regresi — opravou helperů se rozbil `test_bulk_create_books_partial_success`, který předtím procházel. Toto je vzácný případ kde repair loop situaci zhoršil.

### StaleTracker analýza

| Level | Stale avg | Max stale | Stale = never-fixed? |
|-------|-----------|-----------|----------------------|
| L0 | 0.4 | 1 | 100% |
| L1 | 0.4 | 1 | 100% |
| L2 | 0.4 | 1 | 100% |
| L3 | 1.0 | 2 | 100% |
| L4 | 0.8 | 2 | 100% |

Stale testy jsou **vždy totožné** s never-fixed testy. Na rozdíl od Gemini (kde stale tracker zamykal 7–17 testů per run), u DeepSeeku je stale count minimální (0–2). Stale tracker pracuje korektně — nezamyká opravitelné testy, protože failing testy jsou skutečně neopravitelné.

---

## Outlier analýza

### L1 Run 5 — max_tokens truncation (100 %, ale anomální struktura)

| Aspekt | Hodnota | Typický L1 run |
|--------|---------|----------------|
| Validity | 100.0% | 98.67% |
| Assertion depth | **5.13** | 2.77 |
| Avg test length | **21.97** řádků | 11.3 |
| Helper count | **1** (jen unique) | 4–5 |
| Avg HTTP calls | **3.53** | 1.43 |
| Avg helper calls | **0.33** | 2.57 |
| Chaining | **76.7%** | 0% |
| Completion tokens (generation) | **8192** | 3987–4141 |

Completion tokens v generation fázi dosáhly přesně 8192 — `max_tokens` limitu DeepSeek providera. Model generoval velmi dlouhé, self-contained testy bez helper funkcí (inline setup v každém testu). Kód se náhodou uřízl na validním místě (poslední test byl kompletní). Výsledek: 100 % validity ale anomální kódová struktura.

**Implikace pro experiment:** Tento run je validní z hlediska metrik ale nesrovnatelný strukturálně s ostatními runy. Pro statistickou analýzu je assertion depth 5.13 outlier (2σ od průměru L1).

### L3 Run 3 — nejvíce stale testů DeepSeeku (93.33 %)

```
Iter 1: 28p/2f (restore + rate_limit)
Iter 2: 28p/2f → helper_fallback
Iter 3: 28p/2f → all_stale_early_stop (2 stale)
Never-fixed: test_restore_soft_deleted_book_success, test_apply_discount_rate_limit_exceeded
```

Dva nezávislé chyby — restore (`is_deleted` field assertion) a rate limit (timing). Obě jsou neopravitelné repair loopem. L3 Run 3 má také nejvyšší status_code_diversity v celém experimentu (14 unique kódů) a 4 edge cases (13.33 %) — model na L3 generoval ambicióznější plán.

### L2 Run 3 — PIL import problém (96.67 %)

Jediný run kde DeepSeek použil nedostupnou knihovnu. Model viděl ve zdrojovém kódu (L2) file upload handling a rozhodl se generovat reálný JPEG obrázek přes PIL místo `b"fake image data"`. Repair loop test opravit nedokázal — `Image` je undefined po smazání importu, ale test nepoužívá žádnou alternativní strategii.

---

## Token Usage a Cost

### Per-level průměry

| Level | Avg calls | Avg prompt tokens | Avg completion tokens | Avg total | Avg cost ($) |
|-------|-----------|-------------------|-----------------------|-----------|--------------|
| L0 | 2.8 | 26,375 | 6,307 | 32,683 | $0.0045 |
| L1 | 3.2 | 42,441 | 7,536 | 49,977 | $0.0057 |
| L2 | 2.8 | 73,002 | 6,774 | 79,776 | $0.0057 |
| L3 | 3.2 | 75,955 | 7,449 | 83,404 | $0.0064 |
| L4 | 3.6 | 92,251 | 7,633 | 99,884 | $0.0069 |

**Celkový cost za 25 runů: $0.146** — extrémně nízký díky DeepSeek pricingu.

### Porovnání s Gemini cost

| Level | DeepSeek avg cost | Gemini avg cost | Poměr |
|-------|-------------------|-----------------|-------|
| L0 | $0.0045 | $0.020 | **4.4×** levnější |
| L1 | $0.0057 | $0.025 | **4.4×** levnější |
| L2 | $0.0057 | $0.025 | **4.4×** levnější |
| L3 | $0.0064 | $0.028 | **4.4×** levnější |
| L4 | $0.0069 | $0.027 | **3.9×** levnější |

DeepSeek je konzistentně ~4× levnější než Gemini při výrazně vyšší kvalitě výstupů.

### Cache utilization

DeepSeek API efektivně cachuje kontext:
- L0: avg 22,157 cached tokens (85 % z prompt)
- L1: avg 38,755 cached tokens (91 % z prompt)
- L2: avg 70,283 cached tokens (96 % z prompt)
- L3: avg 71,526 cached tokens (94 % z prompt)
- L4: avg 87,693 cached tokens (95 % z prompt)

Cache ratio je výrazně vyšší než u Gemini (60 % na L4 pro Gemini vs. 95 % pro DeepSeek). DeepSeek prefix caching je agresivnější.

### Completion tokens — truncation risk

| Level | Avg completion (generation) | Max completion | Hit 8192 limit? |
|-------|----------------------------|----------------|------------------|
| L0 | 3,568 | 3,692 | Ne |
| L1 | 4,252 | **8,192** | **Ano (Run 5)** |
| L2 | 3,843 | 4,638 | Ne |
| L3 | 4,098 | 4,475 | Ne |
| L4 | 4,611 | 4,788 | Ne |

Pouze L1 Run 5 narazil na max_tokens limit. Paradoxně, vyšší kontextové úrovně (L2–L4) generují kompaktnější kód díky lepším helperům — completion tokens na L2–L4 jsou nižší než na L1.

---

## Helper architektura

### Helper count per level

| Level | Min helpers | Max helpers | Avg | Typická sada |
|-------|-------------|-------------|-----|--------------|
| L0 | 5 | 6 | 5.2 | unique, create_author, create_category, create_book, create_tag (+get_etag v 1 runu) |
| L1 | 1* | 5 | 3.8 | unique, create_author, create_category, create_book (+create_order, create_tag) |
| L2 | 5 | 6 | 5.4 | unique, create_author, create_category, create_book, create_tag (+create_order) |
| L3 | 5 | 15** | 7.4 | unique, create_author, create_category, create_book, create_tag, create_order (+get/delete/restore wrappers) |
| L4 | 6 | 6 | 6.0 | unique, create_author, create_category, create_book, create_tag, create_order |

*L1 Run 5: pouze `unique` helper — model generoval self-contained testy (truncation outlier).

**L3 Run 3: 15 helperů — model vytvořil wrapper pro téměř každou API operaci (`get_author`, `delete_author`, `get_book`, `delete_book`, `restore_book`, `create_order`, `get_order`, `update_order_status`, `get_invoice`). Toto je důsledek DB schématu, které model interpretoval jako kompletní entity diagram a vytvořil CRUD wrappery.

### create_book helper — klíčový diferenciátor

| Level | Typická signatura | Stock field | Published year | ISBN strategie |
|-------|-------------------|-------------|----------------|----------------|
| L0 | `create_book(title=None, isbn=None, price=19.99, stock=10, author_id=None, category_id=None)` | Ano | 2020 | `unique("isbn")[:13]` |
| L1 | Variabilní — od `create_book()` po `create_book(author_id, category_id)` | Variabilní | 2020 | uuid-based |
| L2 | `create_book(title=None, isbn=None, price=10.5, stock=5, ...)` | Ano | 2020 | `unique("isbn")[:13]` |
| L3 | Variabilní — od `create_book()` po full params | Ano | 2020 | `unique("isbn")[:13]` |
| L4 | `create_book(author_id, category_id, title=None, isbn=None, price=29.99, stock=10)` | Ano | 2020 | `unique("isbn")[:13]` |

**Na rozdíl od Gemini, DeepSeek konzistentně používá uuid-based ISBN generování** (`unique("isbn")[:13]`), což eliminuje helper kaskádové selhání. Žádný DeepSeek run nemá hardcoded ISBN. Toto je hlavní strukturální důvod proč DeepSeek dosahuje 98+ % validity na všech úrovních.

---

## Instruction Compliance

| Level | Missing timeout (avg z 5 runů) | Compliance score (avg) |
|-------|-------------------------------|------------------------|
| L0 | 3/5 runů missing (60 %) | 84 |
| L1 | 2/5 runů missing (40 %) | 88 |
| L2 | 3/5 runů OK (60 %) | 92 |
| L3 | 3/5 runů OK (60 %) | 92 |
| L4 | 5/5 runů OK (100 %) | 100 |

Compliance roste s kontextem. L4 dosahuje 100 % ve všech runech — referenční testy explicitně používají `timeout=30`, model to kopíruje. L0 má nižší compliance protože specifikace nezmiňuje timeout požadavek.

---

## Kontextová komprese

| Level | Original tokens | Compressed tokens | Savings (%) |
|-------|-----------------|-------------------|-------------|
| L0 | 30,741 | 15,958 | 48.1 |
| L1 | 38,876 | 23,783 | 38.8 |
| L2 | 59,487 | 43,917 | 26.2 |
| L3 | 60,341 | 44,770 | 25.8 |
| L4 | 69,009 | 53,438 | 22.6 |

| Sekce | Savings (%) |
|-------|-------------|
| OpenAPI specifikace | 48.1 |
| Technická dokumentace | 3.8 |
| Zdrojový kód | 2.3 |
| DB schéma | 0.1 |
| Existující testy | 0.0 (nekomprimovány) |

OpenAPI komprese (48 %) šetří ~15K tokenů na run. Zdrojový kód a testy se komprimují minimálně.

---

## Code Coverage

### Code coverage per level (total)

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| **L0** | 70.5% | 70.4% | 69.8% | 66.8% | 70.6% | **69.6%** | 1.5 |
| **L1** | 69.7% | 71.4% | 73.2% | 73.3% | 69.8% | **71.5%** | 1.7 |
| **L2** | 73.9% | 72.1% | 69.6% | 74.5% | 72.3% | **72.5%** | 1.8 |
| **L3** | 74.9% | 69.9% | 73.9% | 72.1% | 72.9% | **72.7%** | 1.8 |
| **L4** | 74.0% | 72.8% | 73.7% | 72.9% | 74.0% | **73.5%** | 0.5 |

### Code coverage breakdown (crud.py vs main.py)

| Level | crud.py Avg | main.py Avg | Gap (main−crud) |
|-------|-------------|-------------|-----------------|
| L0 | 41.9% | 72.1% | 30.2 p.b. |
| L1 | 50.0% | 68.0% | 18.0 p.b. |
| L2 | 52.2% | 68.4% | 16.2 p.b. |
| L3 | 51.4% | 70.4% | 19.0 p.b. |
| L4 | 53.2% | 70.8% | 17.6 p.b. |

#### crud.py per run

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg |
|-------|-------|-------|-------|-------|-------|-----|
| L0 | 43.9% | 43.9% | 42.6% | 35.1% | 43.9% | **41.9%** |
| L1 | 45.7% | 50.1% | 54.5% | 53.5% | 46.0% | **50.0%** |
| L2 | 56.3% | 51.4% | 44.4% | 57.6% | 51.4% | **52.2%** |
| L3 | 56.6% | 45.7% | 54.3% | 51.4% | 49.1% | **51.4%** |
| L4 | 54.8% | 52.7% | 50.9% | 52.7% | 54.8% | **53.2%** |

#### main.py per run

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg |
|-------|-------|-------|-------|-------|-------|-----|
| L0 | 72.5% | 72.1% | 71.8% | 71.4% | 72.8% | **72.1%** |
| L1 | 67.4% | 67.4% | 68.0% | 69.7% | 67.4% | **68.0%** |
| L2 | 68.0% | 68.0% | 68.7% | 68.4% | 69.1% | **68.4%** |
| L3 | 71.1% | 68.0% | 70.8% | 68.0% | 74.2% | **70.4%** |
| L4 | 70.4% | 69.1% | 74.5% | 69.4% | 70.4% | **70.8%** |

### Code coverage analýza

**Celkový vzorec: monotónní růst L0→L4, plateau na L2+**

Total coverage roste od 69.6 % (L0) přes 71.5 % (L1), 72.5 % (L2), 72.7 % (L3) k 73.5 % (L4). Celkový skok L0→L4 je **+3.9 p.b.** Růst je nejsilnější L0→L1 (+1.9 p.b.), pak zpomaluje (L1→L2 +1.0, L2→L3 +0.2, L3→L4 +0.8). L4 má nejnižší varianci (std 0.5) — referenční testy stabilizují coverage.

**crud.py: klíčový diferenciátor, skok L0→L1, pak plateau**

crud.py coverage je nejcitlivější metrika na kontextovou úroveň:
- **L0: 41.9 %** — model testuje základní CRUD operace (create_author, create_book, create_order) ale neproniká do business logiky (discount, stock, bulk, clone, invoice = 0 %)
- **L1: 50.0 %** — dokumentace přidává **+8.1 p.b.** Nově pokryté funkce: `update_stock` (100 %), `generate_invoice` (90–100 %), `bulk_create_books` (73–89 %). Dokumentace explicitně popisuje tyto business flows.
- **L2: 52.2 %** — zdrojový kód přidává jen +2.2 p.b. oproti L1. Marginální zlepšení.
- **L3: 51.4 %** — **mírný pokles** oproti L2 (−0.8 p.b.). DB schéma nepřidává business coverage — model testuje víc endpointů (EP coverage 38.8 %) ale méně hluboce. Run 2 outlier (45.7 %) snižuje průměr.
- **L4: 53.2 %** — nejvyšší průměr, nejnižší variace. Referenční testy konzistentně pokrývají `bulk_create_books` (73–89 %), `clone_book` (0–88 %), `generate_invoice` (27–100 %).

Celkový skok L0→L4 na crud.py je **+11.3 p.b.** — výrazně silnější než na main.py (−1.3 p.b.). Kontext primárně ovlivňuje hloubku business testování.

**Paradox main.py: L0 > L1, recovery na L3–L4**

main.py coverage má U-tvar: L0 72.1 % → L1 68.0 % (−4.1 p.b.) → L2 68.4 % → **L3 70.4 % → L4 70.8 %** (recovery). Na L0 model „rozhazuje" testy široce a aktivuje více routing cest. Na L1–L2 se fokusuje na menší sadu endpointů. Na L3–L4 se šíře vrací — DB schéma a referenční testy přidávají endpointy (export, maintenance, clone) které zvyšují main.py coverage.

L3 Run 5 má nejvyšší main.py coverage (74.2 %) — tento run má EP coverage 48 % (nejvyšší celkově) a pokrývá export, maintenance a clone endpointy.

**Gap klesá s kontextem, plateau na L1+**

| Přechod | Gap Δ | Interpretace |
|---------|-------|--------------|
| L0→L1 | 30.2 → 18.0 (−12.2) | **Dramatický skok** — dokumentace učí model testovat business logiku |
| L1→L2 | 18.0 → 16.2 (−1.8) | Marginální |
| L2→L3 | 16.2 → 19.0 (+2.8) | **Mírný nárůst** — model na L3 rozhazuje testy šířeji (main↑) ale crud plateau |
| L3→L4 | 19.0 → 17.6 (−1.4) | Recovery díky referenčním testům |

Gap osciluje kolem 16–19 p.b. na L1+. Klíčový přechod je L0→L1 (−12.2 p.b.) — dokumentace je primární katalyzátor business coverage.

**L0 Run 4 outlier (66.8 % total, 35.1 % crud.py)**

Nejnižší coverage v celém experimentu. Tento run měl EP coverage 46 % (nejvyšší na L0) ale nejnižší crud.py (35.1 %). Model pokrýval mnoho endpointů povrchně (status-code-only testy) bez pronikání do business logiky. Response validation jen 40 % (nejnižší). Assertion depth 1.87 (nejnižší).

**L3 Run 1 — nejlepší single run (74.9 % total, 56.6 % crud.py)**

Nejvyšší total i crud.py coverage v celém experimentu. Tento run má EP coverage 42 % a error focus 66.67 % — model generoval error-heavy plán, který aktivoval branching logiku v crud.py (discount 100 %, update_stock 100 %, bulk_create 88.5 %, clone 37.5 %, add_item_to_order 18.8 %).

**Korelace response validation ↔ crud.py coverage**

| Level | Resp. Validation Avg | crud.py Avg | Vzorec |
|-------|---------------------|-------------|--------|
| L0 | 54.0% | 41.9% | Málo body checks → málo business logiky exercised |
| L1 | 90.0% | 50.0% | Body checks → business branching |
| L2 | 95.3% | 52.2% | Plateau na obou metrikách |
| L3 | 95.3% | 51.4% | Plateau — více EP ale ne hlubší |
| L4 | 97.3% | 53.2% | Mírný růst obou |

Response validation koreluje s crud.py coverage. Na L0 model kontroluje body jen v 54 % testů — většina testů jen ověří status kód, čímž neaktivuje validační logiku v crud.py. Na L1+ (90+ % body checks) testy aktivují response konstrukci v crud.py.

**H1b hodnocení: Ostrý skok code coverage L1→L2?**

Hypotéza H1b předpokládala ostrý skok code coverage při přechodu na white-box (L1→L2). Data DeepSeek toto **nepotvrzují** — skok L1→L2 je jen +1.0 p.b. total (+2.2 p.b. crud.py). Největší skok je **L0→L1 (+1.9 p.b. total, +8.1 p.b. crud.py)** — dokumentace, ne zdrojový kód, je primární driver code coverage pro DeepSeek. Toto je opačný vzorec než předpokládaný — black-box dokumentace je efektivnější než white-box zdrojový kód.

---

## Shrnutí klíčových zjištění

### RQ1: Validita a kvalita

1. **Vysoká baseline validity (98.67 %) již na L0** — DeepSeek nepotřebuje kontext pro generování funkčních testů. Monotónní růst dle H1a se **nepotvrdil**.
2. **L3–L4 mají paradoxně mírně nižší validity** (96.67–97.33 %) než L0–L2 (98.67 %) kvůli ambicióznějším ale timing-dependent testům.
3. **Assertion depth a response validation rostou** L0→L1 (+1.08 / +36 p.b.) a pak plateau. Klíčový přechod je L0→L1 (dokumentace), ne L1→L2 (zdrojový kód).
4. **Žádné helper kaskádové selhání** — na rozdíl od Gemini. UUID-based ISBN je stabilní across all levels.
5. **Rate limit test je systematický stale magnet** — 7/25 runů, neopravitelný repair loopem.

### RQ2: Testovací strategie

1. **EP coverage nejvyšší na L0** (40.8 %) — bez kontextu model „rozhazuje" testy široce. S kontextem se fokusuje (L1: 32.4 %).
2. **Happy path klesá** z 49 % (L0) na 37 % (L4) — **částečně potvrzuje H2a**.
3. **Status code diverzita roste** L2→L3 (+2.0) a L3→L4 (+1.4) — **potvrzuje H2b** (skok na L3 díky DB schématu, ne L2).
4. **Edge cases** mají U-tvar: 7.3 % (L0), minimum na L2 (0.7 %), pak opět 6.7 % (L3).

### RQ3: Základ pro cross-model porovnání

1. **Dominantní failure kategorie: wrong_status_code** (ne helper cascade jako u Gemini).
2. **Fix rate je nízký** (0–50 %) protože zbývající chyby po generování jsou principiálně neopravitelné.
3. **Cost-effectiveness je extrémní** — DeepSeek dosahuje 98+ % validity za ~$0.006/run (4× levnější než Gemini při 96.67 % validity).
4. **1 případ max_tokens truncation** (L1 Run 5) — edge case, neovlivnil validity ale zkreslil assertion depth metriku.

### Známé limitace specifické pro DeepSeek

1. **Rate limit test nedeterminismus:** `test_apply_discount_rate_limit` je neopravitelný — potřebuje `time.sleep()` mezi requesty, ale model to generuje nedeterministicky.
2. **max_tokens = 8192 je těsný:** L1 Run 5 narazil na limit. Pro robustnost doporučeno zvýšit na 16384.
3. **PIL import (1 případ):** Model na L2 použil `from PIL import Image` pro cover upload test — import sanitizer by eliminoval tento problém.

---

## Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 34.0% (17/50)
Assert Depth: 2.4
Response Validation: 63.33%
Stale: 0
Iterations: 1
Helpers: 6 (unique, create_author, create_category, create_book [stock=true, year=2020], create_tag, get_etag)
Compliance: 80 (missing timeout)
Status code diversity: 10
Failure taxonomy: 0 failures
Cost: $0.0041
Tokeny: 30,934 (24,609 in / 6,325 out)
```
</details>

<details>
<summary>L0 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 40.0% (20/50)
Assert Depth: 2.17
Response Validation: 56.67%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_author, create_category, create_book, create_tag)
Compliance: 80
Status code diversity: 10
Failure taxonomy: 0 failures
Cost: $0.0039
```
</details>

<details>
<summary>L0 — Run 3 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 42.0% (21/50)
Assert Depth: 2.23
Response Validation: 53.33%
Stale: 1 (test_update_order_status_valid)
Iterations: 3 (early stop)
Failure taxonomy: 1 failure — wrong_status_code
Never-fixed: test_update_order_status_valid (wrong_status_code: assert response.status_code == 200)
Cost: $0.0052
```
</details>

<details>
<summary>L0 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 46.0% (23/50)
Assert Depth: 1.87
Response Validation: 40.0%
Stale: 0
Iterations: 1
Status code diversity: 12 (nejvíce na L0)
Plan: 30/30 — error 66.67% (nejvyšší error podíl na L0)
Compliance: 80
Cost: $0.0039
```
</details>

<details>
<summary>L0 — Run 5 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 42.0% (21/50)
Assert Depth: 2.2
Response Validation: 56.67%
Stale: 1 (test_create_order_with_invalid_email_format)
Iterations: 3 (early stop)
Failure taxonomy: 1 failure — wrong_status_code (assert status == 422, API nepodporuje email validaci)
Compliance: 100 (jediný L0 run s timeout na všech voláních)
Cost: $0.0051
```
</details>

### L1

<details>
<summary>L1 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 32.0% (16/50)
Assert Depth: 2.77
Response Validation: 90.0%
Stale: 0
Iterations: 2
Failure taxonomy (iter 1): 1 failure — assertion_value_mismatch (discounted_price)
Fixed: test_apply_discount_to_old_book_200
Cost: $0.0055
```
</details>

<details>
<summary>L1 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 30.0% (15/50)
Assert Depth: 2.83
Response Validation: 86.67%
Stale: 1 (test_apply_discount_rate_limit_429)
Iterations: 3 (early stop)
Status code diversity: 12
Failure taxonomy: 1 — wrong_status_code (rate limit timing)
Cost: $0.0058
```
</details>

<details>
<summary>L1 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 32.0% (16/50)
Assert Depth: 2.8
Response Validation: 86.67%
Stale: 0
Iterations: 2
Fixed: test_apply_discount_to_old_book_200 (assertion_value_mismatch → opraveno)
Cost: $0.0052
```
</details>

<details>
<summary>L1 — Run 4 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 34.0% (17/50)
Assert Depth: 2.7
Response Validation: 93.33%
Stale: 1 (test_apply_discount_to_old_book_200)
Iterations: 3 (early stop)
Failure taxonomy: 1 — assertion_value_mismatch (discounted_price kalkulace neopravena)
Cost: $0.0056
```
</details>

<details>
<summary>L1 — Run 5 (100.0%) ✅ ⚠️ Truncation outlier</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 34.0% (17/50)
Assert Depth: 5.13 (OUTLIER — 2× vyšší než normál)
Avg Test Length: 21.97 řádků (OUTLIER)
Response Validation: 93.33%
Helper count: 1 (JEN unique!)
Avg HTTP calls: 3.53 (inline setup)
Chaining: 76.7% (inline HTTP call sequences)
Stale: 0
Iterations: 1
Completion tokens (generation): 8192 ← PŘESNĚ max_tokens limit
Cost: $0.0066

ANOMÁLIE: Model vygeneroval self-contained testy bez helper funkcí.
Completion tokens narazily na max_tokens=8192 ale kód byl náhodou
validní Python. Assertion depth 5.13 je statistický outlier.
```
</details>

### L2

<details>
<summary>L2 — Run 1 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 34.0% (17/50)
Assert Depth: 3.77
Response Validation: 96.67%
Stale: 1 (test_restore_soft_deleted_book)
Failure: assertion_value_mismatch (data["is_deleted"] == False — field neexistuje)
Cost: $0.0061
```
</details>

<details>
<summary>L2 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Iterations: 1, Stale: 0
Cost: $0.0055
```
</details>

<details>
<summary>L2 — Run 3 (96.67%) — PIL import</summary>

```
Validity: 96.67% (29/30)
Stale: 1 (test_upload_valid_cover_image)
Failure: other — img = Image.new('RGB', ...) — NameError: Image not defined
NOTE: Model použil from PIL import Image pro generování JPEG obálky.
PIL není v test prostředí dostupná. Import sanitizer by eliminoval.
Cost: $0.0062
```
</details>

<details>
<summary>L2 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Iterations: 1, Stale: 0
Assert Depth: 3.53
Compliance: 100
Cost: $0.0056
```
</details>

<details>
<summary>L2 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Iterations: 1, Stale: 0
Assert Depth: 3.47
Compliance: 100
Cost: $0.0053
```
</details>

### L3

<details>
<summary>L3 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 42.0% (21/50) — vysoké díky DB constraintům
Assert Depth: 2.83
Status code diversity: 12
Plan: happy_path 30%, error 66.67% — nejsilnější error focus
Compliance: 100
Cost: $0.0057
```
</details>

<details>
<summary>L3 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
Stale: 1 (test_apply_discount_rate_limit)
Status code diversity: 11
Cost: $0.0066
```
</details>

<details>
<summary>L3 — Run 3 (93.33%) — nejhorší L3</summary>

```
Validity: 93.33% (28/30)
EP Coverage: 38.0% (19/50)
Stale: 2 (rate_limit + restore)
Status code diversity: 14 (NEJVYŠŠÍ v experimentu)
Edge cases: 13.33% (4/30) — nejvíce edge cases
Helper count: 15 (MAXIMUM — CRUD wrappery pro všechny entity)
Cost: $0.0075
```
</details>

<details>
<summary>L3 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Iterations: 1, Stale: 0
Assert Depth: 3.5
Cost: $0.0055
```
</details>

<details>
<summary>L3 — Run 5 (93.33%)</summary>

```
Validity: 93.33% (28/30)
EP Coverage: 48.0% (24/50) — NEJVYŠŠÍ v celém experimentu
Stale: 2 (discount_new_book + bulk_partial)
Status code diversity: 14
Cost: $0.0066
```
</details>

### L4

<details>
<summary>L4 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 34.0% (17/50)
Assert Depth: 4.03 (nejvyšší ne-outlier)
Response Validation: 96.67%
Helpers: 6 (konzistentní sada s create_book(author_id, category_id, ...))
Compliance: 100
Cost: $0.0060
```
</details>

<details>
<summary>L4 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
Stale: 1 (rate_limit)
Status code diversity: 15
Cost: $0.0070
```
</details>

<details>
<summary>L4 — Run 3 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 44.0% (22/50)
Stale: 1 (rate_limit)
Status code diversity: 16 (MAXIMUM celého experimentu)
Plan: error 83.33% — NEJVYŠŠÍ error podíl (jen 3 happy path testy!)
Cost: $0.0072
```
</details>

<details>
<summary>L4 — Run 4 (93.33%) — regrese v repair</summary>

```
Validity: 93.33% (28/30)
Stale: 2 (rate_limit + bulk_partial)
Iterations: 5 (MAXIMUM — jediný DeepSeek run s 5 iteracemi)
Repair: regrese v iter 3 (+1 failing)
EP Coverage: 40.0% (20/50)
Cost: $0.0085 (NEJDRAŽŠÍ run)
```
</details>

<details>
<summary>L4 — Run 5 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Iterations: 1, Stale: 0
Assert Depth: 3.57
Compliance: 100
Cost: $0.0060
```
</details>