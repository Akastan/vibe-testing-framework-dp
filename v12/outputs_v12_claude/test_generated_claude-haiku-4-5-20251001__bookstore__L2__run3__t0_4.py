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