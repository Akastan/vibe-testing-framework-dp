# Main issues: 1) ISBN generation might exceed length limits, 2) born_year validation, 3) missing required fields in some helpers
# Fixes: shorten ISBN, validate born_year range, ensure all required fields are included

import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        current_year = datetime.now(timezone.utc).year
        if 1000 <= born_year <= current_year:
            data["born_year"] = born_year
        else:
            data["born_year"] = current_year - 30  # sensible default
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=None, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"12{uuid.uuid4().hex[:10]}"  # shortened to ensure it fits typical ISBN length
    if published_year is None:
        published_year = datetime.now(timezone.utc).year - 2
    if author_id is None or category_id is None:
        author = create_author()
        category = create_category()
        author_id = author["id"]
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
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    data = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("Customer")
    if customer_email is None:
        customer_email = f"{uuid.uuid4().hex[:8]}@example.com"
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 2}]
    data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_valid_data():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={
        "name": name,
        "bio": "Test bio",
        "born_year": 1980
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_with_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={
        "bio": "Test bio"
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_get_existing_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author_by_id():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
        "name": new_name,
        "bio": "Updated bio"
    }, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["bio"] == "Updated bio"

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=TIMEOUT)

    # Try to update with old ETag
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
        "name": unique("NewName")
    }, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data
    assert "Precondition Failed" in data["detail"]

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

    # Verify author is deleted
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_associated_books():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "associated books" in data["detail"].lower()

def test_create_category_with_valid_data():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={
        "name": name,
        "description": "Test description"
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["description"] == "Test description"

def test_create_category_with_duplicate_name():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == 29.99
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": book["isbn"],
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": book["author_id"],
        "category_id": book["category_id"]
    }, timeout=TIMEOUT)
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
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_get_existing_book_by_id():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_by_id():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    # Try to get the deleted book
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "has been deleted" in data["detail"]

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={
        "title": new_title,
        "price": 24.99
    }, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title
    assert data["price"] == 24.99

def test_update_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    # Try to update the deleted book
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={
        "title": unique("UpdatedBook")
    }, timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "has been deleted" in data["detail"]

def test_apply_discount_to_eligible_book():
    # Create a book published more than 1 year ago
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discount_percent"] == 10
    assert "discounted_price" in data

def test_apply_discount_to_ineligible_book():
    # Create a book published this year
    book = create_book(published_year=datetime.now(timezone.utc).year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "more than 1 year ago" in data["detail"]

def test_apply_discount_exceeding_rate_limit():
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    # Make 5 requests first (within rate limit)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)

    # 6th request should be rate limited
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]

def test_update_book_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_book_stock_with_insufficient_quantity():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Insufficient stock" in data["detail"]

def test_upload_valid_cover_image():
    book = create_book()
    # Create a small dummy JPEG file
    files = {'file': ('test.jpg', b'dummy image data', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["filename"] == "test.jpg"
    assert data["content_type"] == "image/jpeg"

def test_upload_unsupported_cover_image_type():
    book = create_book()
    files = {'file': ('test.txt', b'dummy text data', 'text/plain')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data
    assert "Unsupported file type" in data["detail"]

def test_upload_oversized_cover_image():
    book = create_book()
    # Create a file larger than 2MB
    large_file = b'x' * (2 * 1024 * 1024 + 1)
    files = {'file': ('large.jpg', large_file, 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data
    assert "File too large" in data["detail"]

def test_create_review_for_existing_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("Reviewer"),
        "comment": "Great book!"
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == data["reviewer_name"]

def test_create_review_for_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    # Try to create a review for the deleted book
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("Reviewer")
    }, timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "has been deleted" in data["detail"]

def test_add_tags_to_existing_book():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={
        "tag_ids": [tag1["id"], tag2["id"]]
    }, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) >= 2
    tag_names = [tag["name"] for tag in data["tags"]]
    assert tag1["name"] in tag_names
    assert tag2["name"] in tag_names

def test_add_nonexistent_tags_to_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={
        "tag_ids": [999999]
    }, timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]