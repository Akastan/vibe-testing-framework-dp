import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    data = {"name": unique("Cat"), "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": unique("1234567890"),
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_ids": [category_id]
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    data = {"name": "", "bio": "Bio"}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_modified():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {
        "title": unique("Book"), "isbn": unique("1234567890"), "price": 50.0,
        "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("1234567890")
    data = {
        "title": "B1", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "stock": 1, "author_id": a["id"], "category_id": c["id"]
    }
    requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_book_soft_delete():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r_get.status_code == 410

def test_delete_already_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_restore_non_deleted_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 422

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    assert "price" in r.json()

def test_apply_discount_rate_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"quantity": -100}, timeout=30)
    assert r.status_code == 422

def test_upload_cover_invalid_type():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.txt", b"content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, timeout=30)
    assert r.status_code == 422

def test_upload_cover_too_large():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    files = {"file": ("test.jpg", b"0" * (3 * 1024 * 1024), "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files=files, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 413

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 10, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    data = {"books": []}
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    a = create_author()
    c = create_category()
    data = {
        "books": [
            {"title": "B1", "isbn": unique("111"), "price": 10, "published_year": 2020, "author_id": a["id"], "category_ids": [c["id"]]},
            {"title": "B2", "isbn": "invalid", "price": 10, "published_year": 2020, "author_id": 999, "category_ids": [999]}
        ]
    }
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 207

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 999}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_invalid_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]}, headers={"X-API-Key": API_KEY}, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_get_invoice_forbidden():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": b["id"], "quantity": 1}]}, headers={"X-API-Key": API_KEY}, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", headers={"X-API-Key": "wrong-key"}, timeout=30)
    assert r.status_code == 403

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202

def test_poll_export_processing():
    r_start = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    job_id = r_start.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r.status_code == 202

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    data = {"enabled": True}
    r = requests.post(f"{BASE_URL}/admin/maintenance", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301