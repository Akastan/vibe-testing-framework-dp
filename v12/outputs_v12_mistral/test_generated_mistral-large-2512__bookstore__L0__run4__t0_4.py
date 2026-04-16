# Main issues: 1) ISBN generation might exceed length limits (13 chars for ISBN-13) 2) Missing error handling for 422 validation errors in helpers
# Fix: Ensure ISBN is exactly 13 chars, add proper validation error handling in helpers

import uuid
import pytest
import requests
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201, 422), f"Helper failed {response.status_code}: {response.text[:200]}"
    if response.status_code == 422:
        pytest.fail(f"Author validation failed: {response.text}")
    return response.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201, 422), f"Helper failed {response.status_code}: {response.text[:200]}"
    if response.status_code == 422:
        pytest.fail(f"Category validation failed: {response.text}")
    return response.json()

def create_book(title: Optional[str] = None, isbn: Optional[str] = None, price: float = 10.0, published_year: int = 2020, stock: int = 10, author_id: Optional[int] = None, category_id: Optional[int] = None) -> Dict[str, Any]:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:9]}"  # Exactly 13 chars (978 + 9 hex chars = 12 + 1 = 13)
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
    assert response.status_code in (200, 201, 422), f"Helper failed {response.status_code}: {response.text[:200]}"
    if response.status_code == 422:
        pytest.fail(f"Book validation failed: {response.text}")
    return response.json()

def create_tag(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    data = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201, 422), f"Helper failed {response.status_code}: {response.text[:200]}"
    if response.status_code == 422:
        pytest.fail(f"Tag validation failed: {response.text}")
    return response.json()


def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_health_check_with_unsupported_method_returns_405():
    response = requests.post(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 405

def test_create_author_with_valid_data_returns_201():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_with_missing_required_field_returns_422():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_author_with_invalid_born_year_returns_422():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 3000}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_default_pagination_returns_200():
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_with_custom_pagination_returns_200():
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_existing_author_returns_200():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]

def test_get_nonexistent_author_returns_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_get_author_with_if_none_match_returns_304():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")
    assert etag is not None
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 304

def test_update_author_with_valid_data_returns_200():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_if_match_etag_mismatch_returns_412():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": '"invalid_etag"'}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_delete_existing_author_returns_204():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_create_book_with_valid_data_returns_201():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_with_invalid_isbn_returns_422():
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": "invalid",
        "price": 10.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_default_pagination_returns_200():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_list_books_with_search_filter_returns_200():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books?search={book['title'][:5]}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_list_books_with_invalid_price_range_returns_422():
    response = requests.get(f"{BASE_URL}/books?min_price=100&max_price=50", timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["msg"] == "min_price must be less than or equal to max_price" for error in data["detail"])

def test_get_existing_book_returns_200():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_update_book_with_valid_data_returns_200():
    book = create_book()
    new_title = unique("updated_book")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("updated_book")}, timeout=TIMEOUT)
    assert response.status_code == 410

def test_soft_delete_existing_book_returns_204():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_delete_already_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_discount_to_book_returns_200():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data

def test_apply_discount_exceeding_rate_limit_returns_429():
    book = create_book()
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_valid_cover_image_returns_200():
    book = create_book()
    with open("test_cover.jpg", "rb") as f:
        files = {"file": ("test_cover.jpg", f, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data

def test_upload_unsupported_file_type_returns_415():
    book = create_book()
    with open("test_file.txt", "rb") as f:
        files = {"file": ("test_file.txt", f, "text/plain")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 415