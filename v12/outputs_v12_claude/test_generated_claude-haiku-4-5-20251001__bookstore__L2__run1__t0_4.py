import pytest
import requests
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
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
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_category(name=None, description=None):
    """Helper to create a category."""
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(title=None, isbn=None, price=100.0, published_year=2020, stock=10, author_id=None, category_id=None):
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


class TestHealth:
    def test_health_check_returns_ok(self):
        """Health check endpoint returns 200 with ok status"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        """Create author with name, bio, and born_year"""
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A famous author",
            "born_year": 1980
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1980

    def test_create_author_with_only_name(self):
        """Create author with only required name field"""
        name = unique("author")
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] is None
        assert data["born_year"] is None

    def test_create_author_with_invalid_born_year(self):
        """Create author with born_year outside valid range (0-2026)"""
        name = unique("author")
        payload = {
            "name": name,
            "born_year": 2027
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_with_pagination(self):
        """List authors with skip and limit parameters"""
        create_author()
        create_author()
        response = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestAuthorsGetDetail:
    def test_get_author_returns_etag(self):
        """Get author detail returns ETag header"""
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_returns_304(self):
        """Get author with matching If-None-Match header returns 304"""
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

    def test_get_nonexistent_author(self):
        """Get author with invalid ID returns 404"""
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_etag_match(self):
        """Update author with matching If-Match ETag succeeds"""
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

    def test_update_author_with_etag_mismatch(self):
        """Update author with mismatched If-Match ETag returns 412"""
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": "invalid-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412
        data = response.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_no_books(self):
        """Delete author with no associated books succeeds"""
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204

    def test_delete_author_with_books_fails(self):
        """Delete author with associated books returns 409 Conflict"""
        author = create_author()
        create_book(author_id=author["id"])
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_success(self):
        """Create category with name and optional description"""
        name = unique("category")
        payload = {
            "name": name,
            "description": "A test category"
        }
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["description"] == "A test category"

    def test_create_duplicate_category_name(self):
        """Create category with duplicate name returns 409"""
        name = unique("category")
        payload1 = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload1, timeout=TIMEOUT)
        
        payload2 = {"name": name}
        response = requests.post(f"{BASE_URL}/categories", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestCategoriesGet:
    def test_list_all_categories(self):
        """List all categories without pagination"""
        create_category()
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestBooksPost:
    def test_create_book_with_all_fields(self):
        """Create book with all required fields and optional stock"""
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        
        payload = {
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 15,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["stock"] == 15

    def test_create_book_with_duplicate_isbn(self):
        """Create book with duplicate ISBN returns 409"""
        isbn = unique("isbn")[:13]
        create_book(isbn=isbn)
        
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_book_with_invalid_isbn_length(self):
        """Create book with ISBN outside 10-13 character range returns 422"""
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
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_with_nonexistent_author(self):
        """Create book with invalid author_id returns 404"""
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": 999999,
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestBooksGet:
    def test_list_books_with_pagination(self):
        """List books with page and page_size parameters"""
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
        """List books filtered by search term in title or ISBN"""
        title = unique("searchable_book")
        create_book(title=title)
        
        response = requests.get(f"{BASE_URL}/books?search={title[:5]}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_list_books_with_price_range_filter(self):
        """List books filtered by min_price and max_price"""
        create_book(price=50.0)
        create_book(price=150.0)
        
        response = requests.get(f"{BASE_URL}/books?min_price=40&max_price=160", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        """Get book detail returns full book information with author and category"""
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data
        assert "tags" in data

    def test_get_soft_deleted_book(self):
        """Get soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        """Delete book performs soft delete and sets is_deleted flag"""
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        """Restore soft-deleted book clears is_deleted flag"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 200

    def test_restore_non_deleted_book(self):
        """Restore non-deleted book returns 400 Bad Request"""
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        """Apply discount to book published more than 1 year ago"""
        book = create_book(published_year=2020)
        payload = {"discount_percent": 25}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 25
        assert data["original_price"] == book["price"]

    def test_apply_discount_to_new_book(self):
        """Apply discount to book published less than 1 year ago returns 400"""
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        payload = {"discount_percent": 25}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_with_invalid_percent(self):
        """Apply discount with percent outside (0, 50] range returns 422"""
        book = create_book(published_year=2020)
        payload = {"discount_percent": 0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data