import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"X-API-Key": "test-api-key"}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Desc"}, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": isbn, "price": 100.0,
        "published_year": 2020, "stock": 10, "author_id": author_id, "category_id": category_id
    }, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_existing_author():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == auth["id"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_duplicate_category():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/categories", json={"name": cat["name"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_isbn():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "123", "price": 10.0, "published_year": 2000,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_missing_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "12345678901", "price": 10.0, "published_year": 2000,
        "author_id": 99999, "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_soft_deleted_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_soft_delete_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_active_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_new_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_invalid_percent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 99.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-100", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_invalid_file_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415

def test_upload_file_too_large():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    large_data = b"0" * (3 * 1024 * 1024)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.png", large_data, "image/png")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_rate_limit():
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers=HEADERS, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 429

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "E", "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "E", "items": [
            {"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}
        ]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "E", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_pending_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "E", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/invalid-job", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_nonexistent_tag():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [99999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_author_etag_mismatch():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "New"}, headers={"If-Match": '"wrong-etag"'}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_clone_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book["isbn"]}, timeout=TIMEOUT)
    assert r.status_code == 409