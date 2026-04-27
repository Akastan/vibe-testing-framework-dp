import uuid
import time
import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id, category_id, title=None, isbn=None, price=29.99, 
                published_year=2020, stock=10):
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
        r = requests.post(
            f"{BASE_URL}/authors",
            json={"name": name, "bio": bio, "born_year": born_year},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_author_missing_name_validation_error(self):
        r = requests.post(
            f"{BASE_URL}/authors",
            json={"bio": "No name provided"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_with_pagination(self):
        create_author(name=unique("author1"))
        create_author(name=unique("author2"))
        r = requests.get(
            f"{BASE_URL}/authors",
            params={"skip": 0, "limit": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestAuthorsGetById:
    def test_get_author_by_id_returns_etag(self):
        author = create_author(name=unique("author"))
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_etag_match(self):
        author = create_author(name=unique("author"))
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        
        r2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT,
        )
        assert r2.status_code == 304

    def test_get_nonexistent_author(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_partial_fields(self):
        author = create_author(name=unique("author"))
        new_name = unique("updated_author")
        r = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": new_name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["id"] == author["id"]

    def test_update_author_with_stale_etag(self):
        author = create_author(name=unique("author"))
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        
        requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("changed")},
            timeout=TIMEOUT,
        )
        
        r2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("stale_update")},
            headers={"If-Match": old_etag},
            timeout=TIMEOUT,
        )
        assert r2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_with_associated_books(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_with_unique_name(self):
        name = unique("category")
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name, "description": "Test category"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        create_category(name=name)
        
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesGet:
    def test_list_all_categories(self):
        create_category(name=unique("category1"))
        create_category(name=unique("category2"))
        
        r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestBooksPost:
    def test_create_book_with_valid_data(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        title = unique("book")
        isbn = unique("isbn")[:13]
        
        r = requests.post(
            f"{BASE_URL}/books",
            json={
                "title": title,
                "isbn": isbn,
                "price": 29.99,
                "published_year": 2020,
                "stock": 10,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn

    def test_create_book_duplicate_isbn(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        isbn = unique("isbn")[:13]
        
        create_book(author["id"], category["id"], isbn=isbn)
        
        r = requests.post(
            f"{BASE_URL}/books",
            json={
                "title": unique("book"),
                "isbn": isbn,
                "price": 29.99,
                "published_year": 2020,
                "stock": 10,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        
        r = requests.post(
            f"{BASE_URL}/books",
            json={
                "title": unique("book"),
                "isbn": "123",
                "price": 29.99,
                "published_year": 2020,
                "stock": 10,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_list_books_with_search_filter(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        title = unique("searchable_book")
        isbn = unique("isbn")[:13]
        
        create_book(author["id"], category["id"], title=title, isbn=isbn)
        
        r = requests.get(
            f"{BASE_URL}/books",
            params={"search": title},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_books_with_price_range_filter(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        
        create_book(author["id"], category["id"], price=50.0)
        create_book(author["id"], category["id"], price=100.0)
        
        r = requests.get(
            f"{BASE_URL}/books",
            params={"min_price": 40.0, "max_price": 75.0},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert all(40.0 <= item["price"] <= 75.0 for item in data["items"])


class TestBooksGetById:
    def test_get_soft_deleted_book_returns_gone(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 200

    def test_restore_non_deleted_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            price=100.0,
            published_year=2020,
        )
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 25},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 25
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            price=50.0,
            published_year=2026,
        )
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_book_stock(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            stock=5,
        )
        
        r = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            stock=3,
        )
        
        r = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": -10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_valid_png_cover(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("cover.png", png_data, "image/png")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book["id"]
        assert data["content_type"] == "image/png"

    def test_upload_unsupported_file_type(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_oversized_cover(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        big_data = b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("big.jpg", big_data, "image/jpeg")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestBooksReviews:
    def test_create_review_with_valid_rating(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json={
                "rating": 5,
                "reviewer_name": unique("reviewer"),
                "comment": "Great book!",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["rating"] == 5
        assert data["book_id"] == book["id"]