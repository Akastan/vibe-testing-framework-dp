import requests
import uuid
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-api-key"

def get_unique_str(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique_str("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert resp.status_code == 201
    return resp.json()["id"]

def create_category():
    name = get_unique_str("Cat")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Desc"}, timeout=TIMEOUT)
    assert resp.status_code == 201
    return resp.json()["id"]

def create_book(author_id, category_id):
    isbn = uuid.uuid4().hex[:13]
    title = get_unique_str("Book")
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": 100.0, "published_year": 2020, "stock": 10,
        "author_id": author_id, "category_id": category_id
    }, timeout=TIMEOUT)
    assert resp.status_code == 201
    return resp.json()["id"]

def test_create_author_success():
    name = get_unique_str("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_author_not_modified():
    aid = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{aid}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{aid}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_create_book_success():
    aid = create_author()
    cid = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    aid = create_author()
    cid = create_category()
    isbn = uuid.uuid4().hex[:13]
    data = {"title": "T", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_book_deleted():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_book_already_deleted():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_book_success():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == bid

def test_restore_book_not_deleted():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_too_new():
    aid = create_author()
    cid = create_category()
    isbn = uuid.uuid4().hex[:13]
    r_create = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": isbn, "price": 100.0, "published_year": datetime.now().year, "author_id": aid, "category_id": cid
    }, timeout=TIMEOUT)
    bid = r_create.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_success():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.patch(f"{BASE_URL}/books/{bid}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.patch(f"{BASE_URL}/books/{bid}/stock?quantity=-20", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_unsupported_type():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415

def test_upload_cover_too_large():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_order_success():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_duplicate_items():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": bid, "quantity": 1}, {"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r_order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r_order.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_forbidden():
    aid = create_author()
    cid = create_category()
    bid = create_book(aid, cid)
    r_order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": bid, "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r_order.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{oid}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    aid = create_author()
    cid = create_category()
    isbn1 = uuid.uuid4().hex[:13]
    isbn2 = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": API_KEY}, json={"books": [
        {"title": "B1", "isbn": isbn1, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": aid, "category_id": cid},
        {"title": "B2", "isbn": isbn2, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": 999, "category_id": 999}
    ]}, timeout=TIMEOUT)
    assert r.status_code == 207

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_poll_export_processing():
    r_start = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    jid = r_start.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{jid}", timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": API_KEY}, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": API_KEY}, json={"enabled": False}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301
    assert "books" in r.headers["Location"]