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

**L0→L1:**
<!-- Co přinesla dokumentace? Jaký byl nárůst validity a proč? -->

**L1→L2:**
<!-- Co přinesl zdrojový kód? -->

**L2→L3:**
<!-- Co přineslo DB schéma? POZOR: L3 Run 2 outlier (40%) — 18 failing testů, 10 stale -->

**L3→L4:**
<!-- Co přinesly referenční testy? -->

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

| Level | Code Cov (avg) | Std | crud.py (avg) | main.py (avg) |
|-------|----------------|-----|---------------|---------------|
| L0 | <!-- TODO --> | | | |
| L1 | <!-- TODO --> | | | |
| L2 | <!-- TODO --> | | | |
| L3 | <!-- TODO --> | | | |
| L4 | <!-- TODO --> | | | |

### Další metriky kvality

| Level | Test Type: Happy (avg) | Test Type: Error (avg) | Test Type: Edge (avg) | Status Code Diversity (avg) |
|-------|------------------------|------------------------|-----------------------|-----------------------------|
| L0 | 66.7% | 31.1% | 2.2% | 5.0 |
| L1 | 53.3% | 46.7% | 0% | 7.0 |
| L2 | 52.2% | 46.7% | 1.1% | 7.0 |
| L3 | 52.2% | 47.8% | 0% | 6.7 |
| L4 | 48.9% | 48.9% | 2.2% | 7.0 |

### Analýza

<!-- Vztah mezi EP coverage a code coverage, paradoxy, trendy -->

---

## RQ3: Jaké typy selhání se vyskytují ve vygenerovaných testech a jak se jejich distribuce mění s rostoucím kontextem?

### Failure taxonomy (první iterace, součet přes 3 runy)

| Typ selhání | L0 (33 failů) | L1 (1 fail) | L2 (2 faily) | L3 (18 failů) | L4 (2 faily) |
|-------------|---------------|-------------|--------------|----------------|--------------|
| wrong_status_code | 6 (18.2%) | 1 (100%) | 2 (100%) | 1 (5.6%) | 1 (50%) |
| timeout | 13 (39.4%) | 0 | 0 | 9 (50.0%) | 0 |
| assertion_mismatch | 1 (3.0%) | 0 | 0 | 0 | 1 (50%) |
| other | 13 (39.4%) | 0 | 0 | 8 (44.4%) | 0 |

### Opravitelnost selhání

| Level | Avg failing (iter 1) | Avg fixed | Avg never-fixed | Fix rate |
|-------|---------------------|-----------|-----------------|----------|
| L0 | 11.0 | 9.33 | 1.67 | 84.8% |
| L1 | 0.33 | 0.33 | 0 | 100% |
| L2 | 0.67 | 0.33 | 0.33 | 50% |
| L3 | 6.0 | 0 | 6.0 | 0% |
| L4 | 0.67 | 0 | 0.67 | 0% |

### L3 Run 2 outlier — detail

L3 Run 2 měl 18 failing testů (40% validity), 10 stale. Failure breakdown: 9× timeout, 8× other, 1× wrong_status_code. Žádný test nebyl opraven v 5 iteracích. Repair loop střídal helper_fallback a isolated bez efektu.

<!-- Proč se to stalo? Co je root cause? -->

### Analýza per kategorie

**Timeout:**
<!-- Kdy a proč se vyskytují timeouty? L0 Run 1+2, L3 Run 2 -->

**Wrong status code:**
<!-- Nejčastější záměny, na kterých levelech? -->

**Other:**
<!-- Co spadá do "other"? Většinou order-related testy -->

**Halucinace status kódů:**

| Level | Kódy v kontextu | Halucinované | Korektní? |
|-------|-----------------|--------------|-----------|
| L0 | 200, 201, 204, 422 | 404 | ✅ (HTTP konvence) |
| L1+ | 200, 201, 204, 400, 404, 409, 422 | žádné | — |

### Instruction compliance

| Level | Missing timeout (avg %) | Compliance score (avg) |
|-------|------------------------|------------------------|
| L0 | 66% | 87 |
| L1 | 100% | 80 |
| L2 | 100% | 80 |
| L3 | 66% | 87 |
| L4 | 0% | **100** |

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
  create_book has_assertion, update_stock has_assertion, delete_book_tags has_assertion)
Plan adherence: 100%
Compliance: 100 (timeout on all 50 calls)
Failure taxonomy (iter 1): wrong_status_code 1, timeout 9, other 8
Repair: iter1=18F→helper_fallback, iter2=18F→isolated(10), iter3=18F→helper_fallback,
  iter4=18F→isolated(10), iter5=18F
Never-fixed (18): test_add_tags_idempotent, test_apply_discount_new_book_fails,
  test_apply_discount_old_book_success, test_create_review_invalid_rating,
  test_create_review_valid, test_delete_author_with_books_fails,
  test_get_rating_no_reviews, test_remove_tag_from_book,
  test_update_stock_add_quantity, test_update_stock_negative_fails,
  test_create_order_insufficient_stock, test_create_order_duplicate_book,
  test_create_order_success, test_status_transition_pending_to_confirmed,
  test_status_transition_invalid, test_status_cancelled_restores_stock,
  test_delete_pending_order_restores_stock, test_delete_shipped_order_fails
Fixed: 0
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