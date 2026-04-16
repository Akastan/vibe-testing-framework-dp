# The ISBN must be unique to prevent 422/409 errors; the original helper used a static string. I will use a random 13-digit sequence.
import requests
import uuid
import random

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"X-API-Key": "test-api-key"}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()

def create_category():
    name = unique("Cat")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()

def create_book(author_id, category_id):
    # Generate a unique 13-digit ISBN string to avoid validation/conflict errors.
    isbn = "".join([str(random.randint(0, 9)) for _ in range(13)])
    data = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "author_id": author_id,
        "category_id": category_id
    }
    resp = requests.post(f"{BASE_URL}/books", json=data, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 201, f"Helper failed {resp.status_code}: {resp.text[:200]}"
    return resp.json()


def test_create_author_success():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["name"] == name

def test_create_author_invalid_name():
    resp = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert resp.status_code == 422
    assert "detail" in resp.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    resp = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_duplicate_category():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = uuid.uuid4().hex[:13]
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": isbn, "price": 10.0, 
        "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert "id" in resp.json()

def test_create_book_invalid_isbn():
    author = create_author()
    cat = create_category()
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": "Test", "isbn": "123", "price": 10.0, 
        "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_get_soft_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", headers=HEADERS, timeout=TIMEOUT)
    resp = requests.get(f"{BASE_URL}/books/{book['id']}", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 410

def test_get_nonexistent_book():
    resp = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_restore_active_book_error():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/restore", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "discounted_price" in resp.json()

def test_apply_discount_new_book_error():
    author = create_author()
    cat = create_category()
    data = {
        "title": unique("Book"), "isbn": "".join([str(i % 10) for i in range(13)]), "price": 100.0,
        "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }
    book = requests.post(f"{BASE_URL}/books", json=data, headers=HEADERS, timeout=TIMEOUT).json()
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_rate_limit():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    for _ in range(6):
        resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 429

def test_update_stock_insufficient():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -1}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_upload_cover_invalid_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 415

def test_upload_cover_too_large():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 413

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester", "comment": "Great"
    }, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 201

def test_create_review_empty_content():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_bulk_create_unauthorized():
    resp = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert resp.status_code == 401

def test_bulk_create_partial_success():
    author = create_author()
    cat = create_category()
    data = {
        "books": [
            {"title": unique("B1"), "isbn": uuid.uuid4().hex[:13], "price": 10.0, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]},
            {"title": unique("B2"), "isbn": "invalid-isbn-format", "price": 10.0, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
        ]
    }
    resp = requests.post(f"{BASE_URL}/books/bulk", json=data, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 207, f"Expected 207 Multi-Status, got {resp.status_code}: {resp.text}"

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "a@b.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 201

def test_create_order_duplicate_items():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "a@b.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_update_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "a@b.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_get_invoice_forbidden_pending():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "User", "customer_email": "a@b.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert resp.status_code == 403

def test_start_export_success():
    resp = requests.post(f"{BASE_URL}/exports/books", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 202

def test_get_export_status_processing():
    job = requests.post(f"{BASE_URL}/exports/books", headers=HEADERS, timeout=TIMEOUT).json()
    resp = requests.get(f"{BASE_URL}/exports/{job['job_id']}", timeout=TIMEOUT)
    assert resp.status_code == 202

def test_get_export_not_found():
    resp = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_toggle_maintenance_success():
    resp = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers=HEADERS, timeout=TIMEOUT)

def test_toggle_maintenance_unauthorized():
    resp = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert resp.status_code == 401

def test_get_statistics_unauthorized():
    resp = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert resp.status_code == 401

def test_get_statistics_success():
    resp = requests.get(f"{BASE_URL}/statistics/summary", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "total_books" in resp.json()