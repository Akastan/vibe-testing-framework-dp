# Analýza běhu: diplomka_v11 — Gemini 3.1 Flash Lite Preview

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM model | gemini-3.1-flash-lite-preview |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 50 endpointů v11 counting) |
| Max iterací | 5 |
| Runů na kombinaci | 5 |
| Testů na run | 30 |
| Temperature | 0.4 |
| Stale threshold | 2 (1× isolated + 1× helper se stejnou normalizovanou chybou) |

---

## RQ1: Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje validitu a sémantickou kvalitu LLM-generovaných API testů?

### Validity rate per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| **L0** | 86.67% | 80.0% | 86.67% | 63.33% | 60.0% | **75.33%** | 11.5 |
| **L1** | 76.67% | 43.33% | 83.33% | 96.67% | 86.67% | **77.33%** | 18.2 |
| **L2** | 43.33% | 96.67% | 90.0% | 100.0% | 96.67% | **85.33%** | 21.3 |
| **L3** | 96.67% | 96.67% | 100.0% | 93.33% | 96.67% | **96.67%** | 2.1 |
| **L4** | 100.0% | 100.0% | 100.0% | 93.33% | 90.0% | **96.67%** | 4.2 |

### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Validation (avg %) |
|-------|--------------------|----------------------------|
| L0 | 1.36 | 28.67 |
| L1 | 1.33 | 25.33 |
| L2 | 1.30 | 25.33 |
| L3 | 1.29 | 23.33 |
| L4 | 1.24 | 22.0 |

### Iterace ke konvergenci a stale testy

| Level | Iterace (avg) | Stale (avg) | Early stopped (z 5) |
|-------|---------------|-------------|----------------------|
| L0 | 3.6 | 7.4 | 5/5 |
| L1 | 3.6 | 6.8 | 5/5 |
| L2 | 3.0 | 4.4 | 4/5 |
| L3 | 2.8 | 1.0 | 4/5 |
| L4 | 2.2 | 1.0 | 3/5 |

### Analýza trendu L0→L4

**Celkový vzorec: monotónní růst validity s kontextem**

Validity roste od 75.33 % (L0) přes 77.33 % (L1) a 85.33 % (L2) k 96.67 % (L3 = L4). Klíčový skok nastává mezi L2 a L3 (+11.3 p.b.), na rozdíl od v10 kde byl klíčový skok L0→L1. L3 a L4 dosahují shodné průměrné validity 96.67 % s výrazně nižší variancí (std 2.1 a 4.2) oproti L0–L2 (std 11–21).

Neočekávané je, že L1 (77.33 %) je jen o 2 p.b. lepší než L0 (75.33 %). To je způsobeno outlierem L1 Run 2 (43.33 %), kde helper `create_book` generoval ISBN ve špatném formátu, což kaskádově shodilo 17 testů. Bez tohoto outlieru by L1 průměr činil ~85.8 %.

**L0: 75.33 % — vysoká variabilita, helper kaskádové selhání**

L0 má rozsah 60–87 %. Runy 4 a 5 (63.33 % a 60.0 %) jsou nejhorší v celém experimentu. Root cause je identická v obou: helper `create_book` generoval ISBN s hardcoded hodnotou `'1234567890123'`, což při prvním volání prošlo (201), ale při druhém vrátilo 409 (duplicate ISBN). Repair loop opravil ISBN na uuid-based formát `978-{uuid_hex[:10]}`, ale ten měl 14 znaků (API limit 13) → 422 string_too_long. Stale tracker poté testy zamkl.

Runy 1 a 3 (86.67 %) měly lepší výchozí ISBN generování (uuid-based od začátku) a selhaly pouze na 4–5 testech se špatnými status kódy (wrong_status_code).

**L1: 77.33 % — dokumentace nepomohla s helper kvalitou**

Překvapivě L1 nedosáhla výrazného zlepšení oproti L0. Příčina: 3 z 5 runů (Run 1, 2, 5) měly kaskádové selhání v `create_book` helperu (kategorie "other" — 13–16 failů z helperu). Dokumentace sice specifikuje správné formáty requestů, ale LLM (gemini-flash-lite) při temperature 0.4 stále generoval helpery s problematickým ISBN.

Run 4 (96.67 %) je důkazem, že L1 *může* fungovat — model vygeneroval správné helpery a selhal jen na `test_upload_cover_too_large` (wrong_status_code 413).

**L2: 85.33 % — zdrojový kód začíná pomáhat, ale outlier přetrvává**

L2 má bimodální distribuci: Run 1 (43.33 %) je outlier se stejným helper kaskádovým problémem (17 stale), zatímco zbylé 4 runy dosahují 90–100 %. Zdrojový kód endpointů umožňuje modelu vidět Pydantic validace a ISBN constraint (`max_length=13`), což v 4/5 runech vedlo ke správnému ISBN formátu.

**L3: 96.67 % — stabilní, DB schéma jako konsolidace**

L3 je nejstabilnější úroveň (std 2.1). Všech 5 runů dosáhlo ≥93.33 %. DB schéma přidává explicitní definice sloupců (ISBN VARCHAR(13)), což eliminuje ISBN problém. Zbývající selhání:
- `test_create_book_duplicate_isbn` (Run 1, 4) — helper volá create_book dvakrát se stejným ISBN, ale parametr `isbn=isbn` nefunguje kvůli helper signaturě
- `test_apply_discount_new_book_error` / `test_apply_discount_too_new_book` (Run 2, 4, 5) — discount boundary edge case (published_year 2026 vs. aktuální rok)

**L3→L4: Referenční testy — stabilita, ne zlepšení**

