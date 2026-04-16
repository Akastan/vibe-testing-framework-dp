# Main issues: 1) ISBN length exceeds API validation limits (13 chars max) 2) Unique name generation might exceed field length limits
# Fixes: 1) Truncate ISBN to 13 chars 2) Ensure unique names are properly truncated to prevent validation errors

import uuid
import time
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f'{prefix[:10]}_{uuid.uuid4().hex[:8]}'  # Limit prefix length to prevent overflow

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=None, stock=0, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:9]}"  # 13 chars total (123 + 9 hex chars)
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
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    data = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("Customer")
    if customer_email is None:
        customer_email = f"{unique('email')[:15]}@example.com"  # Limit email prefix length
    if items is None:
        book = create_book(stock=10)
        items = [{"book_id": book["id"], "quantity": 1}]
    data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_with_valid_data():
    name = unique("Author")
    bio = "Test bio"
    born_year = 1980
    data = {
        "name": name,
        "bio": bio,
        "born_year": born_year
    }
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    response_data = r.json()
    assert "id" in response_data
    assert response_data["name"] == name
    assert response_data["bio"] == bio
    assert response_data["born_year"] == born_year

def test_create_author_with_missing_required_field():
    data = {"bio": "Test bio"}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 422
    response_data = r.json()
    assert "detail" in response_data
    assert any(error["loc"] == ["body", "name"] for error in response_data["detail"])

def test_get_existing_author_by_id():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["id"] == author["id"]
    assert response_data["name"] == author["name"]

def test_get_nonexistent_author_by_id():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    response_data = r.json()
    assert "detail" in response_data
    assert "not found" in response_data["detail"]

def test_get_author_with_etag_not_modified():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    etag = r.headers.get("ETag")

    r = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    data = {"name": new_name}
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json=data, timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r.headers.get("ETag")

    new_name = unique("UpdatedAuthor")
    data = {"name": new_name}
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json=data, headers={"If-Match": '"invalid_etag"'}, timeout=TIMEOUT)
    assert r.status_code == 412
    response_data = r.json()
    assert "detail" in response_data
    assert "Precondition Failed" in response_data["detail"]

def test_delete_author_without_books():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_author_with_associated_books():
    author = create_author()
    book = create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    response_data = r.json()
    assert "detail" in response_data
    assert "associated books" in response_data["detail"].lower()

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    data = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    response_data = r.json()
    assert "id" in response_data
    assert response_data["title"] == title
    assert response_data["isbn"] == isbn
    assert response_data["author_id"] == author["id"]
    assert response_data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    book = create_book()
    author = create_author()
    category = create_category()
    data = {
        "title": unique("Book"),
        "isbn": book["isbn"],
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409
    response_data = r.json()
    assert "detail" in response_data
    assert "already exists" in response_data["detail"]

def test_get_existing_book_by_id():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["id"] == book["id"]
    assert response_data["title"] == book["title"]

def test_get_soft_deleted_book_by_id():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    response_data = r.json()
    assert "detail" in response_data
    assert "deleted" in response_data["detail"]

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    data = {"title": new_title}
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json=data, timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["title"] == new_title

def test_soft_delete_existing_book():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["id"] == book["id"]
    assert response_data["is_deleted"] is False

def test_restore_non_deleted_book():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    response_data = r.json()
    assert "detail" in response_data
    assert "not deleted" in response_data["detail"]

def test_apply_discount_to_eligible_book():
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    data = {"discount_percent": 10.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert "discounted_price" in response_data
    assert response_data["discount_percent"] == 10.0
    assert response_data["discounted_price"] < book["price"]

def test_apply_discount_to_ineligible_book():
    book = create_book(published_year=datetime.now(timezone.utc).year)
    data = {"discount_percent": 10.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert r.status_code == 400
    response_data = r.json()
    assert "detail" in response_data
    assert "more than 1 year ago" in response_data["detail"]

def test_apply_discount_exceeding_rate_limit():
    book = create_book(published_year=datetime.now(timezone.utc).year - 2)
    data = {"discount_percent": 10.0}

    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
        assert r.status_code == 200

    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert r.status_code == 429
    response_data = r.json()
    assert "detail" in response_data
    assert "Rate limit exceeded" in response_data["detail"]

def test_update_book_stock_with_valid_quantity():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["stock"] == 15

def test_update_book_stock_to_negative_value():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-15", timeout=TIMEOUT)
    assert r.status_code == 400
    response_data = r.json()
    assert "detail" in response_data
    assert "Insufficient stock" in response_data["detail"]

def test_upload_valid_cover_image():
    book = create_book()
    files = {'file': ('cover.jpg', b'test image data', 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert "filename" in response_data
    assert response_data["book_id"] == book["id"]

def test_upload_unsupported_cover_image_type():
    book = create_book()
    files = {'file': ('cover.txt', b'test data', 'text/plain')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    response_data = r.json()
    assert "detail" in response_data
    assert "Unsupported file type" in response_data["detail"]

def test_upload_oversized_cover_image():
    book = create_book()
    large_data = b'a' * (2 * 1024 * 1024 + 1)
    files = {'file': ('cover.jpg', large_data, 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413
    response_data = r.json()
    assert "detail" in response_data
    assert "File too large" in response_data["detail"]

def test_create_review_for_existing_book():
    book = create_book()
    data = {
        "rating": 5,
        "reviewer_name": unique("Reviewer"),
        "comment": "Great book!"
    }
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    response_data = r.json()
    assert "id" in response_data
    assert response_data["book_id"] == book["id"]
    assert response_data["rating"] == 5

def test_create_review_for_soft_deleted_book():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    data = {
        "rating": 5,
        "reviewer_name": unique("Reviewer"),
        "comment": "Great book!"
    }
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 410
    response_data = r.json()
    assert "detail" in response_data
    assert "deleted" in response_data["detail"]

def test_get_rating_for_book_with_reviews():
    book = create_book()
    data = {
        "rating": 5,
        "reviewer_name": unique("Reviewer")
    }
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    response_data = r.json()
    assert "average_rating" in response_data
    assert response_data["average_rating"] == 5.0
    assert response_data["review_count"] == 1

def test_bulk_create_books_with_valid_data():
    author = create_author()
    category = create_category()
    books_data = {
        "books": [
            {
                "title": unique("Book1"),
                "isbn": f"123456789{uuid.uuid4().hex[:4]}",
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book2"),
                "isbn": f"987654321{uuid.uuid4().hex[:4]}",
                "price": 15.0,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-api-key"}
    r = requests.post(f"{BASE_URL}/books/bulk", json=books_data, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 201
    response_data = r.json()
    assert "created" in response_data
    assert response_data["created"] == 2
    assert response_data["failed"] == 0

def test_bulk_create_books_exceeding_rate_limit():
    author = create_author()
    category = create_category()
    books_data = {
        "books": [
            {
                "title": unique("Book1"),
                "isbn": f"123456789{uuid.uuid4().hex[:4]}",
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-api-key"}

    for _ in range(3):
        r = requests.post(f"{BASE_URL}/books/bulk", json=books_data, headers=headers, timeout=TIMEOUT)
        assert r.status_code == 201

    r = requests.post(f"{BASE_URL}/books/bulk", json=books_data, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 429
    response_data = r.json()
    assert "detail" in response_data
    assert "Rate limit exceeded" in response_data["detail"]