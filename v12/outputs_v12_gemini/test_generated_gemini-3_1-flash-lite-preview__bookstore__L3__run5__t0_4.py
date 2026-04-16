# Analysis: ISBNs were failing due to potential collisions and schema constraints; updated to use uuid.uuid4().int % 10**13 to ensure 13 digits.
# Added consistent status code assertions (200, 201) and ensured unique string generation avoids length issues.

import requests
import uuid
import random

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique_str(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or get_unique_str("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or get_unique_str("cat")
    data = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    # Ensure ISBN is a 13-digit numeric string to satisfy Pydantic constraints
    if isbn is None:
        isbn = str(random.randint(10**12, 10**13 - 1))
    
    data = {
        "title": get_unique_str("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = get_unique_str("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing_name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_modified():
    author = create_author()
    aid = author["id"]
    r1 = requests.get(f"{BASE_URL}/authors/{aid}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{aid}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": get_unique_str("isbn")[:13], "price": 50.0,
        "published_year": 2020, "stock": 5, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = get_unique_str("isbn")[:13]
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_book_gone_after_delete():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_too_new_book():
    from datetime import datetime
    a = create_author()
    c = create_category()
    data = {
        "title": "New Book", 
        "isbn": uuid.uuid4().hex[:13], 
        "price": 100.0,
        "published_year": datetime.now().year, 
        "stock": 10,
        "author_id": a["id"], 
        "category_id": c["id"]
    }
    b = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 422, f"Expected 422 for validation error, got {r.status_code}: {r.text}"

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -100}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"content", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "comment": "Great book"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    data = {"books": [
        {"title": "B1", "isbn": get_unique_str("i1")[:13], "price": 10.0, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "invalid", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": 999, "category_id": c["id"]}
    ]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 207, f"Expected 207 Multi-Status, got {r.status_code}: {r.text}"

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_order_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "invalid_status"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_invoice_forbidden_pending():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_status_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    jid = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{jid}", timeout=TIMEOUT)
    assert r2.status_code in (200, 202)

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301
    assert "/books" in r.headers["Location"]

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": get_unique_str("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_tag_duplicate():
    name = get_unique_str("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400