import time
import uuid
import pytest
import requests
from typing import Optional

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None):
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


def create_category(name: Optional[str] = None, description: Optional[str] = None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id: int, category_id: int, title: Optional[str] = None, 
                isbn: Optional[str] = None, price: float = 29.99, 
                published_year: int = 2020, stock: int = 10):
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


def create_tag(name: Optional[str] = None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_order(customer_name: str, customer_email: str, items: list):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealth:
    def test_health_check_returns_ok(self):
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author_full")
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "bio": "A famous author",
            "born_year": 1950,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1950

    def test_create_author_missing_name_validation_error(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "No name provided",
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_born_year_out_of_range(self):
        name = unique("author_bad_year")
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "born_year": 2027,
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_by_id_returns_etag(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_etag_not_modified(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author_not_found(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_name_only(self):
        author = create_author()
        new_name = unique("author_updated")
        r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": new_name,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name

    def test_update_author_with_stale_etag_precondition_failed(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        
        requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": unique("author_changed"),
        }, timeout=TIMEOUT)
        
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": unique("author_stale"),
        }, headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_with_associated_books_conflict(self):
        author = create_author()
        category = create_category()
        create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_with_name_and_description(self):
        name = unique("category_full")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
            "description": "A test category",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["description"] == "A test category"

    def test_create_category_duplicate_name_conflict(self):
        name = unique("category_dup")
        create_category(name=name)
        
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_all_required_fields(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book_title")
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": 49.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["price"] == 49.99

    def test_create_book_duplicate_isbn_conflict(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn_dup")[:13]
        
        create_book(author["id"], category["id"], isbn=isbn)
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book_dup"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_isbn_too_short_validation_error(self):
        author = create_author()
        category = create_category()
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book_short_isbn"),
            "isbn": "123456789",
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_negative_price_validation_error(self):
        author = create_author()
        category = create_category()
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book_neg_price"),
            "isbn": unique("isbn_neg")[:13],
            "price": -10.0,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_book_detail_includes_author_and_category(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "author" in data
        assert "category" in data
        assert data["author"]["id"] == author["id"]
        assert data["category"]["id"] == category["id"]

    def test_get_soft_deleted_book_gone(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_delete_book_soft_delete(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


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
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 200

    def test_restore_non_deleted_book_bad_request(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 25,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 25
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book_bad_request(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=50.0, published_year=2026)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_apply_discount_invalid_percentage_validation_error(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], published_year=2020)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 0,
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestStock:
    def test_increase_book_stock(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=10)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": 5}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero_bad_request(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=5)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestReviews:
    def test_create_review_with_rating_and_reviewer_name(self):
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
        assert data["book_id"] == book["id"]

    def test_create_review_on_soft_deleted_book_gone(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 4,
            "reviewer_name": unique("reviewer_deleted"),
        }, timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestRating:
    def test_get_book_average_rating(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 5,
            "reviewer_name": unique("reviewer1"),
        }, timeout=TIMEOUT)
        requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 3,
            "reviewer_name": unique("reviewer2"),
        }, timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "average_rating" in data
        assert "review_count" in data
        assert data["average_rating"] == 4.0
        assert data["review_count"] == 2


class TestTagsPost:
    def test_create_tag_with_unique_name(self):
        name = unique("tag_unique")
        r = requests.post(f"{BASE_URL}/tags", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name