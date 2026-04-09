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
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1990}, timeout=30)
    assert r.status_code == 201, f"Author helper failed: {r.text}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201, f"Category helper failed: {r.text}"
    return r.json()

def create_book(author_id, category_id, isbn=None, stock=10):
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": isbn, "price": 100.0,
        "published_year": 2020, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201, f"Book helper failed: {r.text}"
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
    assert data["author_id"] == a["id"]

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "dup", "isbn": isbn, "price": 10,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_get_book_soft_deleted():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_restore_non_deleted_book():
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
    r_book = requests.post(f"{BASE_URL}/books", json={
        "title": "new", "isbn": unique("isbn"), "price": 100,
        "published_year": 2026, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    b = r_book.json()
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

def test_update_stock_negative_result():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400

def test_upload_cover_unsupported_type():
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

def test_create_tag_duplicate():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_add_invalid_tag_id():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [99999]}, timeout=30)
    assert r.status_code == 404

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "u@u.com",
        "items": [{"book_id": b["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "u@u.com",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "u@u.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    o = r_ord.json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "u@u.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    o = r_ord.json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": "B1", "isbn": unique("isbn"), "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "invalid", "price": -1, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=30)
    assert r.status_code == 422

def test_clone_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": unique("isbn")}, timeout=30)
    assert r.status_code == 201

def test_start_export_authorized():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=30)
    assert r.status_code == 202

def test_get_nonexistent_job():
    r = requests.get(f"{BASE_URL}/exports/fake-id", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401

def test_get_stats_authorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers=AUTH, timeout=30)
    assert r.status_code == 200

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401