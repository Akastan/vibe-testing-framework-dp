# The main errors likely stem from ISBN length constraints (unique() generates strings that may exceed max length) and missing X-API-Key header for authenticated endpoints. Also, the unique function for ISBN may produce strings >13 chars.
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session, name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session, name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, author_id, category_id, title=None, isbn=None, price=10.0, published_year=2020, stock=5):
    if title is None:
        title = unique("book")
    if isbn is None:
        # Ensure ISBN is exactly 13 characters (ISBN-13 standard) and numeric
        isbn = uuid.uuid4().hex[:13]
        # Make sure it's all digits (uuid hex is 0-9a-f, but ISBN should be digits)
        # Replace any non-digit with '0' to keep length 13
        isbn = ''.join(c if c.isdigit() else '0' for c in isbn)
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(session, name=None):
    if name is None:
        name = unique("tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    s = requests.Session()
    name = unique("author")
    r = s.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    s = requests.Session()
    author = create_author(s)
    r = s.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == author["id"]

def test_get_author_not_found():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/authors/9999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_with_etag_match():
    s = requests.Session()
    author = create_author(s)
    get_r = s.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = get_r.headers.get("ETag")
    r = s.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("updated")}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data

def test_delete_author_success():
    s = requests.Session()
    author = create_author(s)
    r = s.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_category_success():
    s = requests.Session()
    name = unique("cat")
    r = s.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_get_category_not_found():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/categories/9999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    title = unique("book")
    isbn = unique("isbn")[:13]
    if len(isbn) < 10:
        isbn = isbn.zfill(10)
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = s.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_invalid_price():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": -5.0,
        "published_year": 2021,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = s.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    create_book(s, author["id"], category["id"], price=20.0)
    r = s.get(f"{BASE_URL}/books?min_price=10&max_price=30", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_soft_deleted_book_returns_410():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_update_book_etag_mismatch():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("newtitle")}, headers={"If-Match": '"wrongetag"'}, timeout=TIMEOUT)
    assert r.status_code == 412
    data = r.json()
    assert "detail" in data

def test_delete_book_soft_delete():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_already_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_apply_discount_rate_limit_exceeded():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    responses = []
    for _ in range(6):
        r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
        responses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in responses

def test_update_stock_positive_quantity():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["stock"] == 20

def test_upload_cover_unsupported_type():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"test", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    s = requests.Session()
    name = unique("tag")
    r = s.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    tag = create_tag(s)
    r = s.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data

def test_create_order_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"], stock=10)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    r = s.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert "total_price" in data

def test_update_order_status_valid():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"], stock=10)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_r = s.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    order = order_r.json()
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "shipped"

def test_bulk_create_books_missing_api_key():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    payload = {
        "books": [
            {
                "title": unique("bulk"),
                "isbn": unique("isbn")[:13],
                "price": 10.0,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    r = s.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_create_book_export_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/exports/books", json={"book_ids": [book["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data

def test_toggle_maintenance_missing_api_key():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data