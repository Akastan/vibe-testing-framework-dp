import pytest
import requests
import uuid
import time
import json

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order():
    book = create_book()
    stock_update_response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    assert stock_update_response.status_code == 200
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_success():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_422():
    payload = {}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
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
    get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 404

def test_delete_author_with_books_409():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    book_response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert book_response.status_code == 201
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
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
    author = create_author()
    category = create_category()
    title1 = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload1 = {
        "title": title1,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
    assert response1.status_code == 201
    title2 = unique("book2")
    payload2 = {
        "title": title2,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2021,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
    assert response2.status_code == 409
    data = response2.json()
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
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410
    data = get_response.json()
    assert "detail" in data

def test_soft_delete_book_204():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_delete_already_deleted_book_410():
    book = create_book()
    delete_response1 = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response1.status_code == 204
    delete_response2 = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response2.status_code == 410
    data = delete_response2.json()
    assert "detail" in data

def test_restore_soft_deleted_book_200():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_restore_not_deleted_book_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book_200():
    book = create_book()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert "discounted_price" in data
    assert data["book_id"] == book["id"]

def test_apply_discount_to_new_book_400():
    author = create_author()
    category = create_category()
    title = unique("newbook")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    current_year = 2026
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": current_year,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    book_response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert book_response.status_code == 201
    book = book_response.json()
    discount_payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_rate_limit_429():
    book = create_book()
    for i in range(5):
        payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200, f"Unexpected status {response.status_code} on request {i+1}: {response.text[:200]}"
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "detail" in data

def test_increase_stock_success():
    book = create_book()
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == book["stock"] + 5

def test_decrease_stock_below_zero_400():
    book = create_book()
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_success():
    book = create_book()
    payload = {
        "rating": 5,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_review_for_deleted_book_410():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    payload = {
        "rating": 5,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_create_order_success():
    book = create_book()
    stock_update_response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    assert stock_update_response.status_code == 200
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2
    get_book_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    updated_book = get_book_response.json()
    assert updated_book["stock"] == 8

def test_create_order_insufficient_stock_400():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition_200():
    order = create_order()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_400():
    order = create_order()
    payload1 = {"status": "confirmed"}
    response1 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload1, timeout=TIMEOUT)
    assert response1.status_code == 200
    payload2 = {"status": "delivered"}
    response2 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload2, timeout=TIMEOUT)
    assert response2.status_code == 400
    data = response2.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order_200():
    order = create_order()
    confirm_payload = {"status": "confirmed"}
    confirm_response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=confirm_payload, timeout=TIMEOUT)
    assert confirm_response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order_403():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    isbn1 = f"978{uuid.uuid4().hex[:9]}"
    isbn2 = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("book1"),
                "isbn": isbn1,
                "price": 19.99,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("book2"),
                "isbn": isbn1,
                "price": 29.99,
                "published_year": 2021,
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

def test_bulk_create_books_missing_api_key_401():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": isbn,
                "price": 19.99,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data