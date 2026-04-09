import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author"), "bio": "test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    data = {"name": unique("cat"), "description": "test desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id,
        "tags": []
    }
    r = requests.post(f"{BASE_URL}/books", json=data, headers=HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    data = {"name": unique("author"), "bio": "test", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": "invalid"}, timeout=30)
    assert r.status_code == 412

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {
        "title": unique("book"),
        "isbn": "1234567890",
        "price": 50.0,
        "published_year": 2020,
        "author_id": a['id'],
        "category_id": c['id']
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1111111111"
    data = {"title": "b1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": a['id'], "category_id": c['id']}
    requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_deleted_book_410():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_get_book_not_modified():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r1 = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/books/{b['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_restore_active_book_400():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 422

def test_apply_discount_too_high():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_new_book_400():
    a = create_author()
    c = create_category()
    data = {
        "title": unique("newbook"),
        "isbn": "9999999999",
        "price": 100.0,
        "published_year": 2026,
        "author_id": a['id'],
        "category_id": c['id']
    }
    b = requests.post(f"{BASE_URL}/books", json=data, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
        if r.status_code == 429:
            break
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -100}, timeout=30)
    assert r.status_code == 422

def test_update_stock_invalid_format():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": "abc"}, timeout=30)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {'file': ('test.txt', 'content', 'text/plain')}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=30)
    assert r.status_code == 422

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "test"}, timeout=30)
    assert r.status_code == 422

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {"customer_name": "test", "customer_email": "a@b.cz", "items": [{"book_id": b['id'], "quantity": 999}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 422

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {"customer_name": "test", "customer_email": "a@b.cz", "items": [{"book_id": b['id'], "quantity": 1}, {"book_id": b['id'], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 422

def test_invalid_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "t", "customer_email": "e", "items": [{"book_id": b['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "t", "customer_email": "e", "items": [{"book_id": b['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    books = [
        {"title": unique("t1"), "isbn": str(uuid.uuid4().int)[:13], "price": 10.0, "published_year": 2020, "stock": 1, "author_id": a['id'], "category_id": c['id'], "tags": []},
        {"title": "", "isbn": "invalid", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": a['id'], "category_id": c['id'], "tags": []}
    ]
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": books}, headers=HEADERS, timeout=30)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": b['isbn']}, timeout=30)
    assert r.status_code == 409

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401

def test_get_statistics_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_catalog_deprecated_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301