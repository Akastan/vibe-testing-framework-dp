import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author():
    name = unique("author")
    data = {
        "name": name,
        "bio": "Test bio",
        "born_year": 1980
    }
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    data = {
        "name": name,
        "description": "Test description"
    }
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id=None, category_id=None):
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]

    isbn = f"978{uuid.uuid4().hex[:10]}"
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_with_valid_data():
    name = unique("author")
    data = {
        "name": name,
        "bio": "Test bio",
        "born_year": 1980
    }
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_required_field():
    data = {
        "bio": "Test bio"
    }
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_create_author_with_invalid_name_length():
    name = "a" * 101
    data = {
        "name": name
    }
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_list_authors_with_default_pagination():
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_with_custom_pagination():
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
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

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

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
    etag = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT).headers.get("ETag")

    new_name = unique("updated_author")
    data = {
        "name": new_name
    }
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json=data,
        headers={"If-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    wrong_etag = '"wrong_etag"'

    data = {
        "name": unique("updated_author")
    }
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json=data,
        headers={"If-Match": wrong_etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_delete_existing_author():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()

    isbn = f"978{uuid.uuid4().hex[:10]}"
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_with_invalid_isbn_length():
    author = create_author()
    category = create_category()

    data = {
        "title": unique("book"),
        "isbn": "123456789",
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

def test_list_books_with_search_filter():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books?search={book['title'][:5]}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert any(item["title"] == book["title"] for item in data["items"])

def test_list_books_with_price_range_filter():
    create_book()
    response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=30", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert 10 <= item["price"] <= 30

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_get_nonexistent_book():
    response = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_book_with_valid_data():
    book = create_book()
    etag = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).headers.get("ETag")

    new_title = unique("updated_book")
    data = {
        "title": new_title
    }
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json=data,
        headers={"If-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_book_with_etag_mismatch():
    book = create_book()
    wrong_etag = '"wrong_etag"'

    data = {
        "title": unique("updated_book")
    }
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json=data,
        headers={"If-Match": wrong_etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_delete_already_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_valid_discount_to_book():
    book = create_book()
    data = {
        "discount_percent": 10
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["discount_percent"] == 10
    assert "discounted_price" in data

def test_apply_discount_exceeding_rate_limit():
    book = create_book()
    data = {
        "discount_percent": 10
    }

    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)

    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_valid_cover_image():
    book = create_book()
    files = {
        "file": ("test_cover.jpg", b"fake image content", "image/jpeg")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert "filename" in data

def test_upload_oversized_cover_image():
    book = create_book()
    large_file = b"x" * (2 * 1024 * 1024 + 1)
    files = {
        "file": ("large_cover.jpg", large_file, "image/jpeg")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413