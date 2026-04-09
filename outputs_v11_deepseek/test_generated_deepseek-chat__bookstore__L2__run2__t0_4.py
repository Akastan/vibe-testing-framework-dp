import uuid
import time
import requests
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
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

def create_book(title=None, isbn=None, price=10.5, published_year=2020, stock=5, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = str(uuid.uuid4().int)[:13]
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
        customer_email = f"{unique()}@example.com"
    if items is None:
        book = create_book(stock=10)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

class TestHealth:
    def test_health_check_returns_ok(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

class TestAuthors:
    def test_create_author_success(self):
        name = unique("author")
        response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == name

    def test_create_author_missing_name_validation(self):
        response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_get_existing_author(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert data["name"] == author["name"]

    def test_get_author_not_found(self):
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_author_without_books(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 404

    def test_delete_author_with_books_conflict(self):
        author = create_author()
        book = create_book(author_id=author["id"])
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestBooks:
    def test_create_book_success(self):
        author = create_author()
        category = create_category()
        isbn = str(uuid.uuid4().int)[:13]
        payload = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 25.99,
            "published_year": 2020,
            "stock": 10,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["isbn"] == isbn
        assert data["author_id"] == author["id"]

    def test_create_book_duplicate_isbn(self):
        book = create_book()
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("book"),
            "isbn": book["isbn"],
            "price": 30.0,
            "published_year": 2021,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"],
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_get_existing_book(self):
        book = create_book()
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert data["title"] == book["title"]

    def test_get_soft_deleted_book_gone(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data

    def test_soft_delete_book_success(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        book_ids = [b["id"] for b in items]
        assert book["id"] not in book_ids

    def test_restore_soft_deleted_book(self):
        book = create_book()
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200

    def test_restore_not_deleted_book(self):
        book = create_book()
        response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_to_old_book(self):
        book = create_book(published_year=2020)
        payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "discounted_price" in data
        assert data["original_price"] == book["price"]
        assert data["discount_percent"] == 10.0

    def test_apply_discount_to_new_book_rejected(self):
        current_year = time.localtime().tm_year
        book = create_book(published_year=current_year)
        payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_increase_stock_success(self):
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 8
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        data2 = response.json()
        assert data2["stock"] == 8

    def test_decrease_stock_below_zero(self):
        book = create_book(stock=5)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestCover:
    def test_upload_valid_cover(self):
        book = create_book()
        files = {"file": ("cover.jpg", b"fake_jpeg_data", "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == book["id"]
        assert data["content_type"] == "image/jpeg"

    def test_upload_cover_unsupported_type(self):
        book = create_book()
        files = {"file": ("cover.gif", b"fake_gif_data", "image/gif")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 415
        data = response.json()
        assert "detail" in data

class TestReviews:
    def test_create_review_success(self):
        book = create_book()
        payload = {
            "rating": 5,
            "reviewer_name": unique("reviewer"),
            "comment": "Great book!",
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["book_id"] == book["id"]
        assert data["rating"] == 5

class TestTags:
    def test_create_tag_success(self):
        name = unique("tag")
        response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == name

    def test_create_tag_duplicate_name(self):
        tag = create_tag()
        response = requests.post(f"{BASE_URL}/tags", json={"name": tag["name"]}, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_add_tags_to_book(self):
        book = create_book()
        tag1 = create_tag()
        tag2 = create_tag()
        payload = {"tag_ids": [tag1["id"], tag2["id"]]}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        tag_ids = [t["id"] for t in data["tags"]]
        assert tag1["id"] in tag_ids
        assert tag2["id"] in tag_ids

class TestOrders:
    def test_create_order_success(self):
        book = create_book(stock=10)
        payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique()}@example.com",
            "items": [{"book_id": book["id"], "quantity": 3}],
        }
        response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert len(data["items"]) == 1
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        book_after = response.json()
        assert book_after["stock"] == 7

    def test_create_order_insufficient_stock(self):
        book = create_book(stock=2)
        payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique()}@example.com",
            "items": [{"book_id": book["id"], "quantity": 5}],
        }
        response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_update_order_status_valid_transition(self):
        order = create_order()
        payload = {"status": "confirmed"}
        response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    def test_update_order_status_invalid_transition(self):
        order = create_order()
        payload = {"status": "delivered"}
        response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_get_invoice_for_confirmed_order(self):
        order = create_order()
        payload = {"status": "confirmed"}
        response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "invoice_number" in data
        assert data["order_id"] == order["id"]

    def test_get_invoice_for_pending_order_forbidden(self):
        order = create_order()
        response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data