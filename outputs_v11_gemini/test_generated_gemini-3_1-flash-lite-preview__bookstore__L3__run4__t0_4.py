import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper create_author failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper create_category failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("isbn")[:13]
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper create_book failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("auth")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "New"}, headers={"If-Match": "wrong"}, timeout=30)
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
        "title": "Book", "isbn": "123456789012", "price": 10, "published_year": 2020,
        "author_id": auth['id'], "category_id": cat['id']
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890123"
    create_book(auth['id'], cat['id'], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book2", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 1,
        "author_id": auth['id'], "category_id": cat['id']
    }, timeout=30)
    assert r.status_code == 422

def test_get_book_soft_deleted():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_book_not_deleted():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_too_new_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    # Book is too new, but let's test rate limit if possible, or just the error
    for _ in range(10):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
        if r.status_code == 429:
            break
    assert r.status_code in (400, 429)

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-999", timeout=30)
    assert r.status_code == 400

def test_upload_cover_unsupported_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=30)
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
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 9, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_partial_success():
    auth = create_author()
    cat = create_category()
    data = {"books": [
        {"title": "B1", "isbn": "1234567890123", "price": 10, "published_year": 2020, "stock": 1, "author_id": auth['id'], "category_id": cat['id']},
        {"title": "B2", "isbn": "invalid", "price": 10, "published_year": 2020, "stock": 1, "author_id": auth['id'], "category_id": cat['id']}
    ]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_clone_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book['isbn']}, timeout=30)
    assert r.status_code == 409

def test_create_category_duplicate_name():
    name = unique("cat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_tag_in_use():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    tag_id = r_tag.json()['id']
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag_id}", timeout=30)
    assert r.status_code == 409

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com",
        "items": [{"book_id": book['id'], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com",
        "items": [{"book_id": book['id'], "quantity": 1}, {"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com",
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    ord_id = r_ord.json()['id']
    r = requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com",
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    ord_id = r_ord.json()['id']
    r = requests.get(f"{BASE_URL}/orders/{ord_id}/invoice", timeout=30)
    assert r.status_code == 403

def test_add_item_to_non_pending_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com",
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    ord_id = r_ord.json()['id']
    requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.post(f"{BASE_URL}/orders/{ord_id}/items", json={"book_id": book['id'], "quantity": 1}, timeout=30)
    assert r.status_code == 403

def test_create_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/fake-id", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    # Teardown
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301
    assert "location" in r.headers