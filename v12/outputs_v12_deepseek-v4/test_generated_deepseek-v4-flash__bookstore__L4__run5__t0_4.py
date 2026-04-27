import uuid
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}


def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = f"Author_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_category(name=None):
    if name is None:
        name = f"Cat_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = f"Book_{uuid.uuid4().hex[:8]}"
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
        name = f"Tag_{uuid.uuid4().hex[:8]}"
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


def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020):
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn=isbn, stock=stock, price=price, published_year=published_year)
    return a, c, b


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_create_author_with_minimal_data():
    name = f"Min_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name


def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_create_author_name_too_long_returns_422():
    long_name = "A" * 101
    r = requests.post(f"{BASE_URL}/authors", json={"name": long_name}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_update_author_name_successfully():
    a = create_author()
    new_name = f"Updated_{uuid.uuid4().hex[:8]}"
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name


def test_delete_author_without_books_returns_204():
    a = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204


def test_create_category_with_duplicate_name_returns_409():
    name = f"DupCat_{uuid.uuid4().hex[:8]}"
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_delete_category_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_book_with_all_fields():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Full Book", "isbn": isbn, "price": 19.99,
        "published_year": 2021, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 19.99


def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Neg", "isbn": isbn, "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_create_book_with_duplicate_isbn_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": b["isbn"], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_book_with_nonexistent_author_returns_404():
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "NoAuthor", "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": 999999, "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()


def test_soft_delete_book_returns_204():
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
    r2 = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r2.status_code == 200


def test_restore_non_deleted_book_returns_400():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_apply_discount_to_old_book_returns_200():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0
    assert "original_price" in data


def test_apply_discount_to_new_book_returns_400():
    _, _, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_increase_stock_returns_updated_book():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15


def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_upload_cover_with_unsupported_type_returns_415():
    _, _, b = setup_book_with_deps()
    r = requests.post(
        f"{BASE_URL}/books/{b['id']}/cover",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        timeout=30,
    )
    assert r.status_code == 415
    assert "detail" in r.json()


def test_upload_cover_exceeding_size_limit_returns_413():
    _, _, b = setup_book_with_deps()
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(
        f"{BASE_URL}/books/{b['id']}/cover",
        files={"file": ("big.jpg", big_data, "image/jpeg")},
        timeout=30,
    )
    assert r.status_code == 413
    assert "detail" in r.json()


def test_create_review_on_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Eve"}, timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()


def test_create_tag_with_duplicate_name_returns_409():
    name = f"DupTag_{uuid.uuid4().hex[:8]}"
    create_tag(name=name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_delete_tag_attached_to_book_returns_409():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_order_insufficient_stock_returns_400():
    _, _, b = setup_book_with_deps(stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [{"book_id": b["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_create_order_with_duplicate_book_ids_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [
            {"book_id": b["id"], "quantity": 1},
            {"book_id": b["id"], "quantity": 2},
        ],
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_transition_order_from_pending_to_shipped_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_get_invoice_for_pending_order_returns_403():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    assert "detail" in r.json()