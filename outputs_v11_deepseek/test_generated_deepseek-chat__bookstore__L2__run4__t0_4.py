import uuid
import time
import requests
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id):
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_valid():
    name = unique("author")
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

def test_get_author_existing():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    assert response.text == ""
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books_conflict():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_valid():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2021,
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
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "title": unique("book"),
        "isbn": book["isbn"],
        "price": 39.99,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_existing():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert data["isbn"] == book["isbn"]

def test_get_book_soft_deleted():
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
    assert response.text == ""
    response = requests.get(f"{BASE_URL}/books", params={"author_id": author["id"]}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert book["id"] not in [b["id"] for b in data["items"]]

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
    assert data["title"] == book["title"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_restore_not_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_old_book():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    book = response.json()
    discount_payload = {"discount_percent": 20.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 20.0
    assert data["discounted_price"] == 80.0

def test_apply_discount_new_book():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = f"978{uuid.uuid4().hex[:9]}"
    current_year = time.localtime().tm_year
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 100.0,
        "published_year": current_year,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    book = response.json()
    discount_payload = {"discount_percent": 20.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_stock_positive():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    original_stock = book["stock"]
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == original_stock + 5

def test_decrease_stock_insufficient():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-999", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_valid():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == payload["reviewer_name"]

def test_create_tag_valid():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert "id" in data

def test_create_tag_duplicate():
    tag = create_tag()
    payload = {"name": tag["name"]}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

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

def test_create_order_valid():
    author = create_author()
    category = create_category()
    book1 = create_book(author["id"], category["id"])
    book2 = create_book(author["id"], category["id"])
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [
            {"book_id": book1["id"], "quantity": 1},
            {"book_id": book2["id"], "quantity": 2}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == payload["customer_name"]
    assert data["status"] == "pending"
    assert len(data["items"]) == 2
    assert data["total_price"] == book1["price"] * 1 + book2["price"] * 2

def test_create_order_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 999}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_response.status_code == 201
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_response.status_code == 201
    order = order_response.json()
    status_payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_response.status_code == 201
    order = order_response.json()
    status_payload = {"status": "confirmed"}
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_payload, timeout=30)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]
    assert data["status"] == "confirmed"
    assert "items" in data
    assert len(data["items"]) == 1

def test_get_invoice_pending_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique()}@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_response.status_code == 201
    order = order_response.json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    existing_book = create_book(author["id"], category["id"])
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("book"),
                "isbn": existing_book["isbn"],
                "price": 20.0,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=30)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert data["total"] == 2
    assert data["created"] == 1
    assert data["failed"] == 1
    assert "results" in data
    assert len(data["results"]) == 2

def test_bulk_create_books_no_api_key():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("book"),
                "isbn": f"978{uuid.uuid4().hex[:9]}",
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data