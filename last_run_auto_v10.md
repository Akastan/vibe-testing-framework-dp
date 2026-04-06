# Report z běhu experimentu

**Testovaný model (LLM):** gemini-3.1-flash-lite-preview
**Testované API:** bookstore
**Parametry:** 50 testů, max 5 iterací, 3 runy per level

---

## 🔍 Detailní výsledky jednotlivých běhů
*Zde je vidět stabilita generování napříč jednotlivými pokusy.*

### Běh (Run) 1
| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |
|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|
| **L0** | 90.0 | 67.65 | 3 | 5 | 0 | 2.03 | 63.33 | 0 |
| **L1** | 96.67 | 55.88 | 1 | 5 | 0 | 1.33 | 33.33 | 0 |
| **L2** | 100.0 | 55.88 | 0 | 1 | 0 | 1.47 | 40.0 | 0 |
| **L3** | 100.0 | 47.06 | 1 | 3 | 0 | 1.43 | 40.0 | 0 |
| **L4** | 96.67 | 52.94 | 1 | 5 | 0 | 1.47 | 46.67 | 0 |

### Běh (Run) 2
| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |
|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|
| **L0** | 96.67 | 70.59 | 1 | 5 | 0 | 1.57 | 40.0 | 0 |
| **L1** | 100.0 | 55.88 | 0 | 1 | 0 | 1.33 | 30.0 | 0 |
| **L2** | 96.67 | 52.94 | 1 | 5 | 0 | 1.4 | 40.0 | 0 |
| **L3** | 100.0 | 52.94 | 0 | 1 | 0 | 1.4 | 36.67 | 0 |
| **L4** | 100.0 | 61.76 | 0 | 1 | 0 | 1.4 | 46.67 | 0 |

### Běh (Run) 3
| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |
|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|
| **L0** | 90.0 | 67.65 | 3 | 5 | 0 | 1.8 | 63.33 | 0 |
| **L1** | 100.0 | 61.76 | 1 | 3 | 0 | 1.47 | 36.67 | 0 |
| **L2** | 100.0 | 50.0 | 0 | 1 | 0 | 1.4 | 40.0 | 0 |
| **L3** | 100.0 | 50.0 | 0 | 1 | 0 | 1.4 | 40.0 | 0 |
| **L4** | 100.0 | 52.94 | 0 | 1 | 0 | 1.47 | 46.67 | 0 |

### Běh (Run) 4
| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |
|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|
| **L0** | 83.33 | 76.47 | 6 | 5 | 0 | 1.83 | 46.67 | 0 |
| **L1** | 100.0 | 61.76 | 1 | 3 | 0 | 1.3 | 30.0 | 0 |
| **L2** | 100.0 | 52.94 | 0 | 1 | 0 | 1.43 | 40.0 | 0 |
| **L3** | 100.0 | 50.0 | 0 | 1 | 0 | 1.4 | 43.33 | 0 |
| **L4** | 100.0 | 55.88 | 0 | 1 | 0 | 1.4 | 43.33 | 0 |

### Běh (Run) 5
| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |
|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|
| **L0** | 96.67 | 67.65 | 1 | 5 | 0 | 1.8 | 66.67 | 0 |
| **L1** | 100.0 | 61.76 | 0 | 1 | 0 | 1.27 | 23.33 | 0 |
| **L2** | 100.0 | 52.94 | 0 | 1 | 0 | 1.47 | 46.67 | 0 |
| **L3** | 100.0 | 47.06 | 0 | 1 | 0 | 1.43 | 36.67 | 0 |
| **L4** | 100.0 | 55.88 | 0 | 1 | 0 | 1.47 | 46.67 | 0 |

---

## 🎯 Výsledky pro Výzkumné otázky (Průměr ze všech runů)

### RQ1: Vliv kontextu na Validity Rate
| Level | Validity Rate (%) | Stale Testy (avg) | Iterace ke konvergenci (avg) | Empty Testy (avg) | Plan Adherence (%) |
|-------|-------------------|-------------------|------------------------------|-------------------|--------------------|
| **L0** | 91.33 | 2.8 | 5.0 | 0.0 | 0.0 |
| **L1** | 99.33 | 0.6 | 2.6 | 0.0 | 0.0 |
| **L2** | 99.33 | 0.2 | 1.8 | 0.0 | 0.0 |
| **L3** | 100.0 | 0.2 | 1.4 | 0.0 | 0.0 |
| **L4** | 99.33 | 0.2 | 1.8 | 0.0 | 0.0 |

**Rychlá analýza (doplň):**
* Roste validity rate stabilně?
* Opravil model něco v repair loopu, nebo testy končí jako stale?

### RQ2: Code & Endpoint Coverage
| Level | EP Coverage (%) | Agreg. Assertion Depth | Avg Test Length (řádky) | Response Validation (%) |
|-------|-----------------|------------------------|-------------------------|-------------------------|
| **L0** | 70.0 | 1.81 | 0.0 | 56.0 |
| **L1** | 59.41 | 1.34 | 0.0 | 30.67 |
| **L2** | 52.94 | 1.43 | 0.0 | 41.33 |
| **L3** | 49.41 | 1.41 | 0.0 | 39.33 |
| **L4** | 55.88 | 1.44 | 0.0 | 46.0 |

**Rychlá analýza (doplň):**
* Klesá nebo roste pokrytí endpointů s vyšším kontextem?
* Zvyšuje se kvalita testů (Response Validation, Ast depth) u L3/L4?

---
*Generováno skriptem z JSON výsledků.*
