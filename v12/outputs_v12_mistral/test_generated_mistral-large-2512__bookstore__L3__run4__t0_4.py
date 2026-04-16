# Main issues: 1) ISBN length validation failing due to uuid4().hex[:4] being too short (needs 10+ chars)
# 2) Author and category creation might exceed name length limits with long prefixes + uuid
# 3) Missing API key header for protected endpoints

import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:6]}'  # Reduced from 8 to 6 to prevent length issues

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    response = requests.post(
        f"{BASE_URL}/authors",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(
        f"{BASE_URL}/categories",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=10.0, published_year=None, stock=0, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:10]}"  # Increased from 4 to 10 chars for ISBN validation
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
    response = requests.post(
        f"{BASE_URL}/books",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_all_fields():
    name = unique("Author")
    bio = "Test bio"
    born_year = 1980
    response = requests.post(f"{BASE_URL}/authors", json={
        "name": name,
        "bio": bio,
        "born_year": born_year
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_optional_fields():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None
    assert "id" in data

def test_create_author_duplicate_name():
    name = unique("Author")
    create_author(name=name)
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

def test_create_author_empty_name():
    response = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_author_with_etag_match():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["id"] == author["id"]

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=30)

    # Try to update with old ETag
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("NewName")},
        headers={"If-Match": etag},
        timeout=30
    )
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data

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

def test_create_book_with_all_fields():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    price = 19.99
    published_year = 2020
    stock = 10

    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == price
    assert data["published_year"] == published_year
    assert data["stock"] == stock
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]
    assert "id" in data

def test_create_book_duplicate_isbn():
    book = create_book()
    isbn = book["isbn"]
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": book["author_id"],
        "category_id": book["category_id"]
    }, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": "123",
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title
    assert data["id"] == book["id"]

def test_update_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("UpdatedBook")}, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    # Verify book is soft deleted
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_eligible_book():
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    book = create_book(published_year=datetime.now(timezone.utc).year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_exceeding_rate_limit():
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)

    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data

def test_update_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_stock_resulting_in_negative():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-15", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_valid_cover_image():
    book = create_book()
    with open("test_image.jpg", "wb") as f:
        f.write(b"dummy image data")
    with open("test_image.jpg", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("test_image.jpg", f, "image/jpeg")},
            timeout=30
        )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["filename"] == "test_image.jpg"
    assert data["content_type"] == "image/jpeg"

def test_upload_unsupported_file_type():
    book = create_book()
    with open("test_file.txt", "wb") as f:
        f.write(b"dummy text data")
    with open("test_file.txt", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("test_file.txt", f, "text/plain")},
            timeout=30
        )
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data

def test_upload_file_exceeding_size_limit():
    book = create_book()
    large_data = b"x" * (2 * 1024 * 1024 + 1)
    with open("large_file.jpg", "wb") as f:
        f.write(large_data)
    with open("large_file.jpg", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("large_file.jpg", f, "image/jpeg")},
            timeout=30
        )
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("Reviewer")
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert "id" in data