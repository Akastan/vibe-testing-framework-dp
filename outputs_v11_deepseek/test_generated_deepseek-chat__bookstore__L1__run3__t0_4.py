import uuid
import time
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

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
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

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_success():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_422():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_by_id_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books_204():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_books_409():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    payload = {
        "title": title,
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
    assert data["title"] == title
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_409():
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

def test_get_book_success():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_410():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book_204():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", [])
    book_ids = [item["id"] for item in items]
    assert book["id"] not in book_ids

def test_restore_soft_deleted_book_200():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_restore_not_deleted_book_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book_200():
    book = create_book(published_year=2020)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    expected_price = round(book["price"] * (1 - 10.0 / 100), 2)
    assert data["discounted_price"] == expected_price

def test_apply_discount_to_new_book_400():
    current_year = 2026
    book = create_book(published_year=current_year)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_rate_limit_429():
    book = create_book(published_year=2020)
    payload = {"discount_percent": 10.0}
    for _ in range(5):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code in (200, 429)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data

def test_increase_stock_success():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_400():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
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

def test_create_review_for_deleted_book_410():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    payload = {
        "rating": 3,
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_create_order_success():
    book = create_book(stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 2
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    updated_book = response.json()
    assert updated_book["stock"] == 8

def test_create_order_insufficient_stock_400():
    book = create_book(stock=1)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 5
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition_200():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 1
            }
        ]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_400():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 1
            }
        ]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order_200():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 1
            }
        ]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    confirm_payload = {"status": "confirmed"}
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=confirm_payload, timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order_403():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {
                "book_id": book["id"],
                "quantity": 1
            }
        ]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    existing_book = create_book(author_id=author["id"], category_id=category["id"])
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": unique("isbn")[:13],
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("book"),
                "isbn": existing_book["isbn"],
                "price": 25.0,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert "created" in data
    assert "failed" in data
    assert "results" in data

def test_bulk_create_books_missing_api_key_401():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": unique("isbn")[:13],
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_clone_book_success():
    book = create_book()
    payload = {
        "new_isbn": unique("clone")[:13],
        "new_title": "Cloned Title",
        "stock": 7
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == payload["new_isbn"]
    assert data["stock"] == 7
    assert data["author_id"] == book["author_id"]