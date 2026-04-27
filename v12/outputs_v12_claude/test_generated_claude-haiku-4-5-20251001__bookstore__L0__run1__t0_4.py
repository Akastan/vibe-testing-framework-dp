# Analysis: The ISBN generation creates strings that are too long. unique("book") produces "book_" (5 chars) + 8 hex chars = 13 chars, then we prepend "978" making it 16 chars, exceeding ISBN-13's 13-char limit. Fix: generate ISBN directly as 13-char string without the "978" prefix concatenation approach.

import pytest
import requests
import uuid
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    """Generate unique string with prefix and uuid suffix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: str = None, bio: str = None, born_year: int = None) -> Dict[str, Any]:
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


def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
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


def create_book(
    title: str = None,
    isbn: str = None,
    price: float = 29.99,
    published_year: int = 2020,
    stock: int = 10,
    author_id: int = None,
    category_id: int = None
) -> Dict[str, Any]:
    """Helper to create a book."""
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
    
    response = requests.post(
        f"{BASE_URL}/books",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_tag(name: str = None) -> Dict[str, Any]:
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
        """Verify health check endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestAuthorsPost:
    def test_create_author_success(self):
        """Create a new author with valid name and optional bio"""
        author_name = unique("author")
        payload = {
            "name": author_name,
            "bio": "A famous author"
        }
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == author_name
        assert data["bio"] == "A famous author"

    def test_create_author_missing_name(self):
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

    def test_create_author_invalid_born_year(self):
        """Create author with born_year exceeding maximum of 2026"""
        author_name = unique("author")
        payload = {
            "name": author_name,
            "born_year": 2027
        }
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
    def test_get_author_success(self):
        """Retrieve a specific author by ID"""
        author = create_author()
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert data["name"] == author["name"]

    def test_get_author_not_found(self):
        """Attempt to get non-existent author returns 404"""
        response = requests.get(
            f"{BASE_URL}/authors/999999",
            timeout=TIMEOUT
        )
        assert response.status_code == 404


class TestAuthorsPut:
    def test_update_author_success(self):
        """Update author with valid data"""
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
        """Update author with incorrect ETag header fails with 412"""
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
        """Delete an author successfully"""
        author = create_author()
        response = requests.delete(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


class TestBooksPost:
    def test_create_book_success(self):
        """Create a new book with all required fields"""
        author = create_author()
        category = create_category()
        book_title = unique("book")
        isbn = f"978{uuid.uuid4().hex[:10]}"[:13]
        
        payload = {
            "title": book_title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
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
        assert data["title"] == book_title
        assert data["isbn"] == isbn

    def test_create_book_invalid_isbn_length(self):
        """Create book with ISBN shorter than 10 characters fails"""
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

    def test_create_book_negative_price(self):
        """Create book with negative price fails validation"""
        author = create_author()
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": f"978{uuid.uuid4().hex[:10]}"[:13],
            "price": -10.0,
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
        """List books with default pagination (page=1, page_size=10)"""
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
        assert "page_size" in data

    def test_list_books_with_filters(self):
        """List books with search, author_id, category_id, and price filters"""
        book = create_book()
        response = requests.get(
            f"{BASE_URL}/books",
            params={
                "search": book["title"],
                "author_id": book["author_id"],
                "category_id": book["category_id"],
                "min_price": 0,
                "max_price": 100
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_invalid_page_size(self):
        """List books with page_size exceeding maximum of 100"""
        response = requests.get(
            f"{BASE_URL}/books",
            params={"page_size": 101},
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestBooksGetById:
    def test_get_book_success(self):
        """Retrieve a specific book by ID with full details"""
        book = create_book()
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert data["title"] == book["title"]
        assert "author" in data
        assert "category" in data

    def test_get_deleted_book(self):
        """Attempt to get soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBooksPut:
    def test_update_book_success(self):
        """Update book with valid partial data"""
        book = create_book()
        new_title = unique("updated_book")
        payload = {"title": new_title}
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title

    def test_update_book_etag_mismatch(self):
        """Update book with incorrect ETag returns 412"""
        book = create_book()
        payload = {"title": unique("updated_book")}
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json=payload,
            headers={"If-Match": "invalid-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412


class TestBooksDelete:
    def test_delete_book_soft_delete(self):
        """Soft delete a book successfully"""
        book = create_book()
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204

    def test_delete_already_deleted_book(self):
        """Attempt to delete already soft-deleted book returns 410"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBooksRestore:
    def test_restore_deleted_book_success(self):
        """Restore a soft-deleted book"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        """Attempt to restore a non-deleted book returns 400"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400


class TestBooksDiscount:
    def test_apply_discount_success(self):
        """Apply valid discount (0-50%) to a book"""
        book = create_book()
        payload = {"discount_percent": 25.0}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 25.0

    def test_apply_discount_exceeds_max(self):
        """Apply discount exceeding 50% maximum fails validation"""
        book = create_book()
        payload = {"discount_percent": 75.0}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_apply_discount_rate_limit(self):
        """Exceed rate limit of 5 requests per 10 seconds"""
        book = create_book()
        payload = {"discount_percent": 10.0}

        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/books/{book['id']}/discount",
                json=payload,
                timeout=TIMEOUT
            )
            assert response.status_code == 200

        time.sleep(0.1)

        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 429


class TestBooksStock:
    def test_update_stock_success(self):
        """Update book stock quantity successfully"""
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            json={"quantity": 20},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 20


class TestBooksReviews:
    def test_create_review_success(self):
        """Create a review for a book with rating and optional comment"""
        book = create_book()
        payload = {
            "rating": 5,
            "comment": "Excellent book!",
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
        assert data["comment"] == "Excellent book!"