import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("Category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id, published_year=2020, stock=10):
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_successfully():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1990

def test_create_author_missing_name_returns_422():
    payload = {"bio": "No name"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author_returns_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_successfully():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
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
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "title": unique("Book"),
        "isbn": book["isbn"],
        "price": 25.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    params = {"page": 1, "page_size": 5, "author_id": author["id"], "min_price": 10}
    response = requests.get(f"{BASE_URL}/books", params=params, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1

def test_get_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", params={"author_id": author["id"]}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    items = [b for b in data["items"] if b["id"] == book["id"]]
    assert len(items) == 0

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_apply_valid_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    payload = {"discount_percent": 10}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "original_price" in data
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * (1 - payload["discount_percent"] / 100), 2)

def test_apply_discount_to_new_book_returns_400():
    author = create_author()
    category = create_category()
    current_year = 2026
    book = create_book(author["id"], category["id"], published_year=current_year)
    payload = {"discount_percent": 10}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["stock"] == 5

def test_add_review_to_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {"rating": 5, "reviewer_name": unique("Reviewer"), "comment": "Great book"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == payload["reviewer_name"]

def test_create_tag_successfully():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_with_sufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    initial_stock = book["stock"]
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 3
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["stock"] == initial_stock - 3

def test_create_order_insufficient_stock_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["stock"] == 2

def test_update_order_status_to_cancelled_returns_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    initial_stock = book["stock"]
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 4}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    book_after_order = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_after_order["stock"] == initial_stock - 4
    payload = {"status": "cancelled"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    book_after_cancel = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_after_cancel["stock"] == initial_stock

def test_invalid_status_transition_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    payload2 = {"status": "delivered"}
    response2 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload2, timeout=TIMEOUT)
    assert response2.status_code == 400
    data = response2.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    status_response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=TIMEOUT)
    assert status_response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]
    assert "items" in data
    assert len(data["items"]) == 1

def test_get_invoice_for_pending_order_returns_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_returns_207():
    author = create_author()
    category = create_category()
    existing_book = create_book(author["id"], category["id"])
    unique_isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("Book"),
                "isbn": existing_book["isbn"],
                "price": 20.0,
                "published_year": 2021,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book"),
                "isbn": unique_isbn,
                "price": 30.0,
                "published_year": 2022,
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
    assert len(data["results"]) == 2
    success = [r for r in data["results"] if r["status"] == "created"]
    failed = [r for r in data["results"] if r["status"] == "error"]
    assert len(success) == 1
    assert len(failed) == 1

def test_bulk_create_without_api_key_returns_401():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("Book"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
                "price": 15.0,
                "published_year": 2020,
                "stock": 2,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_clone_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    new_isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {"new_isbn": new_isbn, "new_title": unique("Clone"), "stock": 7}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["title"] == payload["new_title"]
    assert data["author_id"] == book["author_id"]
    assert data["category_id"] == book["category_id"]
    assert data["price"] == book["price"]
    assert data["published_year"] == book["published_year"]
    assert data["stock"] == 7