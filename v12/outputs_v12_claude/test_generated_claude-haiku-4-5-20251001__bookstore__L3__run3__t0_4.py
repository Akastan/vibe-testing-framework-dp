import pytest
import requests
import uuid
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
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
        name = unique("cat")
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


def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("cust")
    if customer_email is None:
        customer_email = f"{unique('email')}@test.com"
    if items is None:
        book = create_book()
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealthCheck:
    def test_health_check_success(self):
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

    def test_create_author_minimal_fields(self):
        name = unique("author")
        r = requests.post(
            f"{BASE_URL}/authors",
            json={"name": name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_author_empty_name(self):
        r = requests.post(
            f"{BASE_URL}/authors",
            json={"name": ""},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_default_pagination(self):
        create_author()
        r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_list_authors_custom_pagination(self):
        create_author()
        r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


class TestAuthorsGetDetail:
    def test_get_author_detail_success(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert data["id"] == author["id"]

    def test_get_author_with_etag_not_modified(self):
        author = create_author()
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

    def test_get_author_not_found(self):
        r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_etag_match(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        new_name = unique("updated_author")
        r2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": new_name},
            headers={"If-Match": etag},
            timeout=TIMEOUT,
        )
        assert r2.status_code == 200
        data = r2.json()
        assert data["name"] == new_name

    def test_update_author_etag_mismatch(self):
        author = create_author()
        r = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("new_name")},
            headers={"If-Match": '"wrong-etag"'},
            timeout=TIMEOUT,
        )
        assert r.status_code == 412
        data = r.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 204

    def test_delete_author_with_books(self):
        author = create_author()
        category = create_category()
        create_book(author_id=author["id"], category_id=category["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesGet:
    def test_list_categories_success(self):
        create_category()
        r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


class TestBooksPost:
    def test_create_book_with_valid_data(self):
        author = create_author()
        category = create_category()
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
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        requests.post(
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
        author = create_author()
        category = create_category()
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
    def test_list_books_with_filters(self):
        book = create_book()
        r = requests.get(
            f"{BASE_URL}/books?search={book['title'][:5]}&author_id={book['author_id']}&category_id={book['category_id']}&min_price=10&max_price=50",
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_list_books_pagination(self):
        create_book()
        r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        book = create_book()
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_deleted_book_returns_gone(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        book = create_book()
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        book = create_book()
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        book = create_book(published_year=2020)
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

    def test_apply_discount_to_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_apply_discount_invalid_percent(self):
        book = create_book(published_year=2020)
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 0},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_stock_success(self):
        book = create_book(stock=10)
        r = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock?quantity=5",
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15