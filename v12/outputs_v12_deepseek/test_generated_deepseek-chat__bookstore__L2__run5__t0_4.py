# The main error is that ISBN must be exactly 13 characters, but unique() generates 8 random chars plus prefix length, making it too long. We need to generate a 13-digit ISBN.
# Also, some endpoints require X-API-Key header and ETag handling, but helpers are for creation only, so we focus on data format fixes.

import requests
import uuid
import time
from typing import Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> dict:
    payload = {
        "name": name if name is not None else unique("Author"),
        "bio": bio,
        "born_year": born_year
    }
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> dict:
    payload = {
        "name": name if name is not None else unique("Category"),
        "description": description
    }
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: Optional[str] = None, isbn: Optional[str] = None, price: float = 19.99,
                published_year: int = 2020, stock: int = 10, author_id: Optional[int] = None,
                category_id: Optional[int] = None) -> dict:
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    if isbn is None:
        # Generate a 13-digit ISBN: 978 (bookland) + 10 random digits
        random_part = str(uuid.uuid4().int)[:10]
        isbn = f"978{random_part:0>10}"[:13]
    payload = {
        "title": title if title is not None else unique("Book"),
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name: Optional[str] = None, customer_email: Optional[str] = None,
                 items: Optional[list] = None) -> dict:
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name if customer_name is not None else unique("Customer"),
        "customer_email": customer_email if customer_email is not None else f"{unique('email')}@test.com",
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
    payload = {
        "name": unique("Author"),
        "bio": "Test bio",
        "born_year": 1980
    }
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["bio"] == payload["bio"]
    assert data["born_year"] == payload["born_year"]

def test_create_author_missing_required_field():
    payload = {
        "bio": "Test bio"
    }
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
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": unique("ISBN")[:13],
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
    assert data["title"] == payload["title"]
    assert data["isbn"] == payload["isbn"]
    assert data["price"] == payload["price"]

def test_create_book_with_duplicate_isbn():
    book = create_book()
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": book["isbn"],
        "price": 30.00,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["deleted"] == False
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book():
    current_year = time.localtime().tm_year
    book = create_book(published_year=current_year)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 8
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.json()["stock"] == 8

def test_decrease_stock_below_zero():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.json()["stock"] == 5

def test_add_review_to_book():
    book = create_book()
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == payload["rating"]
    assert data["comment"] == payload["comment"]

def test_add_review_with_invalid_rating():
    book = create_book()
    payload = {
        "rating": 6,
        "comment": "Too high",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_order_with_sufficient_stock():
    book = create_book(stock=10)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.json()["stock"] == 7

def test_create_order_with_insufficient_stock():
    book = create_book(stock=2)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.json()["stock"] == 2

def test_update_order_status_valid_transition():
    order = create_order()
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    order = create_order()
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    order = create_order()
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]
    assert "items" in data

def test_get_invoice_for_pending_order():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_with_api_key():
    author = create_author()
    category = create_category()
    books = []
    for i in range(2):
        books.append({
            "title": unique("Book"),
            "isbn": unique("ISBN")[:13],
            "price": 20.0 + i,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    payload = {"books": books}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "total" in data
    assert data["total"] == 2
    assert data["created"] == 2
    assert len(data["results"]) == 2

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    books = [{
        "title": unique("Book"),
        "isbn": unique("ISBN")[:13],
        "price": 20.0,
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

def test_enable_maintenance_mode():
    headers = {"X-API-Key": "test-api-key"}
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] == True
    response = requests.get(f"{BASE_URL}/admin/maintenance", timeout=TIMEOUT)
    assert response.json()["maintenance_mode"] == True
    payload = {"enabled": False}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(title="Python Programming", price=30.0, author_id=author["id"], category_id=category["id"])
    book2 = create_book(title="Advanced Python", price=50.0, author_id=author["id"], category_id=category["id"])
    response = requests.get(f"{BASE_URL}/books?search=Python&min_price=25&max_price=40", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1
    titles = [item["title"] for item in data["items"]]
    assert "Python Programming" in titles
    assert "Advanced Python" not in titles