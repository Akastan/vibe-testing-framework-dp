import uuid
import requests
import pytest


BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    r = requests.post(
        f"{BASE_URL}/authors", 
        json={"name": name, "born_year": 1990}, 
        headers=AUTH, 
        timeout=30
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    r = requests.post(
        f"{BASE_URL}/categories", 
        json={"name": name}, 
        headers=AUTH, 
        timeout=30
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")
    r = requests.post(
        f"{BASE_URL}/books", 
        json={
            "title": unique("book"), 
            "isbn": isbn, 
            "price": 10.0,
            "published_year": 2020, 
            "author_id": author_id, 
            "category_id": category_id
        }, 
        headers=AUTH, 
        timeout=30
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_etag_304():
    a = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{a['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_get_author_nonexistent():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_valid():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_soft_delete_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_get_soft_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_restore_active_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2026, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-1", timeout=30)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=30)
    assert r.status_code == 415

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0"*(3*1024*1024), "image/jpeg")}, timeout=30)
    assert r.status_code == 413

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 6, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn=unique("isbn"))
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, headers=AUTH, timeout=30)
    assert r.status_code == 201

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", 
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, headers=AUTH, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, headers=AUTH, timeout=30)
    assert r.status_code == 422

def test_get_invoice_pending_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, headers=AUTH, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", headers=AUTH, timeout=30)
    assert r.status_code == 400

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": "B1", "isbn": unique("isbn"), "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "invalid", "price": -1, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    job_id = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r2.status_code == 202

def test_toggle_maintenance_mode():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": True}, timeout=30)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": False}, timeout=30)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301