L4 dosahuje stejné průměrné validity (96.67 %) jako L3, s mírně vyšší variancí (std 4.2 vs. 2.1). Run 5 (90.0 %) je nejhorší L4 run kvůli timeout chybám na order-related testech. Referenční testy nepřinášejí validity boost oproti L3, ale zajišťují konzistentní helper architekturu (4 helpery ve všech runech).

### Srovnání s v10

| Metrika | v10 L0 | v11 L0 | v10 L1 | v11 L1 | v10 L3 | v11 L3 | v10 L4 | v11 L4 |
|---------|--------|--------|--------|--------|--------|--------|--------|--------|
| Validity avg | 91.33% | **75.33%** | 99.33% | **77.33%** | 100.0% | **96.67%** | 99.33% | **96.67%** |
| Std | 5.5 | **11.5** | 1.5 | **18.2** | 0.0 | **2.1** | 1.5 | **4.2** |
| Stale avg | 2.8 | **7.4** | 0.6 | **6.8** | 0.2 | **1.0** | 0.2 | **1.0** |

**Hlavní rozdíl v11 vs. v10:** v11 má výrazně horší výsledky na L0 a L1 kvůli agresivnějšímu stale trackeru v kombinaci s helper kaskádovými chybami. V10 měl stale threshold 3 (v11: threshold 2) a zřejmě méně agresivní normalizaci chyb. Změna endpoint countingu (34 → 50) ovlivňuje EP coverage metriku ale ne validity.

---

## RQ2: Testovací strategie — distribuce scénářů a pokrytí

### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg (%) |
|-------|-------|-------|-------|-------|-------|---------|
| L0 | 46.0 | 42.0 | 46.0 | 44.0 | 40.0 | **43.6** |
| L1 | 36.0 | 40.0 | 46.0 | 40.0 | 40.0 | **40.4** |
| L2 | 38.0 | 46.0 | 48.0 | 40.0 | 48.0 | **44.0** |
| L3 | 40.0 | 46.0 | 46.0 | 48.0 | 48.0 | **45.6** |
| L4 | 36.0 | 42.0 | 40.0 | 42.0 | 36.0 | **39.2** |

EP coverage je relativně stabilní (39–46 %) bez jasného trendu. V absolutních číslech pokrývají testy 18–24 endpointů z 50. L4 má paradoxně nejnižší EP coverage (39.2 %) — referenční testy zaměřují model na konkrétní endpointy z ukázky.

### Test type distribution (avg %)

| Level | Happy Path | Error | Edge Case |
|-------|-----------|-------|-----------|
| L0 | 37.3 | 50.7 | 12.0 |
| L1 | 28.0 | 70.0 | 2.0 |
| L2 | 38.0 | 60.0 | 2.0 |
| L3 | 30.7 | 66.7 | 2.7 |
| L4 | 38.7 | 55.3 | 6.0 |

L1 má nejvyšší podíl error testů (70 %) — dokumentace explicitně popisuje chybové stavy. L0 má nejvíce edge cases (12 %) — model bez kontextu experimentuje s hraničními hodnotami. Edge cases na L1–L3 téměř mizí (<3 %).

### Status code diversity (avg)

| Level | Avg unique codes |
|-------|-----------------|
| L0 | 12.8 |
| L1 | 14.0 |
| L2 | 15.2 |
| L3 | 15.0 |
| L4 | 15.2 |

Diverzita roste s kontextem (L0: 12.8 → L2+: ~15). Skok L0→L1 (+1.2) odráží znalost error kódů z dokumentace. L2+ plateau kolem 15 unikátních kódů.

### Code coverage per level (total)

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg | Std |
|-------|-------|-------|-------|-------|-------|-----|-----|
| **L0** | 65.6% | 66.3% | 66.8% | 61.1% | 61.1% | **64.2%** | 2.7 |
| **L1** | 66.6% | 57.2% | 66.5% | 67.4% | 69.3% | **65.4%** | 4.4 |
| **L2** | 59.5% | 70.2% | 69.2% | 71.9% | 70.4% | **68.2%** | 4.6 |
| **L3** | 68.5% | 72.6% | 71.7% | 70.2% | 70.4% | **70.7%** | 1.4 |
| **L4** | 71.4% | 70.7% | 70.2% | 74.5% | 65.9% | **70.5%** | 2.9 |

### Code coverage breakdown (crud.py vs main.py)

| Level | crud.py Avg | main.py Avg | Gap (main−crud) |
|-------|-------------|-------------|-----------------|
| L0 | 31.7% | 67.0% | 35.3 p.b. |
| L1 | 33.3% | 69.1% | 35.8 p.b. |
| L2 | 38.8% | 71.4% | 32.6 p.b. |
| L3 | 44.5% | 72.3% | 27.8 p.b. |
| L4 | 44.8% | 71.5% | 26.7 p.b. |

#### crud.py per run

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg |
|-------|-------|-------|-------|-------|-------|-----|
| L0 | 34.9% | 34.6% | 38.2% | 24.8% | 25.8% | **31.7%** |
| L1 | 35.9% | 16.8% | 34.9% | 37.5% | 41.3% | **33.3%** |
| L2 | 19.9% | 41.6% | 41.3% | 48.8% | 42.4% | **38.8%** |
| L3 | 40.3% | 47.0% | 45.2% | 45.0% | 45.2% | **44.5%** |
| L4 | 46.5% | 47.8% | 43.7% | 52.7% | 33.3% | **44.8%** |

#### main.py per run

| Level | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Avg |
|-------|-------|-------|-------|-------|-------|-----|
| L0 | 67.7% | 70.4% | 67.4% | 65.3% | 64.3% | **67.0%** |
| L1 | 69.7% | 62.6% | 70.8% | 70.4% | 71.8% | **69.1%** |
| L2 | 66.3% | 74.5% | 71.4% | 70.8% | 74.2% | **71.4%** |
| L3 | 70.4% | 75.9% | 74.8% | 70.1% | 70.4% | **72.3%** |
| L4 | 72.1% | 68.0% | 71.8% | 74.8% | 70.8% | **71.5%** |

