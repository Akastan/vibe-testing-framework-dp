import uuid
import requests
import pytest
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: Optional[str] = None, isbn: Optional[str] = None, price: float = 10.0, published_year: int = 2020,
                stock: int = 10, author_id: Optional[int] = None, category_id: Optional[int] = None) -> Dict[str, Any]:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = f"123456789{uuid.uuid4().hex[:3]}"
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

def create_tag(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_review(book_id: int, rating: int = 5, comment: Optional[str] = None, reviewer_name: Optional[str] = None) -> Dict[str, Any]:
    if reviewer_name is None:
        reviewer_name = unique("reviewer")
    payload = {"rating": rating, "reviewer_name": reviewer_name}
    if comment is not None:
        payload["comment"] = comment
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name: Optional[str] = None, customer_email: Optional[str] = None, items: Optional[list] = None) -> Dict[str, Any]:
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book()
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {"customer_name": customer_name, "customer_email": customer_email, "items": items}
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
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

def test_create_author_with_invalid_name_length():
    name = "a" * 101
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

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

def test_get_existing_author():
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

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("updated_author")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch_returns_412():
    author = create_author()
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("author")}, headers={"If-Match": "invalid-etag"}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_delete_existing_author():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"123456789{uuid.uuid4().hex[:3]}"
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

def test_create_book_with_invalid_isbn_length():
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": "123",
        "price": 10.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_list_books_with_search_filter():
    book = create_book(title=unique("searchable_book"))
    response = requests.get(f"{BASE_URL}/books?search=searchable", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_list_books_with_price_range_filter():
    create_book(price=5.0)
    create_book(price=15.0)
    response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=20", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_get_existing_book():
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

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("updated_book")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_book_with_etag_mismatch_returns_412():
    book = create_book()
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("book")}, headers={"If-Match": "invalid-etag"}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_delete_already_deleted_book_returns_410():
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

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_valid_discount_to_book():
    book = create_book(price=100.0)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["discounted_price"] == 90.0

def test_apply_discount_exceeding_rate_limit_returns_429():
    book = create_book(price=100.0)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_valid_cover_image():
    book = create_book()
    with open("test_cover.jpg", "rb") as f:
        files = {"file": ("test_cover.jpg", f, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data

def test_upload_oversized_cover_image_returns_413():
    book = create_book()
    large_file = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large_cover.jpg", large_file, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413