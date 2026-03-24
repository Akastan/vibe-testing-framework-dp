# Analýza běhu: [název] — [datum]

## Konfigurace experimentu

| Parametr | Hodnota |
|----------|---------|
| LLM modely | |
| Úrovně kontextu | L0, L1, L2, L3, L4 |
| API | |
| Iterací | |
| Runů na kombinaci | |
| Testů na run | |
| Stale threshold | |

---

## RQ1: Jak úroveň poskytnutého kontextu (L0–L4) ovlivňuje kvalitu LLM-generovaných API testů, měřenou pomocí test validity rate, hloubky asercí a míry validace response body?

### Validity rate per level

| Level | Run 1 | Run 2 | Run 3 | Avg ± Std |
|-------|-------|-------|-------|-----------|
| L0 | | | | |
| L1 | | | | |
| L2 | | | | |
| L3 | | | | |
| L4 | | | | |

### Assertion depth a response validation

| Level | Assert Depth (avg) | Response Validation (avg) |
|-------|--------------------|---------------------------|
| L0 | | |
| L1 | | |
| L2 | | |
| L3 | | |
| L4 | | |

### Analýza trendu L0→L4

**L0→L1:**
<!-- Co přinesla dokumentace? Jaký byl nárůst validity a proč? -->

**L1→L2:**
<!-- Co přinesl zdrojový kód? -->

**L2→L3:**
<!-- Co přineslo DB schéma? -->

**L3→L4:**
<!-- Co přinesly referenční testy? -->

---

## RQ2: Jak se liší endpoint coverage a code coverage vygenerovaných testů mezi jednotlivými úrovněmi kontextu?

### Endpoint coverage per level

| Level | Run 1 | Run 2 | Run 3 | Avg | Std |
|-------|-------|-------|-------|-----|-----|
| L0 | | | | | |
| L1 | | | | | |
| L2 | | | | | |
| L3 | | | | | |
| L4 | | | | | |

### Code coverage per level

| Level | Code Cov (avg) | Std | crud.py (avg) | main.py (avg) |
|-------|----------------|-----|---------------|---------------|
| L0 | | | | |
| L1 | | | | |
| L2 | | | | |
| L3 | | | | |
| L4 | | | | |

### Analýza

<!-- Vztah mezi EP coverage a code coverage, paradoxy, trendy -->

---

## RQ3: Jaké typy selhání se vyskytují ve vygenerovaných testech a jak se jejich distribuce mění s rostoucím kontextem?

### Failure taxonomy (první iterace)

| Typ selhání | L0 | L1 | L2 | L3 | L4 |
|-------------|----|----|----|----|-----|
| wrong_status_code | | | | | |
| timeout | | | | | |
| assertion_mismatch | | | | | |
| other | | | | | |

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg fixed | Avg never-fixed | Fix rate |
|-------|---------------------|-----------|-----------------|----------|
| L0 | | | | |
| L1 | | | | |
| L2 | | | | |
| L3 | | | | |
| L4 | | | | |

### Analýza per kategorie

**Timeout:**
<!-- Kdy a proč se vyskytují timeouty? -->

**Wrong status code:**
<!-- Nejčastější záměny, na kterých levelech? -->

**Assertion mismatch:**
<!-- Příklady a příčiny -->

**Halucinace endpointů:**
<!-- Vyskytly se? Na kterých levelech? -->

---

## Appendix — surová data per run

### L0

<details>
<summary>L0 — Run 1</summary>

```
```
</details>

<details>
<summary>L0 — Run 2</summary>

```
```
</details>

<details>
<summary>L0 — Run 3</summary>

```
```
</details>

### L1

<details>
<summary>L1 — Run 1</summary>

```
```
</details>

<details>
<summary>L1 — Run 2</summary>

```
```
</details>

<details>
<summary>L1 — Run 3</summary>

```
```
</details>

### L2

<details>
<summary>L2 — Run 1</summary>

```
```
</details>

<details>
<summary>L2 — Run 2</summary>

```
```
</details>

<details>
<summary>L2 — Run 3</summary>

```
```
</details>

### L3

<details>
<summary>L3 — Run 1</summary>

```
```
</details>

<details>
<summary>L3 — Run 2</summary>

```
```
</details>

<details>
<summary>L3 — Run 3</summary>

```
```
</details>

### L4

<details>
<summary>L4 — Run 1</summary>

```
```
</details>

<details>
<summary>L4 — Run 2</summary>

```
```
</details>

<details>
<summary>L4 — Run 3</summary>

```
```
</details>