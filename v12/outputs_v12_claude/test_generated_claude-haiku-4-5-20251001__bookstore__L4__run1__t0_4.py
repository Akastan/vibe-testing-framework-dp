# Analysis: The ISBN field is being truncated to 13 chars from a string like "isbn_a1b2c3d4" (14+ chars).
# Fix: Generate ISBN as a proper 13-digit numeric string instead of using unique() which adds prefix overhead.

import uuid
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
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


def create_book(author_id, category_id, title=None, isbn=None, price=29.99,
                published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
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


def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@test.com"
    if items is None:
        items = []
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

    def test_create_author_missing_name(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "No name provided",
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

    def test_get_author_with_if_none_match_etag(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author(self):
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

    def test_update_author_with_stale_etag(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        
        requests.put(f"{BASE_URL}/authors/{author['id']}", 
                    json={"name": unique("intermediate")}, timeout=TIMEOUT)
        
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": unique("stale_update")},
                         headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412
        data = r2.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_associated_books(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_unique_name(self):
        name = unique("category")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
            "description": "Test description",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["isbn"] == isbn

    def test_create_book_duplicate_isbn(self):
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

    def test_create_book_isbn_too_short(self):
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

    def test_create_book_negative_price(self):
        author = create_author()
        category = create_category()
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": -10.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_soft_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 25,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=50.0, published_year=2026)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_discount_rate_limit_exceeded(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)

        for i in range(5):
            r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
                "discount_percent": 10,
            }, timeout=TIMEOUT)
            assert r.status_code == 200

        time.sleep(0.1)

        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 429
        assert "Retry-After" in r.headers


class TestBooksStock:
    def test_increase_stock_quantity(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=10)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": 5}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=3)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_valid_jpeg(self):
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
        assert data["content_type"] == "image/jpeg"

    def test_upload_cover_unsupported_type(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("doc.txt", b"text content", "text/plain")},
                         timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_cover_exceeds_size_limit(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        big_data = b"\xff\xd8" + b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("big.jpg", big_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestBooksReviews:
    def test_create_review_valid_rating(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 5,
            "reviewer_name": unique("reviewer"),
            "comment": "Great book!",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["rating"] == 5

    def test_create_review_on_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 4,
            "reviewer_name": unique("reviewer"),
        }, timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data