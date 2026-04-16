# The main error is that ISBN must be exactly 13 characters, but unique() generates 8 random chars plus prefix, making it too long. Also, some endpoints require API key headers.
# Fix: Generate proper 13-digit ISBN and add API key headers where needed.

import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        # Generate exactly 13 digits: 978 prefix + 10 random digits
        random_part = str(uuid.uuid4().int)[:10]
        isbn = f"978{random_part:0>10}"[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, headers=AUTH_HEADERS, timeout=30)
    assert r.status_code == 201, f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_name_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_author_with_etag_304():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_delete_author_with_books_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_duplicate_name_409():
    name = unique("Category")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_soft_deleted_book_410():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_update_book_etag_mismatch_412():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r1 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    etag = r1.headers.get("ETag")
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "Updated"}, timeout=30)
    r2 = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "Stale"}, headers={"If-Match": etag}, timeout=30)
    assert r2.status_code == 412
    data = r2.json()
    assert "detail" in data

def test_restore_not_deleted_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_new_book_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_rate_limit_429():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], published_year=2020)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
        assert r.status_code == 200
    time.sleep(10)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    data = r.json()
    assert "detail" in data

def test_update_stock_negative_result_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_wrong_type_415():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"not an image", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_upload_cover_too_large_413():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    large_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("large.jpg", large_data, "image/jpeg")}, timeout=30)
    assert r.status_code == 413
    data = r.json()
    assert "detail" in data

def test_create_tag_duplicate_name_409():
    name = unique("Tag")
    create_tag(name=name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_tag_with_books_409():
    tag = create_tag()
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_order_insufficient_stock_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Customer",
        "customer_email": "customer@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_order_duplicate_book_id_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Customer",
        "customer_email": "customer@test.com",
        "items": [
            {"book_id": book["id"], "quantity": 1},
            {"book_id": book["id"], "quantity": 2}
        ]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_invalid_transition_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_delete_non_pending_cancelled_order_400():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_pending_order_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

def test_add_item_to_non_pending_order_403():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13], stock=10)
    order = create_order("Customer", "customer@test.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.post(f"{BASE_URL}/orders/{order['id']}/items", json={"book_id": book["id"], "quantity": 1}, timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

def test_bulk_create_books_without_api_key_401():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_bulk_create_books_partial_success_207():
    author = create_author()
    category = create_category()
    random_part1 = str(uuid.uuid4().int)[:10]
    isbn1 = f"978{random_part1:0>10}"[:13]
    random_part2 = str(uuid.uuid4().int)[:10]
    isbn2 = f"978{random_part2:0>10}"[:13]
    create_book(author["id"], category["id"], isbn=isbn1)
    r = requests.post(f"{BASE_URL}/books/bulk", headers=AUTH_HEADERS, json={
        "books": [
            {
                "title": unique("Book"),
                "isbn": isbn2,
                "price": 20,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            },
            {
                "title": unique("Book"),
                "isbn": isbn1,
                "price": 30,
                "published_year": 2020,
                "stock": 5,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }, timeout=30)
    assert r.status_code == 207
    data = r.json()
    assert "created" in data
    assert "failed" in data
    assert data["created"] == 1
    assert data["failed"] == 1

def test_clone_book_duplicate_isbn_409():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json={"new_isbn": book["isbn"]}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_export_without_api_key_401():
    r = requests.post(f"{BASE_URL}/exports/books", timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_get_export_job_not_found_404():
    r = requests.get(f"{BASE_URL}/exports/nonexistent", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_toggle_maintenance_without_api_key_401():
    r = requests.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_get_statistics_without_api_key_401():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=30)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data