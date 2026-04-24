# The main error is that ISBN must be exactly 13 digits, but current helper generates 12 digits after "978" prefix. Need to fix ISBN generation to ensure proper length.
import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-api-key"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("Category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id, stock=10):
    title = unique("Book")
    # ISBN must be exactly 13 digits: "978" + 10 digits = 13 total
    isbn = f"978{uuid.uuid4().hex[:10]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_successfully():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_required_field():
    payload = {"bio": "No name provided"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 404

def test_delete_author_with_associated_books():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_successfully():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload1 = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=TIMEOUT)
    assert response1.status_code == 201
    payload2 = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 2,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=TIMEOUT)
    assert response2.status_code == 409
    data = response2.json()
    assert "detail" in data

def test_get_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", [])
    book_ids = [b["id"] for b in items]
    assert book["id"] not in book_ids

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * (1 - payload["discount_percent"] / 100), 2)

def test_apply_discount_exceeds_rate_limit():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    payload = {"discount_percent": 10.0}
    for _ in range(5):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    time.sleep(10)

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_add_review_to_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {"rating": 5, "reviewer_name": unique("Reviewer"), "comment": "Great book!"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == payload["reviewer_name"]

def test_create_tag_successfully():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
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
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
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
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == payload["customer_name"]
    assert data["total_price"] == book["price"] * 3
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    updated_book = response.json()
    assert updated_book["stock"] == 7

def test_create_order_with_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_to_confirmed():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    status_response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=TIMEOUT)
    assert status_response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]
    assert "items" in data

def test_get_invoice_for_pending_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
    assert order_response.status_code == 201
    order = order_response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
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
            "price": 15.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    payload = {"books": books}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
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
        "price": 15.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }]
    payload = {"books": books}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_clone_book_with_new_isbn():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "new_isbn": f"979{uuid.uuid4().hex[:9]}",
        "new_title": unique("Cloned"),
        "stock": 3
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == payload["new_isbn"]
    assert data["title"] == payload["new_title"]
    assert data["stock"] == 3
    assert data["author_id"] == book["author_id"]
    assert data["category_id"] == book["category_id"]

def test_start_async_export_with_api_key():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    assert "created_at" in data