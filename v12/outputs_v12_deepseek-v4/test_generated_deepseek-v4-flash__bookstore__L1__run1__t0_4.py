# Analysis: The main issue is likely that the unique function generates strings that exceed field length limits (e.g., ISBN max 13 chars, name max lengths). Also, the helpers may need to handle API key headers for authenticated endpoints.
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")[:50]  # Truncate to avoid length issues
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("cat")[:50]  # Truncate to avoid length issues
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")[:100]  # Truncate to avoid length issues
    if isbn is None:
        isbn = unique("isbn")[:13]  # ISBN must be exactly 13 chars or less
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")[:30]  # Truncate to avoid length issues
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

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

def test_get_author_by_id_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    book_isbn = unique("isbn")[:13]
    book_title = unique("book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": book_title,
        "isbn": book_isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code in (200, 201)
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    title = unique("book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_nonexistent_author_returns_404():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_get_book_returns_200_with_etag():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "ETag" in r.headers or "etag" in r.headers

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book_returns_204():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_not_deleted_book_returns_400():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_to_old_book_returns_200():
    book = create_book(published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20.0}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 20.0

def test_apply_discount_to_new_book_returns_400():
    current_year = 2026
    book = create_book(published_year=current_year, price=50.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 400

def test_update_stock_positive_delta_returns_200():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_negative_delta_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400

def test_upload_cover_valid_image_returns_200():
    book = create_book()
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type_returns_415():
    book = create_book()
    files = {"file": ("test.txt", b"text data", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("rev"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_create_order_success():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_status_valid_transition_returns_200():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_for_confirmed_order_returns_200():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data

def test_get_invoice_for_pending_order_returns_403():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_books_all_success_returns_201():
    author = create_author()
    category = create_category()
    books_data = []
    for i in range(3):
        books_data.append({
            "title": unique("bulk"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": books_data}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201