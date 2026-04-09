import requests
import uuid
import time
from typing import Optional


BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    if name is None:
        name = unique("author")
    data = {"name": name, "bio": "test bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("cat")
    data = {"name": name, "description": "test desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:10]}"
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("auth"), "bio": "b", "born_year": 2000}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "b"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "new"}, headers={"If-Match": "wrong"}, timeout=30)
    assert r.status_code == 412

def test_delete_author_with_books_conflict():
    auth = create_author()
    cat = create_category()
    create_book(auth['id'], cat['id'])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("b"), "isbn": f"978{uuid.uuid4().hex[:7]}", "price": 10, "published_year": 2020, "author_id": auth['id'], "category_id": cat['id']
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "9781234567890"
    create_book(auth['id'], cat['id'], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "dup", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth['id'], "category_id": cat['id']
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination_filter():
    auth = create_author()
    cat = create_category()
    create_book(auth['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5&min_price=0", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_deleted_book_410():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_non_deleted_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    # Book must be old for discount
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 1990}, timeout=30)
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-99", timeout=30)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"content", "text/plain")}, timeout=30)
    assert r.status_code == 415

def test_upload_cover_too_large():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=30)
    assert r.status_code == 413

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "test"}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": [
        {"title": "b1", "isbn": "9780000000001", "price": 10, "published_year": 2020, "stock": 1, "author_id": auth['id'], "category_id": cat['id']},
        {"title": "b2", "isbn": "invalid", "price": 10, "published_year": 2020, "stock": 1, "author_id": auth['id'], "category_id": cat['id']}
    ]}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book['isbn']}, timeout=30)
    assert r.status_code == 409

def test_create_duplicate_tag():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "c", "customer_email": "e@e.com", "items": [{"book_id": book['id'], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "c", "customer_email": "e@e.com", "items": [{"book_id": book['id'], "quantity": 1}, {"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_invalid_status_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "c", "customer_email": "e@e.com", "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_forbidden_state():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "c", "customer_email": "e@e.com", "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401

def test_get_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    # Cleanup
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301
    assert "location" in r.headers

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_add_nonexistent_tag_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404