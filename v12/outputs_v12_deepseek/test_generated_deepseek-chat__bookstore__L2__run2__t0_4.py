# The main error is that ISBN must be exactly 13 characters, but the helper generates 12 characters (978 + 9 hex digits = 12). Also, some endpoints require X-API-Key header.
import requests
import uuid
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

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
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: str = None, description: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: str = None, isbn: str = None, price: float = 19.99,
                published_year: int = 2020, stock: int = 10,
                author_id: int = None, category_id: int = None) -> Dict[str, Any]:
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:10]}"  # Fixed: 978 + 10 hex digits = 13 characters
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
    headers = {"X-API-Key": "test"}  # Add required API key header
    response = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name: str = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Tag")
    payload = {"name": name}
    headers = {"X-API-Key": "test"}  # Add required API key header
    response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("Author")
    bio = "A prolific writer."
    born_year = 1975
    response = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
    author = create_author()
    author_id = author["id"]
    response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    author_id = author["id"]
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert get_response.status_code == 404

def test_delete_author_with_books_conflict():
    author = create_author()
    author_id = author["id"]
    category = create_category()
    category_id = category["id"]
    isbn = f"978{uuid.uuid4().hex[:9]}"
    book_payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 25.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author_id,
        "category_id": category_id
    }
    requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2022,
        "stock": 15,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2022,
        "stock": 15,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response1 = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response1.status_code == 201
    payload["title"] = unique("Book2")
    response2 = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response2.status_code == 409
    data = response2.json()
    assert "detail" in data

def test_get_existing_book():
    book = create_book()
    book_id = book["id"]
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    book_id = book["id"]
    delete_response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_response.status_code == 410
    data = get_response.json()
    assert "detail" in data

def test_soft_delete_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    book_id = book["id"]
    delete_response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book_id
    assert data["deleted_at"] is None
    get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    book_id = book["id"]
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book_id
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book():
    current_year = time.localtime().tm_year
    book = create_book(published_year=current_year)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    book = create_book(stock=10)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15
    get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_response.json()["stock"] == 15

def test_decrease_stock_below_zero():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_response.json()["stock"] == 5

def test_create_review_for_book():
    book = create_book()
    book_id = book["id"]
    payload = {
        "rating": 5,
        "comment": "Excellent read!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book_id
    assert data["rating"] == 5

def test_create_tag_success():
    name = unique("Tag")
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_tag_duplicate_name():
    tag = create_tag()
    name = tag["name"]
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_add_tags_to_book():
    book = create_book()
    book_id = book["id"]
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book_id}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_sufficient_stock():
    book1 = create_book(stock=10)
    book2 = create_book(stock=5)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [
            {"book_id": book1["id"], "quantity": 2},
            {"book_id": book2["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert len(data["items"]) == 2
    get_book1 = requests.get(f"{BASE_URL}/books/{book1['id']}", timeout=TIMEOUT).json()
    get_book2 = requests.get(f"{BASE_URL}/books/{book2['id']}", timeout=TIMEOUT).json()
    assert get_book1["stock"] == 8
    assert get_book2["stock"] == 4

def test_create_order_insufficient_stock():
    book = create_book(stock=2)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    get_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert get_book["stock"] == 2

def test_update_order_status_valid_transition():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT).json()
    order_id = order["id"]
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT).json()
    order_id = order["id"]
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT).json()
    order_id = order["id"]
    requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order_id
    assert data["status"] == "confirmed"

def test_get_invoice_for_pending_order():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('customer')}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT).json()
    order_id = order["id"]
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    isbn1 = f"978{uuid.uuid4().hex[:9]}"
    isbn2 = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("Book1"),
                "isbn": isbn1,
                "price": 20.0,
                "published_year": 2021,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book2"),
                "isbn": isbn1,
                "price": 25.0,
                "published_year": 2022,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book3"),
                "isbn": isbn2,
                "price": 30.0,
                "published_year": 2023,
                "stock": 7,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 207
    data = response.json()
    assert "total" in data
    assert data["total"] == 3
    assert data["created"] == 2
    assert data["failed"] == 1
    assert len(data["results"]) == 3

def test_bulk_create_books_missing_api_key():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("Book"),
                "isbn": isbn,
                "price": 20.0,
                "published_year": 2021,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data