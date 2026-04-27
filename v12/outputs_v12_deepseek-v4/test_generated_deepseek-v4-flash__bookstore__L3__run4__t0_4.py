import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session, name=None):
    if name is None:
        name = unique("author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session, name=None):
    if name is None:
        name = unique("cat")
    r = session.post(f"{BASE_URL}/categories", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, author_id, category_id, isbn=None, price=10.0, published_year=2020, stock=10, title=None):
    if isbn is None:
        isbn = unique("isbn")[:13]
    if title is None:
        title = unique("book")
    r = session.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(session, name=None):
    if name is None:
        name = unique("tag")[:30]
    r = session.post(f"{BASE_URL}/tags", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("author")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert "name" in data

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    author = create_author(requests.Session())
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    create_book(s, author["id"], cat["id"])
    r = s.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_create_duplicate_category_name():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    r = s.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 15.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["price"] == 15.0

def test_create_book_duplicate_isbn():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    isbn = unique("isbn")[:13]
    s.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = s.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    cat = create_category(requests.Session())
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": 99999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    create_book(s, author["id"], cat["id"], price=20.0, published_year=2022)
    r = s.get(f"{BASE_URL}/books?min_price=15&max_price=25&category_id={cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_soft_deleted_returns_410():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = s.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_apply_discount_old_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], published_year=2020, price=100.0)
    r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_new_book_fails():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    current_year = 2026
    book = create_book(s, author["id"], cat["id"], published_year=current_year, price=50.0)
    r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_positive_delta():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=10)
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_negative_delta():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=3)
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_valid_image():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert data["content_type"] == "image/jpeg"

def test_upload_cover_unsupported_type():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"text data", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")[:30]}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_add_tags_to_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    tag1 = create_tag(s)
    tag2 = create_tag(s)
    r = s.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag1["id"], tag2["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    assert len(data["tags"]) == 2

def test_create_order_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=10, price=25.0)
    r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == 50.0

def test_create_order_insufficient_stock():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=1)
    r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=5)
    order_r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_r.json()
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=5)
    order_r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_r.json()
    s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data