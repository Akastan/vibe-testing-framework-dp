import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_name_validation():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_duplicate_name_conflict():
    name = unique("category")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn_conflict():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_nonexistent_author_404():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": 999999,
        "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_get_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book_gone():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_get_book_with_etag_not_modified():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    etag = r.headers.get("ETag")
    assert etag is not None
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_soft_delete_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books", params={"search": book["isbn"]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0

def test_restore_soft_deleted_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_apply_discount_to_old_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["original_price"] == 100
    assert data["discount_percent"] == 25
    assert data["discounted_price"] == 75

def test_apply_discount_to_new_book_rejected():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], price=100, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], price=100, published_year=2020)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5}, headers=AUTH_HEADERS, timeout=30)
        assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5}, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    data = r.json()
    assert "detail" in data

def test_increase_stock_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_fails():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_file_too_large():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("big.jpg", big_data, "image/jpeg")}, timeout=30)
    assert r.status_code == 413
    data = r.json()
    assert "detail" in data

def test_upload_cover_unsupported_file_type():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("doc.txt", b"hello", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] is not None

def test_create_order_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_price"] == book["price"] * 2
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.json()["stock"] == 8

def test_create_order_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_order_duplicate_book_items():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    order = create_order(unique("customer"), f"{unique('email')}@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    order = create_order(unique("customer"), f"{unique('email')}@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10, price=50)
    order = create_order(unique("customer"), f"{unique('email')}@test.com", [{"book_id": book["id"], "quantity": 2}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["invoice_number"].startswith("INV-")
    assert data["subtotal"] == 100
    assert data["item_count"] == 1

def test_get_invoice_for_pending_order_forbidden():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13], stock=10)
    order = create_order(unique("customer"), f"{unique('email')}@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    isbn1 = unique("isbn")[:13]
    isbn2 = unique("isbn")[:13]
    create_book(author["id"], category["id"], isbn=isbn1)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH_HEADERS, json={
        "books": [
            {
                "title": unique("book"),
                "isbn": isbn1,
                "price": 10,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            {
                "title": unique("book"),
                "isbn": isbn2,
                "price": 20,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"],
            }
        ]
    }, timeout=30)
    assert r.status_code == 207
    data = r.json()
    assert data["total"] == 2
    assert data["created"] == 1
    assert data["failed"] == 1
    assert len(data["results"]) == 2

def test_bulk_create_books_without_api_key_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data