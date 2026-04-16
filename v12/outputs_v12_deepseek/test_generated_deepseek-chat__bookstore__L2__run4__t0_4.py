import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
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

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
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

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
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
    bio = "A test bio"
    born_year = 1980
    payload = {"name": name, "bio": bio, "born_year": born_year}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name_422():
    payload = {"bio": "No name provided"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_existing_author():
    author = create_author()
    author_id = author["id"]
    response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["name"] == author["name"]

def test_get_author_not_found_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    author_id = author["id"]
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 404

def test_delete_author_with_books_409():
    author = create_author()
    author_id = author["id"]
    category = create_category()
    category_id = category["id"]
    book_payload = {
        "title": unique("Book"),
        "isbn": unique("isbn")[:13],
        "price": 25.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=30)
    assert response.status_code == 201
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 29.99,
        "published_year": 2021,
        "stock": 15,
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

def test_create_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    book1 = create_book(isbn=isbn, author_id=author["id"], category_id=category["id"])
    title2 = unique("Book2")
    payload = {
        "title": title2,
        "isbn": isbn,
        "price": 35.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_existing_book():
    book = create_book()
    book_id = book["id"]
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_410():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", [])
    book_ids = [b["id"] for b in items]
    assert book_id not in book_ids

def test_restore_soft_deleted_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == book["title"]
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book_id
    assert "original_price" in data
    assert "discounted_price" in data
    expected = round(book["price"] * (1 - 10.0 / 100), 2)
    assert data["discounted_price"] == expected

def test_apply_discount_to_new_book_400():
    current_year = time.localtime().tm_year
    book = create_book(published_year=current_year)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=7", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 12
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 12

def test_decrease_stock_below_zero_400():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 5

def test_create_review_for_book():
    book = create_book()
    book_id = book["id"]
    payload = {
        "rating": 4,
        "comment": "Great book!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book_id
    assert data["rating"] == 4
    assert data["reviewer_name"] == payload["reviewer_name"]

def test_create_tag_success():
    name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book():
    book = create_book()
    book_id = book["id"]
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book_id}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_sufficient_stock():
    book = create_book(stock=10)
    book_id = book["id"]
    initial_stock = book["stock"]
    quantity = 3
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book_id, "quantity": quantity}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book_id
    assert data["items"][0]["quantity"] == quantity
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == initial_stock - quantity

def test_create_order_insufficient_stock_400():
    book = create_book(stock=2)
    book_id = book["id"]
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [{"book_id": book_id, "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 2

def test_update_order_status_valid_transition():
    order = create_order()
    order_id = order["id"]
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"
    response = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_400():
    order = create_order()
    order_id = order["id"]
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"

def test_get_invoice_for_confirmed_order():
    order = create_order()
    order_id = order["id"]
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order_id
    assert "items" in data
    assert "subtotal" in data

def test_get_invoice_for_pending_order_403():
    order = create_order()
    order_id = order["id"]
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    isbn1 = unique("isbn")[:13]
    isbn2 = unique("isbn2")[:13]
    payload = {
        "books": [
            {
                "title": unique("Book1"),
                "isbn": isbn1,
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book2"),
                "isbn": isbn1,
                "price": 25.0,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book3"),
                "isbn": isbn2,
                "price": 30.0,
                "published_year": 2022,
                "stock": 7,
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
    assert data["total"] == 3
    assert "created" in data
    assert "failed" in data
    assert "results" in data
    assert len(data["results"]) == 3

def test_bulk_create_books_missing_api_key_401():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("Book"),
                "isbn": unique("isbn")[:13],
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
    book_id = book["id"]
    new_isbn = unique("newisbn")[:13]
    payload = {
        "new_isbn": new_isbn,
        "new_title": "Cloned Title",
        "stock": 8
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/clone", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["title"] == "Cloned Title"
    assert data["stock"] == 8
    assert data["author_id"] == book["author_id"]
    assert data["category_id"] == book["category_id"]
    assert data["price"] == book["price"]
    assert data["published_year"] == book["published_year"]

def test_start_book_export_job():
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=30)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    assert "created_at" in data