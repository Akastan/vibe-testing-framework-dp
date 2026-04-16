# The previous helpers failed because they lacked necessary fields required by the schema (e.g., 'books' or specific constraints) and didn't handle potential API key requirements or payload structures.
import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def create_author():
    # Ensure unique name and valid schema fields
    name = f"Author_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "bio": "Biography of " + name,
        "born_year": 1990
    }
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper create_author failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category():
    # Ensure unique name for category
    name = f"Cat_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "description": "Category description for " + name
    }
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper create_category failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id):
    # Ensure unique ISBN and title using uuid
    isbn = f"ISBN-{uuid.uuid4().hex[:8]}"
    title = f"Book_{uuid.uuid4().hex[:8]}"
    payload = {
        "title": title,
        "isbn": isbn,
        "author_id": author_id,
        "category_id": category_id,
        "published_year": 2023,
        "price": 299.0
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"Helper create_book failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_success():
    name = f"Author_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "", "bio": "Bio"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = f"ISBN{uuid.uuid4().hex[:9]}"
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": isbn, "price": 100, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = f"ISBN{uuid.uuid4().hex[:9]}"
    payload = {"title": "B", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_price():
    author = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": -1, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_filter():
    r = requests.get(f"{BASE_URL}/books?min_price=-10", timeout=TIMEOUT)
    assert r.status_code == 422

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Del", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_already_deleted_book():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Del", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_deleted_book_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Res", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_restore_active_book_error():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Res", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Old", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_rate_limit():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "Old", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_apply_discount_new_book_error():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": f"Book_{uuid.uuid4().hex[:8]}", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 100, "published_year": 2026, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "S", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_update_stock_insufficient():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "S", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-1", timeout=TIMEOUT)
    assert r.status_code == 400

def test_upload_cover_invalid_type():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "C", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("test.txt", b"content")}, timeout=TIMEOUT)
    assert r.status_code == 415

def test_create_review_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "R", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_success():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "O", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "O", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"], "stock": 0
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_order_status_invalid_transition():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "O", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_invoice_forbidden_state():
    author = create_author()
    cat = create_category()
    b = requests.post(f"{BASE_URL}/books", json={
        "title": "O", "isbn": f"ISBN{uuid.uuid4().hex[:9]}", "price": 10, "published_year": 2020, 
        "author_id": author["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 403

def test_bulk_create_unauthorized():
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": []}, timeout=TIMEOUT)
    assert r.status_code == 401

def test_start_export_success():
    r = requests.post(f"{BASE_URL}/exports/books", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 202

def test_get_export_not_found():
    r = requests.get(f"{BASE_URL}/exports/job_999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_toggle_maintenance_success():
    r = requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/admin/maintenance", headers={"X-API-Key": "test-api-key"}, json={"enabled": False}, timeout=TIMEOUT)

def test_get_stats_unauthorized():
    r = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert r.status_code == 401

def test_get_stats_large_payload():
    r = requests.get(f"{BASE_URL}/statistics/summary", headers={"X-API-Key": "test-api-key"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total_books" in r.json()

def test_deprecated_catalog_redirect():
    r = requests.get(f"{BASE_URL}/catalog", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 301