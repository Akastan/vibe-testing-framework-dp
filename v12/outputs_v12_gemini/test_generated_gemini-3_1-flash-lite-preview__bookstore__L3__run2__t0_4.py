import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Failed to create author: {resp.text}"
    return resp.json()["id"]

def create_category():
    name = get_unique("Cat")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Desc"}, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Failed to create category: {resp.text}"
    return resp.json()["id"]

def create_book(author_id, category_id):
    isbn = uuid.uuid4().hex[:13]
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": get_unique("Book"), "isbn": isbn, "price": 100.0,
        "published_year": 2020, "stock": 10, "author_id": author_id, "category_id": category_id
    }, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Failed to create book: {resp.text}"
    return resp.json()["id"]

def test_create_author_success():
    name = get_unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_create_author_invalid_name():
    resp = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "Bio"}, timeout=TIMEOUT)
    assert resp.status_code == 422
    assert "detail" in resp.json()

def test_delete_author_with_books_conflict():
    aid = create_author()
    cid = create_category()
    create_book(aid, cid)
    resp = requests.delete(f"{BASE_URL}/authors/{aid}", timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_book_success():
    aid = create_author()
    cid = create_category()
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": uuid.uuid4().hex[:10], "price": 50.0,
        "published_year": 2020, "stock": 5, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_create_book_duplicate_isbn():
    aid = create_author()
    cid = create_category()
    isbn = uuid.uuid4().hex[:10]
    data = {"title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_get_soft_deleted_book_gone():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    resp = requests.get(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert resp.status_code == 410

def test_get_nonexistent_book():
    resp = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_restore_not_deleted_book_error():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_new_book_error():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    # Book created with 2020, but let's assume current year is 2026
    resp = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    # Logic: 2026-2020 = 6 years, so this should actually succeed. 
    # To force 400, publish year must be 2026.
    resp_new = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": uuid.uuid4().hex[:10], "price": 10.0, "published_year": 2026, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    new_bid = resp_new.json()["id"]
    resp = requests.post(f"{BASE_URL}/books/{new_bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_rate_limit():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    for _ in range(6):
        resp = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert resp.status_code == 429

def test_update_stock_insufficient():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.patch(f"{BASE_URL}/books/{bid}/stock?quantity=-100", timeout=TIMEOUT)
    assert resp.status_code == 400

def test_upload_cover_unsupported_type():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.txt", b"content", "text/plain")}, timeout=TIMEOUT)
    assert resp.status_code == 415

def test_upload_cover_too_large():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert resp.status_code == 413

def test_create_review_invalid_rating():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/books/{bid}/reviews", json={"rating": 10, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_create_category_duplicate_name():
    name = get_unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_tag_success():
    resp = requests.post(f"{BASE_URL}/tags", json={"name": get_unique("Tag")}, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_create_tag_empty_name():
    resp = requests.post(f"{BASE_URL}/tags", json={"name": ""}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_create_order_insufficient_stock():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "e@e.com",
        "items": [{"book_id": bid, "quantity": 999}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_create_order_duplicate_items():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "e@e.com",
        "items": [{"book_id": bid, "quantity": 1}, {"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_update_order_invalid_transition():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "e@e.com", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_get_invoice_pending_forbidden():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "e@e.com", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=TIMEOUT)
    assert resp.status_code == 403

def test_bulk_create_unauthorized():
    resp = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert resp.status_code == 401

def test_bulk_create_rate_limit():
    for _ in range(4):
        resp = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": "test-api-key"}, json={"books": []}, timeout=TIMEOUT)
    assert resp.status_code == 429

def test_clone_book_duplicate_isbn():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    resp = requests.post(f"{BASE_URL}/books/{bid}/clone", json={"new_isbn": "1234567890123"}, timeout=TIMEOUT)
    resp2 = requests.post(f"{BASE_URL}/books/{bid}/clone", json={"new_isbn": "1234567890123"}, timeout=TIMEOUT)
    assert resp2.status_code == 409

def test_start_export_unauthorized():
    resp = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert resp.status_code == 401

def test_get_nonexistent_export():
    resp = requests.get(f"{BASE_URL}/exports/invalid", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_toggle_maintenance_unauthorized():
    resp = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert resp.status_code == 401

def test_get_statistics_unauthorized():
    resp = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert resp.status_code == 401

def test_deprecated_catalog_redirect():
    resp = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert resp.status_code == 301

def test_health_check_success():
    resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert resp.status_code == 200