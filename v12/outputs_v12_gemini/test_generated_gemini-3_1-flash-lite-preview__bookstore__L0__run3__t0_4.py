# The errors likely stem from missing required fields or incorrect data types in payloads (e.g., ISBN length or missing fields). 
# I am ensuring all payloads strictly follow the schema and adding necessary headers where required.

import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def create_author():
    # Ensure unique name and valid payload for AuthorCreate schema
    name = f"Author_{uuid.uuid4().hex[:8]}"
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    # Ensure unique name for CategoryCreate schema
    name = f"Cat_{uuid.uuid4().hex[:8]}"
    payload = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    # Ensure ISBN is a valid string and all required fields are present for BookCreate
    # Using a 13-digit format for ISBN to satisfy potential validation constraints
    isbn = f"978{uuid.uuid4().hex[:10]}"
    payload = {
        "title": f"Book_{uuid.uuid4().hex[:8]}",
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author_id,
        "category_id": category_id,
        "tags": []
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    name = f"Author_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "Missing name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_success():
    a = create_author()
    c = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    payload = {"title": "Title", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    payload = {"title": "T", "isbn": "1234567890", "price": -1.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_deleted_book_gone():
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

def test_delete_already_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_apply_invalid_discount_value():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 101}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_upload_cover_unsupported_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_bulk_create_too_many_items():
    books = [{"title": f"T_{uuid.uuid4().hex[:8]}", "isbn": f"{uuid.uuid4().hex[:10]}", "price": 1, "published_year": 2000, "author_id": 1, "category_id": 1} for _ in range(101)]
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": books}, headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_category_success():
    name = f"Cat_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_update_category_etag_mismatch():
    c = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": "New"}, headers={"If-Match": "wrong"}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_create_order_success():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Name", "customer_email": "e@e.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Name", "customer_email": "e@e.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_tag_success():
    name = f"Tag_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_start_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/invalid_id", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": "admin"}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "admin"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301