### Code coverage analýza

**Celkový vzorec: monotónní růst L0→L3, plateau na L3=L4**

Total coverage roste od 64.2 % (L0) přes 65.4 % (L1) a 68.2 % (L2) k 70.7 % (L3), s plateau na L4 (70.5 %). Celkový skok L0→L3 je +6.5 p.b. Růst je silně ovlivněn outliery na L0–L2 (helper kaskádové selhání snižuje coverage). L3 a L4 mají nejnižší varianci (std 1.4 a 2.9) — stabilní validity = stabilní coverage.

L4 Run 5 (65.9 %, crud.py 33.3 %) je outlier — 3 stale testy (order-related timeouty) snížily coverage. Bez tohoto outlieru by L4 avg činil 71.7 %.

**crud.py: klíčový diferenciátor, skok L0→L3**

crud.py coverage je nejcitlivější metrika na kontextovou úroveň:
- **L0: 31.7 %** — helper cascade failures blokují business logiku
- **L1: 33.3 %** — marginální zlepšení, stále helper problémy (L1 Run 2: 16.8 %)
- **L2: 38.8 %** — zdrojový kód pomáhá (+5.5 p.b. vs. L1)
- **L3: 44.5 %** — DB schéma eliminuje ISBN problém (+5.7 p.b. vs. L2)
- **L4: 44.8 %** — plateau, referenční testy nepřidávají business coverage

Celkový skok L0→L3 na crud.py je **+12.8 p.b.** — výrazně silnější než na main.py (+5.3 p.b.). To potvrzuje, že kontext primárně ovlivňuje hloubku testování business logiky, ne šíři routing pokrytí.

**crud.py gap klesá s kontextem**

Gap (main.py − crud.py) klesá: L0 35.3 p.b. → L1 35.8 → L2 32.6 → **L3 27.8 → L4 26.7 p.b.** Testy na L3–L4 pronikají efektivněji do business vrstvy — gap pod 28 p.b. znamená, že testy aktivují branching logiku v crud.py (discount validation, order processing, stock management), ne jen routing.

**Korelace validity ↔ crud.py coverage**

| Run | Validity | crud.py | Vzorec |
|-----|----------|---------|--------|
| L0 Run 4 | 63.3% | 24.8% | helper cascade → nulová business coverage |
| L1 Run 2 | 43.3% | 16.8% | masivní cascade → nejnižší crud.py |
| L2 Run 1 | 43.3% | 19.9% | identický pattern |
| L2 Run 4 | 100.0% | 48.8% | 0 failů → business logika plně exercised |
| L4 Run 4 | 93.3% | 52.7% | nejlepší crud.py v experimentu |

Korelace je silná: runy s validity <50 % mají crud.py <20 %, runy s validity ≥93 % mají crud.py ≥44 %. Business logic coverage je proxy pro kvalitu testů.

---

## RQ3: Failure Analysis (základ pro cross-model porovnání)

### Failure taxonomy — první iterace (součet přes 5 runů)

| Typ selhání | L0 (45) | L1 (64) | L2 (40) | L3 (11) | L4 (8) |
|-------------|---------|---------|---------|---------|--------|
| wrong_status_code | 14 (31.1%) | 9 (14.1%) | 10 (25.0%) | 9 (81.8%) | 5 (62.5%) |
| other (helper cascade) | 29 (64.4%) | 53 (82.8%) | 29 (72.5%) | 2 (18.2%) | 1 (12.5%) |
| assertion_value_mismatch | 2 (4.4%) | 2 (3.1%) | 0 | 0 | 0 |
| timeout | 0 | 0 | 1 (2.5%) | 0 | 2 (25.0%) |

**Dominantní vzorec: helper kaskádové selhání ("other")**

Kategorie "other" — ve skutečnosti `AssertionError` v helper funkci `create_book` — tvoří 64–83 % selhání na L0–L2. Error summary je vždy varianta `b = create_book(a["id"], c["id"])`, kde helper assertion `assert r.status_code in (200, 201)` selže na 409 (duplicate ISBN) nebo 422 (ISBN too long).

Mechanismus: `create_book` generuje ISBN buď hardcoded (`'1234567890123'`) nebo s uuid ale ve špatném formátu (`978-{hex[:10]}` = 14 znaků, limit 13). První test projde, druhý+ test dostane 409 duplicate. Nebo po repair: uuid-based ISBN má 14 znaků → 422.

Na L3–L4 je "other" kategorie marginální (12–18 %) — zdrojový kód/DB schéma odhalují ISBN constraint.

**Wrong status code: zbytková chyba na L3–L4**

Na L3–L4 dominuje wrong_status_code (62–82 %), protože helper kaskádový problém je vyřešen. Konkrétní přetrvávající chyby:
- `test_bulk_create_partial_success` — model očekává 207 (Multi-Status), API vrací jiný kód. Přítomno ve **všech 25 runech** L0–L4 v 1. iteraci (opraveno v 60 % případů).
- `test_apply_discount_new_book_*` — discount boundary (published_year 2026 vs. aktuální rok). Neopravitelné bez explicitní znalosti.

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg never-fixed | Avg stale | Fix rate* |
|-------|---------------------|-----------------|-----------|-----------|
| L0 | 9.0 | 6.0 | 7.4 | 33.3% |
| L1 | 12.8 | 7.8 | 6.8 | 39.1% |
| L2 | 8.0 | 4.2 | 4.4 | 47.5% |
| L3 | 2.2 | 0.8 | 1.0 | 63.6% |
| L4 | 1.6 | 0.6 | 1.0 | 62.5% |

