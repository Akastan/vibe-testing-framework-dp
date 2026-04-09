import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    headers = {"X-API-Key": API_KEY}
    r = requests.post(
        f"{BASE_URL}/authors", 
        json={"name": name, "bio": "bio", "born_year": 1990}, 
        headers=headers,
        timeout=TIMEOUT
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    headers = {"X-API-Key": API_KEY}
    r = requests.post(
        f"{BASE_URL}/categories", 
        json={"name": name, "description": "desc"}, 
        headers=headers,
        timeout=TIMEOUT
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")
    headers = {"X-API-Key": API_KEY}
    r = requests.post(
        f"{BASE_URL}/books", 
        json={
            "title": unique("book"), 
            "isbn": isbn, 
            "price": 100.0,
            "published_year": 2020, 
            "stock": 10, 
            "author_id": author_id, 
            "category_id": category_id
        }, 
        headers=headers,
        timeout=TIMEOUT
    )
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("auth"), "bio": "test", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "test"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_etag_304():
    auth = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{auth['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_412():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "new name"}, headers={"If-Match": '"wrong-etag"'}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_create_duplicate_category():
    name = unique("cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("isbn")[:13], "price": 10.0,
        "published_year": 2020, "author_id": auth['id'], "category_id": cat['id']
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_isbn():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": "123", "price": 10.0,
        "published_year": 2020, "author_id": auth['id'], "category_id": cat['id']
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_deleted_book_410():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_soft_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_discount_new_book_400():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'], isbn="1234567890123")
    # Published 2020, now 2026, so eligible for discount
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-100", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert tag['id'] in [t['id'] for t in r.json()['tags']]

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book['id'], "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book['id'], "quantity": 1}, {"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_invalid_status_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_invoice_forbidden_state():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": [
        {"title": unique("B1"), "isbn": unique("123")[:13], "price": 10, "published_year": 2020, "stock": 5, "author_id": auth['id'], "category_id": cat['id']},
        {"title": unique("B2"), "isbn": "123", "price": 10, "published_year": 2020, "stock": 5, "author_id": auth['id'], "category_id": cat['id']}
    ]}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'], isbn="1234567890")
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": "1234567890"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_poll_export_job_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    job_id = r.json()['job_id']
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=TIMEOUT)
    assert r.status_code == 202

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301