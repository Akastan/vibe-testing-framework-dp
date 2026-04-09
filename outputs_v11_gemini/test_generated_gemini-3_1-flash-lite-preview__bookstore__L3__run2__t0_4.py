import requests
import uuid
import time
from typing import Optional


BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")
    data = {"title": "Book", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["isbn"] == isbn

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")
    create_book(author["id"], cat["id"], isbn=isbn)
    data = {"title": "Book2", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    author = create_author()
    cat = create_category()
    for _ in range(3):
        create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=2", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3

def test_get_book_soft_deleted():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_update_book_etag_mismatch():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New"}, headers={"If-Match": "wrong"}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_restore_non_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_new_book_error():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    # Book must be old for discount
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 2000}, timeout=TIMEOUT)
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_insufficient():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-99", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_too_large():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.jpg", b"0" * 3 * 1024 * 1024, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_upload_cover_invalid_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", b"data", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_create_review_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 9, "reviewer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(t["id"] == tag["id"] for t in r.json()["tags"])

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"customer_name": "Name", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 999}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"customer_name": "Name", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_invalid_status_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    author = create_author()
    cat = create_category()
    data = {"books": [
        {"title": unique("B1"), "isbn": unique("isbn1"), "price": 10, "published_year": 2020, "stock": 1, "author_id": author["id"], "category_id": cat["id"]},
        {"title": unique("B2"), "isbn": "invalid", "price": 10, "published_year": 2020, "stock": 1, "author_id": author["id"], "category_id": cat["id"]}
    ]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_clone_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": "0987654321"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["isbn"] == "0987654321"

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    job_id = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=TIMEOUT)
    assert r2.status_code == 202

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["maintenance_mode"] is True
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301
    assert "/books" in r.headers["Location"]

def test_health_check_operational():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def create_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()


def test_get_author_etag_caching():
    author = create_author()
    author_id = author["id"]
    
    r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    
    r2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304
    assert r2.text == ""