*Fix rate = (avg_failing_iter1 - avg_never_fixed) / avg_failing_iter1

Fix rate roste s kontextem (33 % L0 → 63 % L3+). L0–L1 mají nízký fix rate kvůli helper kaskádovým chybám, které jsou neopravitelné izolovanou opravou testů (root cause je v helperu).

### Per-level never-fixed vzorce

**L0 never-fixed endpointy (z 5 runů):**

| Endpoint/oblast | Výskyty | Root cause |
|-----------------|---------|------------|
| upload_cover (too_large + invalid_type) | 4 | helper cascade → ISBN → status 413/415 nikdy otestován |
| get_statistics / start_export | 4 | vyžaduje API key header, L0 neví |
| update_stock | 2 | PATCH query param vs. JSON body |
| create_order | 2 | book stock = 0 (default), insufficient |
| restore_book | 2 | helper cascade |

**L3–L4 never-fixed endpointy:**

| Test | Výskyty | Root cause |
|------|---------|------------|
| test_apply_discount_new_book_* | 4/5 (L3), 1/5 (L4) | discount boundary edge case |
| test_create_book_duplicate_isbn | 2/5 (L3) | helper signatura neumožňuje 2× isbn param |
| test_update_stock_insufficient | 1/5 (L4) | helper create_book nemá stock param |
| order-related timeouts | 1/5 (L4) | request chaining timeout |

---

## Repair Loop Analýza

### Efektivita repair strategií per level

| Level | Runy s helper_fallback | Helper fix rate | Isolated-only fix rate |
|-------|------------------------|-----------------|------------------------|
| L0 | 4/5 | Pomohl: 1/4 (Run 2) | Run 1: 1 fixed |
| L1 | 5/5 | Pomohl: 3/5 (Run 1,3,5) | — |
| L2 | 4/4 (1 run 100%) | Pomohl: 3/4 | — |
| L3 | 4/5 (1 run 100%) | Pomohl: 3/4 | — |
| L4 | 3/5 (2 runy 100%) | Pomohl: 3/3 | — |

### Detailní repair trajectory per run

**L0 — Run 2 (80.0 %, helper_fallback úspěšný)**
```
Iter 1: 18p/12f → isolated (10 opraveno, 0 stale)
Iter 2: 18p/12f → helper_fallback (12 attempted)
Iter 3: 24p/6f → isolated (2 opraveno, 4 stale)   ← helper_fallback pomohl (+6)
Iter 4: 24p/6f → all_stale_early_stop (6 stale)
Never-fixed: 6 (export, maintenance, restore, upload, statistics)
```

**L0 — Run 4 (63.33 %, helper_fallback neúspěšný)**
```
Iter 1: 19p/11f → isolated (10 opraveno, 0 stale)
Iter 2: 19p/11f → helper_fallback (11 attempted)
Iter 3: 19p/11f → isolated (1 opraveno, 10 stale)  ← helper nepomohl, všechny stale
Iter 4: 19p/11f → all_stale_early_stop (11 stale)
Never-fixed: 11 (všechny ISBN kaskáda + statistics)
```

**L1 — Run 2 (43.33 %, masivní kaskáda)**
```
Iter 1: 10p/20f → isolated (10 opraveno, 0 stale)
Iter 2: 11p/19f → helper_fallback (19 attempted)
Iter 3: 11p/19f → isolated (10 opraveno, 9 stale)
Iter 4: 13p/17f → all_stale_early_stop (17 stale)
Never-fixed: 17 — NEJHORŠÍ run celého experimentu
```

Root cause L1 Run 2: `create_book` helper generoval ISBN ve formátu `{uuid.uuid4().hex[:13]}` (13 hex znaků), ale API vyžaduje string max 13 znaků včetně prefixu. ISBN jako `"978abcdef1234"` má 13 znaků ale není validní formát (API očekává číselný ISBN). Isolated repair nepomohl (opravuje testy, ne helper). Helper repair změnil formát ale stále chybný. Stale tracker zamkl.

**L2 — Run 1 (43.33 %, identický pattern)**
```
Iter 1: 12p/18f → isolated (10 opraveno, 0 stale)
Iter 2: 13p/17f → helper_fallback (17 attempted)
Iter 3: 13p/17f → isolated (8 opraveno, 9 stale)
Iter 4: 13p/17f → all_stale_early_stop (17 stale)
Never-fixed: 17
```

### StaleTracker analýza

| Level | Stale avg | Max stale | Stale = never-fixed? |
|-------|-----------|-----------|----------------------|
| L0 | 7.4 | 12 (Run 5) | ~100% (stale ≈ never-fixed) |
| L1 | 6.8 | 17 (Run 2) | ~100% |
| L2 | 4.4 | 17 (Run 1) | ~100% |
| L3 | 1.0 | 2 (Run 4) | ~100% |
| L4 | 1.0 | 3 (Run 5) | ~100% |

**Kritický nález:** Stale testy jsou téměř vždy totožné s never-fixed testy. To naznačuje, že stale detection je příliš agresivní — zamyká testy které by potenciálně mohly být opraveny dalšími iteracemi, protože normalizace chyb (`_normalize_error`) nahrazuje čísla i stringy, čímž ztotožňuje odlišné chyby (409 duplicate ISBN ≠ 422 ISBN too long, ale po normalizaci obě = `Helper failed NNN: {STR}`).

---

## Outlier analýza

### L1 Run 2 — nejhorší run experimentu (43.33 %)

