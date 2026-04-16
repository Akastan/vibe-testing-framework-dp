# Main issues: 1) create_book helper uses nested author/category objects instead of IDs 2) ISBN generation might exceed length limits 3) Missing error handling for 422 validation errors
# Fixes: 1) Use direct author_id/category_id in book creation 2) Ensure ISBN length is correct 3) Add proper error assertions

import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    name = name or unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201, 422), f"Helper failed {r.status_code}: {r.text[:200]}"
    if r.status_code == 422:
        pytest.fail(f"Author creation validation failed: {r.text}")
    return r.json()

def create_category(name=None, description=None):
    name = name or unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201, 422), f"Helper failed {r.status_code}: {r.text[:200]}"
    if r.status_code == 422:
        pytest.fail(f"Category creation validation failed: {r.text}")
    return r.json()

def create_book(title=None, isbn=None, price=19.99, published_year=None, stock=10, author_id=None, category_id=None):
    title = title or unique("Book")
    isbn = isbn or f"978{uuid.uuid4().hex[:10]}"
    published_year = published_year or datetime.now(timezone.utc).year - 2

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
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201, 422), f"Helper failed {r.status_code}: {r.text[:200]}"
    if r.status_code == 422:
        pytest.fail(f"Book creation validation failed: {r.text}")
    return r.json()

def create_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201, 422), f"Helper failed {r.status_code}: {r.text[:200]}"
    if r.status_code == 422:
        pytest.fail(f"Tag creation validation failed: {r.text}")
    return r.json()


def test_create_author_with_all_fields():
    name = unique("Author")
    bio = "Test bio"
    born_year = 1980
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name,
        "bio": bio,
        "born_year": born_year
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_with_minimal_fields():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] is None
    assert data["born_year"] is None

def test_create_author_with_duplicate_name():
    name = unique("Author")
    r1 = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r1.status_code == 201

    r2 = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r2.status_code == 409
    assert "detail" in r2.json()

def test_create_author_with_empty_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_get_existing_author():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_with_etag_match():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r1.status_code == 200
    etag = r1.headers["ETag"]

    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r1.status_code == 200
    etag = r1.headers["ETag"]

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=TIMEOUT)

    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("NewName")}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 412
    assert "detail" in r2.json()

def test_delete_author_without_books():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    # Verify author is deleted
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_with_all_fields():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:10]}"
    price = 24.99
    published_year = 2020
    stock = 5

    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == price
    assert data["published_year"] == published_year
    assert data["stock"] == stock
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    book1 = create_book()
    book2 = create_book(isbn=book1["isbn"])
    assert book2.status_code == 409
    assert "detail" in book2.json()

def test_create_book_with_invalid_author():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:10]}",
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_with_pagination():
    # Create some books
    for _ in range(5):
        create_book()

    r = requests.get(f"{BASE_URL}/books?page=1&page_size=3", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) == 3
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], price=10.0)
    book2 = create_book(author_id=author["id"], category_id=category["id"], price=20.0)

    # Filter by author
    r = requests.get(f"{BASE_URL}/books?author_id={author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) >= 2

    # Filter by category
    r = requests.get(f"{BASE_URL}/books?category_id={category['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) >= 2

    # Filter by price range
    r = requests.get(f"{BASE_URL}/books?min_price=15&max_price=25", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) >= 1

def test_get_existing_book():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == new_title

def test_update_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("UpdatedBook")}, timeout=TIMEOUT)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_restore_soft_deleted_book():
    book = create_book()
    # Delete the book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False

def test_restore_non_deleted_book():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_to_eligible_book():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    published_year = datetime.now(timezone.utc).year
    book = create_book(published_year=published_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_exceeding_rate_limit():
    published_year = datetime.now(timezone.utc).year - 2
    book = create_book(published_year=published_year)

    # Make 5 requests (the limit)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
        assert r.status_code == 200

    # 6th request should fail
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429
    assert "detail" in r.json()

def test_update_stock_with_valid_quantity():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_with_insufficient_quantity():
    book = create_book(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_valid_cover_image():
    book = create_book()
    # Create a small dummy image
    files = {'file': ('test.jpg', b'dummy image data', 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["filename"] == "test.jpg"
    assert data["content_type"] == "image/jpeg"

def test_upload_unsupported_file_type():
    book = create_book()
    files = {'file': ('test.txt', b'dummy data', 'text/plain')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_upload_oversized_file():
    book = create_book()
    large_file = b'a' * (2 * 1024 * 1024 + 1)  # 2MB + 1 byte
    files = {'file': ('large.jpg', large_file, 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413
    assert "detail" in r.json()