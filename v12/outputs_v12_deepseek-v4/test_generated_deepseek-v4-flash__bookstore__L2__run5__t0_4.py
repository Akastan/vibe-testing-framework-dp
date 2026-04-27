import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("author")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session: requests.Session, author_id: int = None, category_id: int = None, isbn: str = None, stock: int = 10, published_year: int = 2020, price: float = 29.99) -> dict:
    if author_id is None:
        author = create_author(session)
        author_id = author["id"]
    if category_id is None:
        cat = create_category(session)
        category_id = cat["id"]
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
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

def create_tag(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("tag")[:30]
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    session = requests.Session()
    name = unique("author")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    session = requests.Session()
    payload = {}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    create_book(session, author_id=author["id"], category_id=cat["id"])
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_success():
    session = requests.Session()
    name = unique("cat")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category():
    session = requests.Session()
    name = unique("cat")
    payload = {"name": name}
    r1 = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r1.status_code == 201
    r2 = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

def test_delete_category_with_books_conflict():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    create_book(session, author_id=author["id"], category_id=cat["id"])
    r = session.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r1 = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r1.status_code == 201
    r2 = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    session = requests.Session()
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": cat["id"]
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_get_book_soft_deleted():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    r_get = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_get.status_code == 410
    data = r_get.json()
    assert "detail" in data

def test_soft_delete_book_success():
    session = requests.Session()
    book = create_book(session)
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_book_success():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    r_restore = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r_restore.status_code == 200
    data = r_restore.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_not_deleted_book():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    session = requests.Session()
    book = create_book(session)
    payload = {
        "rating": 5,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_create_review_soft_deleted_book():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    payload = {
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Nice"
    }
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_apply_discount_success():
    session = requests.Session()
    book = create_book(session, published_year=2020, price=100.0)
    payload = {"discount_percent": 20}
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_new_book():
    session = requests.Session()
    from datetime import datetime
    current_year = datetime.now().year
    book = create_book(session, published_year=current_year, price=50.0)
    payload = {"discount_percent": 10}
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_insufficient():
    session = requests.Session()
    book = create_book(session, stock=5)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_unsupported_type():
    session = requests.Session()
    book = create_book(session)
    files = {"file": ("test.txt", b"fake image content", "text/plain")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    session = requests.Session()
    name = unique("tag")[:30]
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_delete_tag_with_books_conflict():
    session = requests.Session()
    tag = create_tag(session)
    book = create_book(session)
    r_add = session.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r_add.status_code == 200
    r_del = session.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 409
    data = r_del.json()
    assert "detail" in data

def test_create_order_success():
    session = requests.Session()
    book = create_book(session, stock=10, price=25.0)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == 50.0

def test_create_order_insufficient_stock():
    session = requests.Session()
    book = create_book(session, stock=1, price=10.0)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_invalid_transition():
    session = requests.Session()
    book = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_update = session.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r_update.status_code == 400
    data = r_update.json()
    assert "detail" in data

def test_get_invoice_pending_order():
    session = requests.Session()
    book = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_invoice = session.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=TIMEOUT)
    assert r_invoice.status_code == 403
    data = r_invoice.json()
    assert "detail" in data

def test_add_item_to_non_pending_order():
    session = requests.Session()
    book1 = create_book(session, stock=10)
    book2 = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book1["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_confirm = session.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r_confirm.status_code == 200
    r_add = session.post(f"{BASE_URL}/orders/{order_id}/items", json={"book_id": book2["id"], "quantity": 1}, timeout=TIMEOUT)
    assert r_add.status_code == 403
    data = r_add.json()
    assert "detail" in data

def test_bulk_create_no_api_key():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    payload = {
        "books": [{
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 1,
            "author_id": author["id"],
            "category_id": cat["id"]
        }]
    }
    r = session.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_clone_book_success():
    session = requests.Session()
    book = create_book(session, stock=5, price=30.0)
    new_isbn = unique("clone")[:13]
    payload = {"new_isbn": new_isbn, "new_title": "Cloned Book", "stock": 3}
    r = session.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["stock"] == 3
    assert data["price"] == 30.0