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