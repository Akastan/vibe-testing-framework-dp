import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id=None, category_id=None, title=None, isbn=None, published_year=2020):
    a_id = author_id or create_author()["id"]
    c_id = category_id or create_category()["id"]
    payload = {
        "title": title or unique("Book"),
        "isbn": isbn or unique("ISBN"),
        "price": 100.0,
        "published_year": published_year,
        "stock": 10,
        "author_id": a_id,
        "category_id": c_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_create_author_valid():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_duplicate():
    name = unique("Cat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_valid():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "stock": 5, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["title"] == "Valid Book"

def test_create_book_invalid_year():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Old Book", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 999, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_create_book_nonexistent_author():
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "No Author", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "author_id": 99999, "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_get_book_details():
    b = create_book()
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]
    assert "tags" in r.json()

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_apply_discount_valid():
    b = create_book(published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_too_new():
    b = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_update_stock_increase():
    b = create_book()
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_insufficient():
    b = create_book()
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -50}, timeout=30)
    assert r.status_code == 400

def test_create_review_valid():
    b = create_book()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    b = create_book()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 422

def test_get_rating_empty():
    b = create_book()
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_add_tags_idempotent():
    b = create_book()
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_remove_tag_from_book():
    b = create_book()
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_valid():
    b = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    assert "total_price" in r.json()

def test_create_order_duplicate_items():
    b = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_insufficient_stock():
    b = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 99}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_pending_confirmed():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_status_cancel_restores_stock():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).json()
    assert b_updated["stock"] == 10

def test_delete_pending_order():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_error():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Joe", "customer_email": "joe@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=30)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "None"}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()