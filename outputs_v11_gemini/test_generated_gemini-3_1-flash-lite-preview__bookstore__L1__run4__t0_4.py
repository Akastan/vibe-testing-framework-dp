import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    payload = {"name": name, "bio": "bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_author failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    payload = {"name": name, "description": "desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_category failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_book failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": "invalid"}, timeout=30)
    assert r.status_code == 412

def test_create_book_valid():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "1234567890", "price": 10.0, "published_year": 2020, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "12345678901"
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T2", "isbn": isbn, "price": 10.0, "published_year": 2020, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_get_book_soft_deleted():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_get_book_nonexistent():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=30)
    assert r.status_code == 404

def test_restore_active_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_too_high():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60.0}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": "1111111111", "price": 100.0, "published_year": 2026, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 429

def test_update_stock_negative_result():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-999", timeout=30)
    assert r.status_code == 400

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data")}, timeout=30)
    assert r.status_code == 415

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000)}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 413

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": API_KEY}, json={"books": [
        {"title": unique("B1"), "isbn": unique("111")[:13], "price": 10.0, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]},
        {"title": "", "isbn": "invalid", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=30)
    assert r.status_code == 422

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_add_item_to_shipped_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.post(f"{BASE_URL}/orders/{o['id']}/items", json={"book_id": b["id"], "quantity": 1}, timeout=30)
    assert r.status_code == 403

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200


def test_list_authors_pagination():
    author1 = create_author(name=unique("a1"))
    author2 = create_author(name=unique("a2"))

    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1

    r_next = requests.get(f"{BASE_URL}/authors", params={"skip": 1, "limit": 1}, timeout=30)
    assert r_next.status_code == 200
    data_next = r_next.json()
    assert len(data_next) == 1
    assert data_next[0]["id"] != data[0]["id"]

def test_get_author_etag_caching():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None

    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304