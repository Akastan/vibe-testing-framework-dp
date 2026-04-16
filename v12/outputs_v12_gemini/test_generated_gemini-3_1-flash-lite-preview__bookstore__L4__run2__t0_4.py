# The main error is likely due to missing the required 'X-API-Key' header in helper functions, causing 403/401 errors, and potential validation errors if the API expects specific data structures.
import uuid
import requests

BASE_URL = "http://localhost:8000"
AUTH = {"X-API-Key": "test-api-key"}
TIMEOUT = 30

def get_unique(prefix):
    # Ensure the total length is reasonable for database constraints
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = get_unique("Auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = get_unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    # ISBNs often have length constraints; using a shorter unique string
    isbn = isbn or uuid.uuid4().hex[:13]
    payload = {
        "title": get_unique("Book"), 
        "isbn": isbn, 
        "price": 10.0,
        "published_year": 2020, 
        "author_id": author_id, 
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid():
    data = create_author()
    assert "id" in data
    assert "name" in data

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
    data = create_book(a["id"], c["id"])
    assert "id" in data
    assert data["isbn"] is not None

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = get_unique("ISBN")
    create_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_soft_delete_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r_get.status_code == 410

def test_delete_already_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_apply_discount_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book():
    a = create_author()
    c = create_category()
    r_book = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": get_unique("ISBN"), "price": 10.0,
        "published_year": 2026, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    b = r_book.json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -100}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_malformed_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH, json={"books": [
        {"title": get_unique("B1"), "isbn": get_unique("ISBN1"), "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]},
        {"title": "B2", "isbn": "INVALID", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    ]}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "John", "customer_email": "j@j.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "John", "customer_email": "j@j.com", "items": [{"book_id": b["id"], "quantity": 999}]}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_order_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "John", "customer_email": "j@j.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_invoice_forbidden_state():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "John", "customer_email": "j@j.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 404

def test_start_export_authorized():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=TIMEOUT)
    assert r.status_code == 202

def test_poll_export_processing():
    r = requests.post(f"{BASE_URL}/exports/books", headers=AUTH, timeout=TIMEOUT)
    job_id = r.json()["job_id"]
    r_poll = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=TIMEOUT)
    assert r_poll.status_code in [200, 202]

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/fake", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_mode():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers=AUTH, json={"enabled": False}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_catalog_deprecated_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301