import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "test-secret-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    name = unique("cat")
    payload = {"name": name, "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    payload = {
        "title": unique("book"),
        "isbn": f"978{uuid.uuid4().hex[:10]}",
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author_id,
        "category_id": category_id,
        "tags": []
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("author")
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

def test_get_author_etag_not_modified():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_create_book_valid():
    a = create_author()
    c = create_category()
    payload = {
        "title": unique("book"), "isbn": "1234567890123", "price": 10.0, 
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    payload = {
        "title": unique("book"), "isbn": "1234567890123", "price": -1.0, 
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0", timeout=TIMEOUT)
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

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {"rating": 5, "reviewer_name": "Tester", "comment": "Great"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {"rating": 10, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 20

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.jpg", b"0" * 3 * 1024 * 1024)}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.txt", b"hello")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_clone_book_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {"new_isbn": f"978{uuid.uuid4().hex[:10]}", "new_title": "Clone", "stock": 1}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {
        "customer_name": "John Doe", "customer_email": "john@test.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_update_order_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_start_export_authorized():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "admin-secret"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_statistics_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "admin-secret"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301

def test_search_books_empty_query():
    r = requests.get(f"{BASE_URL}/books?search=", timeout=TIMEOUT)
    assert r.status_code == 200