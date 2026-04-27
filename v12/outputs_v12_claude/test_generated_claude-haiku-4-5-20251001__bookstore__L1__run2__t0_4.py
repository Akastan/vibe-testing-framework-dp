import pytest
import requests
import uuid
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
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    """Helper to create a category."""
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(
    title: str = None,
    isbn: str = None,
    price: float = 29.99,
    published_year: int = 2020,
    stock: int = 10,
    author_id: int = None,
    category_id: int = None,
) -> Dict[str, Any]:
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
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_tag(name: str = None) -> Dict[str, Any]:
    """Helper to create a tag."""
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


class TestHealthCheck:
    def test_health_check_returns_200(self):
        """Verify health check endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        """Create author with name, bio, and born_year"""
        author_name = unique("author")
        payload = {
            "name": author_name,
            "bio": "A famous author",
            "born_year": 1950,
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == author_name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1950

    def test_create_author_with_only_name(self):
        """Create author with only required name field"""
        author_name = unique("author")
        payload = {"name": author_name}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == author_name

    def test_create_author_missing_name(self):
        """Attempt to create author without name returns validation error"""
        payload = {"bio": "No name author"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_default_pagination(self):
        """List authors with default skip and limit parameters"""
        create_author()
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAuthorsGetDetail:
    def test_get_author_detail_returns_etag(self):
        """Get author detail returns ETag header"""
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_etag(self):
        """Get author with matching If-None-Match returns 304 Not Modified"""
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = response1.headers.get("ETag")
        assert etag is not None
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

    def test_get_nonexistent_author(self):
        """Get nonexistent author returns 404"""
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404


class TestAuthorsPut:
    def test_update_author_with_if_match(self):
        """Update author with valid If-Match ETag header"""
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = response1.headers.get("ETag")
        
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["name"] == new_name

    def test_update_author_with_mismatched_etag(self):
        """Update author with mismatched If-Match returns 412 Precondition Failed"""
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": "wrong-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_without_books(self):
        """Delete author without associated books"""
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 404


class TestCategoriesPost:
    def test_create_category_with_name_and_description(self):
        """Create category with name and description"""
        category_name = unique("category")
        payload = {
            "name": category_name,
            "description": "A test category",
        }
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == category_name
        assert data["description"] == "A test category"

    def test_create_category_duplicate_name(self):
        """Create category with duplicate name returns 409 Conflict"""
        category_name = unique("category")
        payload1 = {"name": category_name}
        response1 = requests.post(f"{BASE_URL}/categories", json=payload1, timeout=TIMEOUT)
        assert response1.status_code == 201
        
        payload2 = {"name": category_name}
        response2 = requests.post(f"{BASE_URL}/categories", json=payload2, timeout=TIMEOUT)
        assert response2.status_code == 409


class TestCategoriesGet:
    def test_list_categories(self):
        """List all categories"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBooksPost:
    def test_create_book_with_all_required_fields(self):
        """Create book with all required fields including stock default"""
        author = create_author()
        category = create_category()
        book_title = unique("book")
        isbn = unique("isbn")[:13]
        
        payload = {
            "title": book_title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == book_title
        assert data["isbn"] == isbn
        assert data["stock"] == 5

    def test_create_book_duplicate_isbn(self):
        """Create book with duplicate ISBN returns 409 Conflict"""
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        assert response1.status_code == 201
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response2.status_code == 409

    def test_create_book_invalid_isbn_length(self):
        """Create book with ISBN outside 10-13 character range returns 422"""
        author = create_author()
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": "123",
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422


class TestBooksGet:
    def test_list_books_with_pagination(self):
        """List books with default pagination parameters"""
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_books_with_search_filter(self):
        """List books with search parameter filtering by title or ISBN"""
        book = create_book()
        response = requests.get(
            f"{BASE_URL}/books",
            params={"search": book["title"]},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_price_range_filter(self):
        """List books filtered by min_price and max_price"""
        create_book(price=50.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={"min_price": 20.0, "max_price": 100.0},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetDetail:
    def test_get_book_detail(self):
        """Get book detail with full author and category information"""
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_soft_deleted_book(self):
        """Get soft-deleted book returns 410 Gone"""
        book = create_book()
        delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert delete_response.status_code == 204
        
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 410


class TestBooksDelete:
    def test_soft_delete_book(self):
        """Delete book performs soft delete setting is_deleted flag"""
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        """Restore previously soft-deleted book"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        """Attempt to restore non-deleted book returns 400"""
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        """Apply discount to book published more than 1 year ago"""
        book = create_book(published_year=2020)
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

    def test_apply_discount_to_new_book(self):
        """Apply discount to book published within 1 year returns 400"""
        book = create_book(published_year=2026)
        payload = {"discount_percent": 25.0}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 400

    def test_apply_discount_invalid_percent(self):
        """Apply discount with percent outside (0, 50] range returns 422"""
        book = create_book(published_year=2020)
        payload = {"discount_percent": 0.0}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422


class TestBooksStock:
    def test_increase_book_stock(self):
        """Increase book stock with positive quantity parameter"""
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": 5},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_decrease_book_stock_insufficient(self):
        """Decrease stock below zero returns 400 Insufficient stock"""
        book = create_book(stock=5)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": -10},
            timeout=TIMEOUT
        )
        assert response.status_code == 400