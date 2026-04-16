# The main error is that ISBN must be exactly 13 digits, but unique("978") generates strings like "978_abc12345" which is too long. Need to generate valid 13-digit ISBNs.
# Also, some endpoints require X-API-Key header for authentication, which helpers are missing.

import pytest
import requests
import uuid
import io

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-api-key"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    data = {"name": unique("Category"), "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id, category_id, **kwargs):
    # Generate valid 13-digit ISBN: start with 978 and fill with random digits
    isbn_base = uuid.uuid4().hex[:9]  # 9 hex chars = up to 9 digits
    isbn_digits = ''.join([str(int(c, 16) % 10) for c in isbn_base])  # Convert to decimal digits
    isbn = "978" + isbn_digits.zfill(10)[:10]  # Ensure exactly 13 digits total
    
    data = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    data.update(kwargs)
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    data = {"name": unique("Tag")}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/tags", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_success():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["name"] == data["name"]
    assert body["bio"] == data["bio"]
    assert body["born_year"] == data["born_year"]

def test_create_author_missing_name_422():
    data = {"bio": "Bio"}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body

def test_get_author_by_id_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == author["id"]
    assert body["name"] == author["name"]

def test_get_author_not_found_404():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body

def test_delete_author_without_books_success():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 404

def test_delete_author_with_books_conflict_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 409
    body = response.json()
    assert "detail" in body

def test_create_book_success():
    author = create_author()
    category = create_category()
    data = {
        "title": unique("Book"),
        "isbn": unique("978"),
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["title"] == data["title"]
    assert body["isbn"] == data["isbn"]
    assert body["author_id"] == author["id"]
    assert body["category_id"] == category["id"]

def test_create_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn="9781234567890")
    data = {
        "title": unique("Book2"),
        "isbn": "9781234567890",
        "price": 30.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert response.status_code == 409
    body = response.json()
    assert "detail" in body

def test_get_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == book["id"]
    assert body["title"] == book["title"]

def test_get_soft_deleted_book_gone_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410
    body = get_response.json()
    assert "detail" in body

def test_soft_delete_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_restore_soft_deleted_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    body = restore_response.json()
    assert body["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_restore_not_deleted_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body

def test_apply_discount_to_old_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    data = {"discount_percent": 10.0}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert "book_id" in body
    assert body["book_id"] == book["id"]
    assert "discounted_price" in body
    assert body["discounted_price"] == book["price"] * (1 - data["discount_percent"] / 100)

def test_apply_discount_to_new_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2026)
    data = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=data, timeout=TIMEOUT)
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body

def test_increase_stock_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert body["stock"] == 15

def test_decrease_stock_below_zero_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body

def test_upload_valid_cover_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    files = {'file': ('cover.jpg', img_bytes, 'image/jpeg')}
    headers = {"X-API-Key": "test-api-key"}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert "book_id" in body
    assert body["book_id"] == book["id"]
    assert "filename" in body

def test_upload_cover_file_too_large_413():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    large_data = b'x' * (2 * 1024 * 1024 + 1)
    files = {'file': ('large.jpg', large_data, 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413
    body = response.json()
    assert "detail" in body

def test_create_review_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    data = {"rating": 5, "comment": "Great!", "reviewer_name": unique("Reviewer")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["book_id"] == book["id"]
    assert body["rating"] == data["rating"]

def test_create_tag_success():
    data = {"name": unique("Tag")}
    response = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["name"] == data["name"]

def test_add_tags_to_book_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    tag1 = create_tag()
    tag2 = create_tag()
    data = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=data, timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert "tags" in body
    tag_ids = [t["id"] for t in body["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 3}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["total_price"] == book["price"] * 3
    assert body["status"] == "pending"
    get_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert get_book["stock"] == 7

def test_create_order_insufficient_stock_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body

def test_update_order_status_to_cancelled_returns_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order_data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 4}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT).json()
    book_after_order = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_after_order["stock"] == 6
    status_data = {"status": "cancelled"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_data, timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    book_after_cancel = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_after_cancel["stock"] == 10

def test_update_order_status_invalid_transition_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT).json()
    status_data = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=status_data, timeout=TIMEOUT)
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body

def test_get_invoice_for_confirmed_order_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert "invoice_number" in body
    assert body["order_id"] == order["id"]
    assert body["subtotal"] == book["price"] * 2

def test_get_invoice_for_pending_order_forbidden_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    order_data = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT).json()
    response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert response.status_code == 403
    body = response.json()
    assert "detail" in body

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    unique_isbn = unique("978")
    books = [
        {
            "title": unique("Book"),
            "isbn": unique_isbn,
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        },
        {
            "title": unique("Book2"),
            "isbn": unique_isbn,
            "price": 20.0,
            "published_year": 2021,
            "stock": 3,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    data = {"books": books}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/bulk", json=data, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 207
    body = response.json()
    assert "total" in body
    assert "created" in body
    assert "failed" in body
    assert "results" in body
    assert body["failed"] >= 1