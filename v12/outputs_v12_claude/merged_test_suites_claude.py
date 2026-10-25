# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run1__t0_4.py
# IDENTIFIER: L0_run1
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run2__t0_4.py
# IDENTIFIER: L0_run2
# ===========================================================================

import pytest
import requests
import uuid
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    """Generate unique string with uuid suffix."""
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
        """Create author without required name field returns validation error"""
        payload = {"bio": "A famous author"}
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
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
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


class TestAuthorById:
    def test_get_author_success(self):
        """Retrieve author by ID returns author details with ETag header"""
        author = create_author()
        response = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == author["id"]
        assert "ETag" in response.headers

    def test_get_author_not_found(self):
        """Get non-existent author returns 404"""
        response = requests.get(
            f"{BASE_URL}/authors/999999",
            timeout=TIMEOUT
        )
        assert response.status_code == 404


class TestAuthorUpdate:
    def test_update_author_success(self):
        """Update author with valid ETag header"""
        author = create_author()
        etag = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        ).headers.get("ETag")
        
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": etag},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_etag_mismatch(self):
        """Update author with mismatched ETag returns 412 Precondition Failed"""
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": "invalid-etag"},
            timeout=TIMEOUT
        )
        assert response.status_code == 412


class TestAuthorDelete:
    def test_delete_author_success(self):
        """Delete author returns 204 No Content"""
        author = create_author()
        response = requests.delete(
            f"{BASE_URL}/authors/{author['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 204


class TestCategoriesPost:
    def test_create_category_success(self):
        """Create category with valid name and optional description"""
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


class TestCategoriesGet:
    def test_list_categories_success(self):
        """List all categories"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCategoryById:
    def test_get_category_success(self):
        """Retrieve category by ID with ETag header"""
        category = create_category()
        response = requests.get(
            f"{BASE_URL}/categories/{category['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == category["id"]
        assert "ETag" in response.headers


class TestCategoryUpdate:
    def test_update_category_success(self):
        """Update category with valid ETag"""
        category = create_category()
        etag = requests.get(
            f"{BASE_URL}/categories/{category['id']}",
            timeout=TIMEOUT
        ).headers.get("ETag")
        
        new_name = unique("updated_category")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/categories/{category['id']}",
            json=payload,
            headers={"If-Match": etag},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name


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
        """Create book with ISBN outside 10-13 character range returns validation error"""
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
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_list_books_with_filters(self):
        """List books with search, author_id, category_id, and price range filters"""
        author = create_author()
        category = create_category()
        create_book(author_id=author["id"], category_id=category["id"])
        
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


class TestBookById:
    def test_get_book_success(self):
        """Retrieve book by ID with full details and ETag"""
        book = create_book()
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == book["id"]
        assert "ETag" in response.headers

    def test_get_deleted_book(self):
        """Get soft-deleted book returns 410 Gone"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBookUpdate:
    def test_update_book_success(self):
        """Update book with valid ETag header"""
        book = create_book()
        etag = requests.get(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        ).headers.get("ETag")
        
        new_title = unique("updated_book")
        payload = {"title": new_title}
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json=payload,
            headers={"If-Match": etag},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title


class TestBookDelete:
    def test_delete_book_soft_delete(self):
        """Delete book performs soft delete"""
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

    def test_delete_already_deleted_book(self):
        """Delete already soft-deleted book returns 410"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.delete(
            f"{BASE_URL}/books/{book['id']}",
            timeout=TIMEOUT
        )
        assert response.status_code == 410


class TestBookRestore:
    def test_restore_deleted_book_success(self):
        """Restore soft-deleted book"""
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_restore_non_deleted_book(self):
        """Restore non-deleted book returns 400 Bad Request"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400


class TestBookReviews:
    def test_create_review_success(self):
        """Create review with rating 1-5 and reviewer name"""
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
        """Create review with rating outside 1-5 range returns validation error"""
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

    def test_list_reviews_success(self):
        """List all reviews for a book"""
        book = create_book()
        payload = {
            "rating": 4,
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


class TestBookDiscount:
    def test_apply_discount_success(self):
        """Apply discount with valid percentage (0-50)"""
        book = create_book()
        payload = {"discount_percent": 20}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 20

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run3__t0_4.py
# IDENTIFIER: L0_run3
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run4__t0_4.py
# IDENTIFIER: L0_run4
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run5__t0_4.py
# IDENTIFIER: L0_run5
# ===========================================================================

import pytest
import requests
import uuid
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    """Generate unique string with uuid4 suffix."""
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
        name = unique("cat")
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
        isbn = f"978{uuid.uuid4().hex[:10]}"[:13]
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
        name = unique("author")
        bio = "A famous author"
        response = requests.post(
            f"{BASE_URL}/authors",
            json={"name": name, "bio": bio},
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio

    def test_create_author_missing_name(self):
        """Create author without required name field"""
        response = requests.post(
            f"{BASE_URL}/authors",
            json={},
            timeout=TIMEOUT
        )
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
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": new_name},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_etag_mismatch(self):
        """Update author with mismatched ETag header"""
        author = create_author()
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("author")},
            headers={"If-Match": "invalid-etag"},
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


class TestCategoriesPost:
    def test_create_category_success(self):
        """Create category with valid name"""
        name = unique("cat")
        response = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name},
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_name_too_long(self):
        """Create category with name exceeding 50 characters"""
        long_name = "a" * 51
        response = requests.post(
            f"{BASE_URL}/categories",
            json={"name": long_name},
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestCategoriesGet:
    def test_list_categories_success(self):
        """List all categories"""
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBooksPost:
    def test_create_book_success(self):
        """Create book with all required fields"""
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = f"978{uuid.uuid4().hex[:10]}"[:13]
        response = requests.post(
            f"{BASE_URL}/books",
            json={
                "title": title,
                "isbn": isbn,
                "price": 29.99,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn

    def test_create_book_invalid_isbn_length(self):
        """Create book with ISBN shorter than 10 characters"""
        author = create_author()
        category = create_category()
        response = requests.post(
            f"{BASE_URL}/books",
            json={
                "title": unique("book"),
                "isbn": "123",
                "price": 29.99,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            },
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
        assert "total" in data
        assert "page" in data

    def test_list_books_with_filters(self):
        """List books with search, author_id, category_id and price filters"""
        book = create_book(price=50.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={
                "search": book["title"][:5],
                "author_id": book["author_id"],
                "category_id": book["category_id"],
                "min_price": 10.0,
                "max_price": 100.0
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
        """Retrieve book by valid ID with full details"""
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
        response = requests.put(
            f"{BASE_URL}/books/{book['id']}",
            json={"title": new_title},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title


class TestBooksDelete:
    def test_delete_book_soft_delete(self):
        """Soft delete book by ID"""
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
        """Restore previously soft-deleted book"""
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
        """Attempt to restore book that is not deleted"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/restore",
            timeout=TIMEOUT
        )
        assert response.status_code == 400


class TestReviewsPost:
    def test_create_review_success(self):
        """Create review with rating and reviewer name"""
        book = create_book()
        reviewer_name = unique("reviewer")
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json={
                "rating": 5,
                "comment": "Great book!",
                "reviewer_name": reviewer_name
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["rating"] == 5
        assert data["reviewer_name"] == reviewer_name

    def test_create_review_invalid_rating(self):
        """Create review with rating outside 1-5 range"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json={
                "rating": 10,
                "reviewer_name": unique("reviewer")
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestReviewsGet:
    def test_list_book_reviews_success(self):
        """List all reviews for a book"""
        book = create_book()
        requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json={
                "rating": 4,
                "reviewer_name": unique("reviewer")
            },
            timeout=TIMEOUT
        )
        response = requests.get(
            f"{BASE_URL}/books/{book['id']}/reviews",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDiscount:
    def test_apply_discount_success(self):
        """Apply valid discount percentage to book"""
        book = create_book()
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10.0},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10.0

    def test_apply_discount_rate_limit(self):
        """Exceed rate limit of 5 requests per 10 seconds"""
        book = create_book()
        for i in range(5):
            requests.post(
                f"{BASE_URL}/books/{book['id']}/discount",
                json={"discount_percent": float(i + 1)},
                timeout=TIMEOUT
            )
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10.0},
            timeout=TIMEOUT
        )
        assert response.status_code == 429


class TestStock:
    def test_update_stock_success(self):
        """Update book stock quantity"""
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": 5},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L0__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run1__t0_4.py
# IDENTIFIER: L1_run1
# ===========================================================================

# Analysis: The ISBN field is being truncated to 13 characters, but unique("isbn") generates strings longer than 13 chars (e.g., "isbn_a1b2c3d4" = 14 chars). The [:13] slice cuts off valid ISBN data. Fix: generate ISBN as a proper 13-digit string or use a shorter prefix.

import pytest
import requests
import uuid
import time
from io import BytesIO

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=100.0, published_year=2020, stock=10, author_id=None, category_id=None):
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
        "category_id": category_id,
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("customer")
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
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


class TestHealth:
    def test_health_check_success(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A famous author",
            "born_year": 1980,
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1980

    def test_create_author_missing_name(self):
        payload = {"bio": "A famous author"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_author_name_too_long(self):
        name = "a" * 101
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_get_author_detail_success(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert "ETag" in response.headers

    def test_get_author_with_etag_not_modified(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = response1.headers.get("ETag")
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

    def test_get_nonexistent_author(self):
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404

class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        new_name = unique("updated_author")
        payload = {"name": new_name, "bio": "Updated bio"}
        response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["bio"] == "Updated bio"

    def test_update_author_etag_mismatch(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        
        wrong_etag = '"wrong-etag"'
        payload = {"name": unique("new_name")}
        response2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": wrong_etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 412

class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        response2 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response2.status_code == 404

class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {"name": name, "description": "A test category"}
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["description"] == "A test category"

    def test_create_category_duplicate_name(self):
        name = unique("category")
        payload1 = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload1, timeout=TIMEOUT)
        
        payload2 = {"name": name}
        response = requests.post(f"{BASE_URL}/categories", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestCategoriesGet:
    def test_get_category_detail_success(self):
        category = create_category()
        response = requests.get(f"{BASE_URL}/categories/{category['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category["id"]
        assert "ETag" in response.headers

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
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn

    def test_create_book_duplicate_isbn(self):
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
        requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409

    def test_create_book_invalid_isbn_length(self):
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

    def test_create_book_nonexistent_author(self):
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": 99999,
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 404

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

    def test_list_books_with_search_filter(self):
        title = unique("searchable_book")
        create_book(title=title)
        
        response = requests.get(f"{BASE_URL}/books?search={title}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_list_books_with_price_range(self):
        create_book(price=50.0)
        create_book(price=150.0)
        
        response = requests.get(f"{BASE_URL}/books?min_price=40&max_price=160", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410

class TestBooksDelete:
    def test_soft_delete_book_success(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        response2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response2.status_code == 410

class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400

class TestBooksStock:
    def test_update_stock_increase(self):
        book = create_book(stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400

class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10.0

    def test_apply_discount_to_new_book(self):
        book = create_book(published_year=2026)
        payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400

    def test_apply_discount_rate_limit(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10.0}

        for i in range(5):
            response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
            assert response.status_code == 200

        time.sleep(0.1)
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 429

class TestTags:
    pass

    pass

    pass

    pass

class TestBookTags:
    pass

    pass

class TestReviews:
    pass

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

class TestCover:
    pass

    pass

    pass

    pass

class TestBulkBooks:
    pass

class TestCloneBook:
    pass

class TestExports:
    pass

    pass

    pass

class TestMaintenance:
    pass

    pass

    pass

class TestStatistics:
    pass


# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run2__t0_4.py
# IDENTIFIER: L1_run2
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run3__t0_4.py
# IDENTIFIER: L1_run3
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run4__t0_4.py
# IDENTIFIER: L1_run4
# ===========================================================================

import uuid
import requests
import time
import json
from io import BytesIO

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
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

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_create_author_with_all_fields():
    name = unique("author")
    bio = "A famous author"
    born_year = 1950
    payload = {"name": name, "bio": bio, "born_year": born_year}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_minimal_fields():
    name = unique("author")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    payload = {"bio": "Some bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_author_name_too_long():
    name = "a" * 101
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_custom_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_author_detail_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    assert "ETag" in response.headers
    data = response.json()
    assert data["id"] == author["id"]

def test_get_author_with_etag_match():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")
    response2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response2.status_code == 304

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_success():
    author = create_author()
    new_name = unique("updated_author")
    payload = {"name": new_name}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_etag_mismatch():
    author = create_author()
    payload = {"name": unique("updated_author")}
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}", json=payload, headers={"If-Match": "wrong-etag"}, timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_list_author_books_with_pagination():
    author = create_author()
    create_book(author_id=author["id"])
    response = requests.get(f"{BASE_URL}/authors/{author['id']}/books?page=1&page_size=10", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_create_category_success():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_duplicate_name():
    name = unique("category")
    payload = {"name": name}
    requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409

def test_list_categories_success():
    create_category()
    response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_book_with_valid_data():
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

def test_create_book_invalid_isbn_length():
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

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    payload["title"] = unique("book")
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409

def test_create_book_nonexistent_author():
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 29.99,
        "published_year": 2020,
        "author_id": 99999,
        "category_id": category["id"],
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 404

def test_list_books_default_pagination():
    create_book()
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_list_books_with_search_filter():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books?search={book['title'][:5]}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_list_books_with_price_range():
    create_book(price=50.0)
    response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=100", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_get_book_detail_success():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_update_stock_positive_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_update_stock_negative_quantity():
    book = create_book(stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-3", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 7

def test_update_stock_insufficient_inventory():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020, price=100.0)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discount_percent"] == 10.0

def test_apply_discount_to_new_book():
    current_year = 2026
    book = create_book(published_year=current_year, price=100.0)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass

pass


# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run5__t0_4.py
# IDENTIFIER: L1_run5
# ===========================================================================

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


# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L1__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run1__t0_4.py
# IDENTIFIER: L2_run1
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run2__t0_4.py
# IDENTIFIER: L2_run2
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run3__t0_4.py
# IDENTIFIER: L2_run3
# ===========================================================================

import pytest
import requests
import uuid
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: str = None, bio: str = None, born_year: int = None) -> dict:
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

def create_category(name: str = None, description: str = None) -> dict:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: str = None, isbn: str = None, price: float = 29.99, 
                published_year: int = 2020, stock: int = 10, 
                author_id: int = None, category_id: int = None) -> dict:
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
    def test_health_check_success(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
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
        name = unique("author")
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_author_missing_name(self):
        payload = {"bio": "Some bio"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_list_authors_default_pagination(self):
        create_author()
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_authors_custom_pagination(self):
        create_author()
        response = requests.get(f"{BASE_URL}/authors?skip=0&limit=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAuthorsGetById:
    def test_get_author_by_id(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert "ETag" in response.headers

    def test_get_author_with_etag_match(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        assert etag is not None
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}", 
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

    def test_get_nonexistent_author(self):
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

class TestAuthorsPut:
    def test_update_author_with_valid_etag(self):
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

    def test_update_author_etag_mismatch(self):
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
    def test_delete_author_without_books(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204

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
        payload = {"name": name, "description": "Test category"}
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        payload = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestCategoriesGet:
    def test_list_categories(self):
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestBooksPost:
    def test_create_book_with_valid_data(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        
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

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2021,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
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

    def test_create_book_nonexistent_author(self):
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": 999999,
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

class TestBooksGet:
    def test_list_books_default_pagination(self):
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_books_with_search_filter(self):
        book = create_book(title="Unique Test Book Title")
        response = requests.get(f"{BASE_URL}/books?search=Unique", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_books_with_price_range(self):
        create_book(price=50.0)
        response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=100", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksGetById:
    def test_get_book_by_id(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

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
        
        verify = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert verify.status_code == 410

class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
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
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

    def test_apply_discount_to_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        payload = {"discount_percent": 10}
        response = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run4__t0_4.py
# IDENTIFIER: L2_run4
# ===========================================================================

import pytest
import requests
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: str = None, bio: str = None, born_year: int = None) -> dict:
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


def create_category(name: str = None, description: str = None) -> dict:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(title: str = None, isbn: str = None, price: float = 10.0, 
                published_year: int = 2020, stock: int = 5, 
                author_id: int = None, category_id: int = None) -> dict:
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


class TestHealthCheck:
    def test_health_check_success(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
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

    def test_create_author_missing_name(self):
        payload = {
            "bio": "A famous author",
            "born_year": 1980
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_author_name_too_long(self):
        name = "a" * 101
        payload = {
            "name": name,
            "bio": "A famous author"
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGetById:
    def test_get_author_by_id(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert data["name"] == author["name"]
        assert "ETag" in response.headers

    def test_get_author_with_if_none_match(self):
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
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        new_name = unique("updated_author")
        payload = {"name": new_name, "born_year": 1990}
        response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["born_year"] == 1990

    def test_update_author_with_mismatched_etag(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        
        wrong_etag = '"wrong_etag_value"'
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": wrong_etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_without_books(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 404

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

    def test_create_duplicate_category(self):
        name = unique("category")
        payload = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_success(self):
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        
        payload = {
            "title": title,
            "isbn": isbn,
            "price": 25.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["stock"] == 0

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 25.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 30.00,
            "published_year": 2021,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
        author = create_author()
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": "123",
            "price": 25.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_nonexistent_author(self):
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 25.99,
            "published_year": 2020,
            "author_id": 99999,
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 404
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
        assert isinstance(data["items"], list)

    def test_list_books_with_search_filter(self):
        title = unique("searchable_book")
        create_book(title=title)
        
        response = requests.get(f"{BASE_URL}/books?search={title}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
        assert any(item["title"] == title for item in data["items"])

    def test_list_books_with_price_range(self):
        create_book(price=15.0)
        create_book(price=50.0)
        
        response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=30", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for item in data["items"]:
            assert 10 <= item["price"] <= 30


class TestBooksGetById:
    def test_get_book_success(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert data["title"] == book["title"]
        assert "author" in data
        assert "category" in data
        assert "ETag" in response.headers

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
        
        verify_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 410


class TestBooksRestore:
    def test_restore_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert data["title"] == book["title"]

    def test_restore_non_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        old_year = datetime.now(timezone.utc).year - 2
        book = create_book(published_year=old_year, price=100.0)
        
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == book["id"]
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 10
        assert data["discounted_price"] == 90.0

    def test_apply_discount_to_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year, price=100.0)
        
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_invalid_percent(self):
        book = create_book(published_year=2020, price=100.0)
        
        payload = {"discount_percent": 0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_stock(self):
        book = create_book(stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_decrease_stock_insufficient(self):
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run5__t0_4.py
# IDENTIFIER: L2_run5
# ===========================================================================

import pytest
import requests
import uuid
import json
from io import BytesIO
from PIL import Image

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
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
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=100.0, published_year=2020, stock=10, author_id=None, category_id=None):
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
        customer_name = unique("customer")
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

def create_jpeg_image():
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes

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
        payload = {
            "name": name,
            "bio": "A great author",
            "born_year": 1980,
        }
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A great author"
        assert data["born_year"] == 1980

    def test_create_author_missing_name(self):
        payload = {
            "bio": "A great author",
            "born_year": 1980,
        }
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_invalid_born_year(self):
        name = unique("author")
        payload = {
            "name": name,
            "born_year": 2027,
        }
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_get_author_success(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["id"] == author["id"]
        assert "ETag" in r.headers

    def test_get_author_not_found(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data

    def test_get_author_with_etag_match(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        r2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert r2.status_code == 304

class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        new_name = unique("updated_author")
        payload = {"name": new_name, "born_year": 1990}
        r = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["born_year"] == 1990

    def test_update_author_etag_mismatch(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("temp")}, timeout=TIMEOUT)
        new_name = unique("updated_author")
        payload = {"name": new_name}
        r2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": old_etag},
            timeout=TIMEOUT
        )
        assert r2.status_code == 412

class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r2.status_code == 404

    def test_delete_author_with_books(self):
        author = create_author()
        create_book(author_id=author["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {"name": name, "description": "A test category"}
        r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        payload1 = {"name": name}
        r1 = requests.post(f"{BASE_URL}/categories", json=payload1, timeout=TIMEOUT)
        assert r1.status_code == 201
        payload2 = {"name": name}
        r2 = requests.post(f"{BASE_URL}/categories", json=payload2, timeout=TIMEOUT)
        assert r2.status_code == 409
        data = r2.json()
        assert "detail" in data

class TestBooksPost:
    def test_create_book_success(self):
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        payload = {
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn

    def test_create_book_invalid_isbn_length(self):
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
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_duplicate_isbn(self):
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
        r1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        assert r1.status_code == 201
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert r2.status_code == 409
        data = r2.json()
        assert "detail" in data

    def test_create_book_nonexistent_author(self):
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": 999999,
            "category_id": category["id"],
        }
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data

class TestBooksGet:
    def test_get_book_success(self):
        book = create_book()
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_soft_deleted_book(self):
        book = create_book()
        r1 = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r1.status_code == 204
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410
        data = r2.json()
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
        assert "id" in data
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
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10
        expected_price = book["price"] * 0.9
        assert abs(data["discounted_price"] - expected_price) < 0.01

    def test_apply_discount_to_new_book(self):
        book = create_book(published_year=2026)
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_apply_discount_invalid_percent(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 51}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

class TestBooksStock:
    def test_update_stock_increase(self):
        book = create_book(stock=10)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

class TestBooksCover:
    def test_upload_cover_success(self):
        book = create_book()
        img = create_jpeg_image()
        files = {"file": ("cover.jpg", img, "image/jpeg")}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "book_id" in data
        assert data["book_id"] == book["id"]
        assert "filename" in data

    def test_upload_cover_invalid_type(self):
        book = create_book()
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_cover_too_large(self):
        book = create_book()
        large_data = b"x" * (2 * 1024 * 1024 + 1)
        files = {"file": ("large.jpg", large_data, "image/jpeg")}
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data

class TestReviews:
    pass

    pass

    pass

class TestTags:
    pass

    pass

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

    pass

class TestBulkBooks:
    pass

    pass

    pass

class TestCloneBook:
    pass

    pass

class TestExports:
    pass

    pass

    pass

class TestMaintenance:
    pass


# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L2__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run1__t0_4.py
# IDENTIFIER: L3_run1
# ===========================================================================

import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: str = None, bio: str = None, born_year: int = None) -> dict:
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


def create_category(name: str = None, description: str = None) -> dict:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def create_book(title: str = None, isbn: str = None, price: float = 29.99, 
                published_year: int = 2020, stock: int = 10, 
                author_id: int = None, category_id: int = None) -> dict:
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


def create_tag(name: str = None) -> dict:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


class TestHealth:
    def test_health_check_returns_ok(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        bio = "A famous author"
        born_year = 1980
        payload = {"name": name, "bio": bio, "born_year": born_year}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year

    def test_create_author_with_only_name(self):
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
        name = unique("author")
        payload = {"name": name, "born_year": 2027}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_with_pagination(self):
        create_author()
        create_author()
        response = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 10}, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestAuthorsGetDetail:
    def test_get_author_returns_etag(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_returns_304(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        assert etag is not None
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}", 
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

    def test_get_nonexistent_author(self):
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_if_match_success(self):
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
        author = create_author()
        payload = {"name": unique("updated_author")}
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": '"wrong-etag"'},
            timeout=TIMEOUT
        )
        assert response.status_code == 412
        data = response.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_no_books(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204

    def test_delete_author_with_books_fails(self):
        author = create_author()
        create_book(author_id=author["id"])
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {"name": name, "description": "Test category"}
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_duplicate_category(self):
        name = unique("category")
        payload = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_data(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        
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
        
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_book_with_nonexistent_author(self):
        category = create_category()
        
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "author_id": 99999,
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestBooksGet:
    def test_list_books_with_pagination(self):
        create_book()
        create_book()
        response = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 10}, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_list_books_with_search_filter(self):
        book = create_book(title="Unique Search Title XYZ")
        response = requests.get(
            f"{BASE_URL}/books",
            params={"search": "Unique Search Title"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_list_books_with_price_range(self):
        create_book(price=10.0)
        create_book(price=50.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={"min_price": 20.0, "max_price": 60.0},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
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
    def test_soft_delete_book_success(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestBooksStock:
    def test_update_stock_positive_delta(self):
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": 5},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_update_stock_negative_delta(self):
        book = create_book(stock=10)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": -3},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 7

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        response = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": -10},
            timeout=TIMEOUT
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
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run2__t0_4.py
# IDENTIFIER: L3_run2
# ===========================================================================

import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
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

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

class TestHealth:
    def test_health_check_success(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        bio = "A famous author"
        born_year = 1980
        payload = {"name": name, "bio": bio, "born_year": born_year}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year

    def test_create_author_missing_name(self):
        payload = {"bio": "A bio without name"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_get_author_with_etag(self):
        author = create_author()
        author_id = author["id"]
        response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "ETag" in response.headers
        data = response.json()
        assert data["id"] == author_id

    def test_get_author_not_found(self):
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_author_with_if_none_match(self):
        author = create_author()
        author_id = author["id"]
        response1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        assert etag is not None
        response2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert response2.status_code == 304

class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        author_id = author["id"]
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    def test_update_author_etag_mismatch(self):
        author = create_author()
        author_id = author["id"]
        new_name = unique("updated_author")
        payload = {"name": new_name}
        response = requests.put(
            f"{BASE_URL}/authors/{author_id}",
            json=payload,
            headers={"If-Match": '"wrongetag"'},
            timeout=TIMEOUT
        )
        assert response.status_code == 412
        data = response.json()
        assert "detail" in data

class TestAuthorsDelete:
    def test_delete_author_with_books(self):
        author = create_author()
        author_id = author["id"]
        category = create_category()
        create_book(author_id=author_id, category_id=category["id"])
        response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_duplicate_category(self):
        name = unique("category")
        payload = {"name": name}
        requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestBooksPost:
    def test_create_book_with_valid_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        payload = {
            "title": title,
            "isbn": isbn,
            "price": 25.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["isbn"] == isbn

    def test_create_book_invalid_isbn_length(self):
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": "123",
            "price": 25.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        payload = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 25.99,
            "published_year": 2020,
            "stock": 5,
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

    def test_list_books_with_price_range(self):
        create_book(price=15.99)
        create_book(price=35.99)
        response = requests.get(f"{BASE_URL}/books?min_price=10&max_price=30", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksGetDetail:
    def test_get_book_detail_success(self):
        book = create_book()
        book_id = book["id"]
        response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert "author" in data
        assert "category" in data

    def test_get_soft_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data

class TestBooksDelete:
    def test_soft_delete_book_success(self):
        book = create_book()
        book_id = book["id"]
        response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 204
        verify_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert verify_response.status_code == 410

class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id

    def test_restore_non_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 20}
        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 20

    def test_apply_discount_to_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        book_id = book["id"]
        payload = {"discount_percent": 20}
        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_invalid_percentage(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 0}
        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestBooksStock:
    def test_increase_stock_success(self):
        book = create_book(stock=10)
        book_id = book["id"]
        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_decrease_stock_insufficient(self):
        book = create_book(stock=5)
        book_id = book["id"]
        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksCover:
    def test_upload_cover_valid_jpeg(self):
        book = create_book()
        book_id = book["id"]
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        files = {"file": ("cover.jpg", jpeg_data, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert data["book_id"] == book_id

    def test_upload_cover_invalid_type(self):
        book = create_book()
        book_id = book["id"]
        files = {"file": ("cover.txt", b"not an image", "text/plain")}
        response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 415
        data = response.json()
        assert "detail" in data

    def test_upload_cover_too_large(self):
        book = create_book()
        book_id = book["id"]
        large_data = b'\xff\xd8' + (b'\x00' * (2 * 1024 * 1024 + 1))
        files = {"file": ("cover.jpg", large_data, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 413
        data = response.json()
        assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run3__t0_4.py
# IDENTIFIER: L3_run3
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run4__t0_4.py
# IDENTIFIER: L3_run4
# ===========================================================================

import pytest
import requests
import uuid
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=29.99, published_year=2020, stock=10, author_id=None, category_id=None):
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

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

class TestHealth:
    def test_health_check_success(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

class TestAuthorsPost:
    def test_create_author_success(self):
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A talented author",
            "born_year": 1980,
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A talented author"
        assert data["born_year"] == 1980

    def test_create_author_missing_name(self):
        payload = {
            "bio": "A talented author",
            "born_year": 1980,
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGet:
    def test_list_authors_success(self):
        create_author()
        response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAuthorsGetById:
    def test_get_author_success(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert "ETag" in response.headers

    def test_get_author_not_found(self):
        response = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_author_not_modified(self):
        author = create_author()
        response1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        assert etag is not None
        
        response2 = requests.get(
            f"{BASE_URL}/authors/{author['id']}",
            headers={"If-None-Match": etag},
            timeout=TIMEOUT
        )
        assert response2.status_code == 304

class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        new_name = unique("updated_author")
        payload = {
            "name": new_name,
            "bio": "Updated bio",
        }
        response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["bio"] == "Updated bio"

    def test_update_author_etag_mismatch(self):
        author = create_author()
        payload = {
            "name": unique("updated_author"),
        }
        response = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json=payload,
            headers={"If-Match": '"invalid-etag"'},
            timeout=TIMEOUT
        )
        assert response.status_code == 412
        data = response.json()
        assert "detail" in data

class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 404

class TestCategoriesPost:
    def test_create_category_success(self):
        name = unique("category")
        payload = {
            "name": name,
            "description": "A book category",
        }
        response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name
        assert data["description"] == "A book category"

    def test_create_category_duplicate_name(self):
        name = unique("category")
        payload1 = {"name": name}
        response1 = requests.post(f"{BASE_URL}/categories", json=payload1, timeout=TIMEOUT)
        assert response1.status_code == 201
        
        payload2 = {"name": name}
        response2 = requests.post(f"{BASE_URL}/categories", json=payload2, timeout=TIMEOUT)
        assert response2.status_code == 409
        data = response2.json()
        assert "detail" in data

class TestCategoriesGet:
    def test_list_categories_success(self):
        create_category()
        response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestBooksPost:
    def test_create_book_success(self):
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
        assert data["price"] == 29.99

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        assert response1.status_code == 201
        
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2021,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert response2.status_code == 409
        data = response2.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
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

class TestBooksGet:
    def test_list_books_success(self):
        create_book()
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_books_with_search_filter(self):
        book = create_book(title="Python Programming")
        response = requests.get(f"{BASE_URL}/books?search=Python", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_list_books_with_price_range(self):
        create_book(price=25.00)
        create_book(price=35.00)
        response = requests.get(f"{BASE_URL}/books?min_price=20&max_price=30", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

class TestBooksGetById:
    def test_get_book_success(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data

    def test_get_book_soft_deleted(self):
        book = create_book()
        delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert delete_response.status_code == 204
        
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data

class TestBooksDelete:
    def test_delete_book_soft_delete(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        
        verify_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert verify_response.status_code == 410

class TestBooksRestore:
    def test_restore_book_success(self):
        book = create_book()
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]

    def test_restore_book_not_deleted(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksStock:
    def test_update_stock_increase(self):
        book = create_book(stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksDiscount:
    def test_apply_discount_old_book(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["discount_percent"] == 10

    def test_apply_discount_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        payload = {"discount_percent": 10}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksCover:
    def test_upload_cover_success(self):
        book = create_book()
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        files = {"file": ("cover.jpg", jpeg_data, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert data["book_id"] == book["id"]

    def test_upload_cover_unsupported_type(self):
        book = create_book()
        files = {"file": ("cover.txt", b"not an image", "text/plain")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 415
        data = response.json()
        assert "detail" in data

class TestTags:
    pass

    pass

    pass

    pass

    pass

    pass

    pass

class TestReviews:
    pass

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

class TestMaintenance:
    pass

    pass

class TestStatistics:
    pass

class TestDeprecatedCatalog:
    pass

class TestBulkBooks:
    pass

class TestCloneBook:
    pass

class TestExports:
    pass

    pass

    pass

class TestEdgeCases:
    pass


# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run5__t0_4.py
# IDENTIFIER: L3_run5
# ===========================================================================

# Analysis: The ISBN field is being truncated to 13 chars but unique() generates longer strings.
# Fix: Use unique("isbn")[:13] to ensure ISBN is exactly 13 characters, and verify all payload fields match API schema.

import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def unique(prefix):
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
        name = unique("category")
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


class TestHealth:
    def test_health_check_success(self):
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAuthorsPost:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        payload = {
            "name": name,
            "bio": "A famous author",
            "born_year": 1980,
        }
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == "A famous author"
        assert data["born_year"] == 1980

    def test_create_author_name_only(self):
        name = unique("author")
        payload = {"name": name}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] is None
        assert data["born_year"] is None

    def test_create_author_missing_name(self):
        payload = {"bio": "Some bio"}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_empty_name(self):
        payload = {"name": ""}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_invalid_born_year(self):
        name = unique("author")
        payload = {"name": name, "born_year": 2027}
        r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_success(self):
        author = create_author()
        author_id = author["id"]
        r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == author_id
        assert "ETag" in r.headers

    def test_get_author_with_etag_match(self):
        author = create_author()
        author_id = author["id"]
        r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        r2 = requests.get(f"{BASE_URL}/authors/{author_id}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_author_not_found(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_success(self):
        author = create_author()
        author_id = author["id"]
        new_name = unique("updated_author")
        payload = {"name": new_name, "born_year": 1990}
        r = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["born_year"] == 1990

    def test_update_author_etag_mismatch(self):
        author = create_author()
        author_id = author["id"]
        r1 = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        wrong_etag = '"wrong_etag"'
        payload = {"name": unique("updated")}
        r2 = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, headers={"If-Match": wrong_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_success(self):
        author = create_author()
        author_id = author["id"]
        r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 204
        r_check = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r_check.status_code == 404

    def test_delete_author_with_books(self):
        author = create_author()
        author_id = author["id"]
        category = create_category()
        create_book(author_id=author_id, category_id=category["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_success(self):
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
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["stock"] == 10

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
        assert r1.status_code == 201
        payload2 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 19.99,
            "published_year": 2021,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        r2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
        assert r2.status_code == 409
        data = r2.json()
        assert "detail" in data

    def test_create_book_invalid_isbn_length(self):
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
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_nonexistent_author(self):
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": 999999,
            "category_id": category["id"],
        }
        r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_book_success(self):
        book = create_book()
        book_id = book["id"]
        r = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book_id
        assert "author" in data
        assert "category" in data
        assert "ETag" in r.headers

    def test_get_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        r_delete = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_delete.status_code == 204
        r_get = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_get.status_code == 410


class TestBooksDelete:
    def test_soft_delete_book_success(self):
        book = create_book()
        book_id = book["id"]
        r = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r.status_code == 204
        r_check = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_check.status_code == 410


class TestBooksRestore:
    def test_restore_deleted_book_success(self):
        book = create_book()
        book_id = book["id"]
        r_delete = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert r_delete.status_code == 204
        r_restore = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert r_restore.status_code == 200
        data = r_restore.json()
        assert data["id"] == book_id
        assert data.get("is_deleted") == False

    def test_restore_non_deleted_book(self):
        book = create_book()
        book_id = book["id"]
        r = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_update_stock_increase(self):
        book = create_book(stock=10)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=5", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_update_stock_decrease(self):
        book = create_book(stock=10)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-3", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 7

    def test_update_stock_insufficient(self):
        book = create_book(stock=5)
        book_id = book["id"]
        r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_old_book(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book_id
        assert data["discount_percent"] == 10
        assert "discounted_price" in data
        assert data["discounted_price"] < data["original_price"]

    def test_apply_discount_new_book(self):
        current_year = datetime.now(timezone.utc).year
        book = create_book(published_year=current_year)
        book_id = book["id"]
        payload = {"discount_percent": 10}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_apply_discount_invalid_percent(self):
        book = create_book(published_year=2020)
        book_id = book["id"]
        payload = {"discount_percent": 0}
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_success(self):
        book = create_book()
        book_id = book["id"]
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        files = {"file": ("cover.jpg", jpeg_data, "image/jpeg")}
        r = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book_id
        assert "filename" in data
        assert data["content_type"] == "image/jpeg"

    def test_upload_cover_unsupported_type(self):
        book = create_book()
        book_id = book["id"]
        files = {"file": ("cover.txt", b"not an image", "text/plain")}
        r = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L3__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run1__t0_4.py
# IDENTIFIER: L4_run1
# ===========================================================================

# Analysis: The ISBN field is being truncated to 13 chars from a string like "isbn_a1b2c3d4" (14+ chars).
# Fix: Generate ISBN as a proper 13-digit numeric string instead of using unique() which adds prefix overhead.

import uuid
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix):
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
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id, category_id, title=None, isbn=None, price=29.99,
                published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
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
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@test.com"
    if items is None:
        items = []
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealthCheck:
    def test_health_check_returns_ok(self):
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
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "bio": bio,
            "born_year": born_year,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year

    def test_create_author_missing_name(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "No name provided",
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_born_year_out_of_range(self):
        name = unique("author")
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "born_year": 2027,
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_returns_etag_header(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert "id" in data
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_etag(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_if_match_success(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        
        new_name = unique("updated_author")
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": new_name},
                         headers={"If-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 200
        data = r2.json()
        assert data["name"] == new_name

    def test_update_author_with_stale_etag(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        
        requests.put(f"{BASE_URL}/authors/{author['id']}", 
                    json={"name": unique("intermediate")}, timeout=TIMEOUT)
        
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": unique("stale_update")},
                         headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412
        data = r2.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_associated_books(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_unique_name(self):
        name = unique("category")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
            "description": "Test description",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["isbn"] == isbn

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        
        requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_isbn_too_short(self):
        author = create_author()
        category = create_category()
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": "123456789",
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_negative_price(self):
        author = create_author()
        category = create_category()
        
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": -10.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_soft_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204


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

    def test_restore_non_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 25,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=50.0, published_year=2026)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_discount_rate_limit_exceeded(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)

        for i in range(5):
            r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
                "discount_percent": 10,
            }, timeout=TIMEOUT)
            assert r.status_code == 200

        time.sleep(0.1)

        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 429
        assert "Retry-After" in r.headers


class TestBooksStock:
    def test_increase_stock_quantity(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=10)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": 5}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=3)
        
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_valid_jpeg(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("cover.jpg", jpeg_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "book_id" in data
        assert data["content_type"] == "image/jpeg"

    def test_upload_cover_unsupported_type(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("doc.txt", b"text content", "text/plain")},
                         timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_cover_exceeds_size_limit(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        big_data = b"\xff\xd8" + b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("big.jpg", big_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestBooksReviews:
    def test_create_review_valid_rating(self):
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

    def test_create_review_on_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": 4,
            "reviewer_name": unique("reviewer"),
        }, timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run2__t0_4.py
# IDENTIFIER: L4_run2
# ===========================================================================

import uuid
import time
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
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
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


class TestAuthorsCreate:
    def test_create_author_with_all_fields(self):
        name = unique("author")
        bio = "Test biography"
        born_year = 1980
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "bio": bio,
            "born_year": born_year,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_author_missing_name(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "Test bio",
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_returns_etag(self):
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

        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsUpdate:
    def test_update_author_name(self):
        author = create_author()
        new_name = unique("updated_author")
        r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": new_name,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["id"] == author["id"]

    def test_update_author_with_stale_etag(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")

        requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": unique("changed_author"),
        }, timeout=TIMEOUT)

        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={
            "name": unique("stale_update"),
        }, headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412
        data = r2.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_without_books(self):
        author = create_author()
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 204

        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r2.status_code == 404

    def test_delete_author_with_books(self):
        author = create_author()
        category = create_category()
        create_book(author["id"], category["id"])

        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesCreate:
    def test_create_category_unique_name(self):
        name = unique("category")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        create_category(name=name)
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksCreate:
    def test_create_book_with_valid_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        title = unique("book")
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["isbn"] == isbn
        assert data["title"] == title

    def test_create_book_duplicate_isbn(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        create_book(author["id"], category["id"], isbn=isbn)

        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_negative_price(self):
        author = create_author()
        category = create_category()
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": -5.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_book_detail(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])

        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]
        assert "author" in data
        assert "category" in data
        assert data["author"]["id"] == author["id"]
        assert data["category"]["id"] == category["id"]

    def test_get_soft_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])

        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)

        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book(self):
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

    def test_restore_non_deleted_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])

        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], 
                          price=100.0, published_year=2020)

        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 25,
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book["id"]
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 25
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book(self):
        author = create_author()
        category = create_category()
        current_year = 2026
        book = create_book(author["id"], category["id"], 
                          price=50.0, published_year=current_year)

        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
            "discount_percent": 10,
        }, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_stock(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=5)

        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock",
                          params={"quantity": 10}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=3)

        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock",
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksReviews:
    def test_create_review_valid_rating(self):
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
        assert data["book_id"] == book["id"]
        assert data["rating"] == 5


class TestBooksRating:
    def test_get_average_rating(self):
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


class TestTagsCreate:
    def test_create_tag_unique_name(self):
        name = unique("tag")
        r = requests.post(f"{BASE_URL}/tags", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_tag_duplicate_name(self):
        name = unique("tag")
        create_tag(name=name)
        r = requests.post(f"{BASE_URL}/tags", json={
            "name": name,
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksTagsAdd:
    def test_add_tags_to_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        tag1 = create_tag()
        tag2 = create_tag()

        r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={
            "tag_ids": [tag1["id"], tag2["id"]],
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "tags" in data
        assert len(data["tags"]) == 2
        tag_ids = [t["id"] for t in data["tags"]]
        assert tag1["id"] in tag_ids
        assert tag2["id"] in tag_ids


class TestBooksTagsRemove:
    def test_remove_tags_from_book(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        tag = create_tag()

        requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={
            "tag_ids": [tag["id"]],
        }, timeout=TIMEOUT)

        r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={
            "tag_ids": [tag["id"]],
        }, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "tags" in data
        assert len(data["tags"]) == 0

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run3__t0_4.py
# IDENTIFIER: L4_run3
# ===========================================================================

import uuid
import time
import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id, category_id, title=None, isbn=None, price=29.99, 
                published_year=2020, stock=10):
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


def create_tag(name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@test.com"
    if items is None:
        items = []
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealthCheck:
    def test_health_check_returns_ok(self):
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
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_author_missing_name_validation_error(self):
        r = requests.post(
            f"{BASE_URL}/authors",
            json={"bio": "No name provided"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_list_authors_with_pagination(self):
        create_author(name=unique("author1"))
        create_author(name=unique("author2"))
        r = requests.get(
            f"{BASE_URL}/authors",
            params={"skip": 0, "limit": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestAuthorsGetById:
    def test_get_author_by_id_returns_etag(self):
        author = create_author(name=unique("author"))
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_etag_match(self):
        author = create_author(name=unique("author"))
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

    def test_get_nonexistent_author(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_partial_fields(self):
        author = create_author(name=unique("author"))
        new_name = unique("updated_author")
        r = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": new_name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == new_name
        assert data["id"] == author["id"]

    def test_update_author_with_stale_etag(self):
        author = create_author(name=unique("author"))
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        
        requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("changed")},
            timeout=TIMEOUT,
        )
        
        r2 = requests.put(
            f"{BASE_URL}/authors/{author['id']}",
            json={"name": unique("stale_update")},
            headers={"If-Match": old_etag},
            timeout=TIMEOUT,
        )
        assert r2.status_code == 412


class TestAuthorsDelete:
    def test_delete_author_with_associated_books(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_with_unique_name(self):
        name = unique("category")
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name, "description": "Test category"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_category_duplicate_name(self):
        name = unique("category")
        create_category(name=name)
        
        r = requests.post(
            f"{BASE_URL}/categories",
            json={"name": name},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesGet:
    def test_list_all_categories(self):
        create_category(name=unique("category1"))
        create_category(name=unique("category2"))
        
        r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestBooksPost:
    def test_create_book_with_valid_data(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
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
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        isbn = unique("isbn")[:13]
        
        create_book(author["id"], category["id"], isbn=isbn)
        
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
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        
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
    def test_list_books_with_search_filter(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        title = unique("searchable_book")
        isbn = unique("isbn")[:13]
        
        create_book(author["id"], category["id"], title=title, isbn=isbn)
        
        r = requests.get(
            f"{BASE_URL}/books",
            params={"search": title},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_books_with_price_range_filter(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        
        create_book(author["id"], category["id"], price=50.0)
        create_book(author["id"], category["id"], price=100.0)
        
        r = requests.get(
            f"{BASE_URL}/books",
            params={"min_price": 40.0, "max_price": 75.0},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert all(40.0 <= item["price"] <= 75.0 for item in data["items"])


class TestBooksGetById:
    def test_get_soft_deleted_book_returns_gone(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == book["id"]
        
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 200

    def test_restore_non_deleted_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            price=100.0,
            published_year=2020,
        )
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 25},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 25
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            price=50.0,
            published_year=2026,
        )
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/discount",
            json={"discount_percent": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_book_stock(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            stock=5,
        )
        
        r = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(
            author["id"],
            category["id"],
            isbn=unique("isbn")[:13],
            stock=3,
        )
        
        r = requests.patch(
            f"{BASE_URL}/books/{book['id']}/stock",
            params={"quantity": -10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_valid_png_cover(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("cover.png", png_data, "image/png")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == book["id"]
        assert data["content_type"] == "image/png"

    def test_upload_unsupported_file_type(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_oversized_cover(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        big_data = b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/cover",
            files={"file": ("big.jpg", big_data, "image/jpeg")},
            timeout=TIMEOUT,
        )
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestBooksReviews:
    def test_create_review_with_valid_rating(self):
        author = create_author(name=unique("author"))
        category = create_category(name=unique("category"))
        book = create_book(author["id"], category["id"], isbn=unique("isbn")[:13])
        
        r = requests.post(
            f"{BASE_URL}/books/{book['id']}/reviews",
            json={
                "rating": 5,
                "reviewer_name": unique("reviewer"),
                "comment": "Great book!",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["rating"] == 5
        assert data["book_id"] == book["id"]

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run4__t0_4.py
# IDENTIFIER: L4_run4
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run5__t0_4.py
# IDENTIFIER: L4_run5
# ===========================================================================

import uuid
import time
import pytest
import requests
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}
TIMEOUT = 30


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_author(name: str = None, bio: str = None, born_year: int = None) -> Dict[str, Any]:
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


def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id: int, category_id: int, title: str = None, isbn: str = None,
                price: float = 29.99, published_year: int = 2020, stock: int = 10) -> Dict[str, Any]:
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


def create_tag(name: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_order(customer_name: str, customer_email: str, items: list) -> Dict[str, Any]:
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


class TestHealthCheck:
    def test_health_check_returns_ok(self):
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
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "bio": bio,
            "born_year": born_year,
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert data["bio"] == bio
        assert data["born_year"] == born_year
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_author_missing_name_validation_error(self):
        r = requests.post(f"{BASE_URL}/authors", json={
            "bio": "Test bio",
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_author_born_year_out_of_range(self):
        name = unique("author")
        r = requests.post(f"{BASE_URL}/authors", json={
            "name": name,
            "born_year": 2027,
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestAuthorsGet:
    def test_get_author_returns_etag_header(self):
        author = create_author()
        r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "ETag" in r.headers
        data = r.json()
        assert "id" in data
        assert data["id"] == author["id"]

    def test_get_author_with_if_none_match_returns_304(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r1.status_code == 200
        etag = r1.headers.get("ETag")
        assert etag is not None
        r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", 
                         headers={"If-None-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 304

    def test_get_nonexistent_author_returns_404(self):
        r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data


class TestAuthorsPut:
    def test_update_author_with_if_match_success(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        etag = r1.headers.get("ETag")
        new_name = unique("updated_author")
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": new_name},
                         headers={"If-Match": etag}, timeout=TIMEOUT)
        assert r2.status_code == 200
        data = r2.json()
        assert data["name"] == new_name

    def test_update_author_with_stale_etag_returns_412(self):
        author = create_author()
        r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        old_etag = r1.headers.get("ETag")
        requests.put(f"{BASE_URL}/authors/{author['id']}", 
                    json={"name": unique("changed")}, timeout=TIMEOUT)
        r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                         json={"name": unique("stale_update")},
                         headers={"If-Match": old_etag}, timeout=TIMEOUT)
        assert r2.status_code == 412
        data = r2.json()
        assert "detail" in data


class TestAuthorsDelete:
    def test_delete_author_with_associated_books_returns_409(self):
        author = create_author()
        category = create_category()
        create_book(author["id"], category["id"])
        r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestCategoriesPost:
    def test_create_category_with_unique_name(self):
        name = unique("category")
        r = requests.post(f"{BASE_URL}/categories", json={
            "name": name,
            "description": "Test description",
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert "updated_at" in data

    def test_create_category_duplicate_name_returns_409(self):
        name = unique("category")
        requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksPost:
    def test_create_book_with_valid_isbn_and_price(self):
        author = create_author()
        category = create_category()
        title = unique("book")
        isbn = unique("isbn")[:13]
        price = 29.99
        r = requests.post(f"{BASE_URL}/books", json={
            "title": title,
            "isbn": isbn,
            "price": price,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["title"] == title
        assert data["isbn"] == isbn
        assert data["price"] == price

    def test_create_book_duplicate_isbn_returns_409(self):
        author = create_author()
        category = create_category()
        isbn = unique("isbn")[:13]
        requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": isbn,
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data

    def test_create_book_isbn_too_short_returns_422(self):
        author = create_author()
        category = create_category()
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": "123456789",
            "price": 29.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_create_book_negative_price_returns_422(self):
        author = create_author()
        category = create_category()
        r = requests.post(f"{BASE_URL}/books", json={
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": -5.0,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data


class TestBooksGet:
    def test_get_soft_deleted_book_returns_410(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 410
        data = r.json()
        assert "detail" in data


class TestBooksDelete:
    def test_soft_delete_book_sets_is_deleted_flag(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r.status_code == 204
        r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert r2.status_code == 410


class TestBooksRestore:
    def test_restore_soft_deleted_book_success(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["id"] == book["id"]

    def test_restore_non_deleted_book_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksDiscount:
    def test_apply_discount_to_old_book_success(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=100.0, published_year=2020)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                         json={"discount_percent": 25}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "discounted_price" in data
        assert data["discounted_price"] == 75.0

    def test_apply_discount_to_new_book_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], price=50.0, published_year=2026)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                         json={"discount_percent": 10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksStock:
    def test_increase_stock_with_positive_quantity(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=10)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": 5}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero_returns_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"], stock=3)
        r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", 
                          params={"quantity": -10}, timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data


class TestBooksCover:
    def test_upload_cover_with_valid_jpeg(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("cover.jpg", jpeg_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "book_id" in data
        assert data["book_id"] == book["id"]
        assert "content_type" in data

    def test_upload_cover_with_unsupported_type_returns_415(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("doc.txt", b"hello", "text/plain")},
                         timeout=TIMEOUT)
        assert r.status_code == 415
        data = r.json()
        assert "detail" in data

    def test_upload_cover_exceeding_size_limit_returns_413(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        big_data = b"\xff\xd8\xff\xe0" + b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                         files={"file": ("big.jpg", big_data, "image/jpeg")},
                         timeout=TIMEOUT)
        assert r.status_code == 413
        data = r.json()
        assert "detail" in data


class TestTagsPost:
    def test_create_tag_with_unique_name(self):
        name = unique("tag")
        r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == name
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_tag_duplicate_name_returns_409(self):
        name = unique("tag")
        requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data


class TestBooksTagsPost:
    def test_add_tags_to_book_idempotent(self):
        author = create_author()
        category = create_category()
        book = create_book(author["id"], category["id"])
        tag = create_tag()
        r1 = requests.post(f"{BASE_URL}/books/{book['id']}/tags",
                          json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
        assert r1.status_code == 200
        data1 = r1.json()
        assert "tags" in data1
        tag_count_1 = len(data1["tags"])
        r2 = requests.post(f"{BASE_URL}/books/{book['id']}/tags",
                          json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
        assert r2.status_code == 200
        data2 = r2.json()
        assert "tags" in data2
        tag_count_2 = len(data2["tags"])
        assert tag_count_1 == tag_count_2

# ===========================================================================
# END OF FILE: v12/outputs_v12_claude/test_generated_claude-haiku-4-5-20251001__bookstore__L4__run5__t0_4.py
# ===========================================================================



