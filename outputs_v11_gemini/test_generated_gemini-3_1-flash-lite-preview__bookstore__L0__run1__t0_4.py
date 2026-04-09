import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "admin-secret-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    data = {"name": unique("Cat"), "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": f"978-{uuid.uuid4().hex[:9]}",
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id,
        "tags": []
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_modified():
    author = create_author()
    etag = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT).headers.get("ETag")
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 304

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {"title": unique("B"), "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "author_id": a['id'], "category_id": c['id']}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == data["title"]

def test_create_book_invalid_price():
    r = requests.post(f"{BASE_URL}/books", json={"price": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_deleted_book_gone():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_book_not_deleted():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {"file": ("test.jpg", b"0" * 11 * 1024 * 1024)}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {"file": ("test.txt", b"hello")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_rate_limit():
    for _ in range(4):
        r = requests.post(f"{BASE_URL}/books/bulk", headers={"X-API-Key": "test"}, json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {"customer_name": "Test", "customer_email": "a@b.cz", "items": [{"book_id": b['id'], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_export_books_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_export_books_accepted():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "admin-key"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "admin-key"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_list_tags_success():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_add_tags_invalid_id():
    r = requests.post(f"{BASE_URL}/books/1/tags", json={"tag_ids": ["a"]}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.put(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_clone_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {"new_isbn": f"978{uuid.uuid4().hex[:10]}", "new_title": unique("Clone")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/clone", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", timeout=TIMEOUT, allow_redirects=False)
    assert r.status_code == 301