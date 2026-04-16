# The ISBN generation was static/non-unique causing 422 errors on repeated runs; fixed to use random digits. 
# Added missing headers and ensured consistent status code assertions as per requirements.

import requests
import uuid
import random

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique("Author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]

def create_category():
    name = get_unique("Cat")
    payload = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]

def create_book(author_id, category_id):
    # Generate a unique 13-digit ISBN string to avoid Pydantic/Database uniqueness conflicts
    isbn = "".join([str(random.randint(0, 9)) for _ in range(13)])
    payload = {
        "title": get_unique("Book"), 
        "isbn": isbn, 
        "price": 100.0,
        "published_year": 2020, 
        "stock": 10, 
        "author_id": author_id, 
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]


def test_create_author_success():
    name = get_unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_duplicate():
    name = get_unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    aid, cid = create_author(), create_category()
    isbn = "1234567890" + uuid.uuid4().hex[:3]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_isbn():
    aid, cid = create_author(), create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "123", "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_soft_deleted_book():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_new_book():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_rate_limit():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_insufficient():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.patch(f"{BASE_URL}/books/{bid}/stock", params={"quantity": -100}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.jpg", b"0" * 3000000)}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_wrong_type():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_invalid_rating():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/reviews", json={"rating": 10, "comment": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_nonexistent_tag():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/tags", json={"tag_ids": [999999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_order_insufficient_stock():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": bid, "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_duplicate_items():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": bid, "quantity": 1}, {"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid_transition():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_forbidden_state():
    aid, cid = create_author(), create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Name", "customer_email": "a@b.cz", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{oid}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    aid, cid = create_author(), create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": "test-api-key"}, json={"books": [
        {"title": get_unique("B1"), "isbn": "1234567890123", "price": 10, "published_year": 2020, "stock": 1, "author_id": aid, "category_id": cid},
        {"title": get_unique("B2"), "isbn": "123", "price": 10, "published_year": 2020, "stock": 1, "author_id": aid, "category_id": cid}
    ]}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": False}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200