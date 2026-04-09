import requests
import uuid
import time
from typing import Optional


BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
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
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("auth")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_etag_304():
    auth = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{auth['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_update_author_412_mismatch():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "New"}, headers={"If-Match": '"wrong"'}, timeout=30)
    assert r.status_code == 412

def test_create_duplicate_category():
    name = unique("cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("isbn")[:13], "price": 10, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("isbn")[:13], "price": -1, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_get_deleted_book_410():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    b["published_year"] = 2000
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_negative_result():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-99", timeout=30)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data")}, timeout=30)
    assert r.status_code == 415

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_invalid_order_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_forbidden_state():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": [
        {"title": "B1", "isbn": unique("i1")[:13], "price": 10, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "short", "price": 10, "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]}
    ]}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json={"new_isbn": b["isbn"]}, timeout=30)
    assert r.status_code == 409

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    job_id = r.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r.status_code == 202

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301
    assert "/books" in r.headers["Location"]


def test_list_authors_pagination_limit():
    author1 = create_author(unique("a1"))
    author2 = create_author(unique("a2"))
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1