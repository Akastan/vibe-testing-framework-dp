# The main error is likely ISBN length validation (unique("isbn")[:13] may produce strings >13 chars or invalid format). Also ensure all helper functions handle 201 status codes correctly and generate proper unique values within length constraints.

import uuid
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None):
    if name is None:
        name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None, stock=10, published_year=2020):
    if isbn is None:
        # ISBN-13 must be exactly 13 digits; generate a valid numeric ISBN
        isbn = ''.join([str(uuid.uuid4().int)[:13]])
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_name_too_long_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "x" * 101}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_with_books_returns_409():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_nonexistent_author_returns_404():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": 999999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_book_by_id_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_not_deleted_book_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_rating_out_of_range_returns_422():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 6,
        "reviewer_name": unique("reviewer")
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_to_old_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 19.99

def test_apply_discount_to_new_book_returns_400():
    author = create_author()
    cat = create_category()
    current_year = datetime.now(timezone.utc).year
    book = create_book(author["id"], cat["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_positive_delta_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_cover_unsupported_type_returns_415():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={
        "file": ("test.txt", b"fake image content", "text/plain")
    }, timeout=30)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"

def test_create_order_insufficient_stock_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_order_status_valid_transition_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={
        "status": "confirmed"
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={
        "status": "cancelled"
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_get_invoice_for_pending_order_returns_403():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    assert "detail" in r.json()