| Aspekt | Hodnota |
|--------|---------|
| Validity | 43.33 % (13/30) |
| Never-fixed | 17 testů |
| Stale | 17 |
| Root cause | create_book helper ISBN formát |
| Failure category | 80 % "other" (helper cascade) |
| EP Coverage | 40 % (20/50) |
| Repair attempts | 4 iterace, žádný zisk od iter 2 |

**Proč L1?** Na L1 by měla dokumentace specifikovat správný ISBN formát. Problém: gemini-flash-lite při temperature 0.4 vygeneroval helper s ISBN `{uuid.uuid4().hex[:13]}` — 13 hex znaků, ale API spec říká `max_length: 13` a reálně vyžaduje číselný ISBN. Dokumentace zmiňuje "unique ISBN" ale nespecifikuje formát přesněji. Model tedy splnil constraint délky ale ne formátu.

### L2 Run 1 — identický pattern na vyšší úrovni (43.33 %)

Identický root cause jako L1 Run 2. Zdrojový kód obsahuje Pydantic model s `isbn: str = Field(max_length=13)`, ale model při generování helperu nepoužil tuto informaci korektně. Po isolated repair se ISBN formát zhoršil (přidán prefix `978-` → 14+ znaků).

### L0 Run 5 — nejvíce stale testů (60.0 %)

12 stale testů, 12 never-fixed. Všech 10 "other" kategorií jsou helper cascade failures. Ani 1 test nebyl opravitelný po helper_fallback — helper repair změnil ISBN z hardcoded na uuid-based ale se špatnou délkou.

---

## Instruction Compliance

| Level | Missing timeout (avg %) | Compliance score (avg) | Runs s timeout |
|-------|------------------------|------------------------|----------------|
| L0 | 100% (5/5) | 80 | 0/5 |
| L1 | 0% (0/5) | 100 | 5/5 |
| L2 | 80% (4/5) | 84 | 1/5 (Run 5 missing) |
| L3 | 80% (4/5) | 84 | 1/5 (Run 2 missing) |
| L4 | 100% timeout | 100 | 5/5 |

Překvapivé: L1 má 100 % compliance (timeout na všech HTTP voláních ve všech 5 runech), zatímco L2–L3 mají 80 %. To je opačný vzorec oproti v10, kde L1 měl 80 % a L4 96 %. Možné vysvětlení: L1 dokumentace obsahuje explicitní zmínky o timeoutech, které model na L1 konzistentně dodržuje.

---

## Token Usage a Cost

### Per-level průměry

| Level | Avg calls | Avg prompt tokens | Avg completion tokens | Avg total | Avg cost ($) |
|-------|-----------|-------------------|-----------------------|-----------|--------------|
| L0 | 5.4 | 35,845 | 8,264 | 44,109 | $0.020 |
| L1 | 6.2 | 54,408 | 10,275 | 64,683 | $0.025 |
| L2 | 5.2 | 87,751 | 8,583 | 96,334 | $0.025 |
| L3 | 4.6 | 88,831 | 8,211 | 97,041 | $0.028 |
| L4 | 4.2 | 106,160 | 8,197 | 114,358 | $0.027 |

Prompt tokens rostou s kontextem (36K L0 → 106K L4) díky většímu kontextovému oknu. Completion tokens jsou stabilní (~8K). Cost roste mírně (0.020 → 0.028 $/run). Celkový cost za 25 runů: **~$0.63**.

### Cache utilization

Gemini caching je efektivní na L2+ kde kontext je větší:
- L0: avg 4,904 cached tokens (14 % z prompt)
- L1: avg 16,413 cached tokens (30 % z prompt)
- L2: avg 39,152 cached tokens (45 % z prompt)
- L3: avg 34,381 cached tokens (39 % z prompt)
- L4: avg 63,860 cached tokens (60 % z prompt)

---

## Helper architektura

### Helper count per level

| Level | Runs s 4 helpery | Runs s jiným počtem | Typická sada |
|-------|------------------|---------------------|--------------|
| L0 | 5/5 | 0 | unique, create_author, create_category, create_book |
| L1 | 5/5 | 0 | unique, create_author, create_category, create_book |
| L2 | 5/5 | 0 | unique, create_author, create_category, create_book |
| L3 | 4/5 | 1 (Run 2: +create_tag) | unique, create_author, create_category, create_book |
| L4 | 5/5 | 0 | unique, create_author, create_category, create_book |

Model konzistentně generuje 4 helpery. `create_book` je vždy přítomen a má:
- `has_stock_field`: true ve všech runech na všech úrovních
- `has_assertion`: true ve všech runech
- `default_published_year`: 2020 ve všech runech (důležité pro discount edge case)

### ISBN problém v create_book

| Level | Runs s ISBN problémem | Typ problému |
|-------|----------------------|--------------|
| L0 | 3/5 (Run 2, 4, 5) | Hardcoded ISBN '1234567890123' → duplicate 409 |
| L1 | 3/5 (Run 1, 2, 5) | UUID hex ISBN → wrong format/length |
| L2 | 2/5 (Run 1, 3) | UUID hex ISBN → wrong length after repair |
| L3 | 2/5 (Run 1, 4) | create_book(isbn=isbn) nefunguje |
| L4 | 0/5 | Referenční testy mají správný ISBN pattern |

ISBN problém je **cross-level** a je hlavní příčinou nízké validity na L0–L2. L4 ho eliminuje díky referenčním testům.

---

## Kontextová komprese

| Level | Original tokens | Compressed tokens | Savings (%) |
|-------|-----------------|-------------------|-------------|
| L0 | 30,741 | 15,958 | 48.1 |
| L1 | 38,876 | 23,783 | 38.8 |
| L2 | 59,487 | 43,917 | 26.2 |
| L3 | 60,341 | 44,770 | 25.8 |
| L4 | 69,009 | 53,438 | 22.6 |

