import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}

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
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
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
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    bio = "Test bio"
    born_year = 1980
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_name_validation():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 404

def test_delete_author_with_books_conflict():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    price = 19.99
    published_year = 2020
    stock = 5
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == price
    assert data["published_year"] == published_year
    assert data["stock"] == stock
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 15.99,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert data["isbn"] == book["isbn"]

def test_get_soft_deleted_book_gone():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books", params={"search": book["isbn"]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_restore_not_deleted_book_error():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020, price=100)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["original_price"] == 100
    assert data["discount_percent"] == 25
    assert data["discounted_price"] == 75

def test_apply_discount_to_new_book_rejected():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2026, price=50)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_error():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": "John Doe",
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["comment"] == "Great book!"
    assert data["reviewer_name"] == "John Doe"

def test_upload_valid_cover_image():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    img_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("cover.png", img_data, "image/png")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["content_type"] == "image/png"
    assert data["size_bytes"] == len(img_data)

def test_upload_cover_wrong_file_type():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"hello", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_order_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10, price=25)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Alice",
        "customer_email": "alice@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["customer_name"] == "Alice"
    assert data["customer_email"] == "alice@example.com"
    assert data["status"] == "pending"
    assert data["total_price"] == 50
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 8

def test_create_order_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Bob",
        "customer_email": "bob@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("Charlie", "charlie@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("David", "david@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10, price=30)
    order = create_order("Eve", "eve@example.com", [{"book_id": book["id"], "quantity": 3}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["order_id"] == order["id"]
    assert data["subtotal"] == 90
    assert data["invoice_number"].startswith("INV-")

def test_get_invoice_for_pending_order_forbidden():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("Frank", "frank@example.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

def test_bulk_create_books_all_success():
    author = create_author()
    category = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH_HEADERS, json={
        "books": [
            {
                "title": unique("bulk1"),
                "isbn": unique("isbn1")[:13],
                "price": 10,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            {
                "title": unique("bulk2"),
                "isbn": unique("isbn2")[:13],
                "price": 20,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"],
            },
        ]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["total"] == 2
    assert data["created"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    duplicate_isbn = unique("dup")[:13]
    create_book(author["id"], category["id"], isbn=duplicate_isbn)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH_HEADERS, json={
        "books": [
            {
                "title": unique("ok"),
                "isbn": unique("okisbn")[:13],
                "price": 15,
                "published_year": 2020,
                "stock": 2,
                "author_id": author["id"],
                "category_id": category["id"],
            },
            {
                "title": unique("fail"),
                "isbn": duplicate_isbn,
                "price": 25,
                "published_year": 2021,
                "stock": 1,
                "author_id": author["id"],
                "category_id": category["id"],
            },
        ]
    }, timeout=30)
    assert r.status_code == 207
    data = r.json()
    assert data["total"] == 2
    assert data["created"] == 1
    assert data["failed"] == 1
    assert len(data["results"]) == 2

def test_clone_book_with_new_isbn():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=45, stock=20)
    new_isbn = unique("clone")[:13]
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={
        "new_isbn": new_isbn,
        "new_title": "Cloned Title",
        "stock": 5,
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["isbn"] == new_isbn
    assert data["title"] == "Cloned Title"
    assert data["price"] == 45
    assert data["stock"] == 5
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]