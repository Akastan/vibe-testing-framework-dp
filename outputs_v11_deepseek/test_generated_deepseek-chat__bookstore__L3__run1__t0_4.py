import pytest
import requests
import uuid
import time
import io
import json

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_create_author_valid_data():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_name():
    payload = {"bio": "Test bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books_conflict():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_category_duplicate_name():
    category = create_category()
    payload = {"name": category["name"], "description": "Duplicate"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn():
    book = create_book()
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": book["isbn"],
        "price": 29.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_soft_deleted():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    items = [b for b in data["items"] if b["id"] == book["id"]]
    assert len(items) == 0

def test_restore_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2026,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    book = response.json()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_stock_positive_delta():
    book = create_book()
    original_stock = book["stock"]
    delta = 5
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={delta}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == original_stock + delta

def test_decrease_stock_below_zero():
    book = create_book()
    delta = - (book["stock"] + 1)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={delta}", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_cover_file_too_large():
    book = create_book()
    large_file = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
    files = {"file": ("cover.jpg", large_file, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_for_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    payload = {"rating": 5, "reviewer_name": unique("reviewer")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_delete_tag_assigned_to_book():
    tag = create_tag()
    book = create_book()
    payload = {"tag_ids": [tag["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    response = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_order_insufficient_stock():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": book["stock"] + 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_order_duplicate_book_id():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_invalid_transition():
    order = create_order()
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_pending_order():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_add_item_to_non_pending_order():
    order = create_order()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert response.status_code == 200
    book = create_book()
    payload = {"book_id": book["id"], "quantity": 1}
    response = requests.post(f"{BASE_URL}/orders/{order['id']}/items", json=payload, timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    existing_book = create_book()
    isbn1 = f"978{uuid.uuid4().hex[:9]}"
    isbn2 = existing_book["isbn"]
    isbn3 = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": isbn1,
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("book"),
                "isbn": isbn2,
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("book"),
                "isbn": isbn3,
                "price": 30.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=30)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert data["total"] == 3
    assert "created" in data
    assert "failed" in data
    assert "results" in data
    assert len(data["results"]) == 3

def test_bulk_create_books_missing_api_key():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": isbn,
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_clone_book_duplicate_isbn():
    book = create_book()
    payload = {"new_isbn": book["isbn"], "stock": 5}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_export_without_api_key():
    response = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data