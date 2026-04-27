import uuid
import requests

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
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
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Test bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_with_pagination():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_returns_200_and_etag():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert "ETag" in r.headers

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_update_author_with_valid_if_match_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = r.headers.get("ETag")
    new_name = unique("updated")
    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=30)
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == new_name

def test_update_author_with_wrong_etag_returns_412():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": '"wrong-etag"'}, timeout=30)
    assert r.status_code == 412

def test_delete_author_without_books_returns_204():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("catdup")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = uuid.uuid4().hex[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book1"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_with_filters_returns_paginated_result():
    create_book()
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_returns_200_and_etag():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "ETag" in r.headers

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book_returns_204():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_get_rating_with_reviews_returns_average():
    book = create_book()
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": "tester"}, timeout=30)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "tester2"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert data["review_count"] == 2

def test_apply_discount_to_old_book_returns_200():
    book = create_book(published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data

def test_apply_discount_to_new_book_returns_400():
    book = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_update_stock_positive_delta_returns_200():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400

def test_upload_cover_valid_image_returns_200():
    book = create_book()
    files = {"file": ("test.jpg", b"fakejpegdata", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type_returns_415():
    book = create_book()
    files = {"file": ("test.txt", b"plaintext", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_returns_200():
    book = create_book()
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag["id"] in tag_ids

def test_create_order_success():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400