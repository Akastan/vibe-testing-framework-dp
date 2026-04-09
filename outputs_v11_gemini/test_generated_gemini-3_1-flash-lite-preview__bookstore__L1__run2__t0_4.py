import requests
import uuid
import pytest


BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_author failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    data = {"name": unique("Cat"), "description": "Desc"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/categories", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_category failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": unique("1234567890"),
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books", json=data, headers=headers, timeout=30)
    assert r.status_code in (200, 201), f"Helper create_book failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    data = {"name": unique("Auth"), "bio": "Bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 400

def test_create_book_success():
    author = create_author()
    cat = create_category()
    data = {
        "title": unique("Book"),
        "isbn": unique("1234567890"),
        "price": 50.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("9876543210")
    data = {
        "title": "Book1",
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    data["title"] = "Book2"
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 422

def test_get_soft_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_get_book_etag_304():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r1 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_update_book_etag_mismatch():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New", "price": 100.0, "published_year": 2020, "stock": 10, "author_id": author["id"], "category_id": cat["id"]}, headers={"If-Match": '"wrong-etag"'}, timeout=30)
    assert r.status_code == 412

def test_update_book_not_found():
    r = requests.put(f"{BASE_URL}/books/99999", json={"title": "New"}, timeout=30)
    assert r.status_code == 404

def test_restore_deleted_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_restore_active_book_error():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 409

def test_apply_discount_new_book_error():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_rate_limit():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    # Rate limit is 5 req/10s, so 6th request triggers 429
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 429

def test_update_stock_insufficient():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    headers = {"X-API-Key": API_KEY}
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-99", headers=headers, timeout=30)
    assert r.status_code == 422

def test_upload_cover_too_large():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    large_file = b"0" * 3 * 1024 * 1024
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.jpg", large_file, "image/jpeg")}, headers=headers, timeout=30)
    assert r.status_code == 413

def test_upload_cover_invalid_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"data", "text/plain")}, headers=headers, timeout=30)
    assert r.status_code == 415

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Tester", "comment": "Great"}
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, headers=headers, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_bulk_create_partial_success():
    author = create_author()
    cat = create_category()
    data = {
        "books": [
            {"title": "B1", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]},
            {"title": "", "isbn": "short", "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
        ]
    }
    r = requests.post(f"{BASE_URL}/books/bulk", json=data, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 422

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {
        "customer_name": "C",
        "customer_email": "e@e.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/orders", json=data, headers=headers, timeout=30)
    assert r.status_code == 422

def test_create_order_duplicate_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {
        "customer_name": "C",
        "customer_email": "e@e.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }
    headers = {"X-API-Key": API_KEY}
    r = requests.post(f"{BASE_URL}/orders", json=data, headers=headers, timeout=30)
    assert r.status_code == 422

def test_update_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    headers = {"X-API-Key": API_KEY}
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, headers=headers, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, headers=headers, timeout=30)
    assert r.status_code == 422

def test_get_invoice_pending_forbidden():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    headers = {"X-API-Key": API_KEY}
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, headers=headers, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", headers=headers, timeout=30)
    assert r.status_code == 403

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_export_processing():
    r_post = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    job_id = r_post.json()["job_id"]
    r = requests.get(f"{BASE_URL}/exports/{job_id}", timeout=30)
    assert r.status_code == 202

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 200
    assert r.json()["maintenance_mode"] is True
    # Teardown
    requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": False}, headers={"X-API-Key": API_KEY}, timeout=30)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_catalog_redirect_301():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200


def test_list_authors_pagination_limit():
    author1 = create_author()
    author2 = create_author()
    headers = {"X-API-Key": API_KEY}
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, headers=headers, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1