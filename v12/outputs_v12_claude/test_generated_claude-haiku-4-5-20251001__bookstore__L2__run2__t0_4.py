# Analysis: The ISBN generation uses unique("isbn")[:13] which creates strings like "isbn_XXXXXXXX" (12 chars), 
# then slices to [:13], resulting in valid 13-char ISBNs. However, the real issue is that unique() generates 
# "prefix_hex" format, and for ISBN we need exactly 13 numeric characters. Fix: generate proper numeric ISBN.

import pytest
import requests
import uuid
import time
from typing import Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: Optional[str] = None, bio: str = "Test bio", born_year: int = 1980):
    if name is None:
        name = unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_category(name: Optional[str] = None, description: str = "Test category"):
    if name is None:
        name = unique("category")
    payload = {"name": name, "description": description}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(
    title: Optional[str] = None,
    isbn: Optional[str] = None,
    price: float = 29.99,
    published_year: int = 2020,
    stock: int = 10,
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = str(int(uuid.uuid4().hex[:13], 16))[:13].zfill(13)
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_tag(name: Optional[str] = None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_order(
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    items: Optional[list] = None,
):
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book(stock=100)
        items = [{"book_id": book["id"], "quantity": 1}]
    
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


class TestHealthCheck:
    def test_health_check_returns_ok(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        payload = {"name": name, "bio": "Test bio", "born_year": 1980}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "Test bio"
        assert data["born_year"] == 1980

    def test_create_author_missing_name(self):
        payload = {"bio": "Test bio", "born_year": 1980}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGetDetail:
    def test_get_author_returns_etag(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert "id" in data

    def test_get_author_with_if_none_match_returns_304(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        etag = response.headers.get("ETag")
        
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT,
        )
        assert response.status_code == 304

    def test_get_nonexistent_author(self):
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_if_match(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = response.headers.get("ETag")
        
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": etag},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_with_mismatched_etag(self):
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": '"wrong-etag"'},
            timeout=TIMEOUT,
        )
        assert response.status_code == 412
        data = response.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_books(self):
        author = create_author()
        create_book(author_id=author["id"])
        
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {"name": name, "description": "Test description"}
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_duplicate_category(self):
        name = unique("category")
        payload = {"name": name, "description": "Test description"}
        requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_data(self):
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

    def test_create_book_with_invalid_isbn_length(self):
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
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_with_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        payload = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        
        payload["title"] = unique("book")
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestBooksGet:
    def test_list_books_with_pagination(self):
        create_book()
        create_book()
        
        response = requests.get(f"{BASE_URL}/books?page=1&page_size=10", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_list_books_with_search_filter(self):
        title = unique("searchable_book")
        create_book(title=title)
        
        response = requests.get(f"{BASE_URL}/books?search={title}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_list_books_with_price_range_filter(self):
        create_book(price=10.0)
        create_book(price=50.0)
        
        response = requests.get(f"{BASE_URL}/books?min_price=20&max_price=60", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetDetail:
    def test_get_book_detail(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "author" in data
        assert "category" in data
        assert "tags" in data

    def test_get_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_restore_non_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_book_stock(self):
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock?quantity=5",
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_decrease_book_stock_insufficient(self):
        book = create_book(stock=5)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock?quantity=-10",
            timeout=TIMEOUT,
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

    def test_apply_discount_to_new_book(self):
        current_year = 2026
        book = create_book(published_year=current_year)
        payload = {"discount_percent": 10}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_exceeds_rate_limit(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10}

        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/books/{book['id']}/discount",
                json=payload,
                timeout=TIMEOUT,
            )
            assert response.status_code == 200

        time.sleep(0.1)

        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT,
        )
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestBooksReviewsPost:
    def test_create_review_with_rating(self):
        book = create_book()
        payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer"),
        }
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["rating"] == 5

    def test_create_review_invalid_rating(self):
        book = create_book()
        payload = {
            "rating": 10,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer"),
        }
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT,
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestBooksReviewsGet:
    def test_list_book_reviews(self):
        book = create_book()
        payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer"),
        }
        requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT,
        )
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0