import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None):
    title = title or unique("book")
    data = {
        "title": title,
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test", "born_year": 2000}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "test", "born_year": 2000}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_author_etag_not_modified():
    author = create_author()
    aid = author["id"]
    r1 = requests.get(f"{BASE_URL}/authors/{aid}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{aid}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_create_book_valid():
    a = create_author()
    c = create_category()
    title = unique("book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": "9780123456789", "price": 10.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == title

def test_create_book_invalid_price():
    r = requests.post(f"{BASE_URL}/books", json={"title": "fail", "price": -1.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_book_not_deleted():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "tester", "comment": "good"
    }, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "id" in r.json()

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 11, "reviewer_name": "tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
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
    files = {"file": ("test.jpg", b"0" * 10 * 1024 * 1024, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_add_tags_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [1]}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_empty_list():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@j.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@j.com", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_limit_exceeded():
    headers = {"X-API-Key": "secret"}
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 429

def test_start_export_authorized():
    headers = {"X-API-Key": "test-key"}
    r = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_authorized():
    headers = {"X-API-Key": "test-key"}
    r = requests.get(f"{BASE_URL}/statistics/summary", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_catalog_deprecated_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301