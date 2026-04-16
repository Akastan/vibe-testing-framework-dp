# Main issues: 1) ISBN generation was too long (13+ chars) causing 422 validation errors
# 2) Some helpers weren't properly handling optional fields and default values
# Fixed ISBN length to 13 chars max and improved field handling

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

def create_book(title=None, isbn=None, price=10.0, published_year=None, stock=0, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:9]}"  # Fixed to 13 chars max
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
        book = create_book(stock=10)
        items = [{"book_id": book["id"], "quantity": 1}]
    data = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_create_author_with_all_fields():
    name = unique("Author")
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name, "bio": "Test bio", "born_year": 1980},
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_optional_fields():
    name = unique("Author")
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name},
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None

def test_create_author_duplicate_name():
    name = unique("Author")
    create_author(name=name)
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": name},
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    assert "detail" in response.json()
    assert "already exists" in response.json()["detail"]

def test_create_author_invalid_name_length():
    response = requests.post(
        f"{BASE_URL}/authors",
        json={"name": "a" * 101},
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

# Test cases for /authors/{author_id} GET
def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    assert "detail" in response.json()

def test_get_author_with_etag_match():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers["ETag"]

    response = requests.get(
        f"{BASE_URL}/authors/{author['id']}",
        headers={"If-None-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 304

# Test cases for /authors/{author_id} PUT
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

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers["ETag"]

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
    assert "detail" in response.json()

# Test cases for /authors/{author_id} DELETE
def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

    # Verify author is deleted
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    assert "detail" in response.json()
    assert "books" in response.json()["detail"]

# Test cases for /books POST
def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
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
        timeout=TIMEOUT
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

def test_create_book_duplicate_isbn():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": book["isbn"],
            "price": 19.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": book["author_id"],
            "category_id": book["category_id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    assert "detail" in response.json()

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": "12345678",  # Too short
            "price": 19.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

# Test cases for /books GET
def test_list_books_with_pagination():
    # Create some books
    for _ in range(5):
        create_book()

    response = requests.get(f"{BASE_URL}/books?page=1&page_size=3", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 3
    assert "total" in data
    assert data["total"] >= 5
    assert "page" in data
    assert data["page"] == 1
    assert "page_size" in data
    assert data["page_size"] == 3
    assert "total_pages" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], price=10.0)
    book2 = create_book(author_id=author["id"], category_id=category["id"], price=20.0)

    # Filter by author_id
    response = requests.get(f"{BASE_URL}/books?author_id={author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2

    # Filter by category_id
    response = requests.get(f"{BASE_URL}/books?category_id={category['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2

    # Filter by min_price
    response = requests.get(f"{BASE_URL}/books?min_price=15", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert any(item["id"] == book2["id"] for item in data["items"])
    assert not any(item["id"] == book1["id"] for item in data["items"])

# Test cases for /books/{book_id} GET
def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    assert "detail" in response.json()

# Test cases for /books/{book_id}/discount POST
def test_apply_discount_to_eligible_book():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discount_percent"] == 10
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    published_year = datetime.now(timezone.utc).year
    book = create_book(published_year=published_year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_apply_discount_exceeding_rate_limit():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)

    # Make 5 requests (limit)
    for _ in range(5):
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT
        )
        assert response.status_code == 200

    # 6th request should fail
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 429
    assert "detail" in response.json()
    assert "rate limit" in response.json()["detail"].lower()

# Test cases for /books/{book_id}/stock PATCH
def test_update_stock_with_valid_quantity():
    book = create_book(stock=5)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=3",
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 8

def test_update_stock_resulting_in_negative():
    book = create_book(stock=5)
    response = requests.patch(
        f"{BASE_URL}/books/{book['id']}/stock?quantity=-6",
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    assert "detail" in response.json()

# Test cases for /books/{book_id}/cover POST
def test_upload_valid_cover_image():
    book = create_book()
    # Create a small JPEG file in memory
    files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["content_type"] == "image/jpeg"
    assert "size_bytes" in data

def test_upload_unsupported_file_type():
    book = create_book()
    files = {'file': ('test.txt', b'text data', 'text/plain')}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 415
    assert "detail" in response.json()

def test_upload_oversized_cover_image():
    book = create_book()
    # Create a large file (2.1MB)
    large_file = b'a' * (2 * 1024 * 1024 + 100)  # 2.1MB
    files = {'file': ('large.jpg', large_file, 'image/jpeg')}
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files=files,
        timeout=TIMEOUT
    )
    assert response.status_code == 413
    assert "detail" in response.json()

# Test cases for /books/{book_id}/reviews POST
def test_create_review_for_book():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={"rating": 5, "reviewer_name": "Test Reviewer"},
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Test Reviewer"

def test_create_review_with_invalid_rating():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={"rating": 6, "reviewer_name": "Test Reviewer"},
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "rating"] for error in data["detail"])

# Test cases for /books/{book_id}/clone POST
def test_clone_book_with_valid_data():
    book = create_book()
    new_isbn = f"987654321{uuid.uuid4().hex[:4]}"
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/clone",
        json={"new_isbn": new_isbn, "stock": 5},
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert data["isbn"] == new_isbn
    assert data["stock"] == 5
    assert data["title"] == f"{book['title']} (copy)"

def test_clone_book_with_duplicate_isbn():
    book = create_book()
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/clone",
        json={"new_isbn": book["isbn"], "stock": 5},
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    assert "detail" in response.json()