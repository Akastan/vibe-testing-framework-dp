import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=1980):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code == 201, f"Create author failed: {r.text}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201, f"Create category failed: {r.text}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("book")
    isbn = isbn or unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201, f"Create book failed: {r.text}"
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

def test_update_author_etag_mismatch():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "New Name"}, headers={"If-Match": "wrong-etag"}, timeout=30)
    assert r.status_code == 412

def test_create_book_valid():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": unique("isbn")[:13], "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")[:13]
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    a = create_author()
    c = create_category()
    for _ in range(3): create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 2}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3

def test_list_books_filter_price():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"], price=100.0)
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 50.0, "max_price": 150.0}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1

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

def test_restore_active_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2020)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_update_stock_non_numeric():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": "abc"}, timeout=30)
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
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", 
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": "B1", "isbn": "BULK000001", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "BULK000001", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=30)
    assert r.status_code == 207

def test_start_export_valid():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    job_id = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r2.status_code == 202

def test_poll_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/fake-id", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_mode():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": True}, timeout=30)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": False}, timeout=30)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401