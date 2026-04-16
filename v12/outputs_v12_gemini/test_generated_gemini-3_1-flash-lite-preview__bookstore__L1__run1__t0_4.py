# The error log implies that helpers fail due to missing required fields or incorrect data formats. 
# I am ensuring all data payloads strictly match the expected schema and using unique identifiers for all fields.

import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def create_author():
    # Ensure name and bio are provided as per typical AuthorCreate schema requirements
    name = f"Author_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "bio": "Biography of " + name,
        "born_year": 1990
    }
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    # Ensure name and description are provided as per typical CategoryCreate schema requirements
    name = f"Cat_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "description": "Description for " + name
    }
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    # Ensure all required fields for BookCreate are present and valid
    isbn = f"978-{uuid.uuid4().hex[:7]}"
    title = f"Book_{uuid.uuid4().hex[:8]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = f"Author_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book",
        "isbn": f"978{uuid.uuid4().hex[:7]}",
        "price": 50.0,
        "published_year": 2020,
        "author_id": auth["id"],
        "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    payload = {"title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_deleted_book_gone():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_apply_discount_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    r_book = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": isbn, "price": 100.0, "published_year": 2026, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    book_id = r_book.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-100", timeout=TIMEOUT)
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
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}, timeout=TIMEOUT)
    assert r.status_code == 413

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [
            {"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}
        ]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r_ord.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_forbidden_state():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r_ord = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    oid = r_ord.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{oid}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": "test-api-key"}, json={"books": [
        {"title": f"B1_{uuid.uuid4().hex[:8]}", "isbn": f"978{uuid.uuid4().hex[:7]}", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]},
        {"title": f"B2_{uuid.uuid4().hex[:8]}", "isbn": "invalid", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]}
    ]}, timeout=TIMEOUT)
    assert r.status_code == 207, f"Expected 207 Multi-Status, got {r.status_code}: {r.text}"

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_poll_export_processing():
    r_init = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    jid = r_init.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{jid}", timeout=TIMEOUT)
    assert r.status_code in (200, 202)

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": False}, timeout=TIMEOUT)

def test_get_statistics_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_catalog_deprecated_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_catalog_malformed_query():
    r = requests.get(f"{BASE_URL}/catalog?invalid=param", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301