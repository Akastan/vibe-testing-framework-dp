# The main error is that ISBN must be exactly 13 characters, but unique() generates 8 random chars plus prefix. Also, some endpoints require X-API-Key header.
# Fix: Generate proper 13-digit ISBN and add API key header where needed.
import requests
import uuid
import time
import io

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("Book")
    if isbn is None:
        # Generate exactly 13 digits: prefix "978" + 10 random digits
        random_part = str(uuid.uuid4().int)[:10]
        isbn = "978" + random_part.zfill(10)
        isbn = isbn[:13]
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


def test_health_check_ok():
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

def test_create_author_missing_name():
    payload = {"bio": "No name"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_success():
    author = create_author()
    author_id = author["id"]
    response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_category_duplicate_name():
    category = create_category()
    payload = {"name": category["name"]}
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    book = create_book()
    assert "id" in book
    assert "title" in book
    assert "isbn" in book

def test_create_book_duplicate_isbn():
    book1 = create_book()
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": book1["isbn"],
        "price": 25.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_invalid_author_id():
    category = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": unique("isbn")[:13],
        "price": 25.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": 999999,
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_book_soft_deleted():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_delete_book_soft_delete():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.get(f"{BASE_URL}/books", params={"search": book["title"]}, timeout=30)
    data = response.json()
    assert data["total"] == 0

def test_restore_book_success():
    book = create_book()
    book_id = book["id"]
    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert response.status_code == 204
    response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["deleted_at"] is None

def test_apply_discount_new_book_error():
    book = create_book(published_year=2026)
    book_id = book["id"]
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_stock_insufficient():
    book = create_book(stock=5)
    book_id = book["id"]
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_cover_file_too_large():
    book = create_book()
    book_id = book["id"]
    img = Image.new('RGB', (2000, 2000), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=100)
    img_byte_arr.seek(0)
    files = {'file': ('large.jpg', img_byte_arr, 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=30)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_success():
    book = create_book()
    book_id = book["id"]
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("Reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book_id
    assert data["rating"] == 5

def test_create_tag_success():
    tag = create_tag()
    assert "id" in tag
    assert "name" in tag

def test_add_tags_to_book_success():
    book = create_book()
    book_id = book["id"]
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book_id}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert len(data["tags"]) == 2
    tag_ids = {t["id"] for t in data["tags"]}
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_insufficient_stock():
    book = create_book(stock=1)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [
            {"book_id": book["id"], "quantity": 5}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_order_duplicate_book_id():
    book = create_book(stock=10)
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_order_status_invalid_transition():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_resp.status_code == 201
    order = order_resp.json()
    order_id = order["id"]
    payload = {"status": "delivered"}
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_get_invoice_pending_order_forbidden():
    book = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_resp.status_code == 201
    order = order_resp.json()
    order_id = order["id"]
    response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_add_item_to_non_pending_order_forbidden():
    book1 = create_book(stock=10)
    book2 = create_book(stock=10)
    order_payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book1["id"], "quantity": 1}]
    }
    order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=30)
    assert order_resp.status_code == 201
    order = order_resp.json()
    order_id = order["id"]
    status_payload = {"status": "confirmed"}
    status_resp = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=status_payload, timeout=30)
    assert status_resp.status_code == 200
    item_payload = {"book_id": book2["id"], "quantity": 1}
    response = requests.post(f"{BASE_URL}/orders/{order_id}/items", json=item_payload, timeout=30)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

def test_bulk_create_books_partial_success():
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
            },
            {
                "title": unique("Book"),
                "isbn": "123",
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
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
    assert "created" in data
    assert "failed" in data
    assert "results" in data
    assert len(data["results"]) == 2

def test_bulk_create_books_missing_api_key():
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

def test_clone_book_duplicate_isbn():
    book = create_book()
    book_id = book["id"]
    payload = {
        "new_isbn": book["isbn"],
        "new_title": unique("Clone"),
        "stock": 5
    }
    response = requests.post(f"{BASE_URL}/books/{book_id}/clone", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_export_missing_api_key():
    response = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data

def test_get_export_job_not_found():
    response = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_toggle_maintenance_missing_api_key():
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, timeout=30)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    response = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)