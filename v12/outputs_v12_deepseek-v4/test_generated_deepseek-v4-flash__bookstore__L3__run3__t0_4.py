import uuid
import requests
import io

BASE_URL = "http://localhost:8000"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: str = None, bio: str = "Bio", born_year: int = 1980):
    if name is None:
        name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: str = None, description: str = "Desc"):
    if name is None:
        name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": description}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id: int, category_id: int, title: str = None, isbn: str = None, price: float = 10.0, published_year: int = 2020, stock: int = 10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: str = None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name: str, customer_email: str, items: list):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──────────────────────────────────────────────────────────────

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

# ── /authors POST ─────────────────────────────────────────────────────────

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} GET ──────────────────────────────────────────────

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert "ETag" in r.headers

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} DELETE ───────────────────────────────────────────

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /categories POST ──────────────────────────────────────────────────────

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_duplicate_category_name():
    name = unique("catdup")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ───────────────────────────────────────────────────────────

def test_create_book_success():
    author = create_author()
    cat = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == title
    assert "id" in data

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": 999999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} GET ──────────────────────────────────────────────────

def test_get_book_success_with_etag():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "ETag" in r.headers

def test_get_book_soft_deleted_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ───────────────────────────────────────────────

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

# ── /books/{book_id}/restore POST ─────────────────────────────────────────

def test_restore_soft_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

# ── /books/{book_id}/reviews POST ─────────────────────────────────────────

def test_create_review_for_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    reviewer = unique("reviewer")
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "comment": "Great book",
        "reviewer_name": reviewer
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["reviewer_name"] == reviewer
    assert "id" in data

# ── /books/{book_id}/discount POST ────────────────────────────────────────

def test_apply_discount_to_old_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 80.0
    assert "original_price" in data

def test_apply_discount_to_new_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2026, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ──────────────────────────────────────────

def test_update_stock_positive_delta():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_result():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/cover POST ───────────────────────────────────────────

def test_upload_cover_valid_image():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.jpg", io.BytesIO(b"fake_jpeg_data"), "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "test.jpg"
    assert "size_bytes" in data

def test_upload_cover_unsupported_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", io.BytesIO(b"text data"), "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

# ── /tags POST ────────────────────────────────────────────────────────────

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

# ── /books/{book_id}/tags POST ────────────────────────────────────────────

def test_add_tags_to_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert any(t["id"] == tag["id"] for t in data["tags"])

# ── /orders POST ──────────────────────────────────────────────────────────

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    customer_name = unique("cust")
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["customer_name"] == customer_name
    assert "total_price" in data

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ───────────────────────────────────────

def test_update_order_status_valid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/invoice GET ────────────────────────────────────────

def test_get_invoice_for_confirmed_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data