# Analýza běhu: diplomka_v9 — 2026-03-24

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM modely | gemini-3.1-flash-lite-preview |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | bookstore (FastAPI + SQLite, 34 endpointů) |
| Iterací | 5 |
| Runů na kombinaci | 3 |
| Testů na run | 30 |
| Stale threshold | 3 |

---

## RQ1: Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje kvalitu LLM-generovaných API testů?

### Validity rate per level

| Level | Run 1 | Run 2 | Run 3 | Avg ± Std |
|-------|-------|-------|-------|-----------|
| L0 | 93.33% | 96.67% | 93.33% | 94.44% ± 1.9 |
| L1 | 100.0% | 100.0% | 100.0% | **100.0% ± 0.0** |
| L2 | 100.0% | 96.67% | 100.0% | 98.89% ± 1.9 |
| L3 | 100.0% | **40.0%** | 100.0% | 80.0% ± 34.6 |
| L4 | 96.67% | 96.67% | 100.0% | 97.78% ± 1.9 |

### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Validation (avg) |
|-------|--------------------|---------------------------|
| L0 | 1.81 | 62.22% |
| L1 | 1.29 | 27.78% |
| L2 | 1.38 | 37.78% |
| L3 | 1.59 | 47.78% |
| L4 | 1.49 | 45.55% |

### Iterace ke konvergenci a stale testy

| Level | Iterace (avg) | Stale (avg) |
|-------|---------------|-------------|
| L0 | 5.0 | 1.67 |
| L1 | 1.67 | 0.33 |
| L2 | 3.0 | 0.67 |
| L3 | 2.33 | 3.33 |
| L4 | 3.67 | 0.67 |

### Analýza trendu L0→L4

**L0→L1: Největší kvalitativní skok — dokumentace jako klíčový faktor validity**

Přechod z L0 na L1 je nejvýznamnější změna v celém experimentu. Přidání `api_knowledge` (7 explicitních pravidel o chování API) zvýšilo validitu z 94,44 % na 100 % ve všech třech runech s nulovou variancí.

Kauzální mechanismus: L0 model disponoval pouze OpenAPI specifikací a musel inferovat chování API. To vedlo ke třem kategoriím selhání: (1) špatné status kódy — model očekával 200 na POST místo 201, nebo 422 místo 404 pro neexistující zdroje; (2) špatný formát requestů — model posílal JSON body na PATCH /stock místo query parametru, což způsobovalo timeouty nebo neočekávané odpovědi; (3) chybějící prerekvizity — model nevěděl, že stock default je 0, takže objednávkové testy selhávaly na „insufficient stock".

Kvantitativní důkaz: L0 měl v první iteraci průměrně 11,0 selhání (33 celkem přes 3 runy). L1 měl 0,33 (1 selhání celkem přes 3 runy — discount edge case v Run 2). L0 potřeboval všech 5 iterací repair loopu, L1 konvergoval v průměru za 1,67 iterace.

Paradox assertion depth: L0 má nejvyšší assertion depth (1.81) a response validation (62.22 %), zatímco L1 má nejnižší (1.29 / 27.78 %). Vysvětlení: bez znalosti API kontraktu model kompenzuje nejistotu „defenzivním" testováním — přidává více asercí na strukturu response body, protože neví, co je spolehlivé. L1 model zná přesné chování API a generuje cílené minimalistické testy (typicky jen assert na status code + jedno klíčové pole). Vyšší assertion depth na L0 tedy neznamená vyšší kvalitu — značná část asercí je nesprávná (proto 33 selhání v první iteraci). Jedná se o přechod z explorativního do deterministického režimu generování.

**L1→L2: Zdrojový kód přináší marginální přidanou hodnotu**

Přidání zdrojového kódu endpointů (~1082 řádků, ~11 474 tokenů) zvýšilo kontext o 50 %, ale nepřineslo kvalitativní skok. Validita mírně klesla na 98.89 % (1 selhání v Run 2 z 90 testů — `test_list_reviews_malformed_query_params`). Iterace vzrostly z 1.67 na 3.0. Assertion depth se mírně zvýšila (1.29 → 1.38) a response validation vzrostla o 10 p.b. (27.78 % → 37.78 %).

Kauzální mechanismus: Zdrojový kód je z velké části redundantní s `api_knowledge` — model z kódu může vyčíst, že POST handler vrací `status_code=201`, ale tuto informaci již má z dokumentace. Mírné zlepšení response validation naznačuje, že model vidí strukturu response objektů (Pydantic modely, návratové typy) a na jejich základě přidává kontroly response body. Nárůst iterací je varovný signál — větší kontext může vést k pokusům testovat implementační detaily (viz `test_list_reviews_malformed_query_params`, kde se model pokusil testovat query parsing, který není ve specifikaci).

Interpretace: Pro black-box testování na HTTP úrovni je zdrojový kód redundantní. Ukazuje JAK je API implementováno, ale testy potřebují vědět CO API dělá. Klíčové behaviorální informace jsou již v `api_knowledge`.

**L2→L3: DB schéma — žádné zlepšení, zvýšené riziko nestability**

Přidání DB schématu (~77 řádků, ~929 tokenů) je z hlediska velikosti kontextu nejmenší přírůstek, ale z hlediska dopadu nejrizikovější. Průměrná validita klesla na 80.0 %, ale toto číslo je zavádějící — je téměř výhradně způsobeno outlierem v Run 2 (40 %). Bez outlieru by L3 mělo 100 % validity (Run 1 a Run 3 oba 100 % v 1. iteraci). Směrodatná odchylka vyskočila na 34.6 — nejvyšší v celém experimentu.

Kauzální mechanismus (bimodální chování): DB schéma obsahuje informace o datové vrstvě (typy sloupců, constrainty, foreign keys), které jsou pro HTTP-level testování z velké části irelevantní. Model nemůže přímo otestovat DB constraint přes API — musí je testovat nepřímo. V Run 1 a Run 3 model zvolil konzervativní strategii (4 helpery, stejný vzor jako L1–L2) a dosáhl 100 % validity. V Run 2 zvolil „ambiciózní" strategii (6 helperů včetně `update_stock` a `delete_book_tags`, oba s asercemi) a selhal katastrofálně. DB schéma tedy zvyšuje pravděpodobnost, že model vytvoří nadměrně komplexní testovací architekturu, ale negarantuje to — závisí na nedeterminismu LLM.

Klíčový poznatek: Více kontextu ≠ lepší výsledky. DB schéma zvyšuje komplexitu promptu bez odpovídajícího informačního přínosu pro HTTP-level testování. Podrobná analýza outlieru viz sekce „L3 Run 2 outlier".

**L3→L4: Referenční testy stabilizují formu, ne obsah**

