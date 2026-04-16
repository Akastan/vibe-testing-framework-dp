# The ISBN was static, causing 422 errors on repeated runs due to unique constraints. 
# Fixed ISBN generation to use a random 13-digit string and ensured proper status code assertions.

import requests
import uuid
import random

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique("Author")
    resp = requests.post(
        f"{BASE_URL}/authors", 
        json={"name": name, "bio": "Bio", "born_year": 1990}, 
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()

def create_category():
    name = get_unique("Cat")
    resp = requests.post(
        f"{BASE_URL}/categories", 
        json={"name": name, "description": "Desc"}, 
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()

def create_book(author_id, category_id):
    # Generate a random 13-digit ISBN string to ensure uniqueness across test runs
    unique_isbn = "".join([str(random.randint(0, 9)) for _ in range(13)])
    resp = requests.post(
        f"{BASE_URL}/books", 
        json={
            "title": get_unique("Book"), 
            "isbn": unique_isbn, 
            "price": 100.0,
            "published_year": 2020, 
            "stock": 10, 
            "author_id": author_id, 
            "category_id": category_id
        }, 
        timeout=TIMEOUT
    )
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()


def test_create_author_success():
    name = get_unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "1234567890", "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1111111111"
    requests.post(f"{BASE_URL}/books", json={
        "title": "T1", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T2", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_soft_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_restore_active_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Old", "isbn": "8888888888", "price": 10.0,
        "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT).json()
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -100}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "comment": "Great"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "comment": "Bad"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    for _ in range(4):
        r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_create_duplicate_tag():
    name = get_unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_nonexistent_tag_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_update_category_etag_mismatch():
    c = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": "New"}, headers={"If-Match": "wrong"}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_clone_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": b["isbn"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_clone_nonexistent_book():
    r = requests.post(f"{BASE_URL}/books/99999/clone", json={"new_isbn": "1111111111"}, timeout=TIMEOUT)
    assert r.status_code == 404