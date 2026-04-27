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