Přidání referenčních testů (~490 řádků, ~5759 tokenů) zvýšilo validitu zpět na 97.78 % a zejména stabilizovalo instruction compliance na 100 (vs. 80 na L1–L2). Missing timeout kleslo na 0 % (vs. 100 % na L1–L2). Variabilita se vrátila na 1.9 std.

Kauzální mechanismus: Referenční testy fungují jako in-context few-shot příklady. Model se z nich učí dodržovat formální pravidla (timeout na každém volání, pojmenování helperů, struktura testu). Instruction compliance vyskočila na 100 % — model replikuje vzor `timeout=30`, který vidí v referenčních testech. Jde o klasický příklad, že ukázkový kód je účinnější než psaná instrukce.

Paradox L4: Assertion depth (1.49) a response validation (45.55 %) se nezlepšily oproti L3 ani oproti L0. Referenční testy by měly být „nejsilnějším" kontextem, ale model je využívá primárně pro formální compliance, nikoliv pro obsahovou kvalitu. Endpoint coverage je na L4 nejnižší (49.02 %) — model se „zamyká" do vzorů referenčních testů a pokrývá menší škálu endpointů.

### Shrnutí RQ1

L1 (api_knowledge) je jednoznačně nejdůležitější kontextová vrstva: přináší skok na 100 % validitu s nulovou variancí a minimální potřebou repair loopu. Další vrstvy (L2 zdrojový kód, L3 DB schéma, L4 referenční testy) přinášejí marginální nebo žádné zlepšení validity a v případě L3 zvyšují riziko katastrofálního selhání. Assertion depth paradoxně klesá s kontextem (L0 > L1), protože model s více informacemi generuje cílenější, minimalistické testy — efektivnější, ale měřitelně „plytší". Jedná se o trade-off: validita vs. hloubka.

---

## RQ2: Jak se liší endpoint coverage a code coverage vygenerovaných testů mezi jednotlivými úrovněmi kontextu?

### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Avg | Std |
|-------|-------|-------|-------|-----|-----|
| L0 | 61.76% | 52.94% | 61.76% | 58.82% | 5.1 |
| L1 | 55.88% | 52.94% | 52.94% | 53.92% | 1.7 |
| L2 | 50.0% | 55.88% | 52.94% | 52.94% | 2.9 |
| L3 | 61.76% | 47.06% | 58.82% | 55.88% | 7.8 |
| L4 | 47.06% | 55.88% | 44.12% | 49.02% | 6.1 |

### Code coverage per level

| Level | Run 1 | Run 2 | Run 3 | Avg | Std |
|-------|-------|-------|-------|-----|-----|
| L0 | 82.7% | 79.4% | 84.4% | 82.2% | 2.6 |
| L1 | 85.8% | 84.1% | 86.1% | **85.4%** | 1.1 |
| L2 | 84.1% | 84.6% | 83.9% | 84.2% | 0.3 |
| L3 | 86.8% | **65.8%** | 83.8% | 78.8% | 11.3 |
| L4 | 83.0% | 85.0% | 82.7% | 83.6% | 1.3 |

### Code coverage breakdown (crud.py vs main.py)

| Level | crud.py Run 1 | Run 2 | Run 3 | crud.py Avg | main.py Run 1 | Run 2 | Run 3 | main.py Avg |
|-------|---------------|-------|-------|-------------|---------------|-------|-------|-------------|
| L0 | 64.3% | 58.1% | 68.8% | 63.7% | 89.3% | 86.1% | 88.5% | 88.0% |
| L1 | 72.4% | 68.4% | 73.2% | 71.3% | 87.7% | 87.7% | 87.7% | 87.7% |
| L2 | 68.4% | 69.5% | 68.4% | 68.8% | 87.7% | 87.7% | 86.9% | 87.4% |
| L3 | 73.5% | **31.3%** | 67.7% | 57.5% | 90.2% | **75.4%** | 87.7% | 84.4% |
| L4 | 66.5% | 70.6% | 65.8% | 67.6% | 86.1% | 87.7% | 86.1% | 86.6% |

### Další metriky kvality

| Level | Test Type: Happy (avg) | Test Type: Error (avg) | Test Type: Edge (avg) | Status Code Diversity (avg) |
|-------|------------------------|------------------------|-----------------------|-----------------------------|
| L0 | 66.7% | 31.1% | 2.2% | 5.0 |
| L1 | 53.3% | 46.7% | 0% | 7.0 |
| L2 | 52.2% | 46.7% | 1.1% | 7.0 |
| L3 | 52.2% | 47.8% | 0% | 6.7 |
| L4 | 48.9% | 48.9% | 2.2% | 7.0 |

### Analýza

**Endpoint coverage: klesající trend s rostoucím kontextem**

EP coverage mírně klesá s přibývajícím kontextem: L0 (58.82 %) → L4 (49.02 %). Pokles není monotónní (L3 má mírný nárůst díky Run 1 s 61.76 %), ale trend je zřetelný.

Kauzální mechanismus — efekt zaměření: S rostoucím kontextem model získává detailnější informace o chování endpointů a zaměřuje se na testování specifických behaviorálních scénářů (error cases, edge cases) namísto plošného pokrytí. L0 bez kontextu „rozhazuje síť" přes co nejvíce endpointů, protože nemá důvod upřednostňovat jeden nad druhým. L4 s referenčními testy se koncentruje na endpointy pokryté v referenčních testech a nekriticky tento výběr kopíruje. Distribuce typů testů tento trend potvrzuje: L0 generuje 66.7 % happy path (jedno volání na endpoint = širší pokrytí), L4 generuje jen 48.9 % happy path a 48.9 % error testů (víc testů na méně endpointů).

Experimentální omezení: Fixní limit 30 testů na run při 34 endpointech API znamená, že 100 % EP coverage je prakticky nedosažitelná — model musí volit, které endpointy testovat. S kontextem volí „důležitější" endpointy, bez kontextu volí šířeji.

**Code coverage: stabilní navzdory klesajícímu EP coverage**

Code coverage zůstává překvapivě stabilní: 82.2 %–85.4 % (po vyloučení L3 outlieru). Toto je důležitý nález — i když EP coverage klesá, code coverage neklesá proporcionálně.

Vysvětlení: Code coverage měří řádky kódu, ne endpointy. Většina kódu `main.py` (routing, middleware, error handling) se aktivuje při jakémkoli API volání. I test na jeden endpoint spouští značnou část `main.py`. Rozhodující je pokrytí `crud.py` (business logika), které vyžaduje specifické scénáře pro aktivaci branching logiky.

