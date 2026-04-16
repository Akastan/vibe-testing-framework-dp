# Main issues: 1) ISBN generation might exceed length limits (13 chars expected), 2) missing API key header for protected endpoints
# Fix: Shorten ISBN to 13 chars, add API key header to all helpers that might need it

import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

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

def create_book(title=None, isbn=None, price=10.0, published_year=None, stock=0, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:10]}"[:13]  # Ensure 13 chars max
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
    response = requests.post(
        f"{BASE_URL}/books",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    data = {"name": name}
    response = requests.post(
        f"{BASE_URL}/tags",
        json=data,
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_all_fields():
    name = unique("author")
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name, "bio": "Test bio", "born_year": 1980},
        timeout=30
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_optional_fields():
    name = unique("author")
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name},
        timeout=30
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None

def test_create_author_invalid_name_length():
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": ""},
        timeout=30
    )
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

    response = requests.get(
        f"{BASE_URL}/authors/{author['id']}",
        headers={"If-None-Match": etag},
        timeout=30
    )
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": new_name, "bio": "Updated bio"},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["bio"] == "Updated bio"

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = response.headers.get("ETag")

    # First update to change the ETag
    requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("temp_name")},
        timeout=30
    )

    # Second update with old ETag should fail
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("new_name")},
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

def test_create_category_with_unique_name():
    name = unique("category")
    response = requests.post(
        f"{BASE_URL}/categories",
        json={"name": name, "description": "Test description"},
        timeout=30
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_with_duplicate_name():
    name = unique("category")
    requests.post(
        f"{BASE_URL}/categories",
        json={"name": name},
        timeout=30
    )
    response = requests.post(
        f"{BASE_URL}/categories",
        json={"name": name},
        timeout=30
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:10]}"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": title,
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=30
    )
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
    book = create_book()
    isbn = book["isbn"]
    author = create_author()
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=30
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("book"),
            "isbn": "123",
            "price": 19.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=30
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_list_books_with_pagination():
    create_book()
    create_book()
    create_book()

    response = requests.get(f"{BASE_URL}/books?page=1&page_size=2", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] >= 1

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], price=10.0)
    book2 = create_book(author_id=author["id"], category_id=category["id"], price=20.0)

    response = requests.get(
        f"{BASE_URL}/books?author_id={author['id']}&category_id={category['id']}&min_price=5&max_price=15",
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == book1["id"]

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_eligible_book():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discount_percent"] == 10
    assert "discounted_price" in data

def test_apply_discount_to_new_book():
    published_year = datetime.now(timezone.utc).year
    book = create_book(published_year=published_year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=30
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_exceeding_rate_limit():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)

    # First 5 requests should succeed
    for _ in range(5):
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # 6th request should fail
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=30
    )
    assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text}"
    data = response.json()
    assert "detail" in data, f"Expected 'detail' in response, got {data}"

def test_update_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=5",
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_stock_resulting_in_negative_stock():
    book = create_book(stock=10)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=-15",
        timeout=30
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_valid_cover_image():
    book = create_book()
    with open("test_image.jpg", "wb") as f:
        f.write(b"fake image data")

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
        f.write(b"fake text data")

    with open("test_file.txt", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("test_file.txt", f, "text/plain")},
            timeout=30
        )

    assert response.status_code == 415
    data = response.json()
    assert "detail" in data

def test_upload_oversized_cover_image():
    book = create_book()
    large_data = b"x" * (2 * 1024 * 1024 + 1)  # 2MB + 1 byte

    with open("large_image.jpg", "wb") as f:
        f.write(large_data)

    with open("large_image.jpg", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("large_image.jpg", f, "image/jpeg")},
            timeout=30
        )

    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={"rating": 5, "reviewer_name": unique("reviewer")},
        timeout=30
    )
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert "id" in data

def test_create_review_with_invalid_rating():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={"rating": 6, "reviewer_name": unique("reviewer")},
        timeout=30
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "rating"] for error in data["detail"])

def test_add_tags_to_book():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()

    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/tags",
        json={"tag_ids": [tag1["id"], tag2["id"]]},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 2
    tag_ids = [tag["id"] for tag in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids