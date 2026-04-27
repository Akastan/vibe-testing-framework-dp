# Analysis: The ISBN field is being truncated to 13 chars but unique() generates longer strings.
# Fix: Use unique("isbn")[:13] to ensure ISBN is exactly 13 characters, and verify all payload fields match API schema.

import pytest
import requests
import uuid
from datetime import datetime, timezone

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
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    if author_id is None:
        author_id = create_author()["id"]
    if category_id is None:
        category_id = create_category()["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealth:
    def test_health_check_success(self):
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A famous author",
            "born_year": 1980,
        }
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1980

    def test_create_author_name_only(self):
        name = unique("author")
        payload = {"name": name}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] is None
        assert data["born_year"] is None

    def test_create_author_missing_name(self):
        payload = {"bio": "Some bio"}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_empty_name(self):
        payload = {"name": ""}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_invalid_born_year(self):
        name = unique("author")
        payload = {"name": name, "born_year": 2027}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_success(self):
        author = create_author()
        author_id = author["id"]
        r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == author_id
        assert "ETag" in r.headers

    def test_get_author_with_etag_match(self):
        author = create_author()
        author_id = author["id"]
        r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        r2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_author_not_found(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        author_id = author["id"]
        new_name = unique("updated_author")
        payload = {"name": new_name, "born_year": 1990}
        r = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["born_year"] == 1990

    def test_update_author_etag_mismatch(self):
        author = create_author()
        author_id = author["id"]
        r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        wrong_etag = '"wrong_etag"'
        payload = {"name": unique("updated")}
        r2 = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, headers={"If-Match": wrong_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        author_id = author["id"]
        r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 204
        r_check = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r_check.status_code == 404

    def test_delete_author_with_books(self):
        author = create_author()
        author_id = author["id"]
        category = create_category()
        create_book(author_id=author_id, category_id=category["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_success(self):
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
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["stock"] == 10

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        assert r1.status_code == 201
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2021,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert r2.status_code == 409
        data = r2.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": "123",
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_nonexistent_author(self):
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": 999999,
            "category_id": category["id"],
        }
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_book_success(self):
        book = create_book()
        book_id = book["id"]
        r = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book_id
        assert "author" in data
        assert "category" in data
        assert "ETag" in r.headers

    def test_get_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        r_delete = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_delete.status_code == 204
        r_get = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_get.status_code == 410


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        book = create_book()
        book_id = book["id"]
        r = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r.status_code == 204
        r_check = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_check.status_code == 410


class TestBooksRestore:
    def test_restore_deleted_book_success(self):
        book = create_book()
        book_id = book["id"]
        r_delete = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_delete.status_code == 204
        r_restore = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert r_restore.status_code == 200
        data = r_restore.json()
        assert data["id"] == book_id
        assert data.get("is_deleted") == False

    def test_restore_non_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        r = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_update_stock_increase(self):
        book = create_book(stock=10)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=5", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_update_stock_decrease(self):
        book = create_book(stock=10)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-3", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 7

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_old_book(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book_id
        assert data["discount_percent"] == 10
        assert "discounted_price" in data
        assert data["discounted_price"] < data["original_price"]

    def test_apply_discount_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        book_id = book["id"]
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_apply_discount_invalid_percent(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 0}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_success(self):
        book = create_book()
        book_id = book["id"]
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        files = {"file": ("cover.jpg", jpeg_data, "image/jpeg")}
        r = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book_id
        assert "filename" in data
        assert data["content_type"] == "image/jpeg"

    def test_upload_cover_unsupported_type(self):
        book = create_book()
        book_id = book["id"]
        files = {"file": ("cover.txt", b"not an image", "text/plain")}
        r = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data