Paradox L1: L1 má nejvyšší code coverage (85.4 %) i přes nižší EP coverage (53.92 %) než L0 (58.82 %). To znamená, že L1 testy, byť pokrývají méně endpointů, procházejí hlubšími větvemi kódu — díky správnému testování error cases, které aktivují branching logiku v CRUD operacích. L1 má zároveň nejvyšší `crud.py` coverage (71.3 %) a nejmenší gap mezi `crud.py` a `main.py` (16.4 p.b.), což potvrzuje hloubku testování.

**crud.py vs main.py: indikátor hloubky testování**

`main.py` (routing) má stabilně vysoké pokrytí (86–88 %) napříč levely — každé HTTP volání prochází routing vrstvou. `crud.py` (business logika) je variabilnější (57.5–71.3 %) a citlivější na kvalitu testů. L3 Run 2 outlier dramaticky táhne `crud.py` průměr dolů (31.3 %), protože 17 z 18 failing testů nedorazilo za helper `create_book` — selhaly na ISBN validaci před tím, než stihly pokrýt jakoukoliv business logiku.

Implikace: „Plytké" testy (jen happy path na hodně endpointů) pokrývají `main.py` efektivně, ale neprocházejí business logikou. „Hluboké" testy (error/edge cases na méně endpointech) mají nižší EP coverage, ale vyšší `crud.py` coverage. `crud.py` coverage je tedy lepší indikátor kvality testů než `main.py` coverage.

**Test type distribution: posun od happy path k error testům**

S rostoucím kontextem klesá podíl happy path testů (66.7 % L0 → 48.9 % L4) a roste podíl error testů (31.1 % → 48.9 %). L0 bez znalosti chybových stavů preferuje „bezpečné" testy. S kontextem model ví o validacích, unikátních klíčích, neexistenci zdrojů a systematicky testuje tyto scénáře. Vyšší podíl error testů je známkou profesionálnějšího testování — nejde jen o to, že API funguje za ideálních podmínek, ale že správně reaguje na chybné vstupy.

Edge cases zůstávají marginální (0–2.2 %) napříč levely. Gemini-3.1-flash-lite-preview zjevně neprodukuje edge case testy bez explicitního vedení.

**Status code diversity**

L0 používá 5 unikátních kódů (200, 201, 204, 404, 422), L1+ používá 7 (+ 400, 409). Nárůst odpovídá explicitním informacím v `api_knowledge`, která zmiňuje 400 pro špatné požadavky, 404 pro nenalezené zdroje a 409 pro konflikty. L0 „halucinuje" 404 z HTTP konvencí — viz analýza v RQ3.

---

## RQ3: Jaké typy selhání se vyskytují ve vygenerovaných testech a jak se jejich distribuce mění s rostoucím kontextem?

### Failure taxonomy (první iterace, součet přes 3 runy)

| Typ selhání | L0 (33 failů) | L1 (1 fail) | L2 (2 faily) | L3 (18 failů) | L4 (2 faily) |
|-------------|---------------|-------------|--------------|----------------|--------------|
| wrong_status_code | 6 (18.2%) | 1 (100%) | 2 (100%) | 1 (5.6%) | 1 (50%) |
| timeout | 13 (39.4%) | 0 | 0 | 9 (50.0%)* | 0 |
| assertion_mismatch | 1 (3.0%) | 0 | 0 | 0 | 1 (50%) |
| other | 13 (39.4%) | 0 | 0 | 8 (44.4%)* | 0 |

*⚠️ **Taxonomická korekce pro L3 Run 2:** Analýza surového pytest logu (viz sekce L3 Run 2 outlier) odhalila, že 9 selhání klasifikovaných jako „timeout" a 8 jako „other" jsou ve skutečnosti všechna `KeyError: 'id'`. Diagnostický parser (`phase6_diagnostics.py`) špatně klasifikoval tyto chyby, protože regex narazil na substring `timeout=30` v traceback řádku (ten obsahuje parametr timeout z HTTP volání, nikoliv skutečný timeout). Skutečná taxonomie L3 Run 2 je: 1× wrong_status_code (`assert 204 == 409`) + 17× KeyError: 'id' (helper cascade failure). Viz podrobná analýza níže.

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg fixed | Avg never-fixed | Fix rate |
|-------|---------------------|-----------|-----------------|----------|
| L0 | 11.0 | 9.33 | 1.67 | 84.8% |
| L1 | 0.33 | 0.33 | 0 | 100% |
| L2 | 0.67 | 0.33 | 0.33 | 50% |
| L3 | 6.0 | 0 | 6.0 | 0% |
| L4 | 0.67 | 0 | 0.67 | 0% |

### Analýza per kategorie

**Timeout (L0: 39.4 %)**

Na L0 tvoří timeouty dominantní kategorii selhání (13 ze 33, koncentrované v Run 1 a Run 2). Pravděpodobný mechanismus: model bez znalosti API kontraktu posílá requesty ve špatném formátu. Konkrétně PATCH `/books/{id}/stock` vyžaduje query parametr (`params={"quantity": N}`), ale L0 model pravděpodobně posílá JSON body. Podobně endpointy jako `/discount`, `/rating`, `/tags` vyžadují specifický formát, který model bez `api_knowledge` musí hádat. Server může na neočekávaný formát reagovat čekáním na data nebo neúspěšným zpracováním, což vyústí v 30s timeout.

Timeouty se na L1+ nevyskytují vůbec — `api_knowledge` obsahuje explicitní informaci o formátu requestů pro problematické endpointy.

**Wrong status code (L0: 18.2 %, L1+: dominantní zbytková chyba)**

Na L0 tvoří wrong_status_code 6 ze 33 selhání. Nejčastější záměny: 200 vs. 201 (model očekává 200 na POST, API vrací 201), 422 vs. 404 (model očekává 422 pro neexistující zdroj, API vrací 404), 204 vs. 200 (DELETE odpovědi). Na L1+ zbývají jen idiosynkratické záměny kolem discount logiky (`test_apply_discount_too_new_book`, `test_apply_discount_new_book_error`), kde hranice „nová kniha" vyžaduje znalost aktuálního roku vs. `published_year` — tento edge case přetrvává napříč levely.

**Other (L0: 39.4 %)**

Na L0 tvoří „other" 13 ze 33 selhání. Z kontextu (order-related testy, stock management) jde pravděpodobně o: chybějící response klíče (test přistupuje k `book["id"]`, ale response nemá klíč `id` kvůli chybnému setupu), business logic failures (objednávka selže na `stock=0`), chyby v závislostech mezi testy.

Kategorie „other" je catch-all pro vše, co nespadá do definovaných kategorií. Při 39–44 % selhání v této kategorii je to slabina taxonomie, která snižuje diagnostickou hodnotu. Pro budoucí práci by bylo vhodné rozšířit taxonomii o: `helper_cascade_failure`, `business_logic_violation`, `state_inconsistency`, `validation_error`.

