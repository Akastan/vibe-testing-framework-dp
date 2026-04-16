import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("Category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_name():
    payload = {"bio": "Test bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload1 = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=30)
    assert response1.status_code == 201
    payload2 = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 25.99,
        "published_year": 2021,
        "stock": 2,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=30)
    assert response2.status_code == 409
    data = response2.json()
    assert "detail" in data

def test_get_book_by_id():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    items = [b for b in data["items"] if b["id"] == book["id"]]
    assert len(items) == 0

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    payload = {"discount_percent": 10}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book():
    author = create_author()
    category = create_category()
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], published_year=current_year)
    payload = {"discount_percent": 10}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 8

def test_decrease_stock_below_zero():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_for_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": "Test Reviewer"
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_tag_success():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_with_sufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    payload = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 3}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = response.json()
    assert updated_book["stock"] == 7

def test_create_order_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    payload = {
        "customer_name": "Jane Doe",
        "customer_email": "jane@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 5}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": "Alice",
        "customer_email": "alice@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": "Bob",
        "customer_email": "bob@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    order = order_response.json()
    status_payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": "Charlie",
        "customer_email": "charlie@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": "David",
        "customer_email": "david@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    order = order_response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_with_api_key():
    author = create_author()
    category = create_category()
    books = []
    for _ in range(2):
        books.append({
            "title": unique("Book"),
            "isbn": f"978{uuid.uuid4().hex[:9]}",
            "price": 15.99,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    payload = {"books": books}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "total" in data
    assert data["total"] == 2
    assert data["created"] == 2

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    books = [{
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:9]}",
        "price": 15.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }]
    payload = {"books": books}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_create_book_export_with_auth():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=30)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"

def test_enable_maintenance_mode():
    headers = {"X-API-Key": API_KEY}
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] == True
    payload = {"enabled": False}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] == False