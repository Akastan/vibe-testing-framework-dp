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

*Čeká na spuštění*

---

### L2 – L1 + zdrojový kód

*Čeká na spuštění*

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
| **L1** | – | – | – | – | – |
| **L2** | – | – | – | – | – |
| **L3** | – | – | – | – | – |
| **L4** | – | – | – | – | – |