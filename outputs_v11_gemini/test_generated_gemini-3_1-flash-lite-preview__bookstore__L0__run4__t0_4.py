import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
API_KEY = "admin" # Předpokládaný klíč pro endpointy vyžadující autentizaci

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("auth"), "bio": "bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    data = {"name": unique("cat"), "description": "desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("book"),
        "isbn": f"978-{uuid.uuid4().hex[:10]}",
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

def test_create_author_valid():
    data = {"name": unique("auth"), "bio": "bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    data = {"name": "", "bio": "bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_etag_not_modified():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_create_book_valid():
    a = create_author()
    c = create_category()
    data = {
        "title": unique("book"),
        "isbn": "1234567890123",
        "price": 50.0,
        "published_year": 2022,
        "author_id": a['id'],
        "category_id": c['id']
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    data = {
        "title": unique("book"),
        "isbn": "1234567890123",
        "price": -10.0,
        "published_year": 2022,
        "author_id": a['id'],
        "category_id": c['id']
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=TIMEOUT)
    assert r.status_code == 422

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

def test_restore_active_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 409

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_apply_discount_invalid_value():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 101}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {'file': ('test.jpg', b'0' * 11 * 1024 * 1024)}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_upload_cover_wrong_type():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    files = {'file': ('test.txt', b'hello')}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": b['id'], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code in (200, 201)
    assert "id" in r.json()

def test_create_order_no_items():
    data = {"customer_name": "John Doe", "customer_email": "john@example.com", "items": []}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_export_books_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_export_job_not_found():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_statistics_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_create_category_valid():
    data = {"name": unique("cat")}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_valid():
    data = {"name": unique("tag")}
    r = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_empty_list():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    data = {"rating": 10, "reviewer_name": "Tester", "comment": "Great book"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_forbidden():
    r = requests.get(f"{BASE_URL}/orders/99999", timeout=TIMEOUT)
    assert r.status_code in (403, 404)


def test_update_author_etag_precondition_failed():
    author = create_author()
    author_id = author["id"]
    
    r_get = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    etag = r_get.headers.get("ETag")
    
    update_data = {"name": unique("updated"), "bio": "new bio", "born_year": 1995}
    headers = {"If-Match": "invalid-etag"}
    
    r_put = requests.put(f"{BASE_URL}/authors/{author_id}", json=update_data, headers=headers, timeout=TIMEOUT)
    
    assert r_put.status_code == 412
    assert "detail" in r_put.json()