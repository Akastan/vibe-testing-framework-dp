import pytest
import requests
import uuid
import time
import json
import io

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

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def get_etag(url):
    response = requests.get(url, timeout=TIMEOUT)
    return response.headers.get("ETag")

def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_valid_data():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_author_name_too_long():
    long_name = "a" * 101
    response = requests.post(f"{BASE_URL}/authors", json={"name": long_name}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_with_custom_limit():
    for _ in range(5):
        create_author()
    response = requests.get(f"{BASE_URL}/authors", params={"limit": 2, "skip": 1}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 2

def test_get_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_with_etag():
    author = create_author()
    url = f"{BASE_URL}/authors/{author['id']}"
    etag = get_etag(url)
    new_name = unique("updated_author")
    headers = {"If-Match": etag}
    response = requests.put(url, json={"name": new_name}, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = str(uuid.uuid4().int)[:13]
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

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": "123",
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.get(f"{BASE_URL}/books", params={"author_id": author["id"], "min_price": 0, "max_price": 100}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_list_books_invalid_page_size():
    response = requests.get(f"{BASE_URL}/books", params={"page_size": 150}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_book_by_id():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_book_soft_deleted():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_delete_book_soft_delete():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_delete_book_already_deleted():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    second_delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert second_delete_response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_create_review_for_book():
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

def test_create_review_rating_out_of_range():
    book = create_book()
    payload = {
        "rating": 10,
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_apply_valid_discount():
    book = create_book(price=100.0)
    payload = {"discount_percent": 20.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 20.0
    assert data["discounted_price"] == 80.0

def test_apply_discount_rate_limit_exceeded():
    book = create_book()
    payload = {"discount_percent": 10.0}
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_valid_cover_image():
    book = create_book()
    file_content = b"fake_image_data"
    files = {"file": ("cover.png", io.BytesIO(file_content), "image/png")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert data["book_id"] == book["id"]

def test_upload_cover_file_too_large():
    book = create_book()
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", io.BytesIO(large_content), "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_update_tag_etag_mismatch():
    tag = create_tag()
    url = f"{BASE_URL}/tags/{tag['id']}"
    headers = {"If-Match": "invalid-etag"}
    response = requests.put(url, json={"name": unique("updated_tag")}, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 412

def test_create_order_with_items():
    book = create_book(stock=20)
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
    assert data["customer_name"] == payload["customer_name"]
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    assert data["items"][0]["quantity"] == 2

def test_update_order_status_valid():
    book = create_book(stock=20)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid():
    book = create_book(stock=20)
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    status_payload = {"status": "invalid_status"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("bulkbook"),
                "isbn": str(uuid.uuid4().int)[:13],
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401

def test_bulk_create_books_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("bulkbook"),
                "isbn": str(uuid.uuid4().int)[:13],
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-key"}
    for _ in range(4):
        response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 429