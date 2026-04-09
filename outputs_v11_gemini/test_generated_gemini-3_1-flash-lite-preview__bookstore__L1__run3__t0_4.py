import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    payload = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    payload = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None):
    # ISBN musí být unikátní string, generujeme náhodný řetězec 10 číslic
    isbn = isbn or "".join([str(uuid.uuid4().int)[:10]])
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "test", "born_year": 1990}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book",
        "isbn": "1234567890",
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = "1111111111"
    create_book(author["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup",
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_get_soft_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_active_book_error():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 422

def test_apply_discount_new_book_error():
    author = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "New Book",
        "isbn": "9999999999",
        "price": 100.0,
        "published_year": 2026,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    book_id = r.json()["id"]
    r_disc = requests.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r_disc.status_code == 400

def test_update_stock_negative_result():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": -999}, timeout=30)
    assert r.status_code == 422

def test_create_review_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester", "comment": "test"}, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag_r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    tag_id = tag_r.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=30)
    assert r.status_code == 200
    assert any(t["id"] == tag_id for t in r.json()["tags"])

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John",
        "customer_email": "j@test.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 422

def test_create_order_duplicate_items():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John",
        "customer_email": "j@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 422

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401

def test_clone_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], isbn="1234567890")
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": "1234567890"}, timeout=30)
    assert r.status_code == 400

def test_start_export_authorized():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 202
    assert "job_id" in r.json()

def test_get_nonexistent_export():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404

def test_toggle_maintenance_unauthorized():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401

def test_catalog_redirect_check():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=30)
    assert r.status_code == 301
    assert "/books" in r.headers.get("Location", "")

def test_update_author_etag_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", 
                     headers={"If-Match": "wrong-etag"}, 
                     json={"name": "New Name"}, timeout=30)
    assert r.status_code == 412

def test_list_books_pagination_invalid():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=30)
    assert r.status_code == 422

def test_health_method_not_allowed():
    r = requests.put(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 405


def test_list_authors_pagination_default_values():
    author1 = create_author()
    author2 = create_author()
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1

def test_get_author_etag_caching():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_update_author_success():
    author = create_author()
    new_name = unique("new_name")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name, "bio": "updated bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == new_name
    assert r.json()["bio"] == "updated bio"

def test_create_author_validation_error():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "bio", "born_year": 2025}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json() == {}

def test_list_authors_empty_result():
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 9999, "limit": 10}, timeout=30)
    assert r.status_code == 200
    assert r.json() == []