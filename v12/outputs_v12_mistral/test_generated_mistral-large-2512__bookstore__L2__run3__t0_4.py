# Main issues: 1) ISBN length might exceed API limits (unique() generates 8 chars + prefix could make it too long)
# 2) create_book() doesn't handle 422 validation errors properly in assertion message
# 3) Missing proper error handling for required fields in all helpers

import uuid
import time
import pytest
import requests

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
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    data = {"name": name}
    if description is not None:
        data["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text}"
    return response.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"123{uuid.uuid4().hex[:9]}"  # Shorter prefix to ensure total length is valid
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
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text}"
    return response.json()


def test_create_valid_author():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

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
    data = response.json()
    assert "detail" in data

def test_get_author_with_etag_match():
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

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = response.headers.get("ETag")

    # Update the author first to change the ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("TempName")}, timeout=TIMEOUT)

    # Try to update with old ETag
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("NewName")},
        headers={"If-Match": etag},
        timeout=TIMEOUT
    )
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_valid_category():
    name = unique("Category")
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_name():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_valid_book():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": title,
            "isbn": isbn,
            "price": 10.0,
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

def test_create_book_with_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = f"123456789{uuid.uuid4().hex[:4]}"
    create_book(isbn=isbn, author_id=author["id"], category_id=category["id"])
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": isbn,
            "price": 10.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_invalid_author_id():
    category = create_category()
    response = requests.post(
        f"{BASE_URL}/books",
        json={
            "title": unique("Book"),
            "isbn": f"123456789{uuid.uuid4().hex[:4]}",
            "price": 10.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": 999999,
            "category_id": category["id"]
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_list_books_with_pagination():
    response = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

def test_filter_books_by_author():
    author1 = create_author()
    author2 = create_author()
    create_book(author_id=author1["id"])
    create_book(author_id=author1["id"])
    create_book(author_id=author2["id"])

    response = requests.get(f"{BASE_URL}/books?author_id={author1['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2
    for item in data["items"]:
        assert item["author_id"] == author1["id"]

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("UpdatedBook")}, timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_delete_already_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False
    # Verify the book is actually restored by fetching it
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_valid_review():
    book = create_book()
    reviewer_name = unique("Reviewer")
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={
            "rating": 5,
            "reviewer_name": reviewer_name
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["reviewer_name"] == reviewer_name

def test_create_review_for_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/reviews",
        json={
            "rating": 5,
            "reviewer_name": unique("Reviewer")
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_apply_valid_discount():
    book = create_book(published_year=2020)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == book["price"] * 0.9

def test_apply_discount_to_new_book():
    book = create_book(published_year=2023)
    response = requests.post(
        f"{BASE_URL}/books/{book['id']}/discount",
        json={"discount_percent": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_exceed_discount_rate_limit():
    book = create_book(published_year=2020)
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
    data = response.json()
    assert "detail" in data

def test_update_stock_valid_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15