**Halucinace status kódů**

| Level | Kódy v kontextu | Halucinované | Korektní? |
|-------|-----------------|--------------|-----------|
| L0 | 200, 201, 204, 422 | 404 | ✅ (HTTP konvence) |
| L1+ | 200, 201, 204, 400, 404, 409, 422 | žádné | — |

L0 „halucinuje" 404 — používá status kód, který není v OpenAPI specifikaci. Nejde ale o chybnou halucinaci, nýbrž o korektní inferenci z HTTP konvencí (RFC 7231 definuje 404 jako standardní odpověď pro „resource not found"). API skutečně vrací 404 pro neexistující zdroje. Taxonomie by měla rozlišovat „korektní inferenci mimo kontext" od „chybné halucinace". Na L1+ se halucinace nevyskytují — model má explicitní seznam status kódů z `api_knowledge`.

**Vzorec opravitelnosti: povrchové vs. strukturální chyby**

L0 chyby jsou „povrchové" — špatný status kód, špatný request formát — a repair loop je efektivně opraví (84.8 % fix rate), protože pytest error message obsahuje dostatečnou informaci (Expected 201, got 200). Typický průběh: helper_fallback v 1. iteraci opraví kaskádové chyby, isolated v dalších opraví individuální problémy.

L3/L4 chyby jsou „strukturální" — problém v helper architektuře nebo v pochopení business logiky — a repair loop je neopraví (0 % fix rate), protože error message neposkytuje dostatečný kontext pro opravu root cause. Viz L3 Run 2 analýza pro detailní ukázku tohoto fenoménu.

Nulový fix rate na L4 (u 2 přetrvávajících selhání) je specifický: `test_apply_discount_new_book_fails` (model špatně chápe discount boundary) a `test_list_books_pagination` (assertion na `total == 3`, ale jiný počet knih v DB). Repair loop ukazuje error message, ale model opakovaně generuje stejnou špatnou opravu.

---

## L3 Run 2 outlier — hloubková analýza

### Fakta

- **Validity:** 40.0 % (12/30) — nejnižší v celém experimentu
- **18 failing testů, 0 opraveno** v 5 iteracích
- **10 testů stale**, 18 never-fixed
- **Taxonomie z diagnostiky:** 9× timeout, 8× other, 1× wrong_status_code
- **Skutečná taxonomie z logu:** 17× `KeyError: 'id'`, 1× `assert 204 == 409`
- **6 helperů** (vs. standardní 4): `unique`, `create_author` (has_assertion), `create_category` (has_assertion), `create_book` (has_assertion), `update_stock` (has_assertion), `delete_book_tags` (has_assertion)
- **Compliance:** 100 (timeout na všech 50 voláních)
- **Celý pytest suite doběhl za 1.54s** — žádné skutečné timeouty

### Taxonomická korekce: žádné timeouty, jen KeyError

Diagnostický parser (`phase6_diagnostics.py`) klasifikoval 9 selhání jako „timeout". Analýza surového pytest logu odhalila, že ve skutečnosti jde o `KeyError: 'id'`. Příčina misklasifikace: parser detekoval substring `timeout=30` v traceback řádku, např.:

```
r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
                                          ^^^^^^^^^^
E   KeyError: 'id'
```

Parser parsuje celý traceback blok a při hledání klíčového slova „timeout" narazí na parametr `timeout=30` z HTTP volání, nikoliv na skutečný timeout exception. Podobně 8 selhání klasifikovaných jako „other" jsou taktéž `KeyError: 'id'` — parser je zařadil do catch-all kategorie.

**Dopad na RQ3 metriky:** L3 taxonomie „9× timeout, 8× other" je chybná. Skutečná distribuce je: 1× wrong_status_code + 17× helper_cascade (KeyError). Toto je important threat to validity — automatická taxonomie má v tomto konkrétním případě 100 % false positive rate pro kategorii „timeout".

**Doporučení:** Upravit parser tak, aby četl pouze typ výjimky z posledního řádku tracebacku (regex `^E\s+(\w+Error|Timeout|AssertionError)`), nikoliv substring match přes celý blok.

### Root cause: ISBN prefix o 1 znak příliš dlouhý

Příčina 17 ze 18 selhání je v helperu `create_book`:

```python
def create_book(author_id, category_id, stock=10, year=2020):
    data = {
        "title": unique("Book"),
        "isbn": unique("97801"),  # ← ROOT CAUSE
        ...
    }
```

Funkce `unique(prefix)` vrací `f"{prefix}_{uuid.uuid4().hex[:8]}"`. Pro prefix `"97801"` je výsledek 14 znaků: `97801` (5) + `_` (1) + uuid (8) = 14. API (pravděpodobně přes Pydantic model nebo DB constraint) validuje ISBN na maximálně 13 znaků. Server proto vrací `422 Unprocessable Entity`.

**Důkaz — proč test_create_book_with_stock_ten PROŠEL:**

```python
def test_create_book_with_stock_ten():
    data = {
        "title": "B1", "isbn": unique("9781"),  # ← TADY JE KLÍČ
        ...
    }
```

Tento test nepoužívá helper `create_book`, ale vytváří data lokálně s prefixem `"9781"`. Výsledek: `9781` (4) + `_` (1) + uuid (8) = 13 znaků — přesně na hranici validace. Test prošel. Také `test_create_duplicate_isbn_fails` a `test_create_book_invalid_category` prošly ze stejného důvodu (používají `unique("9781")` přímo).

**Proč zrovna L3?** Model viděl DB schéma, kde je ISBN sloupec definován pravděpodobně s délkovým omezením. V reakci na to se pokusil generovat „realističtější" ISBN prefix (`97801` vypadá jako začátek ISBN-13), ale nepočítal s tím, že `unique()` přidá dalších 9 znaků. V Run 1 a Run 3 (také L3) model zvolil jiný prefix nebo jiný přístup a problém nenastal — klasický příklad interakce nedeterminismu LLM s vlastnostmi kontextu.

### Evoluce selhání přes iterace: The Masking Effect

**Iterace 1 — Tiché selhání helperu:**
Helper `create_book` v první iteraci NEMĚL assertion na status code. Odeslal request s 14znakovým ISBN, API vrátilo `422` a JSON s chybou (pravděpodobně `{"detail": "String should have at most 13 characters"}`). Tento JSON nemá klíč `"id"`. Helper vrátil tento JSON a test udělal `book['id']` → `KeyError: 'id'`. Chybová hláška v logu ukazuje na řádek v testu, ne v helperu — root cause je maskovaná.

**Iterace 2 — Repair loop přidá assertion, ale zamaskuje kontext:**
Repair loop detekoval 18 selhání → `helper_fallback` strategie. LLM viděl `KeyError: 'id'` a logicky usoudil: „Helper neověřuje, zda se kniha vytvořila. Přidám `assert response.status_code == 201`." Od iterace 2 se všechny chyby změnily na:

