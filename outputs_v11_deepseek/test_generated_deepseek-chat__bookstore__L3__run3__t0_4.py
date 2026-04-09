import json
import uuid
import time
import io
from pathlib import Path
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

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
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def get_author(author_id):
    response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    return response

def delete_author(author_id):
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    return response

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def get_category(category_id):
    response = requests.get(f"{BASE_URL}/categories/{category_id}", timeout=TIMEOUT)
    return response

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = str(uuid.uuid4().int)[:13]
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def get_book(book_id):
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    return response

def delete_book(book_id):
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    return response

def restore_book(book_id):
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
    return response

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def get_order(order_id):
    response = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    return response

def update_order_status(order_id, status):
    payload = {"status": status}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=TIMEOUT)
    return response

def get_invoice(order_id):
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=TIMEOUT)
    return response


def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert "created_at" in data

def test_create_author_missing_name_validation():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_author_with_if_none_match_304():
    author = create_author()
    first = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag is not None
    second = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert second.status_code == 304

def test_delete_author_with_books_conflict():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = str(uuid.uuid4().int)[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]

def test_create_book_duplicate_isbn_conflict():
    book = create_book()
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": book["isbn"],
        "price": 30.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_soft_deleted_gone():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410
    data = get_response.json()
    assert "detail" in data

def test_soft_delete_book_success():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_restore_soft_deleted_book_success():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    restored_book = get_response.json()
    assert restored_book["is_deleted"] is False

def test_restore_not_deleted_book_error():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book_success():
    book = create_book(published_year=2020)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book_error():
    current_year = time.localtime().tm_year
    book = create_book(published_year=current_year)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_rate_limit_exceeded():
    book = create_book(published_year=2020)
    payload = {"discount_percent": 5.0}
    for _ in range(5):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
    time.sleep(0.1)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "Retry-After" in response.headers

def test_update_stock_increase_success():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    assert get_response.json()["stock"] == 15

def test_update_stock_insufficient_error():
    book = create_book(stock=3)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_cover_file_too_large():
    book = create_book()
    large_file = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
    files = {"file": ("cover.jpg", large_file, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_success():
    book = create_book()
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_tag_duplicate_name_conflict():
    tag = create_tag()
    payload = {"name": tag["name"]}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_add_tags_to_book_success():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = {t["id"] for t in data["tags"]}
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_with_insufficient_stock_error():
    book = create_book(stock=1)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_order_duplicate_book_id_error():
    book = create_book(stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_invalid_transition_error():
    order = create_order()
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_to_cancelled_returns_stock():
    book = create_book(stock=20)
    order = create_order(items=[{"book_id": book["id"], "quantity": 5}])
    initial_stock = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()["stock"]
    assert initial_stock == 15
    payload = {"status": "cancelled"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    final_stock = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()["stock"]
    assert final_stock == 20

def test_get_invoice_for_pending_order_forbidden():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    existing_book = create_book(author_id=author["id"], category_id=category["id"])
    books = [
        {
            "title": unique("book"),
            "isbn": str(uuid.uuid4().int)[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        {
            "title": unique("book"),
            "isbn": existing_book["isbn"],
            "price": 20.0,
            "published_year": 2021,
            "stock": 3,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    payload = {"books": books}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert data["total"] == 2
    assert data["created"] == 1
    assert data["failed"] == 1
    assert "results" in data

def test_bulk_create_books_missing_api_key_401():
    author = create_author()
    category = create_category()
    books = [{
        "title": unique("book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }]
    payload = {"books": books}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_clone_book_duplicate_isbn_conflict():
    source_book = create_book()
    payload = {
        "new_isbn": source_book["isbn"],
        "new_title": unique("clone"),
        "stock": 0
    }
    response = requests.post(f"{BASE_URL}/books/{source_book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data