import pytest
import requests
import uuid
import time
import io

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    bio = "Test bio"
    born_year = 1980
    data = create_author(name=name, bio=bio, born_year=born_year)
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_name_validation():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data
    assert any("name" in str(item.get("loc")) for item in data["detail"])

def test_delete_author_with_books_conflict():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "associated book" in data["detail"].lower()

def test_create_category_duplicate_name_conflict():
    name = unique("category")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_create_book_success():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    price = 39.99
    published_year = 2021
    stock = 5
    data = create_book(author["id"], category["id"], title=title, isbn=isbn, price=price, published_year=published_year, stock=stock)
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == price
    assert data["published_year"] == published_year
    assert data["stock"] == stock
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_book_duplicate_isbn_conflict():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 25.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_create_book_nonexistent_author_404():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 25.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data
    assert "author" in data["detail"].lower()

def test_get_soft_deleted_book_gone():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data
    assert "deleted" in data["detail"].lower()

def test_get_book_with_etag_not_modified():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    etag = r.headers.get("ETag")
    assert etag is not None
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_update_book_etag_mismatch_precondition_failed():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    old_etag = r.headers.get("ETag")
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "Changed"}, timeout=30)
    r2 = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "Stale Update"}, headers={"If-Match": old_etag}, timeout=30)
    assert r2.status_code == 412
    data = r2.json()
    assert "detail" in data
    assert "precondition" in data["detail"].lower() or "modified" in data["detail"].lower()

def test_restore_not_deleted_book_bad_request():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "not deleted" in data["detail"].lower()

def test_apply_discount_new_book_rejected():
    author = create_author()
    category = create_category()
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "more than 1 year ago" in data["detail"].lower()

def test_apply_discount_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], published_year=2020)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5}, headers=AUTH_HEADERS, timeout=30)
        assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5}, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    data = r.json()
    assert "detail" in data
    assert "rate limit" in data["detail"].lower()

def test_update_stock_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "insufficient stock" in data["detail"].lower()

def test_upload_cover_unsupported_media_type():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    file_data = b"fake pdf content"
    files = {"file": ("test.pdf", io.BytesIO(file_data), "application/pdf")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data
    assert "unsupported" in data["detail"].lower() or "jpeg" in data["detail"].lower() or "png" in data["detail"].lower()

def test_upload_cover_file_too_large():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    file_data = b"\x00" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", io.BytesIO(file_data), "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 413
    data = r.json()
    assert "detail" in data
    assert "too large" in data["detail"].lower() or "2 mb" in data["detail"].lower()

def test_create_review_on_deleted_book_gone():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": "Reviewer",
        "comment": "Great"
    }, timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data
    assert "deleted" in data["detail"].lower()

def test_create_tag_duplicate_name_conflict():
    name = unique("tag")
    create_tag(name=name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()

def test_add_nonexistent_tag_to_book_not_found():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999999]}, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data
    assert "tag" in data["detail"].lower()

def test_create_order_insufficient_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Customer",
        "customer_email": "customer@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "insufficient stock" in data["detail"].lower()

def test_create_order_duplicate_book_items():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Customer",
        "customer_email": "customer@test.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "duplicate" in data["detail"].lower()

def test_update_order_status_invalid_transition():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data
    assert "transition" in data["detail"].lower() or "allowed" in data["detail"].lower()

def test_get_invoice_pending_order_forbidden():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    assert "pending" in data["detail"].lower() or "forbidden" in data["detail"].lower()

def test_add_item_to_non_pending_order_forbidden():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    author2 = create_author()
    category2 = create_category()
    book2 = create_book(author2["id"], category2["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders/{order['id']}/items", json={"book_id": book2["id"], "quantity": 1}, timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    assert "pending" in data["detail"].lower() or "forbidden" in data["detail"].lower()

def test_bulk_create_books_without_api_key_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "api key" in data["detail"].lower() or "unauthorized" in data["detail"].lower()

def test_bulk_create_books_partial_success():
    author = create_author()
    category = create_category()
    isbn1 = unique("isbn")[:13]
    isbn2 = unique("isbn")[:13]
    create_book(author["id"], category["id"], isbn=isbn1)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH_HEADERS, json={
        "books": [
            {
                "title": "New Book",
                "isbn": isbn2,
                "price": 20.0,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": "Duplicate Book",
                "isbn": isbn1,
                "price": 25.0,
                "published_year": 2020,
                "stock": 3,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }, timeout=30)
    assert r.status_code == 207
    data = r.json()
    assert "total" in data
    assert "created" in data
    assert "failed" in data
    assert "results" in data
    assert data["created"] == 1
    assert data["failed"] == 1

def test_create_export_without_api_key_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "api key" in data["detail"].lower() or "unauthorized" in data["detail"].lower()

def test_get_nonexistent_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent_job_id", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_toggle_maintenance_without_api_key_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data
    assert "api key" in data["detail"].lower() or "unauthorized" in data["detail"].lower()
    r2 = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH_HEADERS, json={"enabled": False}, timeout=30)