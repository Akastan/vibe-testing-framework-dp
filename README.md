# Vibe Testing Framework – Výsledky experimentu

## ⚠️ Netestovat na reálných API – testuji s lokálním bookstorem
## https://github.com/Akastan/bookstore-api
# Testy mažou databázi!

## Konfigurace

| Parametr | Hodnota |
|---|---|
| **LLM** | gemini-3.1-flash-lite-preview |
| **API** | Bookstore API (34 endpointů) |
| **Max iterací** | 5 |
| **Datum** | 2026-03-18 |
| **Run** | 1 (první reálný pokus) |

---

## Výsledky podle úrovně kontextu

### L0 – OpenAPI specifikace (black-box baseline)

**Kontext:** Pouze OpenAPI specifikace. LLM nemá přístup k dokumentaci, zdrojovému kódu ani DB schématu.

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 58.33% (28/48) |
| **Endpoint Coverage** | 94.12% (32/34) |
| **Assertion Depth** | 1.0 avg |
| **Iterací použito** | 5 / 5 |
| **Všechny testy prošly** | ❌ Ne |
| **Doba běhu** | 1130 s (~18 min) |
| **Plánovaných testů** | 49 |

**Nepokryté endpointy:** `GET /categories/{category_id}`, `GET /tags/{tag_id}`

**Hlavní problém:** Helper `create_book()` používal hardcoded ISBN `"1234567890123"`, což způsobovalo 409 Conflict při opakovaném volání. 20 z 20 selhání bylo způsobeno tímto jediným bugem v helperu. Model to nedokázal opravit ani po 5 iteracích.

**Iterační delta:** Validity se zlepšila z 54.17% (iter 1) na 58.33% (iter 5), tedy +4.16 p.p.

---

### L1 – OpenAPI + byznys dokumentace

**Kontext:** OpenAPI specifikace + technická a byznys dokumentace (chybové kódy, byznys pravidla, known issues).

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 94.34% (50/53) |
| **Endpoint Coverage** | 97.06% (33/34) |
| **Assertion Depth** | 1.0 avg |
| **Iterací použito** | 5 / 5 |
| **Všechny testy prošly** | ❌ Ne |
| **Doba běhu** | 1714 s (~28 min) |
| **Plánovaných testů** | 54 |

**Nepokryté endpointy:** `PUT /categories/{category_id}`

**Zbývající selhání (3):**
- `test_apply_discount_too_new_error` – očekával 400, dostal 200 (špatný předpoklad o tom, co je "nová kniha")
- `test_remove_nonexistent_tag_from_book` – očekával 200, dostal 404 (API vrací 404 pro neexistující tag)
- `test_update_stock_boundary_zero` – snaha odečíst -100 z počátečního skladu, API správně vrátilo 400

**Iterační delta:** Validity se zlepšila z 84.91% (iter 1) na 94.34% (iter 5), tedy +9.43 p.p.

---

### L2 – L1 + zdrojový kód

**Kontext:** OpenAPI + dokumentace + zdrojový kód endpointů (main.py, crud.py, schemas.py).

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | ✅ 100.0% (47/47) |
| **Endpoint Coverage** | 76.47% (26/34) |
| **Assertion Depth** | 1.04 avg |
| **Iterací použito** | 4 / 5 |
| **Všechny testy prošly** | ✅ Ano |
| **Doba běhu** | 1311 s (~22 min) |
| **Plánovaných testů** | 48 |

**Nepokryté endpointy (8):** `DELETE /categories/{category_id}`, `GET /books/{book_id}/reviews`, `GET /categories`, `GET /orders/{order_id}`, `GET /tags`, `GET /tags/{tag_id}`, `PUT /authors/{author_id}`, `PUT /categories/{category_id}`

**Iterační delta:** Validity se zlepšila z 97.87% (iter 1) na 100.0% (iter 4), tedy +2.13 p.p. Stačily 4 iterace.

---

### L3 – L2 + DB schéma

**Kontext:** OpenAPI + dokumentace + zdrojový kód + databázové schéma (models.py).

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 89.47% (34/38) |
| **Endpoint Coverage** | 82.35% (28/34) |
| **Assertion Depth** | 1.0 avg |
| **Iterací použito** | 5 / 5 |
| **Všechny testy prošly** | ❌ Ne |
| **Doba běhu** | 1271 s (~21 min) |
| **Plánovaných testů** | 39 |

