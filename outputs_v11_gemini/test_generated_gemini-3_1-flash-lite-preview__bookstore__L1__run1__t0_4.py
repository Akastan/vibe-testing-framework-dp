import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    payload = {"name": unique("author"), "bio": "test bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    payload = {"name": unique("cat"), "description": "test desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    payload = {
        "title": unique("book"),
        "isbn": isbn or unique("1234567890")[:13],
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new name"}, headers={"If-Match": "invalid-etag"}, timeout=30)
    assert r.status_code == 412

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": "1234567890", "price": 10.0, "published_year": 2020, "author_id": a['id'], "category_id": c['id']
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1234567890"
    create_book(a['id'], c['id'], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book2", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": a['id'], "category_id": c['id']
    }, timeout=30)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=30)
    assert r.status_code == 422

def test_get_book_gone():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == b['id']

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 409

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 200
    assert "price" in r.json()

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    payload = {
        "title": "New Book", "isbn": "9876543210", "price": 100.0, "published_year": 2026, "author_id": a['id'], "category_id": c['id']
    }
    b = requests.post(f"{BASE_URL}/books", json=payload, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 429

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.put(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.put(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -20}, timeout=30)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {'file': ('test.txt', 'content', 'text/plain')}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=30)
    assert r.status_code == 400

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {'file': ('test.jpg', 'a' * 2100000, 'image/jpeg')}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=30)
    assert r.status_code == 413

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 422

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.com", "items": [{"book_id": b['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.com", "items": [{"book_id": b['id'], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.com", "items": [{"book_id": b['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_forbidden():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    headers = {"X-API-Key": API_KEY}
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.com", "items": [{"book_id": b['id'], "quantity": 1}]
    }, headers=headers, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", headers=headers, timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    payload = {"books": [
        {"title": unique("B1"), "isbn": unique("111")[:13], "price": 10, "published_year": 2020, "stock": 1, "author_id": a['id'], "category_id": c['id']},
        {"title": unique("B2"), "isbn": "invalid", "price": 10, "published_year": 2020, "stock": 1, "author_id": a['id'], "category_id": c['id']}
    ]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    job_id = r.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r.status_code == 202

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    # Teardown
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_maintenance_access_denied():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401