import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020, author_name=None, cat_name=None):
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    a = create_author(name=author_name or unique("Author"))
    c = create_category(name=cat_name or unique("Cat"))
    b = create_book(a["id"], c["id"], isbn=isbn, stock=stock, price=price, published_year=published_year)
    return a, c, b

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["born_year"] == 1990

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_existing_author_returns_200():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == a["id"]

def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_without_books_returns_204():
    a = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_with_valid_name():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_existing_category_returns_200():
    c = create_category()
    r = requests.get(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == c["id"]

def test_create_book_with_all_required_fields():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": isbn, "price": 29.99,
        "published_year": 2020, "stock": 10,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad", "isbn": uuid.uuid4().hex[:13], "price": -5,
        "published_year": 2020, "stock": 10,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_existing_book_returns_200():
    _, _, b = setup_book_with_deps()
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_existing_book_returns_204():
    _, _, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_apply_discount_to_old_book_returns_200():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0

def test_apply_discount_to_new_book_returns_400():
    _, _, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_increase_stock_by_positive_quantity():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Alice"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_get_rating_for_book_with_reviews():
    _, _, b = setup_book_with_deps()
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 4, "reviewer_name": "Bob"}, timeout=30)
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 2, "reviewer_name": "Eve"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["average_rating"] == 3.0
    assert data["review_count"] == 2

def test_create_tag_with_valid_name():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_delete_tag_not_associated_with_books_returns_204():
    t = create_tag()
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 204

def test_add_tags_to_existing_book():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["tags"]) == 1

def test_create_order_with_valid_items():
    _, _, b = setup_book_with_deps(stock=10, price=50)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@test.com",
        "items": [{"book_id": b["id"], "quantity": 2}],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["total_price"] == 100.0

def test_create_order_with_insufficient_stock_returns_400():
    _, _, b = setup_book_with_deps(stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [{"book_id": b["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_transition_order_from_pending_to_confirmed():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_transition_order_from_pending_to_shipped_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    _, _, b = setup_book_with_deps(stock=10, price=50)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 2}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["subtotal"] == 100.0
    assert data["invoice_number"].startswith("INV-")

def test_get_invoice_for_pending_order_returns_403():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data