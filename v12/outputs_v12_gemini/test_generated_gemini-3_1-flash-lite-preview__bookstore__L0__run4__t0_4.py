# Analysis: The unique ISBN generation was creating strings potentially longer than typical ISBN-10/13 formats or schema constraints. 
# Fix: Adjusted ISBN generation to ensure it remains a valid string length and ensured all helpers strictly follow the 201/200 status code assertion.

import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]

def create_category():
    name = unique("Cat")
    payload = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]

def create_book():
    author_id = create_author()
    category_id = create_category()
    # Ensure ISBN is a valid length string (13 chars) to avoid Pydantic validation errors
    isbn = f"978{uuid.uuid4().hex[:10]}"
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()["id"]


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_health_check_invalid_method():
    r = requests.post(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 405

def test_create_author_success():
    name = unique("Auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "B", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_success():
    aid = create_author()
    r = requests.get(f"{BASE_URL}/authors/{aid}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == aid

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_success():
    aid = create_author()
    cid = create_category()
    payload = {"title": unique("B"), "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "author_id": aid, "category_id": cid}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "price": -1.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_success():
    bid = create_book()
    r = requests.get(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == bid

def test_get_book_gone():
    bid = create_book()
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_delete_book_success():
    bid = create_book()
    r = requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_book_already_gone():
    bid = create_book()
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_book_success():
    bid = create_book()
    requests.delete(f"{BASE_URL}/books/{bid}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == bid

def test_restore_book_not_deleted():
    bid = create_book()
    r = requests.post(f"{BASE_URL}/books/{bid}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    bid = create_book()
    r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_rate_limit():
    bid = create_book()
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{bid}/discount", json={"discount_percent": 5.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_upload_cover_success():
    bid = create_book()
    files = {"file": ("test.jpg", b"fake_image_content", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "book_id" in r.json()

def test_upload_cover_too_large():
    bid = create_book()
    files = {"file": ("test.jpg", b"0" * 3 * 1024 * 1024, "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{bid}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 413

def test_bulk_create_success():
    aid = create_author()
    cid = create_category()
    payload = {"books": [{"title": unique("B"), "isbn": f"978{uuid.uuid4().hex[:7]}", "price": 1.0, "published_year": 2020, "author_id": aid, "category_id": cid}]}
    r = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code in (200, 201)

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_create_order_success():
    bid = create_book()
    payload = {"customer_name": "Name", "customer_email": "e@e.cz", "items": [{"book_id": bid, "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201)
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_status_success():
    bid = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": bid, "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "shipped"

def test_update_order_status_invalid():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_create_export_unauthorized():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert r.status_code == 401

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["maintenance_mode"] is True
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": "test"}, timeout=TIMEOUT)

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_success():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401