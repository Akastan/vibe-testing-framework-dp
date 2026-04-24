# The main error is that ISBN must be exactly 13 characters, but unique() generates 8 random chars plus prefix, making it too long. Also, some endpoints require API key headers.
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
        isbn = uuid.uuid4().hex[:13]  # Exactly 13 characters, no prefix
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
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    payload = {"name": name}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
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

def test_create_author_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
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

def test_get_nonexistent_author():
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

def test_delete_author_with_associated_books():
    author = create_author()
    author_id = author["id"]
    category = create_category()
    category_id = category["id"]
    book = create_book(author_id=author_id, category_id=category_id)
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    author = create_author()
    category = create_category()
    title = unique("Book")
    isbn = unique("ISBN")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 25.50,
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

def test_create_book_with_duplicate_isbn():
    book = create_book()
    isbn = book["isbn"]
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 30.0,
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

def test_get_soft_deleted_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_soft_delete_existing_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", headers={"X-API-Key": API_KEY}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["is_deleted"] == False
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    book_id = book["id"]
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book(published_year=2020)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
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
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=3", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 8
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.json()["stock"] == 8

def test_decrease_stock_below_zero():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.json()["stock"] == 5

def test_add_review_to_book():
    book = create_book()
    book_id = book["id"]
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": "Test Reviewer"
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book_id
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Test Reviewer"

def test_create_tag_with_unique_name():
    name = unique("Tag")
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert "id" in data

def test_create_tag_with_duplicate_name():
    tag = create_tag()
    name = tag["name"]
    response = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

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

def test_create_order_with_sufficient_stock():
    book1 = create_book(stock=10)
    book2 = create_book(stock=5)
    payload = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [
            {"book_id": book1["id"], "quantity": 2},
            {"book_id": book2["id"], "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == "John Doe"
    assert data["status"] == "pending"
    assert len(data["items"]) == 2
    response = requests.get(f"{BASE_URL}/books/{book1['id']}", timeout=30)
    assert response.json()["stock"] == 8
    response = requests.get(f"{BASE_URL}/books/{book2['id']}", timeout=30)
    assert response.json()["stock"] == 4

def test_create_order_with_insufficient_stock():
    book = create_book(stock=2)
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
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.json()["stock"] == 2

def test_update_order_status_valid_transition():
    book = create_book(stock=10)
    payload = {
        "customer_name": "Alice",
        "customer_email": "alice@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30).json()
    order_id = order["id"]
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    book = create_book(stock=10)
    payload = {
        "customer_name": "Bob",
        "customer_email": "bob@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30).json()
    order_id = order["id"]
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    book = create_book(stock=10)
    payload = {
        "customer_name": "Charlie",
        "customer_email": "charlie@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30).json()
    order_id = order["id"]
    requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=30)
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order_id
    assert data["status"] == "confirmed"
    assert "items" in data
    assert len(data["items"]) == 1

def test_get_invoice_for_pending_order():
    book = create_book(stock=10)
    payload = {
        "customer_name": "David",
        "customer_email": "david@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30).json()
    order_id = order["id"]
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_with_api_key():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("BulkBook"),
                "isbn": unique("ISBN")[:13],
                "price": 15.99,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("BulkBook2"),
                "isbn": unique("ISBN2")[:13],
                "price": 22.50,
                "published_year": 2021,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "total" in data
    assert data["total"] == 2
    assert data["created"] == 2
    assert data["failed"] == 0

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    payload = {
        "books": [
            {
                "title": unique("BulkBook"),
                "isbn": unique("ISBN")[:13],
                "price": 15.99,
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