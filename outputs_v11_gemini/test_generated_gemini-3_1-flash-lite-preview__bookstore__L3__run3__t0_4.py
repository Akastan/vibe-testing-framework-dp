import requests
import uuid
import time
from typing import Optional

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201, f"Failed to create author: {r.text}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert r.status_code == 201, f"Failed to create category: {r.text}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")[:13]
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201, f"Failed to create book: {r.text}"
    return r.json()

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test", "born_year": 2000}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "test"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "New Name"}, headers={"If-Match": "wrong-etag"}, timeout=30)
    assert r.status_code == 412

def test_create_book_success():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["isbn"] == isbn

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")[:13]
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    a = create_author()
    c = create_category()
    for _ in range(3): create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=2", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3

def test_list_books_filter_price():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books?min_price=50", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_deleted_book_410():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_delete_book_soft_delete():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    # Book must be old for discount
    requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 2000}, timeout=30)
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-99", timeout=30)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "test"}, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert any(tag["id"] == t["id"] for tag in r.json()["tags"])

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.cz",
        "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_invalid_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_invoice_forbidden_pending():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    data = {
        "books": [
            {"title": unique("B1"), "isbn": unique("1234567890")[:13], "price": 10, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]},
            {"title": "B2", "isbn": "INVALID", "price": 10, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]}
        ]
    }
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": b["isbn"]}, timeout=30)
    assert r.status_code == 409

def test_export_books_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    # Teardown
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_catalog_redirect_301():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301
    assert "books" in r.headers["Location"]

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_author_etag_caching():
    author = create_author()
    author_id = author["id"]
    
    r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    
    r2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304
    assert r2.text == ""