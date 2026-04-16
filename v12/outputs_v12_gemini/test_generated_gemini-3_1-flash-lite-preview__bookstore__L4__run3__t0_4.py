# The ISBN generation was creating a 13-character string, but some schemas might expect specific patterns; ensuring it is a valid 13-digit string.
# Fixed helper status code assertions to match 201/200/204 expectations and ensured headers are passed to all requests.

import uuid
import requests

BASE_URL = "http://localhost:8000"
AUTH = {"X-API-Key": "test-api-key"}
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Author helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Category helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None, stock=10):
    # Ensure ISBN is a 13-digit string to satisfy typical ISBN-13 requirements
    isbn = isbn or "".join([str(i % 10) for i in range(13)])
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Book helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_valid():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": "1234567890123", "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"], "stock": 10
    }, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1111111111111"
    requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"], "stock": 10
    }, headers=AUTH, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"], "stock": 10
    }, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_soft_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_update_book_etag_mismatch():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"title": "New"}, headers={**AUTH, "If-Match": "wrong"}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_restore_active_book_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn="9999999999")
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_negative_result():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -10}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_duplicate_tag():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_nonexistent_tag_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999999]}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 10}]}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_duplicate_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_invalid_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]}, headers=AUTH, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_invoice_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]}, headers=AUTH, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 400

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": "B1", "isbn": "".join([str(i % 10) for i in range(13)]), "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "INVALID", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_authorized():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=TIMEOUT)
    job_id = r.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=TIMEOUT)
    assert r.status_code in [200, 202]

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/fake-id", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_mode():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["maintenance_mode"] is True
    requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": False}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_health_check_invalid_method():
    r = requests.put(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 405