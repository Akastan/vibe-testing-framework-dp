# The main error is that ISBN must be exactly 13 digits, but the helper generates only 12 characters (9 hex digits + "978" prefix = 12). Also, some endpoints require API key headers.
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("Category")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:10]}"  # Changed from 9 to 10 to get 13 total digits
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order():
    book = create_book()
    customer_name = unique("Customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_valid_data():
    name = unique("Author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    payload = {}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
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
    payload = {"name": unique("Updated")}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 412

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
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
        "title": unique("Book"),
        "isbn": "123",
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    book = create_book()
    params = {
        "search": book["title"][:5],
        "author_id": book["author_id"],
        "min_price": 0,
        "max_price": 100
    }
    response = requests.get(f"{BASE_URL}/books", params=params, timeout=TIMEOUT)
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
    assert "title" in data

def test_get_book_soft_deleted():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

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
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]

def test_create_review_for_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    payload = {
        "rating": 3,
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 410

def test_apply_discount_within_limit():
    book = create_book()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["original_price"] == book["price"]

def test_apply_discount_rate_limit_exceeded():
    book = create_book()
    payload = {"discount_percent": 10.0}
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_book_cover_valid_file():
    book = create_book()
    files = {"file": ("cover.jpg", b"fake_jpeg_content", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert data["book_id"] == book["id"]

def test_upload_cover_file_too_large():
    book = create_book()
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_content, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_bulk_create_books_with_api_key():
    author = create_author()
    category = create_category()
    books = []
    for _ in range(2):
        books.append({
            "title": unique("BulkBook"),
            "isbn": f"978{uuid.uuid4().hex[:9]}",
            "price": 15.0,
            "published_year": 2022,
            "stock": 3,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    payload = {"books": books}
    headers = {"X-API-Key": "test-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text[:200]}"

def test_bulk_create_books_missing_api_key():
    author = create_author()
    category = create_category()
    books = [{
        "title": unique("BulkBook"),
        "isbn": f"978{uuid.uuid4().hex[:9]}",
        "price": 15.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }]
    payload = {"books": books}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401

def test_create_order_with_items():
    book = create_book()
    customer_name = unique("Customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == customer_name
    assert len(data["items"]) == 1

def test_create_order_empty_items():
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": "test@example.com",
        "items": []
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid():
    order = create_order()
    payload = {"status": "shipped"}
    headers = {"X-API-Key": "test-key"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert data["status"] == "shipped"

def test_update_order_status_invalid():
    order = create_order()
    payload = {"status": "invalid_status"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_start_book_export_job():
    headers = {"X-API-Key": "test-key"}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"

def test_get_export_job_status_processing():
    headers = {"X-API-Key": "test-key"}
    export_response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert export_response.status_code == 202, f"Expected 202, got {export_response.status_code}: {export_response.text[:200]}"
    job_id = export_response.json()["job_id"]
    response = requests.get(f"{BASE_URL}/exports/{job_id}", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text[:200]}"

def test_enable_maintenance_mode():
    headers = {"X-API-Key": "test-key"}
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert data["maintenance_mode"] is True
    disable_payload = {"enabled": False}
    disable_response = requests.post(f"{BASE_URL}/admin/maintenance", json=disable_payload, headers=headers, timeout=TIMEOUT)
    assert disable_response.status_code == 200, f"Expected 200, got {disable_response.status_code}: {disable_response.text[:200]}"