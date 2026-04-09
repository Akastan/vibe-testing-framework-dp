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
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("tag")
    payload = {"name": name}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/orders", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
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

def test_get_author_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    book = create_book()
    author_id = book["author_id"]
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_category_duplicate_name():
    category = create_category()
    payload = {"name": category["name"], "description": "Another"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]

def test_create_book_duplicate_isbn():
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_soft_deleted_gone():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_delete_book_soft_delete_success():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", params={"author_id": book["author_id"]}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    found = any(b["id"] == book["id"] for b in data["items"])
    assert not found

def test_restore_book_success():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_apply_discount_new_book_error():
    book = create_book()
    payload = {"discount_percent": 10.0}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, headers=headers, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_rate_limit():
    book = create_book()
    payload = {"discount_percent": 10.0}
    for _ in range(5):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "Retry-After" in response.headers

def test_update_stock_insufficient_error():
    book = create_book()
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-100", timeout=30)
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

def test_create_review_success():
    book = create_book()
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_tag_success():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert "id" in data

def test_add_tags_to_book_success():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_insufficient_stock():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1000}]
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

def test_get_invoice_pending_order_forbidden():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_add_item_to_non_pending_order_forbidden():
    order = create_order()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert response.status_code == 200
    book2 = create_book()
    payload = {"book_id": book2["id"], "quantity": 1}
    response = requests.post(f"{BASE_URL}/orders/{order['id']}/items", json=payload, timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        {
            "title": unique("book"),
            "isbn": "123",
            "price": 20.0,
            "published_year": 2021,
            "stock": 3,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    payload = {"books": books}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=30)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert "created" in data
    assert "failed" in data
    assert data["failed"] > 0
    assert data["created"] > 0

def test_bulk_create_books_missing_api_key():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    payload = {"books": books}
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

def test_create_book_export_success():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=30)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"

def test_get_export_job_processing():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=30)
    assert response.status_code == 202
    job = response.json()
    response = requests.get(f"{BASE_URL}/exports/{job['job_id']}", timeout=30)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processing"

def test_toggle_maintenance_enable():
    headers = {"X-API-Key": API_KEY}
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] is True
    response = requests.get(f"{BASE_URL}/admin/maintenance", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] is True
    payload = {"enabled": False}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] is False