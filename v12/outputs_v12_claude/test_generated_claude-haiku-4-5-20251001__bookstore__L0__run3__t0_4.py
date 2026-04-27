import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix):
    """Generate unique string with prefix and 8-char hex suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name=None, bio=None, born_year=None):
    """Helper to create an author."""
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(
        f"{BASE_URL}/authors",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_category(name=None, description=None):
    """Helper to create a category."""
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(
        f"{BASE_URL}/categories",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(title=None, isbn=None, price=29.99, published_year=2020, author_id=None, category_id=None, stock=10):
    """Helper to create a book."""
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
        "author_id": author_id,
        "category_id": category_id,
        "stock": stock
    }
    response = requests.post(
        f"{BASE_URL}/books",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_tag(name=None):
    """Helper to create a tag."""
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(
        f"{BASE_URL}/tags",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


class TestHealth:
    def test_health_check_success(self):
        """Verify health check endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        """Create author with name, bio, and born_year"""
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A famous author",
            "born_year": 1950
        }
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1950

    def test_create_author_missing_required_name(self):
        """Attempt to create author without required name field"""
        payload = {"bio": "A famous author"}
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_author_name_exceeds_max_length(self):
        """Create author with name exceeding 100 character limit"""
        name = "a" * 101
        payload = {"name": name}
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_default_pagination(self):
        """List authors with default skip=0 and limit=100"""
        create_author()
        response = requests.get(
            f"{BASE_URL}/authors",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_authors_custom_pagination(self):
        """List authors with custom skip and limit parameters"""
        create_author()
        response = requests.get(
            f"{BASE_URL}/authors",
            params={"skip": 0, "limit": 10},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAuthorsGetById:
    def test_get_author_by_id_success(self):
        """Retrieve author details by valid ID and verify ETag header present"""
        author = create_author()
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author["id"]

    def test_get_author_not_found(self):
        """Attempt to retrieve non-existent author"""
        response = requests.get(
            f"{BASE_URL}/authors/999999",
            timeout=TIMEOUT
        )
        assert response.status_code == 404

    def test_get_author_with_etag_not_modified(self):
        """Request author with If-None-Match header matching ETag"""
        author = create_author()
        response1 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        etag = response1.headers.get("ETag")
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304


class TestAuthorsPut:
    def test_update_author_partial_fields(self):
        """Update author with only some fields"""
        author = create_author()
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_etag_mismatch(self):
        """Update author with mismatched If-Match ETag header"""
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": "invalid-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_success(self):
        """Delete author and verify no content returned"""
        author = create_author()
        response = requests.delete(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


class TestBooksPost:
    def test_create_book_with_all_required_fields(self):
        """Create book with all required fields"""
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        payload = {
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(
            f"{BASE_URL}/books",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title

    def test_create_book_missing_required_field(self):
        """Create book without required isbn field"""
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(
            f"{BASE_URL}/books",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
        """Create book with ISBN shorter than 10 characters"""
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": "123",
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(
            f"{BASE_URL}/books",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestBooksGet:
    def test_list_books_default_pagination(self):
        """List books with default page=1 and page_size=10"""
        create_book()
        response = requests.get(
            f"{BASE_URL}/books",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_list_books_with_search_filter(self):
        """List books filtered by search query parameter"""
        book = create_book(title="Unique Book Title XYZ")
        response = requests.get(
            f"{BASE_URL}/books",
            params={"search": "Unique"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_price_range(self):
        """List books filtered by min_price and max_price"""
        create_book(price=50.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={"min_price": 10.0, "max_price": 100.0},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetById:
    def test_get_book_success(self):
        """Retrieve book details with full author and category information"""
        book = create_book()
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_deleted_book_returns_gone(self):
        """Attempt to retrieve soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBooksPut:
    def test_update_book_price_only(self):
        """Update only book price field"""
        book = create_book()
        payload = {"price": 39.99}
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 39.99

    def test_update_deleted_book_returns_gone(self):
        """Attempt to update soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        payload = {"price": 39.99}
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        """Soft delete book and verify subsequent GET returns 410"""
        book = create_book()
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204
        
        get_response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert get_response.status_code == 410


class TestBooksRestore:
    def test_restore_deleted_book_success(self):
        """Restore soft-deleted book and verify it becomes accessible"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book_error(self):
        """Attempt to restore book that is not deleted"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400


class TestBooksReviews:
    def test_create_review_with_rating_and_comment(self):
        """Create review with rating, comment, and reviewer_name"""
        book = create_book()
        payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer")
        }
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["rating"] == 5

    def test_create_review_on_deleted_book(self):
        """Attempt to create review on soft-deleted book"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer")
        }
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 410

    def test_list_book_reviews_success(self):
        """List all reviews for a book"""
        book = create_book()
        payload = {
            "rating": 4,
            "comment": "Good book",
            "reviewer_name": unique("reviewer")
        }
        requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT
        )
        
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}/reviews",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBooksDiscount:
    def test_apply_discount_valid_percentage(self):
        """Apply discount with valid percentage between 0 and 50"""
        book = create_book(price=100.0)
        payload = {"discount_percent": 10}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

    def test_apply_discount_exceeds_rate_limit(self):
        """Exceed rate limit of 5 requests per 10 seconds"""
        book = create_book(price=100.0)
        payload = {"discount_percent": 10}
        
        responses = []
        for i in range(6):
            response = requests.post(
                f"{BASE_URL}/books/{book['id']}/discount",
                json=payload,
                timeout=TIMEOUT
            )
            responses.append(response.status_code)
        
        assert 429 in responses