OpenAPI spec komprese (48 %) je nejúčinnější. Zdrojový kód a testy se komprimují minimálně (2–4 %).

---

## Shrnutí klíčových zjištění

### RQ1: Validita a kvalita

1. **Monotónní růst validity L0→L3**, plateau na L3=L4 (96.67 %).
2. **L0–L2 jsou nestabilní** (std 11–21) kvůli helper kaskádovým chybám. L3–L4 jsou stabilní (std 2–4).
3. **ISBN helper bug je cross-level** a hlavní příčina selhání na L0–L2. Zdrojový kód (L2) a DB schéma (L3) postupně eliminují tento problém.
4. **Assertion depth klesá s kontextem** (L0: 1.36 → L4: 1.24) — paradox z v10 se nepotvrdil tak silně, ale trend přetrvává.
5. **Response validation klesá** (L0: 28.67 % → L4: 22.0 %) — model s více kontextem generuje méně defenzivní testy.

### RQ2: Testovací strategie

1. **EP coverage je stabilní** (39–46 %) bez jasného trendu.
2. **Error test podíl roste** s kontextem (L0: 51 % → L1: 70 %), pak klesá (L4: 55 %).
3. **Status code diverzita roste** L0→L2 (12.8 → 15.2), plateau na L2+.
4. **Edge cases jsou vzácné** na L1+ (<3 %) vs. L0 (12 %).

### RQ3: Failure patterns (pro cross-model porovnání)

1. **Helper kaskádové selhání** je dominantní kategorie na L0–L2 (64–83 %). Na L3–L4 je marginální.
2. **Wrong status code** je zbytková chyba na L3–L4 (62–82 %), typicky `bulk_create 207` a `discount boundary 400`.
3. **Fix rate roste** s kontextem (33 % L0 → 63 % L3+).
4. **Stale tracker je příliš agresivní** — normalizace ztotožňuje odlišné chyby, zamyká testy předčasně.

### Známé framework limitace (v11)

1. **Stale tracker normalizace:** `_normalize_error()` nahrazuje VŠECHNA čísla a stringy, čímž ztotožňuje různé chyby (409 != 422 ale normalizovaně stejné). → Opraveno ve v5 stale refresh logikou.
2. **Maintenance mode poisoning:** Test `toggle_maintenance_mode` může nechat API v maintenance stavu, následné testy dostávají 503. → Opraveno v phase4 v2 s maintenance recovery.
3. **No helper retry on progress:** Pokud helper repair změní chybu (progres), framework přepne na isolated místo retry helperu. → Opraveno ve v5 alternační logikou.

---

## Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1 (86.67%)</summary>

```
Validity: 86.67% (26/30)
EP Coverage: 46.0% (23/50)
Assert Depth: 1.33
Response Validation: 26.67%
Stale: 4 (test_export_books_accepted, test_get_stats_success, test_update_stock_success, test_upload_cover_too_large)
Iterations: 3 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Plan adherence: 100%
Compliance: 80 (missing timeout on all 35 calls)
Status code diversity: 14
Failure taxonomy (iter 1): 5 failures — wrong_status_code 4, assertion_value_mismatch 1
Repair: iter1=25p/5f→isolated, iter2=26p/4f→helper_fallback, iter3=26p/4f→all_stale
Never-fixed (4): test_export_books_accepted, test_get_stats_success, test_update_stock_success, test_upload_cover_too_large
Fixed (1): test_clone_book_success
Cost: $0.017
```
</details>

<details>
<summary>L0 — Run 2 (80.0%)</summary>

```
Validity: 80.0% (24/30)
EP Coverage: 42.0% (21/50)
Assert Depth: 1.43
Response Validation: 36.67%
Stale: 6 (export, statistics, restore, start_export, maintenance, upload_cover)
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Plan adherence: 100%
Compliance: 80
Status code diversity: 12
Failure taxonomy (iter 1): 12 failures — other 9 (create_book cascade), wrong_status_code 3
Repair: iter1=18p/12f→isolated, iter2=18p/12f→helper_fallback, iter3=24p/6f→isolated+4stale, iter4=all_stale(6)
Never-fixed (6): export, statistics, restore, start_export, maintenance, upload_cover
Fixed (6): discount, order, delete_book, get_deleted, etag, upload_cover_too_large
Cost: $0.020
NOTE: helper_fallback pomohl (+6 passed v iter 3)
```
</details>

<details>
<summary>L0 — Run 3 (86.67%)</summary>

```
Validity: 86.67% (26/30)
EP Coverage: 46.0% (23/50)
Assert Depth: 1.33
Response Validation: 26.67%
Stale: 4 (test_get_statistics_success, test_start_export_authorized, test_update_stock_valid, test_upload_cover_too_large)
Iterations: 3 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Plan adherence: 100%
Compliance: 80
Status code diversity: 13
Failure taxonomy (iter 1): 5 failures — wrong_status_code 4, assertion_value_mismatch 1
Repair: iter1=25p/5f→isolated, iter2=26p/4f→helper_fallback, iter3=26p/4f→all_stale
Never-fixed (4): statistics, export, stock_valid, cover_too_large
Fixed (1): test_clone_book_valid
Cost: $0.021
```
</details>

<details>
<summary>L0 — Run 4 (63.33%) ⚠️</summary>

```
Validity: 63.33% (19/30)
EP Coverage: 44.0% (22/50)
Assert Depth: 1.33
Response Validation: 26.67%
Stale: 11
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Plan adherence: 96.67%
Compliance: 80
Status code diversity: 13
Failure taxonomy (iter 1): 11 failures — other 10 (create_book cascade!), wrong_status_code 1
Repair: iter1=19p/11f→isolated, iter2=19p/11f→helper_fallback, iter3=19p/11f→isolated+10stale, iter4=all_stale(11)
Never-fixed (11): 10× helper cascade + statistics
Fixed (0): ŽÁDNÝ test nebyl opraven!
Cost: $0.021

ROOT CAUSE: create_book ISBN '1234567890123' hardcoded → 409 duplicate. Repair: '978-{hex[:10]}' = 14 chars → 422 too_long. Stale po 2 iteracích.
```
</details>

