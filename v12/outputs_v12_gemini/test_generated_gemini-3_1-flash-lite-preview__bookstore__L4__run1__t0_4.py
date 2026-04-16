# Analysis: The ISBN generator was creating a static 13-digit string causing collisions. Fixed by using a random 13-digit numeric string. Added missing headers to ensure compliance with API requirements.

import uuid
import requests
import random

BASE_URL = "http://localhost:8000"
AUTH = {"X-API-Key": "test-api-key"}
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = get_unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    # Generate a random 13-digit ISBN string to avoid collisions and satisfy schema constraints
    if isbn is None:
        isbn = "".join([str(random.randint(0, 9)) for _ in range(13)])
    
    payload = {
        "title": get_unique("Book"), 
        "isbn": isbn, 
        "price": 10.0,
        "published_year": 2020, 
        "author_id": author_id, 
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    name = get_unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_duplicate_category():
    name = get_unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_isbn():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "123", "price": 10.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_negative_price():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "1234567890", "price": -1.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_soft_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_invalid_percent():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn="1234567890")
    # Need old book for discount
    requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 2000}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -1}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 415

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn="1234567890")
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_duplicate_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn="1234567890")
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_invoice_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 404

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    a = create_author()
    c = create_category()
    for _ in range(4):
        requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [{
            "title": "T", "isbn": get_unique("1234567890"), "price": 1, "published_year": 2020,
            "author_id": a["id"], "category_id": c["id"]
        }]}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_clone_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn="1234567890")
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": "1234567890"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_export_books_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/fake", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_list_books_pagination_invalid():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_author_books_invalid_size():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}/books?page_size=999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_remove_nonexistent_tag_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999999]}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_shipped_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 403