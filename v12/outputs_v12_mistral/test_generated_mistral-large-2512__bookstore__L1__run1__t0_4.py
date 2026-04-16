import uuid
import pytest
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

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
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=10.0, published_year=None, stock=0, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123456789{uuid.uuid4().hex[:4]}"
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
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200

def test_create_author_with_valid_data():
    name = unique("Author")
    data = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_with_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={"bio": "Test bio"}, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_create_author_with_invalid_born_year():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 3000}, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "born_year"] for error in data["detail"])

def test_list_authors_with_default_pagination():
    response = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 0

def test_list_authors_with_custom_pagination():
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

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

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    etag = response.headers.get("ETag")

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": new_name},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = response.headers.get("ETag")

    # First update to change the ETag
    requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("FirstUpdate")},
        timeout=30
    )

    # Second update with old ETag should fail
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("SecondUpdate")},
        headers={"If-Match": etag},
        timeout=30
    )
    assert response.status_code == 412

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

def test_create_category_with_valid_data():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test description"}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["description"] == "Test description"

def test_create_category_with_duplicate_name():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert response.status_code == 409

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

def test_create_book_with_invalid_isbn():
    author = create_author()
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": "123",  # Too short
            "price": 19.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=30
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "isbn"] for error in data["detail"])

def test_create_book_with_nonexistent_author():
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": f"123456789{uuid.uuid4().hex[:4]}",
            "price": 19.99,
            "published_year": 2020,
            "author_id": 999999,
            "category_id": category["id"]
        },
        timeout=30
    )
    assert response.status_code == 404

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book = create_book(author_id=author["id"], category_id=category["id"])

    response = requests.get(f"{BASE_URL}/books?author_id={author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["author_id"] == author["id"]

    response = requests.get(f"{BASE_URL}/books?category_id={category['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["category_id"] == category["id"]

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

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json={"title": new_title},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.put(
        f"{BASE_URL}/books/{book['id']}",
        json={"title": unique("UpdatedBook")},
        timeout=30
    )
    assert response.status_code == 410

def test_soft_delete_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

    # Verify book is soft deleted
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_delete_already_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

    # Verify book is restored
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400

def test_apply_discount_to_eligible_book():
    book = create_book(published_year=datetime.now().year - 2)
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
    book = create_book(published_year=datetime.now().year)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=30
    )
    assert response.status_code == 400