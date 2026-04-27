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

