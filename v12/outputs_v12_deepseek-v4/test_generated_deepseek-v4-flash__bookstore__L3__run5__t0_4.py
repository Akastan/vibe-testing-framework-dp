import uuid
import requests
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(
    title: Optional[str] = None,
    isbn: Optional[str] = None,
    price: float = 10.0,
    published_year: int = 2020,
    stock: int = 10,
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = unique("ISBN")[:13]
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(
    customer_name: Optional[str] = None,
    customer_email: str = "test@example.com",
    items: Optional[list] = None,
) -> Dict[str, Any]:
    if customer_name is None:
        customer_name = unique("Customer")
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──────────────────────────────────────────────

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

# ── /authors POST ────────────────────────────────────────

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1980}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors GET ─────────────────────────────────────────

def test_list_authors_with_pagination():
    create_author()
    create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=1", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

# ── /authors/{author_id} GET ─────────────────────────────

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} PUT ─────────────────────────────

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

# ── /authors/{author_id} DELETE ──────────────────────────

def test_delete_author_without_books_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /categories POST ─────────────────────────────────────

def test_create_category_success():
    name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ──────────────────────────────────────────

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 2,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_invalid_price_returns_422():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": -5.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /books GET ───────────────────────────────────────────

def test_list_books_with_filters():
    create_book()
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5&min_price=0&max_price=100", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

# ── /books/{book_id} GET ─────────────────────────────────

def test_get_book_by_id_success():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ──────────────────────────────

def test_soft_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

# ── /books/{book_id}/restore POST ────────────────────────

def test_restore_soft_deleted_book_success():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/reviews POST ────────────────────────

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "comment": "Great book",
        "reviewer_name": unique("Reviewer"),
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

# ── /books/{book_id}/discount POST ───────────────────────

def test_apply_discount_to_old_book_success():
    book = create_book(published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] > data["discounted_price"]

def test_apply_discount_to_new_book_returns_400():
    from datetime import datetime
    current_year = datetime.now().year
    book = create_book(published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ─────────────────────────

def test_update_stock_positive_delta_success():
    book = create_book(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders POST ─────────────────────────────────────────

def test_create_order_success():
    book = create_book(stock=5)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "buyer@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}],
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "buyer@example.com",
        "items": [{"book_id": book["id"], "quantity": 10}],
    }, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ──────────────────────

def test_update_order_status_valid_transition():
    order = create_order()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    order = create_order()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/invoice GET ───────────────────────

def test_get_invoice_for_confirmed_order_success():
    order = create_order()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]