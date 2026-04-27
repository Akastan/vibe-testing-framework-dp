import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _create_author(name: str = None, bio: str = "Test bio", born_year: int = 1980) -> dict:
    if name is None:
        name = _unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_category(name: str = None, description: str = "Test category") -> dict:
    if name is None:
        name = _unique("cat")
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_book(
    title: str = None,
    isbn: str = None,
    price: float = 19.99,
    published_year: int = 2020,
    stock: int = 10,
    author_id: int = None,
    category_id: int = None,
) -> dict:
    if title is None:
        title = _unique("book")
    if isbn is None:
        isbn = _unique("isbn")[:13]
    if author_id is None:
        author = _create_author()
        author_id = author["id"]
    if category_id is None:
        category = _create_category()
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
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_tag(name: str = None) -> dict:
    if name is None:
        name = _unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_order(
    customer_name: str = None,
    customer_email: str = "test@example.com",
    items: list = None,
) -> dict:
    if customer_name is None:
        customer_name = _unique("cust")
    if items is None:
        book = _create_book(stock=10)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

# ── /authors POST ──

def test_create_author_success():
    name = _unique("author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Bio"
    assert data["born_year"] == 1990

def test_create_author_missing_name():
    payload = {"bio": "No name"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors GET ──

def test_list_authors_with_pagination():
    _create_author()
    _create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=100", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2

# ── /authors/{author_id} GET ──

def test_get_author_by_id_success():
    author = _create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} PUT ──

def test_update_author_name_success():
    author = _create_author()
    new_name = _unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

# ── /authors/{author_id} DELETE ──

def test_delete_author_without_books():
    author = _create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

# ── /categories POST ──

def test_create_category_success():
    name = _unique("cat")
    payload = {"name": name, "description": "Test"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category():
    name = _unique("cat")
    payload = {"name": name}
    r1 = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r1.status_code == 201
    r2 = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

# ── /categories/{category_id} GET ──

def test_get_category_by_id_success():
    cat = _create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cat["id"]

# ── /categories/{category_id} DELETE ──

def test_delete_category_with_books_conflict():
    cat = _create_category()
    author = _create_author()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ──

def test_create_book_success():
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 15,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 25.50

def test_create_book_duplicate_isbn():
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r1 = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r1.status_code == 201
    payload2 = {
        "title": _unique("book2"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=30)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

# ── /books GET ──

def test_list_books_with_search_filter():
    title = _unique("searchable")
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    r = requests.get(f"{BASE_URL}/books?search={title[:10]}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] >= 1

# ── /books/{book_id} GET ──

def test_get_book_by_id_success():
    book = _create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    book = _create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ──

def test_soft_delete_book_success():
    book = _create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

# ── /books/{book_id}/restore ──

def test_restore_soft_deleted_book():
    book = _create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r2.status_code == 200

# ── /books/{book_id}/reviews POST ──

def test_create_review_success():
    book = _create_book()
    payload = {"rating": 4, "reviewer_name": _unique("rev"), "comment": "Great book"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4
    assert data["reviewer_name"] == payload["reviewer_name"]

# ── /books/{book_id}/rating GET ──

def test_get_book_rating_with_reviews():
    book = _create_book()
    payload1 = {"rating": 5, "reviewer_name": _unique("rev"), "comment": "Excellent"}
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload1, timeout=30)
    payload2 = {"rating": 3, "reviewer_name": _unique("rev"), "comment": "Okay"}
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload2, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert data["average_rating"] == 4.0
    assert data["review_count"] == 2

# ── /books/{book_id}/discount POST ──

def test_apply_discount_to_old_book():
    book = _create_book(published_year=2020)
    payload = {"discount_percent": 20}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    expected = round(book["price"] * 0.8, 2)
    assert data["discounted_price"] == expected

def test_apply_discount_to_new_book():
    current_year = 2026
    book = _create_book(published_year=current_year)
    payload = {"discount_percent": 10}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ──

def test_update_stock_positive_delta():
    book = _create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient():
    book = _create_book(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /tags POST ──

def test_create_tag_success():
    name = _unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

# ── /books/{book_id}/tags POST ──

def test_add_tags_to_book_success():
    book = _create_book()
    tag1 = _create_tag()
    tag2 = _create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

# ── /orders POST ──

def test_create_order_success():
    book = _create_book(stock=10)
    payload = {
        "customer_name": _unique("cust"),
        "customer_email": "customer@test.com",
        "items": [{"book_id": book["id"], "quantity": 3}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_price"] == round(book["price"] * 3, 2)
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r2.json()["stock"] == 7

def test_create_order_insufficient_stock():
    book = _create_book(stock=2)
    payload = {
        "customer_name": _unique("cust"),
        "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 10}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ──

def test_update_order_status_valid_transition():
    order = _create_order()
    payload = {"status": "confirmed"}
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"