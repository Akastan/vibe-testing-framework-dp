import requests
import uuid
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
        json={"name": name, "bio": "bio", "born_year": 1990}, 
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

def create_book(author_id, category_id, isbn=None, title=None):
    isbn = isbn or unique("isbn")[:13]
    title = title or unique("book")
    r = requests.post(
        f"{BASE_URL}/books", 
        json={
            "title": title, 
            "isbn": isbn, 
            "price": 100.0,
            "published_year": 2020, 
            "stock": 10,
            "author_id": author_id, 
            "category_id": category_id
        }, 
        headers=AUTH,
        timeout=30
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    data = create_author()
    assert "id" in data
    assert data["name"].startswith("author_")

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_valid():
    a = create_author()
    c = create_category()
    data = create_book(a["id"], c["id"])
    assert "id" in data
    assert data["isbn"] is not None

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

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

def test_restore_active_book():
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

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 422

def test_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 422

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
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=30)
    assert r.status_code == 413

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 201

def test_add_tags_nonexistent():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_duplicate_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", 
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": "B1", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=30)
    assert r.status_code == 207

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_clone_book_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": "9876543210"}, timeout=30)
    assert r.status_code == 201

def test_start_export_valid():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    jid = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{jid}", timeout=30)
    assert r2.status_code == 202

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/invalid", timeout=30)
    assert r.status_code == 404

def test_get_stats_authorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers=AUTH, timeout=30)
    assert r.status_code == 200

def test_toggle_maintenance_mode():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": True}, timeout=30)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": False}, timeout=30)

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301


def test_get_author_etag_caching():
    author = create_author()
    author_id = author["id"]
    
    r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    
    r2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304
    
    r3 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": "invalid-etag"}, timeout=30)
    assert r3.status_code == 200
    assert r3.json()["id"] == author_id