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
        isbn = f"978000{uuid.uuid4().hex[:7]}"[:13]
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
        """Verify health check endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200


class TestAuthorsPost:
    def test_create_author_success(self):
        """Create author with valid name and optional bio"""
        author_name = unique("author")
        payload = {
            "name": author_name,
            "bio": "A talented author"
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
        assert data["bio"] == "A talented author"

    def test_create_author_missing_name(self):
        """Create author without required name field"""
        payload = {"bio": "A talented author"}
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
            f"{BASE_URL}/authors",
            params={"skip": 0, "limit": 5},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAuthorsGetById:
    def test_get_author_success(self):
        """Retrieve author by valid ID"""
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
        """Retrieve author with non-existent ID"""
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
        """Update author with mismatched ETag header"""
        author = create_author()
        payload = {"name": unique("updated_author")}
        headers = {"If-Match": "invalid-etag"}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_success(self):
        """Delete author by valid ID"""
        author = create_author()
        response = requests.delete(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


class TestAuthorBooks:
    def test_list_author_books_success(self):
        """List books by author with pagination"""
        author = create_author()
        create_book(author_id=author["id"])
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}/books",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_author_books_invalid_page_size(self):
        """List author books with page_size exceeding maximum of 100"""
        author = create_author()
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}/books",
            params={"page_size": 101},
            timeout=TIMEOUT
        )
        assert response.status_code == 422


class TestCategoriesPost:
    def test_create_category_success(self):
        """Create category with valid name"""
        category_name = unique("category")
        payload = {"name": category_name}
        response = requests.post(
            f"{BASE_URL}/categories",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == category_name


class TestCategoriesGet:
    def test_list_categories_success(self):
        """List all categories"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCategoriesGetById:
    def test_get_category_success(self):
        """Retrieve category by valid ID"""
        category = create_category()
        response = requests.get(
            f"{BASE_URL}/categories/{category['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category["id"]


class TestCategoriesPut:
    def test_update_category_success(self):
        """Update category with valid data"""
        category = create_category()
        new_name = unique("updated_category")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/categories/{category['id']}",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name


class TestCategoriesDelete:
    def test_delete_category_success(self):
        """Delete category by valid ID"""
        category = create_category()
        response = requests.delete(
            f"{BASE_URL}/categories/{category['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


class TestBooksPost:
    def test_create_book_success(self):
        """Create book with all required fields"""
        author = create_author()
        category = create_category()
        book_title = unique("book")
        isbn = f"978000{uuid.uuid4().hex[:7]}"[:13]
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
        """List books with default pagination"""
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_filters(self):
        """List books with search, author_id, category_id, and price filters"""
        author = create_author()
        category = create_category()
        create_book(author_id=author["id"], category_id=category["id"], price=25.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={
                "search": "book",
                "author_id": author["id"],
                "category_id": category["id"],
                "min_price": 10.0,
                "max_price": 50.0
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_invalid_price_range(self):
        """List books with min_price greater than max_price"""
        create_book()
        response = requests.get(
            f"{BASE_URL}/books",
            params={
                "min_price": 50.0,
                "max_price": 10.0
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetById:
    def test_get_book_success(self):
        """Retrieve book by valid ID with full details"""
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
        """Retrieve soft-deleted book returns 410 Gone"""
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


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        """Soft delete book by valid ID"""
        book = create_book()
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


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

    def test_restore_non_deleted_book_error(self):
        """Attempt to restore a book that is not deleted"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400


class TestBooksReviews:
    def test_create_review_success(self):
        """Create review with rating and reviewer name"""
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

    def test_create_review_invalid_rating(self):
        """Create review with rating outside 1-5 range"""
        book = create_book()
        payload = {
            "rating": 10,
            "reviewer_name": unique("reviewer")
        }
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data