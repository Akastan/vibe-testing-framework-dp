import uuid
import pytest
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

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
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200

def test_create_author_with_valid_data():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_with_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={"bio": "Some bio"}, timeout=30)
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
    assert "ETag" in response.headers

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = response.headers["ETag"]

    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = response.headers["ETag"]

    # First update to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=30)

    # Second update with old ETag
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("NewName")},
        headers={"If-Match": etag},
        timeout=30
    )
    assert response.status_code == 412

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_category_with_valid_data():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_with_duplicate_name():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_delete_category_without_books():
    category = create_category()
    response = requests.delete(f"{BASE_URL}/categories/{category['id']}", timeout=30)
    assert response.status_code == 204

def test_delete_category_with_books():
    category = create_category()
    create_book(category_id=category["id"])
    response = requests.delete(f"{BASE_URL}/categories/{category['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    book = create_book()
    assert "id" in book
    assert book["stock"] == 0

def test_create_book_with_duplicate_isbn():
    isbn = f"978{uuid.uuid4().hex[:10]}"
    create_book(isbn=isbn)
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": datetime.now().year - 2,
        "author_id": create_author()["id"],
        "category_id": create_category()["id"]
    }, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_invalid_price():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:10]}",
        "price": -5.0,
        "published_year": datetime.now().year - 2,
        "author_id": create_author()["id"],
        "category_id": create_category()["id"]
    }, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "price"] for error in data["detail"])

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"])
    book2 = create_book(author_id=author["id"])

    response = requests.get(f"{BASE_URL}/books?author_id={author['id']}&category_id={category['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert any(item["id"] == book1["id"] for item in data["items"])
    assert not any(item["id"] == book2["id"] for item in data["items"])

def test_list_books_with_search_query():
    title = unique("SearchableBook")
    book = create_book(title=title)

    response = requests.get(f"{BASE_URL}/books?search={title[:5]}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(item["id"] == book["id"] for item in data["items"])

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert "ETag" in response.headers

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204

def test_delete_already_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book(published_year=datetime.now().year - 2)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    book = create_book(published_year=datetime.now().year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
