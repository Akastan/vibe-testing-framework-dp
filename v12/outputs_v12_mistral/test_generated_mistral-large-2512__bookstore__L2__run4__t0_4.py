# Main issues: 1) ISBN length exceeds API validation limits (13 chars max) 2) Unique name generation might exceed field length limits
# Fix: Shorten ISBN to 13 chars and ensure unique names stay within typical DB limits (50 chars)

import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"[:50]  # Ensure total length <= 50 chars

# Helper functions
def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=None, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:9]}"  # 13 chars total
    if published_year is None:
        published_year = datetime.now(timezone.utc).year - 2
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    data = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    data = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("Customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 2}]
    data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_valid_data():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={
        "name": name,
        "bio": "Test bio",
        "born_year": 1980
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_with_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={
        "bio": "Test bio",
        "born_year": 1980
    }, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    assert data["detail"][0]["loc"] == ["body", "name"]

# Test cases for /authors/{author_id} GET
def test_get_existing_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_non_existent_author_by_id():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    etag = response.headers["ETag"]

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert response.status_code == 304

# Test cases for /authors/{author_id} PUT
def test_update_author_with_valid_data():
    author = create_author()
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
        "name": unique("UpdatedAuthor"),
        "bio": "Updated bio"
    }, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] != author["name"]
    assert data["bio"] == "Updated bio"

def test_update_author_with_etag_mismatch():
    author = create_author()
    # Get current ETag
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = response.headers["ETag"]

    # Update author to change ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={
        "name": unique("UpdatedAuthor")
    }, timeout=30)

    # Try to update with old ETag
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
        "name": unique("AnotherUpdate")
    }, headers={"If-Match": etag}, timeout=30)
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data
    assert "Precondition Failed" in data["detail"]

# Test cases for /authors/{author_id} DELETE
def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204

    # Verify author is deleted
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "associated book" in data["detail"]

# Test cases for /categories POST
def test_create_category_with_valid_data():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={
        "name": name,
        "description": "Test description"
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["description"] == "Test description"

def test_create_category_with_duplicate_name():
    name = unique("Category")
    # First creation
    response = requests.post(f"{BASE_URL}/categories", json={
        "name": name
    }, timeout=30)
    assert response.status_code == 201

    # Second creation with same name
    response = requests.post(f"{BASE_URL}/categories", json={
        "name": name
    }, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

# Test cases for /books POST
def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 24.99,
        "published_year": 2020,
        "stock": 15,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == 24.99
    assert data["stock"] == 15
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    book = create_book()
    isbn = book["isbn"]
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

def test_create_book_with_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": "123",  # Too short
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    assert "isbn" in data["detail"][0]["loc"]

# Test cases for /books/{book_id} GET
def test_get_existing_book_by_id():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert data["isbn"] == book["isbn"]

def test_get_soft_deleted_book_by_id():
    book = create_book()
    # Soft delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "deleted" in data["detail"]

# Test cases for /books/{book_id} PUT
def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={
        "title": new_title,
        "price": 29.99
    }, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title
    assert data["price"] == 29.99
    assert data["isbn"] == book["isbn"]

def test_update_soft_deleted_book():
    book = create_book()
    # Soft delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={
        "title": unique("UpdatedBook")
    }, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "deleted" in data["detail"]

# Test cases for /books/{book_id} DELETE
def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    # Verify book is soft deleted
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_delete_already_soft_deleted_book():
    book = create_book()
    # First delete
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    # Second delete
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "deleted" in data["detail"]

# Test cases for /books/{book_id}/restore POST
def test_restore_soft_deleted_book():
    book = create_book()
    # Soft delete the book
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False

    # Verify book is restored
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    restored_data = response.json()
    assert restored_data["is_deleted"] is False

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "not deleted" in data["detail"]

# Test cases for /books/{book_id}/discount POST
def test_apply_discount_to_eligible_book():
    # Create a book published more than 1 year ago
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10.0
    }, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discount_percent"] == 10.0
    assert "discounted_price" in data
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    # Create a book published this year
    published_year = datetime.now(timezone.utc).year
    book = create_book(published_year=published_year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10.0
    }, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "more than 1 year ago" in data["detail"]

def test_apply_discount_exceeding_rate_limit():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)

    # Make 5 requests (limit)
    for _ in range(5):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10.0
        }, timeout=30)
        assert response.status_code == 200

    # 6th request should fail
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10.0
    }, timeout=30)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]

# Test cases for /books/{book_id}/stock PATCH
def test_update_book_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_book_stock_resulting_in_negative():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-15", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Insufficient stock" in data["detail"]

# Test cases for /books/{book_id}/cover POST
def test_upload_valid_cover_image():
    book = create_book()
    # Create a small dummy image
    files = {'file': ('cover.jpg', b'dummy image content', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["filename"] == "cover.jpg"
    assert data["content_type"] == "image/jpeg"
    assert "size_bytes" in data

def test_upload_unsupported_cover_type():
    book = create_book()
    files = {'file': ('cover.txt', b'dummy content', 'text/plain')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data
    assert "Unsupported file type" in data["detail"]

def test_upload_oversized_cover_image():
    book = create_book()
    # Create a large dummy image (2.1MB)
    large_content = b'a' * (2 * 1024 * 1024 + 100)  # 2MB + 100 bytes
    files = {'file': ('large.jpg', large_content, 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data
    assert "File too large" in data["detail"]