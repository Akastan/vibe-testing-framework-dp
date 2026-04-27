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

