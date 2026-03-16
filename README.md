# Vibe Testing Framework – Výsledky experimentu

## Konfigurace
| Parametr | Hodnota |
|---|---|
| **LLM** | Gemini 3 Flash Preview |
| **API** | Bookstore API |
| **Počet testů (plán)** | 40 |
| **Max iterací** | 5 |
| **Datum** | 2026-03-16 |

---

## Výsledky podle úrovně kontextu

### L0 – OpenAPI specifikace (black-box baseline)

**Kontext:** Pouze OpenAPI specifikace. LLM nemá přístup k dokumentaci, zdrojovému kódu ani DB schématu.

#### Automatické metriky (pipeline)

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 100.0% (44/44) |
| **Endpoint Coverage** | 90.91% (20/22) |
| **Assertion Depth** | 1.61 avg (71 asserts / 44 tests) |
| **Iterací použito** | ? / 5 |

**Nepokryté endpointy:**
- `DELETE /categories/{category_id}`
- `GET /categories/{category_id}`

#### Code Coverage (ruční měření)

| Soubor | Statements | Miss | Coverage |
|---|---|---|---|
| `app/__init__.py` | 0 | 0 | 100% |
| `app/crud.py` | 151 | 20 | 87% |
| `app/database.py` | 17 | 0 | 100% |
| `app/main.py` | 79 | 2 | 97% |
| `app/models.py` | 43 | 0 | 100% |
| `app/schemas.py` | 99 | 0 | 100% |
| **TOTAL** | **389** | **22** | **94%** |

---

### L1 – OpenAPI + byznys dokumentace

**Kontext:** OpenAPI specifikace + technická a byznys dokumentace (chybové kódy, byznys pravidla, known issues).

#### Automatické metriky (pipeline)

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 100.0% (42/42) |
| **Endpoint Coverage** | 81.82% (18/22) |
| **Assertion Depth** | 2.02 avg (85 asserts / 42 tests) |
| **Iterací použito** | ? / 5 |

**Nepokryté endpointy:**
- `GET /categories`
- `GET /categories/{category_id}`
- `PUT /authors/{author_id}`
- `PUT /books/{book_id}`

#### Code Coverage (ruční měření)

| Soubor | Statements | Miss | Coverage |
|---|---|---|---|
| `app/__init__.py` | 0 | 0 | 100% |
| `app/crud.py` | 151 | 28 | 81% |
| `app/database.py` | 17 | 0 | 100% |
| `app/main.py` | 79 | 4 | 95% |
| `app/models.py` | 43 | 0 | 100% |
| `app/schemas.py` | 99 | 0 | 100% |
| **TOTAL** | **389** | **32** | **92%** |

---

### L2 – L1 + zdrojový kód

**Kontext:** OpenAPI + dokumentace + zdrojový kód endpointů (main.py, crud.py, schemas.py).

#### Automatické metriky (pipeline)

| Metrika | Hodnota |
|---|---|
| **Test Validity Rate** | 100.0% (40/40) |
| **Endpoint Coverage** | 77.27% (17/22) |
| **Assertion Depth** | 2.20 avg (88 asserts / 40 tests) |
| **Iterací použito** | ? / 5 |

**Nepokryté endpointy:**
- `GET /books/{book_id}`
- `GET /categories`
- `GET /categories/{category_id}`
- `PUT /authors/{author_id}`
- `PUT /categories/{category_id}`

#### Code Coverage (ruční měření)

| Soubor | Statements | Miss | Coverage |
|---|---|---|---|
| `app/__init__.py` | 0 | 0 | 100% |
| `app/crud.py` | 151 | 28 | 81% |
| `app/database.py` | 17 | 0 | 100% |
| `app/main.py` | 79 | 5 | 94% |
| `app/models.py` | 43 | 0 | 100% |
| `app/schemas.py` | 99 | 0 | 100% |
| **TOTAL** | **389** | **33** | **92%** |

---

### L3 – L2 + DB schéma

*Čeká na spuštění*

---

### L4 – L3 + existující testy (plný kontext)

*Čeká na spuštění*

---

## Souhrn

| Úroveň | Validity | Endpoint Cov | Assertion Depth | Code Coverage | Iterací |
|---|---|---|---|---|---|
| **L0** | 100.0% | 90.91% | 1.61 | 94% | ? |
| **L1** | 100.0% | 81.82% | 2.02 | 92% | ? |
| **L2** | 100.0% | 77.27% | 2.20 | 92% | ? |
| **L3** | – | – | – | – | – |
| **L4** | – | – | – | – | – |