import uuid
import requests
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id):
    title = unique("book")
    isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
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

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200

def test_create_author_success():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_422():
    payload = {}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_by_id_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books_204():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
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
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book_204():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_delete_already_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_restore_soft_deleted_book_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_restore_not_deleted_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {"discount_percent": 10.0}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book_400():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 20.0,
        "published_year": 2026,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    book = response.json()
    discount_payload = {"discount_percent": 5.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_stock_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    initial_stock = book["stock"]
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == initial_stock + 5

def test_decrease_stock_below_zero_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-999", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_valid_cover_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    files = {"file": ("cover.png", b"fake_png_content", "image/png")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]

def test_upload_cover_file_too_large_413():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_content, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
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

def test_create_review_for_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    payload = {
        "rating": 3,
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_create_tag_success():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_tag_duplicate_name_409():
    tag = create_tag()
    payload = {"name": tag["name"]}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_order_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["total_price"] == book["price"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = response.json()
    assert updated_book["stock"] == book["stock"] - 1

def test_create_order_insufficient_stock_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 999}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert response.status_code == 201
    order = response.json()
    status_payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order_200():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
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