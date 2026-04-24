# The main error is that ISBN must be exactly 13 characters, but unique() generates 8 random chars plus prefix. We need to generate exactly 13 chars for ISBN.
# Also, some endpoints require API key header for authentication which is missing in helpers.

import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        # Generate exactly 13 characters for ISBN
        isbn = uuid.uuid4().hex[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_name_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "associated book" in data["detail"].lower()

def test_create_category_duplicate_name_409():
    name = unique("Category")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_create_book_nonexistent_author_404():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": unique("ISBN")[:13],
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data
    assert "author" in data["detail"].lower()

def test_get_soft_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data
    assert "deleted" in data["detail"].lower()

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", headers=AUTH, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20.0}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 100.0
    assert data["discounted_price"] == 80.0
    assert data["book_id"] == book["id"]

def test_apply_discount_to_new_book_400():
    author = create_author()
    category = create_category()
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], published_year=current_year, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "more than 1 year ago" in data["detail"].lower()

def test_update_stock_negative_result_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "insufficient" in data["detail"].lower()

def test_upload_cover_wrong_type_415():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"not an image", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data
    assert "unsupported" in data["detail"].lower()

def test_upload_cover_too_large_413():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    large_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("large.jpg", large_data, "image/jpeg")}, timeout=30)
    assert r.status_code == 413
    data = r.json()
    assert "detail" in data
    assert "too large" in data["detail"].lower()

def test_create_review_on_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": "Test Reviewer",
        "comment": "Great book"
    }, timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data
    assert "deleted" in data["detail"].lower()

def test_create_tag_duplicate_name_409():
    name = unique("Tag")
    create_tag(name=name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_delete_tag_with_books_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "associated" in data["detail"].lower()

def test_create_order_insufficient_stock_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "insufficient stock" in data["detail"].lower()

def test_create_order_duplicate_book_id_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "duplicate" in data["detail"].lower()

def test_update_order_status_invalid_transition_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Test Customer", "test@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "transition" in data["detail"].lower()

def test_delete_confirmed_order_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Test Customer", "test@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "cannot delete" in data["detail"].lower()

def test_get_invoice_pending_order_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Test Customer", "test@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    assert "cannot generate invoice" in data["detail"].lower()

def test_add_item_to_non_pending_order_403():
    author = create_author()
    category = create_category()
    book1 = create_book(author["id"], category["id"], isbn=unique("ISBN1")[:13], stock=10)
    book2 = create_book(author["id"], category["id"], isbn=unique("ISBN2")[:13], stock=10)
    order = create_order("Test Customer", "test@example.com", [{"book_id": book1["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/orders/{order['id']}/items", json={"book_id": book2["id"], "quantity": 1}, timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    assert "only pending orders" in data["detail"].lower()

def test_bulk_create_without_api_key_401():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "invalid or missing api key" in data["detail"].lower()

def test_bulk_create_partial_success_207():
    author = create_author()
    category = create_category()
    isbn1 = unique("ISBN")[:13]
    isbn2 = unique("ISBN")[:13]
    create_book(author["id"], category["id"], isbn=isbn1)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={
        "books": [
            {
                "title": unique("Book"),
                "isbn": isbn1,
                "price": 29.99,
                "published_year": 2020,
                "stock": 10,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book"),
                "isbn": isbn2,
                "price": 19.99,
                "published_year": 2021,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }, timeout=30)
    assert r.status_code == 207
    data = r.json()
    assert "created" in data
    assert "failed" in data
    assert data["created"] == 1
    assert data["failed"] == 1
    assert "results" in data
    assert len(data["results"]) == 2

def test_clone_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book["isbn"]}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_export_books_without_api_key_401():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "invalid or missing api key" in data["detail"].lower()

def test_toggle_maintenance_without_api_key_401():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "invalid or missing api key" in data["detail"].lower()

def test_get_statistics_without_api_key_401():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "invalid or missing api key" in data["detail"].lower()