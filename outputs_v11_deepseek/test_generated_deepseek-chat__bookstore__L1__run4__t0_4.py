import pytest
import requests
import uuid
import time
import json
from pathlib import Path

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

def create_book(author_id, category_id, published_year=2020, stock=10):
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(book_id, quantity=1):
    customer_name = unique("customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book_id, "quantity": quantity}]
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
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_books_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
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
        "price": 25.50,
        "published_year": 2020,
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
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "title": unique("book"),
        "isbn": book["isbn"],
        "price": 30.0,
        "published_year": 2021,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book_204():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    book_ids = [item["id"] for item in data["items"]]
    assert book["id"] not in book_ids

def test_restore_soft_deleted_book_200():
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

def test_restore_not_deleted_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    payload = {"discount_percent": 10.0}
    headers = {"X-API-Key": "admin"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == book["price"] * (1 - 10.0 / 100)

def test_apply_discount_to_new_book_400():
    author = create_author()
    category = create_category()
    current_year = 2026
    book = create_book(author["id"], category["id"], published_year=current_year)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_stock_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_for_book_201():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
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
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
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
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=2)
    assert order["total_price"] == book["price"] * 2
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    updated_book = response.json()
    assert updated_book["stock"] == 8

def test_create_order_insufficient_stock_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=1)
    customer_name = unique("customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_with_api_key_201():
    author = create_author()
    category = create_category()
    books = []
    for i in range(2):
        books.append({
            "title": unique("bulkbook"),
            "isbn": f"978{uuid.uuid4().hex[:9]}",
            "price": 20.0 + i,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    payload = {"books": books}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "total" in data
    assert data["total"] == 2

def test_bulk_create_books_without_api_key_401():
    author = create_author()
    category = create_category()
    books = [{
        "title": unique("bulkbook"),
        "isbn": f"978{uuid.uuid4().hex[:9]}",
        "price": 20.0,
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

def test_clone_book_success_201():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    new_isbn = f"979{uuid.uuid4().hex[:9]}"
    payload = {
        "new_isbn": new_isbn,
        "new_title": "Cloned Title",
        "stock": 3
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["title"] == "Cloned Title"
    assert data["stock"] == 3

def test_start_book_export_with_api_key_202():
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"