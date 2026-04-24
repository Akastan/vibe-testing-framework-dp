# The main error is that ISBN must be exactly 13 characters, but the helper generates 12 characters (978 + 9 hex digits = 12). Also, some endpoints require X-API-Key header.
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
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
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        # ISBN must be exactly 13 characters: 978 + 10 digits
        # Generate 10 random digits using uuid4 hex (0-9a-f) but we need only digits 0-9
        # Use random numbers instead
        import random
        random_digits = ''.join(str(random.randint(0, 9)) for _ in range(10))
        isbn = f"978{random_digits}"
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
    headers = {"X-API-Key": "test123"}  # Add required API key header
    response = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    payload = {"name": name}
    headers = {"X-API-Key": "test123"}  # Add required API key header
    response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_valid_data():
    name = unique("Author")
    bio = "A short biography."
    born_year = 1980
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=TIMEOUT)
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
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "Updated"}, headers={"If-Match": "invalid-etag"}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    price = 25.50
    published_year = 2021
    stock = 5
    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == price
    assert data["published_year"] == published_year
    assert data["stock"] == stock
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Short ISBN",
        "isbn": "123",
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    book = create_book(author_id=author["id"], price=15.0)
    response = requests.get(f"{BASE_URL}/books", params={"author_id": author["id"], "min_price": 10.0, "max_price": 20.0, "page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5

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
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": "Test Reviewer"
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Test Reviewer"

def test_apply_discount_within_limit():
    book = create_book(price=100.0)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 10.0
    assert data["discounted_price"] == 90.0

def test_apply_discount_rate_limit_exceeded():
    book = create_book()
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5.0}, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_cover_valid_file():
    book = create_book()
    files = {"file": ("cover.jpg", b"fake_jpeg_content", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "filename" in data

def test_upload_cover_file_too_large():
    book = create_book()
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_content, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("BulkBook"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
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

def test_create_tag_valid_name():
    name = unique("Tag")
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag1["id"], tag2["id"]]}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_with_items():
    book = create_book(stock=10)
    customer_name = unique("Customer")
    customer_email = f"{customer_name}@example.com"
    response = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": [
            {"book_id": book["id"], "quantity": 2}
        ]
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == customer_name
    assert data["customer_email"] == customer_email
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    assert data["items"][0]["quantity"] == 2

def test_create_order_empty_items():
    response = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Customer",
        "customer_email": "customer@example.com",
        "items": []
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "customer@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert order.status_code in (200, 201), f"Order creation failed {order.status_code}: {order.text[:200]}"
    order_data = order.json()
    response = requests.patch(f"{BASE_URL}/orders/{order_data['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "shipped"

def test_update_order_status_invalid():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "customer@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "invalid_status"}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_start_book_export_job():
    headers = {"X-API-Key": "admin-key"}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"

def test_get_export_job_status_processing():
    headers = {"X-API-Key": "admin-key"}
    export_response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert export_response.status_code == 202
    export = export_response.json()
    response = requests.get(f"{BASE_URL}/exports/{export['job_id']}", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == export["job_id"]
    assert data["status"] == "processing"

def test_get_maintenance_status():
    response = requests.get(f"{BASE_URL}/admin/maintenance", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "maintenance_mode" in data
    assert "message" in data

def test_enable_maintenance_mode():
    headers = {"X-API-Key": "admin-key"}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] is True
    disable_response = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers=headers, timeout=TIMEOUT)
    assert disable_response.status_code == 200