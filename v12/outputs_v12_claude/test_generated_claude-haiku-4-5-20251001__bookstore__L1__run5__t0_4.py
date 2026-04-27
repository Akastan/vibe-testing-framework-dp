import pytest
import requests
import uuid
import json
from io import BytesIO

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    """Generate unique string with prefix and 8-char UUID suffix."""
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
    response = requests.post(
        f"{BASE_URL}/books",
        json=payload,
        timeout=TIMEOUT
    )
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    """Helper to create an order."""
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book(stock=100)
        items = [{"book_id": book["id"], "quantity": 2}]
    
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(
        f"{BASE_URL}/orders",
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
        """Verify health check endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200

class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        """Create author with name, bio, and born_year"""
        author_name = unique("author")
        payload = {
            "name": author_name,
            "bio": "A famous author",
            "born_year": 1980
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
        assert data["born_year"] == 1980

    def test_create_author_minimal_fields(self):
        """Create author with only required name field"""
        author_name = unique("author")
        payload = {"name": author_name}
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == author_name

    def test_create_author_missing_name(self):
        """Attempt to create author without name returns validation error"""
        payload = {"bio": "A famous author"}
        response = requests.post(
            f"{BASE_URL}/authors",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_author_name_too_long(self):
        """Author name exceeding 100 characters returns validation error"""
        long_name = "a" * 101
        payload = {"name": long_name}
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
        """List authors with default skip and limit parameters"""
        create_author()
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_authors_custom_pagination(self):
        """List authors with custom skip and limit values"""
        create_author()
        response = requests.get(
            f"{BASE_URL}/authors?skip=0&limit=5",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAuthorsGetDetail:
    def test_get_author_detail_success(self):
        """Retrieve author detail and verify ETag header is present"""
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
        """Attempt to get non-existent author returns 404"""
        response = requests.get(
            f"{BASE_URL}/authors/99999",
            timeout=TIMEOUT
        )
        assert response.status_code == 404

    def test_get_author_with_etag_match(self):
        """Conditional GET with matching ETag returns 304 Not Modified"""
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
    def test_update_author_success(self):
        """Update author with new name and bio"""
        author = create_author()
        new_name = unique("updated_author")
        payload = {
            "name": new_name,
            "bio": "Updated bio"
        }
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["bio"] == "Updated bio"

    def test_update_author_etag_mismatch(self):
        """PUT with incorrect If-Match ETag returns 412 Precondition Failed"""
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
    def test_delete_author_success(self):
        """Delete author without assigned books returns 204"""
        author = create_author()
        response = requests.delete(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204
        verify_response = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert verify_response.status_code == 404

class TestCategoriesPost:
    def test_create_category_success(self):
        """Create category with name and optional description"""
        category_name = unique("category")
        payload = {
            "name": category_name,
            "description": "A test category"
        }
        response = requests.post(
            f"{BASE_URL}/categories",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == category_name
        assert data["description"] == "A test category"

    def test_create_category_duplicate_name(self):
        """Attempt to create category with duplicate name returns 409 Conflict"""
        category_name = unique("category")
        create_category(name=category_name)
        payload = {"name": category_name}
        response = requests.post(
            f"{BASE_URL}/categories",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 409

class TestCategoriesGet:
    def test_list_categories_success(self):
        """List all categories without pagination"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestBooksPost:
    def test_create_book_success(self):
        """Create book with all required fields and valid author and category"""
        author = create_author()
        category = create_category()
        book_title = unique("book")
        isbn = unique("isbn")[:13]
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
        """ISBN outside 10-13 character range returns validation error"""
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

    def test_create_book_duplicate_isbn(self):
        """Attempt to create book with duplicate ISBN returns 409 Conflict"""
        book = create_book()
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": book["isbn"],
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
        assert response.status_code == 409

    def test_create_book_nonexistent_author(self):
        """Create book with non-existent author_id returns 404"""
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": 99999,
            "category_id": category["id"]
        }
        response = requests.post(
            f"{BASE_URL}/books",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 404

class TestBooksGet:
    def test_list_books_default_pagination(self):
        """List books with default page and page_size"""
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_books_with_search_filter(self):
        """List books filtered by search term in title or ISBN"""
        book = create_book(title="Python Programming")
        response = requests.get(
            f"{BASE_URL}/books?search=Python",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_price_range(self):
        """List books filtered by min_price and max_price"""
        create_book(price=50.0)
        response = requests.get(
            f"{BASE_URL}/books?min_price=10&max_price=100",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        """Retrieve book detail with author and category information"""
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
        """Attempt to get soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410

class TestBooksDelete:
    def test_soft_delete_book_success(self):
        """Soft delete book sets is_deleted flag without physical removal"""
        book = create_book()
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204
        verify_response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert verify_response.status_code == 410

class TestBooksRestore:
    def test_restore_deleted_book_success(self):
        """Restore soft-deleted book returns it to active state"""
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
        """Attempt to restore non-deleted book returns 400 Bad Request"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400

class TestBooksStock:
    def test_update_stock_increase(self):
        """Increase book stock with positive quantity delta"""
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock?quantity=5",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_update_stock_insufficient(self):
        """Attempt to reduce stock below zero returns 400 Bad Request"""
        book = create_book(stock=5)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock?quantity=-10",
            timeout=TIMEOUT
        )
        assert response.status_code == 400

class TestBooksDiscount:
    pass

    pass

class TestBooksReviews:
    pass

    pass

    pass

class TestBooksCover:
    pass

    pass

    pass

class TestTags:
    pass

    pass

    pass

    pass

    pass

class TestBookTags:
    pass

    pass

class TestOrders:
    pass

    pass

    pass

    pass

    pass

    pass

    pass

    pass

class TestBulkBooks:
    pass