**Nepokryté endpointy (6):** `DELETE /books/{book_id}`, `GET /categories`, `GET /categories/{category_id}`, `GET /tags`, `GET /tags/{tag_id}`, `PUT /authors/{author_id}`

**Zbývající selhání (4):** Všechna 4 selhání byla způsobena tím, že `create_order()` helper nespecifikoval `stock` u knihy – výchozí hodnota nebyla dostatečná a API vracelo 400 (insufficient stock). Testy pro order status transitions a order detail tak padaly v setup fázi.

**Iterační delta:** Validity se zhoršila z 94.74% (iter 1) na 89.47% (iter 5), tedy **-5.27 p.p.** – model regresoval při opravách.

---

### L4 – L3 + existující testy (plný kontext)

**Kontext:** OpenAPI + dokumentace + zdrojový kód + DB schéma + existující referenční testy.

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | ✅ 100.0% (46/46) |
| **Endpoint Coverage** | 79.41% (27/34) |
| **Assertion Depth** | 1.0 avg |
| **Iterací použito** | 2 / 5 |
| **Všechny testy prošly** | ✅ Ano |
| **Doba běhu** | 656 s (~11 min) |
| **Plánovaných testů** | 47 |

**Nepokryté endpointy (7):** `DELETE /categories/{category_id}`, `GET /books/{book_id}/reviews`, `GET /categories/{category_id}`, `GET /tags/{tag_id}`, `POST /tags`, `PUT /authors/{author_id}`, `PUT /tags/{tag_id}`

**Iterační delta:** Validity se zlepšila z 97.83% (iter 1) na 100.0% (iter 2), tedy +2.17 p.p. Stačily pouhé 2 iterace.

---

## Souhrn

| Úroveň | Validity | Endpoint Cov | Assertion Depth | Iterací | Čas | Všechny OK |
|---|---|---|---|---|---|---|
| **L0** | 58.33% | 94.12% | 1.00 | 5/5 | ~18 min | ❌ |
| **L1** | 94.34% | 97.06% | 1.00 | 5/5 | ~28 min | ❌ |
| **L2** | **100.0%** | 76.47% | 1.04 | 4/5 | ~22 min | ✅ |
| **L3** | 89.47% | 82.35% | 1.00 | 5/5 | ~21 min | ❌ |
| **L4** | **100.0%** | 79.41% | 1.00 | 2/5 | ~11 min | ✅ |

---

## Pozorování z prvního runu

1. **L0 selhává na triviálním problému.** Bez kontextu model nedokáže opravit ani hardcoded ISBN v helperu – 20 testů padá kvůli jednomu řádku.

2. **L1 přináší dramatické zlepšení.** Byznys dokumentace pomohla modelu pochopit unikátnost ISBN, správné status kódy a byznys pravidla. Skok z 58% na 94%.

3. **L2 dosáhlo 100% validity.** Přístup ke zdrojovému kódu umožnil modelu plně pochopit chování API. Pokles endpoint coverage (76%) naznačuje, že model generoval méně testů, ale přesnějších.

4. **L3 regresovalo.** Přidání DB schématu paradoxně zhoršilo výsledky. Model vygeneroval méně testů (38 vs 47) a helper pro vytváření objednávek měl chybu, kterou nedokázal opravit. Více kontextu nemusí automaticky znamenat lepší výsledky.

5. **L4 je nejefektivnější.** S existujícími testy jako vzorem model dosáhl 100% validity za pouhé 2 iterace a 11 minut – nejrychlejší ze všech úrovní.

6. **Assertion depth je konzistentně nízká (~1.0).** Model generuje převážně jeden assert na test (kontrola status kódu). To je slabina – testy neověřují obsah odpovědí.

7. **Endpoint coverage klesá s kontextem.** Zatímco L0/L1 pokrývají 94–97% endpointů, L2–L4 pokrývají jen 76–82%. Více kontextu vede k menšímu počtu testů, ale vyšší přesnosti.

---

## Code Coverage

⏳ Ruční měření code coverage zatím neproběhlo pro tento run. Bude doplněno.