<details>
<summary>L0 — Run 5 (60.0%) ⚠️ Nejhorší L0 run</summary>

```
Validity: 60.0% (18/30)
EP Coverage: 40.0% (20/50)
Assert Depth: 1.37
Response Validation: 26.67%
Stale: 12 (NEJVÍCE v celém experimentu)
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author(name=None), create_category(name=None), create_book(author_id, category_id, title=None) [stock=true, year=2020])
Plan adherence: 100%
Compliance: 80
Status code diversity: 12
Failure taxonomy (iter 1): 12 failures — other 10, wrong_status_code 2
Repair: iter1=18p/12f→isolated, iter2=18p/12f→helper_fallback, iter3=18p/12f→isolated+10stale, iter4=all_stale(12)
Never-fixed (12): 10× helper cascade + export + statistics
Fixed (0): ŽÁDNÝ test nebyl opraven!
Cost: $0.024

ROOT CAUSE: Identický s Run 4. create_book ISBN hardcoded → 409 → repair → 422. helper_fallback nepomohl.
```
</details>

### L1

<details>
<summary>L1 — Run 1 (76.67%)</summary>

```
Validity: 76.67% (23/30)
EP Coverage: 36.0% (18/50)
Assert Depth: 1.30
Response Validation: 23.33%
Stale: 7
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book(isbn=None) [stock=true, year=2020])
Compliance: 100 (timeout on all 41 calls)
Status code diversity: 12
Failure taxonomy (iter 1): 17 failures — other 16 (create_book cascade!), wrong_status_code 1
Repair: iter1=13p/17f→isolated, iter2=13p/17f→helper_fallback, iter3=21p/9f→isolated+7stale, iter4=23p/7f→all_stale
Never-fixed (7): discount, dup_isbn, restore(2x), stock(2x), upload_cover
Fixed (10): discount_rate_limit, bulk, order(2x), review(2x), get_book, invoice, order_status, upload_cover_large
Cost: $0.026
NOTE: helper_fallback pomohl (+8 passed v iter 3)
```
</details>

<details>
<summary>L1 — Run 2 (43.33%) ⚠️ Nejhorší run experimentu</summary>

```
Validity: 43.33% (13/30)
EP Coverage: 40.0% (20/50)
Assert Depth: 1.30
Response Validation: 33.33%
Stale: 17 (MAXIMUM)
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Compliance: 100
Status code diversity: 16 (paradoxně nejvyšší)
Failure taxonomy (iter 1): 20 failures — other 16, wrong_status_code 3, assertion_mismatch 1
Repair: iter1=10p/20f→isolated, iter2=11p/19f→helper_fallback, iter3=11p/19f→isolated+9stale, iter4=13p/17f→all_stale(17)
Never-fixed (17): MASIVNÍ helper cascade — 14× create_book failure, 2× wrong_status, 1× assertion
Fixed (3): bulk_partial, dup_isbn, pagination_limit
Cost: $0.029

ROOT CAUSE: create_book ISBN uuid hex format → nevalidní pro API. Identický pattern jako L0 Run 4/5.
```
</details>

<details>
<summary>L1 — Run 3 (83.33%)</summary>

```
Validity: 83.33% (25/30)
EP Coverage: 46.0% (23/50)
Assert Depth: 1.50
Response Validation: 36.67%
Stale: 5
Iterations: 3 (early stop)
Helpers: 4 (unique, create_author(name=None), create_category(name=None), create_book(isbn=None) [stock=true, year=2020])
Compliance: 100
Status code diversity: 13
Failure taxonomy (iter 1): 10 failures — other 8, assertion_mismatch 2
Repair: iter1=20p/10f→isolated, iter2=21p/9f→helper_fallback, iter3=25p/5f→all_stale(5)
Never-fixed (5): clone_dup_isbn, order(2x), health_check, restore_active
Fixed (5): get_soft_deleted, review, stock, tags, pagination
Cost: $0.025
NOTE: helper_fallback pomohl (+4 passed)
```
</details>

<details>
<summary>L1 — Run 4 (96.67%) ✅ Nejlepší L1 run</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 40.0% (20/50)
Assert Depth: 1.30
Response Validation: 13.33%
Stale: 1 (test_upload_cover_too_large)
Iterations: 3 (early stop)
Helpers: 4 (unique, create_author(name=None), create_category(name=None), create_book(isbn=None) [stock=true, year=2020])
Compliance: 100
Status code diversity: 15
Failure taxonomy (iter 1): 3 failures — wrong_status_code 2, assertion_mismatch 1
Repair: iter1=27p/3f→isolated, iter2=29p/1f→helper_fallback, iter3=29p/1f→all_stale(1)
Never-fixed (1): test_upload_cover_too_large
Fixed (2): bulk_partial, pagination
Cost: $0.024
```
</details>

<details>
<summary>L1 — Run 5 (86.67%)</summary>

```
Validity: 86.67% (26/30)
EP Coverage: 40.0% (20/50)
Assert Depth: 1.27
Response Validation: 20.0%
Stale: 4
Iterations: 4 (early stop)
Helpers: 4 (unique, create_author, create_category, create_book [stock=true, year=2020])
Compliance: 100
Status code diversity: 14
Failure taxonomy (iter 1): 14 failures — other 13 (create_book cascade), wrong_status_code 1
Repair: iter1=16p/14f→isolated, iter2=16p/14f→helper_fallback, iter3=25p/5f→isolated+4stale, iter4=26p/4f→all_stale
Never-fixed (4): order(2x), restore, upload_cover
Fixed (10): discount(2x), bulk, clone, review, book_not_modified, invoice, stock(2x), status_transition
Cost: $0.023
NOTE: helper_fallback pomohl (+9 passed v iter 3)
```
</details>

### L2

<details>
<summary>L2 — Run 1 (43.33%) ⚠️ Outlier</summary>

```
Validity: 43.33% (13/30)
EP Coverage: 38.0% (19/50)
Stale: 17
Failure taxonomy (iter 1): 18 failures — other 15 (create_book cascade), wrong_status_code 3
Repair: iter1=12p/18f→isolated, iter2=13p/17f→helper_fallback, iter3=13p/17f→isolated+9stale, iter4=all_stale(17)
Never-fixed (17): Identický pattern jako L1 Run 2
Fixed (1): create_book_duplicate_isbn
Cost: $0.029
```
</details>

<details>
<summary>L2 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30), Stale: 1 (test_apply_discount_new_book_error)
Repair: iter1=27p/3f→isolated, iter2=29p/1f→helper_fallback, iter3=all_stale(1)
Fixed (2): bulk_partial, pagination_limit. Cost: $0.030
```
</details>