```
assert response.status_code == 201
E   assert 422 == 201
```

**Iterace 3–5 — Slepota modelu:**
Assertion ukončí helper okamžitě při neshodě status kódů a do logu vypíše pouze `assert 422 == 201`. Model NEVIDÍ response body ze serveru (ten JSON s informací o délce stringu), protože assertion pád ukončí dříve. LLM v repair promptu dostane tento log, ale nemá nejmenší tušení, PROČ API vrací 422. Zkouší helper přepsat naslepo — mění strukturu, ale nikdy nezmění prefix `"97801"` na kratší. Testy zamrznou jako stale.

**The Masking Effect:** Standardní assertion `assert r.status_code == 201` je pro autonomní LLM agenty nedostatečná, protože skrývá diagnostický kontext. Aby LLM mohl efektivně opravovat validační chyby, testovací framework by ho měl instruovat psát assertions s výpisem těla: `assert r.status_code == 201, r.text`. Bez toho je model odkázán na hádání root cause.

### Proč repair loop kompletně selhal

Repair trajectory: `helper_fallback → isolated(10) → helper_fallback → isolated(10) → konec`

1. **Iterace 1 → 2:** 18 selhání → `helper_fallback` (oprav helpery). LLM přidá assertion do `create_book`. Ale root cause (ISBN prefix) zůstává.
2. **Iterace 2 → 3:** 18 selhání přetrvává → `previous_repair_type = helper_fallback` → přepne na `isolated` (max 10 testů). Ale 17 testů má identickou chybu v helperu — izolovaná oprava jednoho testu nemůže opravit helper.
3. **Iterace 3 → 4:** Alternace zpět na `helper_fallback`. LLM vidí `assert 422 == 201`, ale neví proč 422 → přepíše helper jinak, ISBN prefix stále `"97801"`.
4. **Iterace 4 → 5:** Zpět na `isolated`. Stale tracker označí 10 testů. Zbývajících 8 stále selhává.
5. **Iterace 5:** Konec bez opravy.

Strukturální problém: Repair loop nemá strategii „přepiš celou helper architekturu od základu". Může opravit helper (helper_fallback) nebo jednotlivý test (isolated), ale nemůže říct „smaž helpers `update_stock` a `delete_book_tags`, zkrať ISBN prefix". Toto je designové omezení — zachovává invariant „počet testů se nemění" a „helper architektura je z velké části zachována".

### Proč Run 1 a Run 3 prošly na 100 %

| Run | Helpery | create_book ISBN prefix | Výsledek |
|-----|---------|------------------------|----------|
| Run 1 | 4 (standardní, žádné assertions) | Neznámý (pravděpodobně ≤13 znaků) | 100 % v 1. iteraci |
| Run 2 | 6 (všechny s assertions) | `"97801"` → 14 znaků | 40 % (katastrofa) |
| Run 3 | 4 (standardní, žádné assertions) | Neznámý (pravděpodobně ≤13 znaků) | 100 % v 1. iteraci |

