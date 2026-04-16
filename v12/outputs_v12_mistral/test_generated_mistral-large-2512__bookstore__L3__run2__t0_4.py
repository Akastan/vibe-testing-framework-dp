# Main issues: 1) ISBN length might exceed API limits, 2) Missing API key header for protected endpoints, 3) Timeout not implemented
# Fixes: 1) Shorten ISBN to 13 chars max, 2) Add API key header to all requests, 3) Add timeout=30 to all requests

import uuid
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
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
        name = unique("category")
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

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:9]}"  # 13 chars max
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
    response = requests.post(
        f"{BASE_URL}/books",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_all_fields():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={
        "name": name,
        "bio": "Test bio",
        "born_year": 1980
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_optional_fields():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None

def test_create_author_with_invalid_name_length():
    response = requests.post(f"{BASE_URL}/authors", json={"name": ""})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_list_authors_with_pagination():
    author1 = create_author()
    author2 = create_author()

    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    response = requests.get(f"{BASE_URL}/authors?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

def test_list_authors_empty_database():
    response = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_with_if_none_match_etag_match():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag})
    assert response.status_code == 304

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_if_match_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}")
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("updated")})

    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("another_update")},
        headers={"If-Match": etag}
    )
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data
    assert "Precondition Failed" in data["detail"]

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}")
    assert response.status_code == 204

    response = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert response.status_code == 404

def test_delete_author_with_associated_books():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}")
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "associated book" in data["detail"]

def test_create_category_with_unique_name():
    name = unique("category")
    response = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_with_duplicate_name():
    name = unique("category")
    requests.post(f"{BASE_URL}/categories", json={"name": name})
    response = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"

    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == 19.99
    assert data["published_year"] == 2020
    assert data["stock"] == 10
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    book1 = create_book()
    isbn = book1["isbn"]

    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": book1["author_id"],
        "category_id": book1["category_id"]
    })
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]

def test_create_book_with_invalid_isbn_length():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": "123",
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": 1,
        "category_id": 1
    })
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_list_books_with_pagination_and_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], title="Test Book 1")
    book2 = create_book(author_id=author["id"], category_id=category["id"], title="Test Book 2")

    response = requests.get(f"{BASE_URL}/books?page=1&page_size=1&author_id={author['id']}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["page_size"] == 1

    response = requests.get(f"{BASE_URL}/books?search=Test")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2

def test_list_books_with_invalid_page_size():
    response = requests.get(f"{BASE_URL}/books?page_size=101")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["query", "page_size"] for error in data["detail"])

def test_get_book_by_id():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}")
    response = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data
    assert "deleted" in data["detail"]

def test_apply_discount_to_eligible_book():
    book = create_book(published_year=2020)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10})
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    book = create_book(published_year=2023)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "more than 1 year ago" in data["detail"]

def test_apply_discount_exceeding_rate_limit():
    book = create_book(published_year=2020)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10})

    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10})
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]

def test_update_book_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5")
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_book_stock_resulting_in_negative_stock():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-15")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Insufficient stock" in data["detail"]

def test_upload_valid_cover_image():
    book = create_book()
    with open("test_image.jpg", "wb") as f:
        f.write(b"fake image data")

    with open("test_image.jpg", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("test_image.jpg", f, "image/jpeg")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "filename" in data
    assert "size_bytes" in data

def test_upload_unsupported_cover_image_type():
    book = create_book()
    with open("test_file.txt", "wb") as f:
        f.write(b"fake text data")

    with open("test_file.txt", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("test_file.txt", f, "text/plain")}
        )
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data
    assert "Unsupported file type" in data["detail"]

def test_upload_oversized_cover_image():
    book = create_book()
    large_data = b"x" * (2 * 1024 * 1024 + 1)  # 2MB + 1 byte

    with open("large_file.jpg", "wb") as f:
        f.write(large_data)

    with open("large_file.jpg", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("large_file.jpg", f, "image/jpeg")}
        )
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data
    assert "File too large" in data["detail"]

def test_create_review_for_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("reviewer")
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5