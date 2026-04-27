import uuid
import requests
import time
import json
from io import BytesIO

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
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
        "category_id": category_id,
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_create_author_with_all_fields():
    name = unique("author")
    bio = "A famous author"
    born_year = 1950
    payload = {"name": name, "bio": bio, "born_year": born_year}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_minimal_fields():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    payload = {"bio": "Some bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_author_name_too_long():
    name = "a" * 101
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_custom_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_author_detail_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert "ETag" in response.headers
    data = response.json()
    assert data["id"] == author["id"]

def test_get_author_with_etag_match():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")
    response2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response2.status_code == 304

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_success():
    author = create_author()
    new_name = unique("updated_author")
    payload = {"name": new_name}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_etag_mismatch():
    author = create_author()
    payload = {"name": unique("updated_author")}
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}", json=payload, headers={"If-Match": "wrong-etag"}, timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_list_author_books_with_pagination():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.get(f"{BASE_URL}/authors/{author['id']}/books?page=1&page_size=10", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_create_category_success():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_duplicate_name():
    name = unique("category")
    payload = {"name": name}
    requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409

def test_list_categories_success():
    create_category()
    response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"],
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": "123",
        "price": 29.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"],
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    payload["title"] = unique("book")
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409

def test_create_book_nonexistent_author():
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 29.99,
        "published_year": 2020,
        "author_id": 99999,
        "category_id": category["id"],
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 404

def test_list_books_default_pagination():
    create_book()
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_list_books_with_search_filter():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books?search={book['title'][:5]}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_list_books_with_price_range():
    create_book(price=50.0)
    response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=100", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_get_book_detail_success():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_update_stock_positive_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_stock_negative_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-3", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 7

def test_update_stock_insufficient_inventory():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020, price=100.0)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discount_percent"] == 10.0

def test_apply_discount_to_new_book():
    current_year = 2026
    book = create_book(published_year=current_year, price=100.0)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

