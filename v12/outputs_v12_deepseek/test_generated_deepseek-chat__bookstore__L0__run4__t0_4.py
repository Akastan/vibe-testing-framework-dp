# The main error is that ISBN must be exactly 13 digits, but current helper generates only 12 characters (9 hex digits after "978"). Also, some endpoints require API key headers.
# Fixed: ISBN now uses 10 hex digits after "978" to make 13 total digits, and added API key header for protected endpoints.

import requests
import uuid
import time
import io

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author")}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    data = {"name": unique("Category")}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:10]}",  # Fixed: 10 hex digits to make total 13 digits
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": "test"}  # Added API key header for protected endpoints
    response = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(book_id):
    data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book_id, "quantity": 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_valid_data():
    data = {"name": unique("Author")}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == data["name"]

def test_create_author_missing_name():
    data = {}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    response = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert "name" in data

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_with_etag_mismatch():
    author = create_author()
    headers = {"If-Match": "invalid-etag"}
    data = {"name": unique("Updated")}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 412

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    data = {
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:9]}",
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == data["title"]

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    data = {
        "title": unique("Book"),
        "isbn": "123",
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    params = {
        "page": 1,
        "page_size": 5,
        "author_id": author["id"],
        "min_price": 10,
        "max_price": 100
    }
    response = requests.get(f"{BASE_URL}/books", params=params, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_get_book_by_id():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert "title" in data

def test_get_book_soft_deleted():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_soft_delete_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_delete_book_already_deleted():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    second_delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert second_delete_response.status_code == 410

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_create_review_for_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    data = {
        "rating": 5,
        "comment": unique("Great book"),
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]

def test_create_review_for_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    data = {
        "rating": 5,
        "comment": unique("Great book"),
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert response.status_code == 410

def test_apply_valid_discount():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    data = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["book_id"] == book["id"]

def test_apply_discount_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    data = {"discount_percent": 10.0}
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_book_cover_valid_file():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    files = {"file": ("cover.png", io.BytesIO(b"fake image data"), "image/png")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert data["book_id"] == book["id"]

def test_upload_cover_file_too_large():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    large_data = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", io.BytesIO(large_data), "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    data = {
        "books": [
            {
                "title": unique("BulkBook"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
                "price": 15.99,
                "published_year": 2022,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=data, timeout=TIMEOUT)
    assert response.status_code == 401

def test_bulk_create_books_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    data = {
        "books": [
            {
                "title": unique("BulkBook"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
                "price": 15.99,
                "published_year": 2022,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-key"}
    for _ in range(4):
        response = requests.post(f"{BASE_URL}/books/bulk", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 429

def test_create_order_with_items():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "items" in data
    assert len(data["items"]) == 1

def test_create_order_empty_items():
    data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": []
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order = create_order(book["id"])
    data = {"status": "shipped"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=data, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert data["status"] == "shipped"

def test_update_order_status_invalid_value():
    order = create_order(create_book(create_author()["id"], create_category()["id"])["id"])
    data = {"status": "invalid_status"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_start_book_export_without_api_key():
    response = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert response.status_code == 401

def test_get_export_job_not_found():
    response = requests.get(f"{BASE_URL}/exports/nonexistentjob", timeout=TIMEOUT)
    assert response.status_code == 404

def test_toggle_maintenance_without_api_key():
    data = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=data, timeout=TIMEOUT)
    assert response.status_code == 401