<details>
<summary>L2 — Run 3 (90.0%)</summary>

```
Validity: 90.0% (27/30), Stale: 3
Failure taxonomy (iter 1): 17 failures — other 14 (cascade), wrong_status 2, timeout 1
Repair: iter1=13p/17f→isolated, iter2=13p/17f→helper_fallback, iter3=26p/4f→isolated+3stale, iter4=27p/3f→all_stale
Never-fixed (3): discount_new_book, create_book_success, restore_not_deleted
Fixed (14): helper_fallback pomohl masivně (+13)
Cost: $0.027
```
</details>

<details>
<summary>L2 — Run 4 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Stale: 0, Iterations: 1
0 failures in iter 1. Cost: $0.021
```
</details>

<details>
<summary>L2 — Run 5 (96.67%)</summary>

```
Validity: 96.67% (29/30), Stale: 1 (test_discount_new_book_400)
Repair: iter1=28p/2f→isolated, iter2=29p/1f→helper_fallback, iter3=all_stale(1)
Fixed (1): bulk_partial_success. Cost: $0.019
```
</details>

### L3

<details>
<summary>L3 — Run 1 (96.67%)</summary>

```
Validity: 96.67% (29/30), Stale: 1 (test_create_book_duplicate_isbn)
Empty tests: 1 (test_apply_discount_too_new)
Repair: iter1=28p/2f→isolated, iter2=29p/1f→helper_fallback, iter3=all_stale(1)
Fixed (1): bulk_partial. Cost: $0.022
```
</details>

<details>
<summary>L3 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30), Stale: 1 (test_apply_discount_new_book_error)
Helpers: 5 (added create_tag)
Compliance: 80 (missing timeout on 41 calls)
Repair: iter1=28p/2f→isolated, iter2=29p/1f→helper_fallback, iter3=all_stale(1)
Fixed (1): bulk_partial. Cost: $0.031
```
</details>

<details>
<summary>L3 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Stale: 0, Iterations: 2
iter 1: 28p/2f → isolated(2) → iter 2: 30p/0f ✅
Fixed (2): discount_new_book, bulk_partial. Cost: $0.030
```
</details>

<details>
<summary>L3 — Run 4 (93.33%)</summary>

```
Validity: 93.33% (28/30), Stale: 2 (discount_too_new, dup_isbn)
Repair: iter1=27p/3f→isolated, iter2=28p/2f→helper_fallback, iter3=all_stale(2)
Fixed (1): bulk_partial. Cost: $0.032
```
</details>

<details>
<summary>L3 — Run 5 (96.67%)</summary>

```
Validity: 96.67% (29/30), Stale: 1 (test_apply_discount_new_book_error)
Repair: iter1=28p/2f→isolated, iter2=29p/1f→helper_fallback, iter3=all_stale(1)
Fixed (1): bulk_partial. Cost: $0.026
```
</details>

### L4

<details>
<summary>L4 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Stale: 0, Iterations: 1
0 failures. Compliance: 100 (timeout on all 40 calls). Cost: $0.038
```
</details>

<details>
<summary>L4 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Stale: 0, Iterations: 2
iter 1: 29p/1f (bulk_partial wrong_status) → isolated → iter 2: 30p/0f ✅
Compliance: 100. Cost: $0.022
```
</details>

<details>
<summary>L4 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30), Stale: 0, Iterations: 2
iter 1: 29p/1f (bulk_partial wrong_status) → isolated → iter 2: 30p/0f ✅
Compliance: 100. Cost: $0.030
```
</details>

<details>
<summary>L4 — Run 4 (93.33%)</summary>

```
Validity: 93.33% (28/30), Stale: 2 (discount_new_book, update_stock_insufficient)
Failure taxonomy: 2× "other" (helper create_book s extra params published_year=2026 a stock=2 nekompatibilní s helper signaturou)
Repair: iter1=28p/2f→isolated, iter2=28p/2f→helper_fallback, iter3=all_stale(2)
Compliance: 100. Cost: $0.024
```
</details>

<details>
<summary>L4 — Run 5 (90.0%)</summary>

```
Validity: 90.0% (27/30), Stale: 3 (create_order, invoice_pending, status_transition)
Failure taxonomy: 2× wrong_status_code, 2× timeout (order-related chaining)
Repair: iter1=26p/4f→isolated, iter2=27p/3f→helper_fallback, iter3=all_stale(3)
Compliance: 100. Cost: $0.020
```
</details>