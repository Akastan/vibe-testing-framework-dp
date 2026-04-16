import requests
import uuid
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: str = None, bio: str = None, born_year: int = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: str = None, isbn: str = None, price: float = 19.99,
                published_year: int = 2020, stock: int = 10,
                author_id: int = None, category_id: int = None) -> Dict[str, Any]:
    if title is None:
        title = unique("Book")
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
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name: str = None, customer_email: str = None,
                 items: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    if customer_name is None:
        customer_name = unique("Customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
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
    bio = "Test bio"
    born_year = 1980
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
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
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book",
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]

def test_create_book_duplicate_isbn():
    book = create_book()
    author = create_author()
    category = create_category()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Another Book",
        "isbn": book["isbn"],
        "price": 39.99,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    items = [b for b in data["items"] if b["id"] == book["id"]]
    assert len(items) == 0

def test_restore_soft_deleted_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book():
    current_year = time.localtime().tm_year
    book = create_book(published_year=current_year)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 8

def test_decrease_stock_below_zero():
    book = create_book(stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_for_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": "Tester"
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_review_invalid_rating():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 6,
        "reviewer_name": "Tester"
    }, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_order_sufficient_stock():
    book = create_book(stock=10)
    response = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = response.json()
    assert updated_book["stock"] == 7

def test_create_order_insufficient_stock():
    book = create_book(stock=2)
    response = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jane Doe",
        "customer_email": "jane@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    order = create_order()
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    order = create_order()
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    order = create_order()
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order():
    order = create_order()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    isbn1 = unique("isbn")[:13]
    isbn2 = unique("isbn")[:13]
    payload = {
        "books": [
            {
                "title": "Book One",
                "isbn": isbn1,
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": "Book Two",
                "isbn": isbn1,
                "price": 25.0,
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
    assert "created" in data
    assert "failed" in data
    assert data["total"] == 2

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    payload = {
        "books": [
            {
                "title": "Book One",
                "isbn": isbn,
                "price": 20.0,
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

def test_clone_book_with_new_isbn():
    book = create_book()
    new_isbn = unique("isbn")[:13]
    response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={
        "new_isbn": new_isbn,
        "new_title": "Cloned Book",
        "stock": 7
    }, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["title"] == "Cloned Book"
    assert data["stock"] == 7

def test_start_book_export_with_api_key():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=30)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"