Run 1 a Run 3 zvolily konzervativní 4-helper architekturu bez nadměrných assertions. Run 2 zvolil ambiciózní 6-helper architekturu s assertions ve všech helperech — a fatální 1-znakový rozdíl v ISBN prefixu. LLM generování je nedeterministické — stejný prompt může vygenerovat buď bezpečnou nebo riskantní architekturu. DB schéma v L3 kontextu zvyšuje pravděpodobnost riskantní varianty (model vidí ISBN constraint a snaží se generovat „realističtější" data), ale negarantuje ji.

### Význam pro diplomovou práci

Tento outlier je důležitý datový bod, nikoliv anomálie k vyloučení. Demonstruje několik klíčových fenoménů:

1. **Kontextové přehlcení:** DB schéma motivovalo model k „realističtějšímu" ISBN, ale model nezvládl aritmetiku délky stringů s frameworkovým `unique()` prefixem.
2. **Antipattern „assertions v helperech":** Vložení `assert response.status_code == 201` do helperu `create_book` způsobilo, že selhání jednoho helperu kaskádovalo do 17 závislých testů. Helper s assertion se stává single point of failure — pokud selže, zničí celý test suite. Toto je známý antipattern, ale LLM na L3 ho spontánně vytvořil.
3. **The Masking Effect:** Standardní assertion (`assert r.status_code == 201`) skrývá diagnostický kontext před repair loopem. Model vidí `422 == 201`, ale nevidí response body s vysvětlením PROČ 422. Toto je architektonický limit repair loopu — pro budoucí práci by assertions v helperech měly obsahovat `assert r.status_code == 201, r.text`.
4. **Taxonomická kontaminace:** Automatická failure taxonomie chybně klasifikovala 17 KeyError selhání jako 9× timeout + 8× other kvůli substring match na `timeout=30` v traceback řádcích. Toto je threat to validity pro RQ3 metriky.
5. **1-znakový bug:** Celé katastrofální selhání způsobil rozdíl jednoho znaku v ISBN prefixu (`"97801"` místo `"9781"` → 14 vs. 13 znaků). Ukazuje extrémní citlivost LLM generovaného kódu na zdánlivě triviální detaily.

**Doporučení pro reportování:**
- Reportovat L3 průměr s outlierem (80.0 %) i bez něj (100.0 %)
- Věnovat outlieru samostatnou sekci jako case study
- Interpretovat ho jako threat to validity: „Při třech runech nemůžeme odlišit systematický efekt od náhodného — pro robustnější odhad by bylo potřeba 10+ runů na L3"

---

## Repair loop analýza

### Efektivita per level

| Level | Avg failing (iter 1) | Avg opraveno | Fix rate | Iterace ke konvergenci | Dominantní strategie |
|-------|---------------------|-------------|----------|------------------------|---------------------|
| L0 | 11.0 | 9.33 | 84.8% | 5.0 (max) | helper_fallback → isolated alternace |
| L1 | 0.33 | 0.33 | 100% | 1.67 | isolated (1 případ) |
| L2 | 0.67 | 0.33 | 50% | 3.0 | isolated |
| L3 | 6.0 | 0 | 0% | 2.33 | helper_fallback / isolated (Run 2 only) |
| L4 | 0.67 | 0 | 0% | 3.67 | isolated |

### L0: nejlepší showcase repair loopu

L0 je paradoxně nejlepší demonstrace hodnoty repair loopu — transformuje nízkou initial quality na vysokou finální validitu:

- **Run 1:** 16 failing → 14 opraveno (87.5 % fix rate). Iter 1: helper_fallback opraví kaskádové chyby (stock, status kódy). Iter 2–3: isolated opraví zbývající individuální problémy.
- **Run 2:** 14 failing → 13 opraveno (92.9 % fix rate). Stejný vzorec.
- **Run 3:** 3 failing → 1 opraveno (33.3 % fix rate). Menší počet chyb, ale 2 zůstaly stale (delete author, update stock — endpointy s neobvyklými kontrakty).

Typický průběh oprav na L0: (1) masivní selhání v 1. iteraci → helper_fallback opraví sdílenou příčinu (špatný stock v helperu, špatný request formát); (2) zbývá 3–4 failing → isolated per-test opravy; (3) zbývá 1–2 → stale_skip nebo další isolated; (4–5) stabilizace.

Alternace strategií (`previous_repair_type`) funguje na L0 efektivně: helper_fallback v první iteraci řeší kaskádové chyby, isolated v dalších řeší individuální. Zabraňuje opakování nefunkční strategie.

### Proč repair loop selhává na L3 a L4

**L3 Run 2 (0 % fix rate):** Root cause je v ISBN prefixu helperu — viz sekce L3 Run 2. Alternace helper_fallback ↔ isolated nepřinesla žádnou opravu v 5 iteracích, protože: (1) helper_fallback přidá assertion, ale nezmění ISBN prefix; (2) isolated opravuje jednotlivé testy, ale chyba je v sdíleném helperu; (3) The Masking Effect — model nevidí response body s vysvětlením 422.

**L4 (0 % fix rate u 2 selhání):** `test_apply_discount_new_book_fails` — model špatně chápe discount boundary (hranice „nová kniha" závisí na `published_year` vs. aktuální rok). `test_list_books_pagination` — assertion `total == 3`, ale v DB je jiný počet knih. V obou případech model opakovaně generuje stejnou špatnou opravu — error message neposkytuje dostatečný kontext pro identifikaci root cause.

**Vzorec:** Repair loop je efektivní pro **syntaktické a kontraktní chyby** (špatný status kód, špatný request formát — model se učí z error message). Selhává pro **sémantické chyby** (špatné porozumění business logice, chyba v datech/prefixech), kde error message neposkytuje dostatečný diagnostický kontext.

### StaleTracker

| Level | Stale (avg) | Popis |
|-------|-------------|-------|
| L0 | 1.67 | Konzistentně `test_delete_*` a `test_update_stock_*` — endpointy s neobvyklými kontrakty |
| L1 | 0.33 | 1 test v Run 2 (`test_apply_discount_too_new_book`), opraven v iter 3 |
| L2 | 0.67 | 1 test v Run 2 a Run 3 (discount/malformed query) |
| L3 | 3.33 | V Run 2 bylo 10 stale z 18 failing — masivní eskalace |
| L4 | 0.67 | 1 test v Run 1 a Run 2 (discount, pagination) |

StaleTracker (threshold = 2 po sobě jdoucí iterace se stejnou normalizovanou chybou) splnil svůj účel — zabraňuje nekonečnému opakování nefunkčních oprav a plýtvání LLM tokeny. V L3 Run 2 to vedlo k tomu, že po 5 iteracích skončil repair loop s 10 stale + 8 aktivně failing (18 celkem neopraveno) místo aby se snažil donekonečna.

Omezení: StaleTracker zastavuje opravy, ale neidentifikuje root cause. Test je „zamrzlý" = přestane se opravovat, ale důvod zamrznutí zůstává neznámý pro pipeline.

### Konvergence

Rychlost konvergence silně koreluje s počtem selhání v 1. iteraci:

- **0 selhání** → konvergence v 1. iteraci (L1 Run 1/3, L2 Run 1, L3 Run 1/3, L4 Run 3)
- **1–2 selhání** → konvergence ve 3.–5. iteraci (L1 Run 2, L2 Run 2/3, L4 Run 1/2)
- **3+ selhání** → buď konvergence v 5. iteraci s 1–2 never-fixed (L0), nebo žádná konvergence (L3 Run 2)

Distribuce je bimodální: buď se problém vyřeší rychle (1–3 iterace), nebo vůbec. Neexistuje případ, kde by se z 18 selhání postupně opravilo 15 — buď je root cause opravitelná naráz (kaskádová oprava helperu), nebo není opravitelná vůbec.

---

## Instruction compliance

### Compliance score per level

| Level | Missing timeout (avg %) | Compliance score (avg) |
|-------|------------------------|------------------------|
| L0 | 66% (2/3 runů) | 87 |
| L1 | 100% (3/3) | 80 |
| L2 | 100% (3/3) | 80 |
| L3 | 66% (2/3) | 87 |
| L4 | **0%** (0/3) | **100** |

Compliance score se skládá z: missing timeout, uses_unique, calls_reset, uses_fixtures. Jediný reálný diferenciátor je **missing timeout** — všechny runy používají `unique()`, žádný nevolá `/reset`, žádný nepoužívá fixtures.

### Proč L4 = 100 % compliance

Referenční testy obsahují `timeout=30` na každém HTTP volání. Model vidí tento vzor v kódu a replikuje ho. Toto je klasický příklad in-context learning: ukázkový kód s `timeout=30` je výrazně účinnější než psaná instrukce v `framework_rules` („Timeout=30 na každém HTTP volání"). LLM modely jsou architektované na doplňování vzorů — vzor v kódu má mnohem vyšší váhu než instrukce v textu.

### Proč L1 a L2 mají nejhorší compliance (100 % missing timeout)

Toto je kontraintuitivní: L1–L2 mají více kontextu, ale horší compliance. Pravděpodobný mechanismus — **attention priority / context dilution**: L1+ kontext je větší (22 538 tokenů L1 vs. 20 737 L0), obsahuje doménově specifické informace (`api_knowledge`, zdrojový kód), které „přetáhnou pozornost" od technických pravidel v `framework_rules`. Model prioritizuje nové, doménové informace nad technickými detaily jako timeout.

Alternativní vysvětlení: L0 Run 3 má compliance 100 (timeout na všech 39 voláních) — to je 1 run ze 3. Na L3 má Run 2 compliance 100 — opět 1 run. Při 3 runech je rozdíl mezi 0/3 (L1–L2) a 1/3 (L0, L3) statisticky nevýznamný. Může jít o statistický artefakt malého vzorku.

### Je compliance score dobrá metrika?

**Omezení:**
- Binární na úrovni runu (0 nebo 100 pro timeout) — nezachycuje parciální compliance (např. timeout na 28/30 voláních)
- Neměří kvalitu compliance — test může mít timeout na GET ale chybět na POST
- Neváží důležitost pravidel — missing timeout je funkčně závažnější (může způsobit reálné timeouty) než uses_unique (hygienické)
- Neměří dodržování implicitních pravidel (např. správné pořadí setup → action → assert)

Doporučení: Reportovat compliance jako doplňkovou metriku s jasným upozorněním na omezenou granularitu. Hlavní závěr je robustní: referenční testy (L4) jsou o řád účinnější pro vynucení technických pravidel než psané instrukce (L0–L3).

---

## Shrnutí, vzory a limity

### Hlavní zjištění — RQ1

`api_knowledge` je nejdůležitější kontextová vrstva: přechod L0 → L1 přináší skok z 94.4 % na 100 % validity a z 11.0 na 0.33 selhání v první iteraci. Další vrstvy (zdrojový kód, DB schéma, referenční testy) přinášejí marginální nebo žádné zlepšení validity a v případě L3 zvyšují riziko katastrofálního selhání. Assertion depth a response validation paradoxně klesají s kontextem (L0 > L1), protože model s více informacemi generuje cílenější, minimalistické testy — efektivnější, ale měřitelně „plytší". Jde o trade-off validita vs. hloubka a přechod modelu z explorativního do deterministického režimu generování.

### Hlavní zjištění — RQ2

EP coverage mírně klesá s kontextem (58.8 % → 49.0 %), zatímco code coverage zůstává stabilní (82–85 %). Více kontextu vede k hlubšímu testování méně endpointů — posun od kvantity k kvalitě pokrytí. L1 dosahuje nejvyššího code coverage (85.4 %) díky efektivnímu testování error/edge cases, které aktivují branching logiku v business vrstvě (`crud.py`: 71.3 % vs. L0: 63.7 %). Podíl error testů roste s kontextem (31 % L0 → 49 % L4), což je známka profesionálnějšího testování.

### Hlavní zjištění — RQ3

L0 selhání jsou „povrchová" (špatné kódy, špatné formáty) a opravitelná (84.8 % fix rate). L3/L4 selhání jsou „strukturální" (helper cascade, sémantické nepochopení) a neopravitelná (0 % fix rate). Kategorie „other" (39–44 %) je příliš široká a snižuje diagnostickou hodnotu taxonomie. Analýza L3 Run 2 navíc odhalila taxonomickou kontaminaci — parser chybně klasifikoval KeyError jako timeout kvůli substring match na `timeout=30`.

### Neočekávané vzory

1. **Assertion depth paradox:** L0 (nejméně kontextu) má nejvyšší assertion depth (1.81) — kompenzační chování v podmínkách nejistoty, nikoliv známka kvality.
2. **Marginalita vyšších vrstev:** L2, L3, L4 nepřinášejí kvalitativní skok nad L1 — `api_knowledge` „nasytí" potřebu informací pro generování validních testů.
3. **DB schéma jako rizikový faktor:** L3 je jediný level s destruktivním outlierem — DB schéma může vést ke generování „realističtějších" ale fatálně chybných dat (ISBN prefix).
4. **Referenční testy učí formu, ne obsah:** L4 zlepšuje compliance (100), ale ne assertion depth ani response validation. Ukázkový kód je účinnější pro technická pravidla než psané instrukce.
5. **Bimodální opravitelnost:** Selhání buď repair loop opraví rychle (1–3 iterace), nebo vůbec — neexistuje graduální zlepšování.
6. **Taxonomická kontaminace:** Automatický parser může chybně klasifikovat chyby kvůli substring match v traceback řádcích.

### Limity experimentu

1. **Jeden model:** Všechna zjištění jsou specifická pro gemini-3.1-flash-lite-preview. Větší modely (GPT-4o, Claude Sonnet) mají větší kapacitu udržet instrukce a pravděpodobně nepodlehnou context dilution tak rychle na L2–L3.
2. **Jedna API:** Bookstore API je relativně jednoduchá (34 endpointů, CRUD + orders). U složitějších API (microservices, autentizace, statefull workflows) by výsledky mohly být odlišné.
3. **3 runy:** Nedostatečný počet pro robustní statistiku. L3 variance (std = 34.6) ukazuje potřebu 10+ runů.
4. **Fixní počet testů (30):** Limituje EP coverage ceiling. Při 34 endpointech je 100 % pokrytí prakticky nemožné.
5. **Agregované metriky:** Assertion depth a response validation nerozlišují správné a nesprávné aserce. Metrika by měla být doplněna o „valid assertion depth" — jen pro testy, které prošly v 1. iteraci.
6. **Failure taxonomie:** Kategorie „other" (39–44 %) je příliš široká. Navíc parser trpí false positives (substring match na `timeout`).
7. **Manuální code coverage:** Sbírá se mimo automatickou pipeline — potenciální lidská chyba v procesu měření.

### Threats to validity

**Internal validity:**
- LLM nedeterminismus — stejný prompt produkuje odlišné výsledky (L3 Run 2 vs. Run 1/3). 3 runy nemusí dostatečně pokrýt distribuci výstupů.
- Gemini-3.1-flash-lite-preview nenastavuje temperature — default hodnota může být vysoká, což zvyšuje variabilitu.
- Repair loop design (alternace strategií, stale threshold) může favorizovat určité typy selhání nad jinými.
- Taxonomická kontaminace — parser chybně klasifikuje chyby v L3 Run 2 (viz sekce outlier).

**External validity:**
- Single API (bookstore) — omezená generalizovatelnost na jiné typy API.
- Single model — nelze tvrdit závěry o LLM obecně, pouze o tomto konkrétním modelu.
- `api_knowledge` je manuálně vytvořená — kvalita závisí na autorovi. V praxi by tento typ dokumentace nemusel existovat nebo být kompletní.

**Construct validity:**
- Assertion depth neměří kvalitu/korektnost asercí — L0 má nejvyšší depth, ale nejnižší validitu.
- Compliance score má nízkou granularitu (binární per pravidlo per run).
- Response validation regex může mít false positives/negatives.
- „Halucinace" 404 na L0 je ve skutečnosti korektní inference — taxonomie směšuje chybnou a korektní inferenci mimo kontext.

**Conclusion validity:**
- Malý počet runů (3) omezuje statistickou sílu. Efekty s p > 0.05 by neměly být interpretovány jako „žádný efekt".
- L3 průměry jsou dominovány outlierem — median (100 %) by byl robustnější míra centrální tendence než mean (80 %).

---

## Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1 (93.33%)</summary>

```
Validity: 93.33% (28/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.93
Response Validation: 73.33%
Stale: 2 (test_delete_book_successful, test_update_order_to_shipped)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80 (timeout missing on all 39 calls)
Failure taxonomy (iter 1): wrong_status_code 2, timeout 7, other 7
Repair: iter1=16F→helper_fallback, iter2=4F→isolated, iter3=2F→isolated, iter4=2F→stale_skip, iter5=2F
Never-fixed (2): test_delete_book_successful, test_update_order_to_shipped
Fixed (14): test_add_tags_to_book, test_apply_invalid_discount, test_apply_valid_discount,
  test_create_book_review, test_create_invalid_rating, test_create_order_zero_quantity,
  test_create_valid_order, test_delete_author_successful, test_get_book_details,
  test_get_nonexistent_author, test_get_rating_value, test_get_single_order,
  test_increase_stock_level, test_invalid_status_transition
Status codes hallucinated: 404
```
</details>

<details>
<summary>L0 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.6
Response Validation: 46.67%
Stale: 1 (test_update_stock_success)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80 (timeout missing on all 38 calls)
Failure taxonomy (iter 1): wrong_status_code 2, timeout 6, other 6
Repair: iter1=14F→helper_fallback, iter2=3F→isolated, iter3=1F→isolated, iter4=1F→stale_skip, iter5=1F
Never-fixed (1): test_update_stock_success
Fixed (13): test_add_tags_to_book_empty_list, test_add_valid_tags_to_book,
  test_apply_discount_too_high, test_apply_valid_discount, test_create_order_valid_items,
  test_create_review_out_of_bounds_rating, test_create_valid_review,
  test_delete_existing_author, test_delete_non_existent_order, test_delete_pending_order,
  test_get_book_rating, test_update_order_status_invalid, test_update_order_status_valid
Status codes hallucinated: 404
```
</details>

<details>
<summary>L0 — Run 3 (93.33%)</summary>

```
Validity: 93.33% (28/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.9
Response Validation: 66.67%
Stale: 2 (test_delete_existing_author, test_update_stock_partial)
Iterations: 5
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 100 (timeout on all 39 calls!)
Failure taxonomy (iter 1): wrong_status_code 2, assertion_value_mismatch 1
Repair: iter1=3F→isolated, iter2=2F→isolated, iter3=2F→stale_skip, iter4=2F→stale_skip, iter5=2F
Never-fixed (2): test_delete_existing_author, test_update_stock_partial
Fixed (1): test_delete_book_successfully
Status codes hallucinated: 404
```
</details>

### L1

<details>
<summary>L1 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.23
Response Validation: 20.0%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L1 — Run 2 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.43
Response Validation: 30.0%
Stale: 1 (test_apply_discount_too_new_book — opraveno v iter 3)
Iterations: 3
Helpers: 4 (unique, create_author, create_category, create_book published_year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Fixed (1): test_apply_discount_too_new_book
```
</details>

<details>
<summary>L1 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.2
Response Validation: 33.33%
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
EP Coverage: 50.0% (17/34)
Assert Depth: 1.33
Response Validation: 33.33%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_author, create_category, create_book, create_tag)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L2 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.47
Response Validation: 50.0%
Stale: 1 (test_list_reviews_malformed_query_params)
Iterations: 5
Helpers: 4 (unique, create_author has_assertion, create_category has_assertion, create_book has_assertion)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Never-fixed (1): test_list_reviews_malformed_query_params
```
</details>

<details>
<summary>L2 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 52.94% (18/34)
Assert Depth: 1.33
Response Validation: 30.0%
Stale: 1 (test_apply_discount_new_book_error — opraveno v iter 3)
Iterations: 3
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): wrong_status_code 1
Fixed (1): test_apply_discount_new_book_error
```
</details>

### L3

<details>
<summary>L3 — Run 1 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 61.76% (21/34)
Assert Depth: 1.53
Response Validation: 50.0%
Stale: 0
Iterations: 1
Helpers: 4 (unique, create_author, create_category, create_book stock=10 year=2020)
Plan adherence: 100%
Compliance: 80
Failure taxonomy (iter 1): 0 failures
```
</details>

<details>
<summary>L3 — Run 2 (40.0%) ⚠️ OUTLIER</summary>

```
Validity: 40.0% (12/30)
EP Coverage: 47.06% (16/34)
Assert Depth: 1.73
Response Validation: 46.67%
Stale: 10
Iterations: 5
Helpers: 6 (unique, create_author has_assertion, create_category has_assertion,
  create_book has_assertion [isbn=unique("97801") → 14 chars, API max 13],
  update_stock has_assertion, delete_book_tags has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 50 calls)

SKUTEČNÁ failure taxonomy (iter 1, z logu):
  - KeyError: 'id' × 17 (helper create_book vrací 422 JSON bez klíče "id")
  - wrong_status_code × 1 (assert 204 == 409 v test_delete_author_with_books_fails)

DIAGNOSTICKÁ failure taxonomy (z parseru — CHYBNÁ):
  - timeout × 9 (false positive — parser detekoval substring "timeout=30" v traceback)
  - other × 8 (catch-all pro KeyError)
  - wrong_status_code × 1 (korektní)

Root cause: isbn prefix "97801" → unique() produkuje 14znakové ISBN → API vrací 422
Masking effect: Od iter 2 assert v helperu skrývá response body → LLM nevidí důvod 422

Repair: iter1=18F→helper_fallback, iter2=18F→isolated(10), iter3=18F→helper_fallback,
  iter4=18F→isolated(10), iter5=18F
Never-fixed (18): ALL failing tests
Fixed: 0
Celý pytest suite doběhl za 1.54s — žádné skutečné timeouty
```
</details>

<details>
<summary>L3 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 58.82% (20/34)
Assert Depth: 1.5
Response Validation: 46.67%
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
EP Coverage: 47.06% (16/34)
Assert Depth: 1.53
Response Validation: 53.33%
Stale: 1 (test_apply_discount_new_book_fails)
Iterations: 5
Helpers: 4 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion)
Plan adherence: 100%
Compliance: 100
Failure taxonomy (iter 1): wrong_status_code 1
Never-fixed (1): test_apply_discount_new_book_fails
```
</details>

<details>
<summary>L4 — Run 2 (96.67%)</summary>

```
Validity: 96.67% (29/30)
EP Coverage: 55.88% (19/34)
Assert Depth: 1.57
Response Validation: 43.33%
Stale: 1 (test_list_books_pagination)
Iterations: 5
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 100%
Compliance: 100
Failure taxonomy (iter 1): assertion_value_mismatch 1
Never-fixed (1): test_list_books_pagination
```
</details>

<details>
<summary>L4 — Run 3 (100.0%) ✅</summary>

```
Validity: 100.0% (30/30)
EP Coverage: 44.12% (15/34)
Assert Depth: 1.37
Response Validation: 40.0%
Stale: 0
Iterations: 1
Helpers: 5 (unique, create_test_author has_assertion, create_test_category has_assertion,
  create_test_book has_assertion, create_test_tag has_assertion)
Plan adherence: 96.67%
Compliance: 100
Failure taxonomy (iter 1): 0 failures
```
</details>