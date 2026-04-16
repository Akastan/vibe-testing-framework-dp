import uuid
import pytest
import requests
from datetime import datetime, timedelta

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
        isbn = f"978{uuid.uuid4().hex[:10]}"
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

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_with_valid_data():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_create_author_with_invalid_born_year():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 3000}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "born_year"] for error in data["detail"])

def test_list_authors_with_default_pagination():
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 0

def test_list_authors_with_custom_pagination():
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_get_existing_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author_by_id():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_author_with_if_none_match_returns_304():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_if_match_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=TIMEOUT)

    # Try to update with old ETag
    new_name = unique("UpdatedAuthor")
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": new_name},
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

def test_delete_author_with_books_returns_409():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_category_with_valid_data():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_with_duplicate_name():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:10]}"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": title,
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2020,
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

def test_create_book_with_duplicate_isbn():
    book = create_book()
    new_title = unique("Book")
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": new_title,
            "isbn": book["isbn"],
            "price": 19.99,
            "published_year": 2020,
            "author_id": book["author_id"],
            "category_id": book["category_id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_invalid_published_year():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:10]}"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": title,
            "isbn": isbn,
            "price": 19.99,
            "published_year": 3000,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "published_year"] for error in data["detail"])

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"])
    book2 = create_book(author_id=author["id"])

    response = requests.get(f"{BASE_URL}/books?author_id={author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2

    response = requests.get(f"{BASE_URL}/books?category_id={category['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert any(item["id"] == book1["id"] for item in data["items"])

def test_get_existing_book_by_id():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_returns_410():
    book = create_book()
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

def test_update_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json={"title": unique("UpdatedBook")},
        timeout=TIMEOUT
    )
    assert response.status_code == 410

def test_soft_delete_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

    # Verify book is soft-deleted
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_delete_already_soft_deleted_book_returns_410():
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

    # Verify book is restored
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

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
    assert "discounted_price" in data

def test_apply_discount_to_new_book_returns_400():
    book = create_book(published_year=datetime.now().year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data