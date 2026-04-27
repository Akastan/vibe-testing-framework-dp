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