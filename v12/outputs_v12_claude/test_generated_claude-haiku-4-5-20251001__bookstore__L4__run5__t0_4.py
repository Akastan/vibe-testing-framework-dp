import uuid
import time
import pytest
import requests
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: str = None, bio: str = None, born_year: int = None) -> Dict[str, Any]:
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


def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id: int, category_id: int, title: str = None, isbn: str = None,
                price: float = 29.99, published_year: int = 2020, stock: int = 10) -> Dict[str, Any]:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
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


def create_tag(name: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_order(customer_name: str, customer_email: str, items: list) -> Dict[str, Any]:
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealthCheck:
    def test_health_check_returns_ok(self):
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        bio = "Test biography"
        born_year = 1980
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "bio": bio,
            "born_year": born_year,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_author_missing_name_validation_error(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "Test bio",
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_born_year_out_of_range(self):
        name = unique("author")
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "born_year": 2027,
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_returns_etag_header(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert "id" in data
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_returns_304(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author_returns_404(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_if_match_success(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        new_name = unique("updated_author")
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": new_name},
                         headers={"If-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 200
        data = r2.json()
        assert data["name"] == new_name

    def test_update_author_with_stale_etag_returns_412(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        requests.put(f"{BASE_URL}/authors/{author['id']}", 
                    json={"name": unique("changed")}, timeout=TIMEOUT)
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": unique("stale_update")},
                         headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412
        data = r2.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_associated_books_returns_409(self):
        author = create_author()
        category = create_category()
        create_book(author["id"], category["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_with_unique_name(self):
        name = unique("category")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
            "description": "Test description",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert "updated_at" in data

    def test_create_category_duplicate_name_returns_409(self):
        name = unique("category")
        requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_isbn_and_price(self):
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        price = 29.99
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": price,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["price"] == price

    def test_create_book_duplicate_isbn_returns_409(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_isbn_too_short_returns_422(self):
        author = create_author()
        category = create_category()
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": "123456789",
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_negative_price_returns_422(self):
        author = create_author()
        category = create_category()
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": -5.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_soft_deleted_book_returns_410(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted_flag(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book_success(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book_success(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                         json={"discount_percent": 25}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=50.0, published_year=2026)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                         json={"discount_percent": 10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_stock_with_positive_quantity(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=10)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": 5}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=3)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_with_valid_jpeg(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("cover.jpg", jpeg_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "book_id" in data
        assert data["book_id"] == book["id"]
        assert "content_type" in data

    def test_upload_cover_with_unsupported_type_returns_415(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("doc.txt", b"hello", "text/plain")},
                         timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_cover_exceeding_size_limit_returns_413(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        big_data = b"\xff\xd8\xff\xe0" + b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("big.jpg", big_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestTagsPost:
    def test_create_tag_with_unique_name(self):
        name = unique("tag")
        r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_tag_duplicate_name_returns_409(self):
        name = unique("tag")
        requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksTagsPost:
    def test_add_tags_to_book_idempotent(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        tag = create_tag()
        r1 = requests.post(f"{BASE_URL}/books/{book['id']}/tags",
                          json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
        assert r1.status_code == 200
        data1 = r1.json()
        assert "tags" in data1
        tag_count_1 = len(data1["tags"])
        r2 = requests.post(f"{BASE_URL}/books/{book['id']}/tags",
                          json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
        assert r2.status_code == 200
        data2 = r2.json()
        assert "tags" in data2
        tag_count_2 = len(data2["tags"])
        assert tag_count_1 == tag_count_2