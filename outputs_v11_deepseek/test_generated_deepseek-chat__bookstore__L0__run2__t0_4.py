import uuid
import requests
import pytest
import time

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

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

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
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("updated")},
        headers={"If-Match": "invalid-etag"},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_create_book_valid_data():
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
    book = create_book()
    response = requests.get(
        f"{BASE_URL}/books",
        params={"author_id": book["author_id"], "min_price": 0},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

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
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_soft_delete_book():
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

def test_apply_discount_within_limit():
    book = create_book(price=100.0)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 90.0

def test_apply_discount_rate_limit_exceeded():
    book = create_book()
    payload = {"discount_percent": 10.0}
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_cover_valid_file():
    book = create_book()
    files = {"file": ("cover.jpg", b"fake_jpeg_content", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data

def test_upload_cover_file_too_large():
    book = create_book()
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_content, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_create_tag_valid_name():
    name = unique("tag")
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name

def test_add_tags_to_book():
    book = create_book()
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

def test_create_order_with_items():
    book = create_book(stock=10)
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

def test_create_order_empty_items():
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": []
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    update_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=update_payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid():
    book = create_book()
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    order = order_response.json()
    update_payload = {"status": "invalid_status"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=update_payload, timeout=TIMEOUT)
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

def test_bulk_create_books_rate_limit():
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
    headers = {"X-API-Key": "testkey"}
    for _ in range(4):
        response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 429

def test_start_book_export_without_api_key():
    response = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert response.status_code == 401

def test_get_maintenance_status():
    response = requests.get(f"{BASE_URL}/admin/maintenance", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "maintenance_mode" in data
    original_mode = data["maintenance_mode"]
    if original_mode:
        toggle_response = requests.post(
            f"{BASE_URL}/admin/maintenance",
            json={"enabled": False},
            headers={"X-API-Key": "admin"},
            timeout=TIMEOUT
        )
        assert toggle_response.status_code == 200