import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = unique("cat")
    data = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    isbn = str(uuid.uuid4().int)[:13]
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
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": "wrong-etag"}, timeout=30)
    assert r.status_code == 412
    assert "detail" in r.json()

def test_create_category_duplicate():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/categories", json={"name": cat["name"]}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": unique("1234567890"), "price": 10.0,
        "published_year": 2020, "stock": 5, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_isbn():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test", "isbn": "123", "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_gone():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_delete_book_soft():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_book_not_deleted():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 409

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 99, "reviewer_name": "tester"}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_apply_discount_new_book():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": unique("1234567890"), "price": 100.0,
        "published_year": datetime.now().year, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    book = r.json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 403

def test_update_stock_negative():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": -100}, timeout=30)
    assert r.status_code == 422

def test_upload_cover_too_large():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    files = {"file": ("test.jpg", b"0" * 3 * 1024 * 1024, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 413

def test_upload_cover_invalid_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    files = {"file": ("test.txt", b"data", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert any(t["id"] == tag["id"] for t in r.json()["tags"])

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_forbidden():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": [
        {"title": "B1", "isbn": unique("1234567890"), "price": 10, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]},
        {"title": "B2", "isbn": "invalid", "price": 10, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]}
    ]}, headers=HEADERS, timeout=30)
    assert r.status_code == 422

def test_clone_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book["isbn"]}, timeout=30)
    assert r.status_code == 409

def test_create_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202

def test_get_export_processing():
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
    assert "Location" in r.headers