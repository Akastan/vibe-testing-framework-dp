import requests
import uuid
import pytest


BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-secret-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    payload = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Author creation failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    payload = {"name": unique("Cat")}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Category creation failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    payload = {
        "title": unique("Book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id,
        "tags": []
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Book creation failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_book_success():
    a = create_author()
    c = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == payload["title"]

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    payload = {
        "title": unique("Book"),
        "isbn": "1234567890123",
        "price": -10.0,
        "published_year": 2020,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_update_book_etag_mismatch():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r_get = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    etag = r_get.headers.get("ETag")
    headers = {"If-Match": "wrong-etag"}
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"title": "New", "isbn": b["isbn"], "price": b["price"], "published_year": b["published_year"], "stock": b["stock"], "author_id": a["id"], "category_id": c["id"]}, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 412

def test_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
        if r.status_code == 429:
            break
    assert r.status_code == 429

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    large_file = b"0" * (11 * 1024 * 1024)
    files = {"file": ("test.jpg", large_file, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    headers = {"X-API-Key": API_KEY}
    for _ in range(4):
        r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 429

def test_create_author_success():
    payload = {"name": unique("Author"), "bio": "Bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_author_success():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "Updated Name"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201)
    assert "id" in r.json()

def test_create_order_empty_items():
    payload = {"customer_name": "John", "customer_email": "j@e.com", "items": []}
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_start_export_success():
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_status_pending():
    headers = {"X-API-Key": API_KEY}
    r_start = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    job_id = r_start.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 202)

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers=headers, timeout=TIMEOUT)

def test_get_statistics_success():
    headers = {"X-API-Key": API_KEY}
    r = requests.get(f"{BASE_URL}/admin/statistics/summary", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301