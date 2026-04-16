# Main issues: 1) ISBN generation might exceed length limits 2) Missing required fields in payloads 3) Incorrect status code checks
# Fixes: 1) Ensure ISBN length is within API limits 2) Add all required fields to payloads 3) Keep status code assertions strict

import pytest
import requests
import uuid
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name: str = None, bio: str = None, born_year: int = None) -> Dict[str, Any]:
    if name is None:
        name = unique("author")
    payload = {
        "name": name,
        "bio": bio if bio is not None else "Default bio",
        "born_year": born_year if born_year is not None else 1900
    }
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    payload = {
        "name": name,
        "description": description if description is not None else "Default description"
    }
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: str = None, isbn: str = None, price: float = 10.0,
                published_year: int = 2000, stock: int = 10,
                author_id: int = None, category_id: int = None) -> Dict[str, Any]:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:10]}"  # 13 chars max to stay within typical ISBN limits
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_health_check_with_unsupported_method_returns_405():
    response = requests.post(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 405

def test_create_author_with_valid_data():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_with_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    assert data["detail"][0]["loc"] == ["body", "name"]

def test_create_author_with_invalid_name_length():
    name = "a" * 101
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("max_length" in error["msg"] for error in data["detail"])
    assert any("name" in error["loc"] for error in data["detail"])

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
    assert data["name"] == author["name"]

def test_get_nonexistent_author_returns_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_get_author_with_if_none_match_returns_304():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")
    assert etag is not None
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_if_match_mismatch_returns_412():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")
    assert etag is not None
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("author")},
        headers={"If-Match": "invalid_etag"},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_delete_existing_author():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_create_book_with_valid_data():
    book = create_book()
    assert "id" in book
    assert "title" in book
    assert "isbn" in book

def test_create_book_with_invalid_isbn_length():
    isbn = "123456789"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 10.0,
            "published_year": 2000,
            "author_id": create_author()["id"],
            "category_id": create_category()["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "min_length" in data["detail"][0]["msg"]

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

def test_list_books_with_search_filter():
    book = create_book(title=unique("search_test_book"))
    response = requests.get(f"{BASE_URL}/books?search={book['title']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["title"] == book["title"]

def test_list_books_with_price_range_filter():
    create_book(price=5.0)
    create_book(price=15.0)
    response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=20", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert 10 <= item["price"] <= 20

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("updated_book")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_soft_deleted_book_returns_410():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("book")}, timeout=TIMEOUT)
    assert response.status_code == 410

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_delete_already_soft_deleted_book_returns_410():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_valid_discount_to_book():
    book = create_book(price=100.0)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discounted_price"] == 90.0

def test_apply_discount_exceeding_rate_limit_returns_429():
    book = create_book()
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 429

def test_bulk_create_books_with_valid_data():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("bulk_book1"),
            "isbn": f"123{uuid.uuid4().hex[:10]}",
            "price": 10.0,
            "published_year": 2000,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        {
            "title": unique("bulk_book2"),
            "isbn": f"456{uuid.uuid4().hex[:10]}",
            "price": 20.0,
            "published_year": 2001,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    response = requests.post(
        f"{BASE_URL}/books/bulk",
        json={"books": books},
        headers={"X-API-Key": "test_api_key"},
        timeout=TIMEOUT
    )
    assert response.status_code == 201

def test_bulk_create_books_exceeding_rate_limit_returns_429():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("bulk_book"),
            "isbn": f"123{uuid.uuid4().hex[:10]}",
            "price": 10.0,
            "published_year": 2000,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    for _ in range(3):
        requests.post(
            f"{BASE_URL}/books/bulk",
            json={"books": books},
            headers={"X-API-Key": "test_api_key"},
            timeout=TIMEOUT
        )
    response = requests.post(
        f"{BASE_URL}/books/bulk",
        json={"books": books},
        headers={"X-API-Key": "test_api_key"},
        timeout=TIMEOUT
    )
    assert response.status_code == 429