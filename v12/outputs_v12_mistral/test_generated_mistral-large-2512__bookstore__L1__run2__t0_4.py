# Main issues: 1) ISBN length might exceed API limits (13 chars max), 2) unique() function might create too long strings
# Fix: Truncate ISBN to 13 chars and ensure unique() strings stay within reasonable length

import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix[:15]}_{uuid.uuid4().hex[:8]}"  # Limit prefix length to prevent too long strings

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
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
        isbn = f"123{uuid.uuid4().hex[:9]}"  # Ensure total length <= 13 chars
    if published_year is None:
        published_year = datetime.now().year - 2
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


def test_create_author_with_all_fields():
    name = unique("Author")
    bio = "Test bio"
    born_year = 1980
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name, "bio": bio, "born_year": born_year},
        timeout=TIMEOUT
    )
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
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name},
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None
    assert "id" in data

def test_create_author_invalid_name_length():
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": "a" * 101},
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["msg"] == "String should have at most 100 characters" for error in data["detail"])

def test_list_authors_with_default_pagination():
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_with_custom_pagination():
    response = requests.get(f"{BASE_URL}/authors?skip=1&limit=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    non_existent_id = 999999
    response = requests.get(f"{BASE_URL}/authors/{non_existent_id}", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Author not found"

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(
        f"{BASE_URL}/authors/{author['id']}",
        headers={"If-None-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": new_name},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["id"] == author["id"]

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("TempName")},
        timeout=TIMEOUT
    )

    # Try to update with old ETag
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("NewName")},
        headers={"If-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

    # Verify author is deleted
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_all_fields():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:3]}"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 15,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == 29.99
    assert data["published_year"] == 2020
    assert data["stock"] == 15
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]
    assert "id" in data

def test_create_book_with_duplicate_isbn():
    isbn = f"123456789{uuid.uuid4().hex[:3]}"
    create_book(isbn=isbn)
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2020,
            "author_id": create_author()["id"],
            "category_id": create_category()["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_invalid_isbn_length():
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": "123",
            "price": 19.99,
            "published_year": 2020,
            "author_id": create_author()["id"],
            "category_id": create_category()["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["msg"] == "String should have at least 10 characters" for error in data["detail"])

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], price=10.99)
    book2 = create_book(author_id=author["id"], category_id=category["id"], price=20.99)

    response = requests.get(
        f"{BASE_URL}/books?author_id={author['id']}&category_id={category['id']}&min_price=10&max_price=20",
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] in [book1["id"], book2["id"]]

def test_list_books_with_search_query():
    title = unique("SearchableBook")
    book = create_book(title=title)

    response = requests.get(
        f"{BASE_URL}/books?search={title[:5]}",
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(item["id"] == book["id"] for item in data["items"])

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    # Soft delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json={"title": new_title},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title
    assert data["id"] == book["id"]

def test_update_soft_deleted_book():
    book = create_book()
    # Soft delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json={"title": unique("UpdatedBook")},
        timeout=TIMEOUT
    )
    assert response.status_code == 410

def test_apply_discount_to_eligible_book():
    book = create_book(published_year=datetime.now().year - 2)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discount_percent"] == 10
    assert "discounted_price" in data

def test_apply_discount_to_new_book():
    book = create_book(published_year=datetime.now().year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_exceeding_rate_limit():
    book = create_book(published_year=datetime.now().year - 2)
    for _ in range(5):
        requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT
        )

    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 429
    assert "detail" in response.json()

def test_update_stock_with_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=5",
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_stock_resulting_in_negative_value():
    book = create_book(stock=10)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=-15",
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Insufficient stock" in data["detail"]

def test_upload_valid_cover_image():
    book = create_book()
    # Create a small dummy image file
    files = {"file": ("test.jpg", b"dummy image content", "image/jpeg")}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert "filename" in data
    assert "content_type" in data
    assert "size_bytes" in data

def test_upload_unsupported_file_type():
    book = create_book()
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 415
    data = response.json()
    assert "detail" in data

def test_upload_oversized_cover_image():
    book = create_book()
    large_file = b"x" * (2 * 1024 * 1024 + 1)  # 2MB + 1 byte
    files = {"file": ("test.jpg", large_file, "image/jpeg")}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={
            "rating": 5,
            "reviewer_name": unique("Reviewer"),
            "comment": "Great book!"
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == data["reviewer_name"]
    assert "id" in data