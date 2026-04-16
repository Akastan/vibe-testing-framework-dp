# The ISBN field likely requires a specific format (e.g., 13 digits) or the payload structure is missing required fields. 
# I am ensuring ISBN is numeric-only and adding a unique identifier to all string fields to avoid validation errors.

import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    # Ensure all fields match schema requirements
    payload = {
        "name": get_unique("Author"), 
        "bio": "Test bio", 
        "born_year": 1990
    }
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    # Ensure all fields match schema requirements
    payload = {
        "name": get_unique("Cat"), 
        "description": "Test description"
    }
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book():
    # Ensure ISBN is a string of digits to satisfy potential Pydantic constraints
    author = create_author()
    category = create_category()
    payload = {
        "title": get_unique("Book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": 100.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    payload = {"name": get_unique("Author"), "bio": "Bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_success():
    author = create_author()
    cat = create_category()
    payload = {"title": "Test", "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    r = requests.post(f"{BASE_URL}/books", json={"price": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_deleted_book_gone():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_get_book_etag_not_modified():
    book = create_book()
    r1 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_active_book_error():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    book = create_book()
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_apply_discount_invalid_value():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 150.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    book = create_book()
    files = {"file": ("test.txt", b"hello", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_upload_cover_too_large():
    book = create_book()
    files = {"file": ("test.jpg", b"0" * 3 * 1024 * 1024, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    for _ in range(4):
        r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": "test"}, json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_create_order_success():
    book = create_book()
    payload = {"customer_name": "Test", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_statistics_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_invalid_rating():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_add_tags_invalid_format():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": "not_an_array"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_empty_array():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422