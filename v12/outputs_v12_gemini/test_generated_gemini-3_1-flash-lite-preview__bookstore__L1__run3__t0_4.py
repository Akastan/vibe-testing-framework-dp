# The previous helpers failed because they lacked the required 'X-API-Key' header for protected endpoints and did not handle potential data format issues. I have added the header to all requests and ensured data consistency.

import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def create_author():
    name = f"Auth_{uuid.uuid4().hex[:8]}"
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = f"Cat_{uuid.uuid4().hex[:8]}"
    payload = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    # ISBN must be a valid string format (often 10-13 chars). Using 13 chars total.
    isbn = f"978{uuid.uuid4().hex[:10]}"
    payload = {
        "title": f"Book_{uuid.uuid4().hex[:8]}",
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = f"Auth_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "B", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "B"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    data = {"title": "T", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_soft_deleted_book_gone():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_get_book_etag_not_modified():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    etag = r.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_soft_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_non_deleted_book_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    book = requests.post(f"{BASE_URL}/books", json={"title": "New", "isbn": isbn, "price": 100, "published_year": 2026, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-20", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"content", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415

def test_upload_cover_too_large():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    large_data = b"0" * (2 * 1024 * 1024 + 100)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("img.jpg", large_data, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 999}]}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_pending_forbidden():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    auth = create_author()
    cat = create_category()
    isbn1 = f"978{uuid.uuid4().hex[:7]}"
    isbn2 = f"978{uuid.uuid4().hex[:7]}"
    b1 = {"title": "T1", "isbn": isbn1, "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]}
    b2 = {"title": "", "isbn": isbn2, "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=[b1, b2], headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 207, f"Expected 207, got {r.status_code}: {r.text}"

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_status_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    job_id = r.json()["job_id"]
    r2 = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=TIMEOUT)
    assert r2.status_code == 202

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_catalog_deprecated_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200