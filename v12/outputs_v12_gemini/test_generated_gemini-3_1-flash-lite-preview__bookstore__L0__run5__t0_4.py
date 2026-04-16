# The primary error stems from the ISBN format (must be 13 digits) and potential schema mismatches in creation payloads. 
# I will ensure ISBN is exactly 13 digits and verify that all required fields for authors/books match the expected API schema.

import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def get_unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    # Ensure all required fields are present according to AuthorCreate schema
    data = {"name": get_unique("Author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    # Ensure all required fields are present according to CategoryCreate schema
    data = {"name": get_unique("Cat")}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book():
    author = create_author()
    category = create_category()
    # ISBN must be 13 digits; using a fixed prefix 978 and 10 random digits
    isbn = "978" + "".join([str(uuid.uuid4().int % 10) for _ in range(10)])
    data = {
        "title": get_unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    name = get_unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Test", "born_year": 2000}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_author_not_modified():
    author = create_author()
    etag = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT).headers.get("ETag")
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 304

def test_create_book_success():
    author = create_author()
    category = create_category()
    data = {"title": "Test", "isbn": "1234567890", "price": 10.0, "published_year": 2020, "author_id": author["id"], "category_id": category["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    r = requests.post(f"{BASE_URL}/books", json={"title": "Test", "price": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_already_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_active_book_fail():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_rate_limit():
    book = create_book()
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_upload_cover_too_large():
    book = create_book()
    files = {"file": ("test.jpg", b"0" * 3000000, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_upload_cover_invalid_type():
    book = create_book()
    files = {"file": ("test.txt", b"hello", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_bulk_create_missing_key():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    for _ in range(4):
        r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_create_order_success():
    book = create_book()
    data = {"customer_name": "Test", "customer_email": "test@test.com", "items": [{"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Test", "customer_email": "a@b.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid_value():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/books/export", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_statistics_success():
    r = requests.get(f"{BASE_URL}/statistics", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    assert "total_books" in r.json()

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": get_unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 50}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": get_unique("Cat")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_duplicate_category():
    name = get_unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409