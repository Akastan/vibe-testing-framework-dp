import uuid
import time
import requests
import pytest

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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_valid():
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

def test_get_author_existing():
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

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    assert response.text == ""
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books():
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_valid():
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

def test_get_book_existing():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

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
    assert response.text == ""
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

def test_apply_discount_old_book():
    book = create_book()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_new_book():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
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
    discount_payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_stock_valid():
    book = create_book()
    original_stock = book["stock"]
    quantity = 5
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={quantity}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == original_stock + quantity

def test_decrease_stock_below_zero():
    book = create_book()
    quantity = -999
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={quantity}", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_valid():
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
    assert data["reviewer_name"] == payload["reviewer_name"]

def test_upload_cover_valid_jpeg():
    book = create_book()
    files = {"file": ("cover.jpg", b"fake_jpeg_data", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "filename" in data
    response = requests.delete(f"{BASE_URL}/books/{book['id']}/cover", timeout=30)
    assert response.status_code == 204

def test_upload_cover_invalid_type():
    book = create_book()
    files = {"file": ("cover.txt", b"text data", "text/plain")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data

def test_create_tag_valid():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_tag_duplicate_name():
    tag = create_tag()
    payload = {"name": tag["name"]}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_add_tags_to_book():
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

def test_create_order_valid():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == payload["customer_name"]
    assert data["status"] == "pending"
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = response.json()
    assert updated_book["stock"] == book["stock"] - 1

def test_create_order_insufficient_stock():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 999}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    status_payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_confirmed_order():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]
    assert "items" in data
    assert len(data["items"]) == 1

def test_get_invoice_pending_order():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data