import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    if name is None:
        name = unique("author")
    data = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("cat")
    data = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, isbn=None):
    if isbn is None:
        isbn = "".join([str(uuid.uuid4().int)[:13]])
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
    assert r.status_code == 201
    return r.json()

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "born_year": 1990}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_etag_304():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    cat = create_category()
    data = {
        "title": unique("book"),
        "isbn": "123456789012",
        "price": 50.0,
        "published_year": 2022,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = "111111111111"
    create_book(author["id"], cat["id"], isbn=isbn)
    data = {
        "title": "Dup",
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r_get.status_code == 410

def test_get_deleted_book_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_deleted_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_restore_non_deleted_book_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_400():
    author = create_author()
    cat = create_category()
    data = {
        "title": "NewBook",
        "isbn": "999999999999",
        "price": 100.0,
        "published_year": 2026,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    book = requests.post(f"{BASE_URL}/books", json=data, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-20", timeout=30)
    assert r.status_code == 400

def test_upload_cover_unsupported_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"rating": 10, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = create_category(unique("tag")) # Using category helper as tag structure is similar for test
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tagname")}, timeout=30)
    tag_id = r.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 400

def test_update_order_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "a@b.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_403():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "a@b.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_clone_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"new_isbn": "1234567890123", "stock": 5}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=data, timeout=30)
    assert r.status_code == 201

def test_start_book_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    # Teardown
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)