import pytest
import requests
import uuid
import time
from io import BytesIO
from PIL import Image

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    """Generate unique string with uuid4 suffix."""
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

def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
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
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    """Helper to create a tag."""
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

class TestHealthCheck:
    def test_health_check_success(self):
        """Verify health check endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

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

    def test_create_author_minimal_fields(self):
        """Create author with only required name field"""
        name = unique("author")
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_author_missing_name(self):
        """Attempt to create author without required name field"""
        payload = {}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_list_authors_default_pagination(self):
        """List authors with default skip=0 and limit=100"""
        create_author()
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_authors_custom_pagination(self):
        """List authors with custom skip and limit parameters"""
        create_author()
        response = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAuthorsDetail:
    def test_get_author_detail_success(self):
        """Retrieve author detail and verify ETag header is present"""
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author["id"]

    def test_get_author_not_found(self):
        """Attempt to retrieve non-existent author"""
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404

    def test_get_author_with_etag_not_modified(self):
        """Retrieve author with If-None-Match header matching ETag"""
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = response1.headers.get("ETag")
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

class TestAuthorsPut:
    def test_update_author_success(self):
        """Update author with valid data"""
        author = create_author()
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_with_etag_mismatch(self):
        """Update author with If-Match header containing outdated ETag"""
        author = create_author()
        payload = {"name": unique("updated")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": "wrong-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412

class TestAuthorsDelete:
    def test_delete_author_success(self):
        """Delete author without associated books"""
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        verify_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 404

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

class TestCategoriesGet:
    def test_list_categories_success(self):
        """List all categories without pagination"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestBooksPost:
    def test_create_book_with_all_fields(self):
        """Create book with all required and optional fields"""
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
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["stock"] == 10

    def test_create_book_missing_required_field(self):
        """Attempt to create book without required title field"""
        author = create_author()
        category = create_category()
        payload = {
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
        """Create book with ISBN outside 10-13 character range"""
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

class TestBooksGet:
    def test_list_books_default_pagination(self):
        """List books with default page=1 and page_size=10"""
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_books_with_search_filter(self):
        """List books filtered by search parameter in title or ISBN"""
        book = create_book(title="Python Programming")
        response = requests.get(f"{BASE_URL}/books?search=Python", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_price_range(self):
        """List books filtered by min_price and max_price"""
        create_book(price=25.00)
        response = requests.get(f"{BASE_URL}/books?min_price=20&max_price=30", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksDetail:
    def test_get_book_detail_success(self):
        """Retrieve book detail with author and category information"""
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_soft_deleted_book(self):
        """Attempt to retrieve soft-deleted book"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410

class TestBooksDelete:
    def test_soft_delete_book_success(self):
        """Soft delete book by setting is_deleted flag"""
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
        """Attempt to restore book that is not deleted"""
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400

class TestBooksStock:
    def test_update_stock_increase(self):
        """Increase book stock with positive quantity parameter"""
        book = create_book(stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_update_stock_decrease(self):
        """Decrease book stock with negative quantity parameter"""
        book = create_book(stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-3", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 7

    def test_update_stock_insufficient(self):
        """Attempt to decrease stock below zero"""
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400

class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        """Apply valid discount to book published more than 1 year ago"""
        book = create_book(published_year=2020, price=100.0)
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discounted_price"] == 90.0

    def test_apply_discount_to_new_book(self):
        """Attempt to apply discount to book published within last year"""
        book = create_book(published_year=2026, price=100.0)
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400