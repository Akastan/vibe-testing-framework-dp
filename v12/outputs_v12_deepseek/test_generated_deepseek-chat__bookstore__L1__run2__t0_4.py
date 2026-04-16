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

def create_order(book_id, quantity=1):
    customer_name = unique("Customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book_id, "quantity": quantity}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200

def test_create_author_successfully():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_name_returns_422():
    payload = {"bio": "Test bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
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

def test_get_nonexistent_author_returns_404():
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

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
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

def test_create_book_duplicate_isbn_returns_409():
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
    response1 = requests.post(f"{BASE_URL}/books", json=payload1, timeout=30)
    assert response1.status_code == 201
    payload2 = {
        "title": unique("Book2"),
        "isbn": isbn,
        "price": 20.0,
        "published_year": 2021,
        "stock": 2,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=30)
    assert response2.status_code == 409
    data = response2.json()
    assert "detail" in data

def test_get_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
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
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 410

def test_delete_already_deleted_book_returns_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete1 = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete1.status_code == 204
    delete2 = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete2.status_code == 410
    data = delete2.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert get_response.status_code == 200

def test_restore_not_deleted_book_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    payload = {"discount_percent": 10.0}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    assert data["discounted_price"] == round(book["price"] * 0.9, 2)

def test_apply_discount_to_new_book_returns_400():
    author = create_author()
    category = create_category()
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], published_year=current_year)
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_add_review_to_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_add_review_to_deleted_book_returns_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_create_order_with_sufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    initial_stock = book["stock"]
    order = create_order(book["id"], quantity=3)
    assert order["total_price"] == book["price"] * 3
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = response.json()
    assert updated_book["stock"] == initial_stock - 3

def test_create_order_insufficient_stock_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    customer_name = unique("Customer")
    payload = {
        "customer_name": customer_name,
        "customer_email": f"{customer_name}@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    payload = {"status": "confirmed"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    confirm_payload = {"status": "confirmed"}
    confirm_response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=confirm_payload, timeout=30)
    assert confirm_response.status_code == 200
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order_returns_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order(book["id"], quantity=1)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_returns_207():
    author = create_author()
    category = create_category()
    isbn1 = f"978{uuid.uuid4().hex[:9]}"
    isbn2 = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("Book1"),
                "isbn": isbn1,
                "price": 10.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book2"),
                "isbn": isbn1,
                "price": 20.0,
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
                "stock": 2,
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
    assert "created" in data
    assert "failed" in data
    assert "results" in data

def test_bulk_create_books_without_api_key_returns_401():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "books": [
            {
                "title": unique("Book"),
                "isbn": isbn,
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

def test_enable_maintenance_mode_with_api_key():
    headers = {"X-API-Key": API_KEY}
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance_mode"] is True
    disable_payload = {"enabled": False}
    disable_response = requests.post(f"{BASE_URL}/admin/maintenance", json=disable_payload, headers=headers, timeout=30)
    assert disable_response.status_code == 200