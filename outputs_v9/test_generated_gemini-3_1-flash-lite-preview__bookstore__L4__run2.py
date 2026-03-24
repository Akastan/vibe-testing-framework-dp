import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None, bio=None, born_year=1980):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("book")
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_book_valid():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_year():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Old Book", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 999, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    a = create_test_author()
    c = create_test_category()
    for i in range(3):
        create_test_book(a["id"], c["id"], isbn=unique("isbn"))

    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 2}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=30)
    assert r.status_code == 404

def test_apply_discount_new_book_fails():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], price=100.0, published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_increase_stock_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_insufficient():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 400

def test_create_review_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Fan", "comment": "Great!"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 6, "reviewer_name": "Hater"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_add_tags_to_book_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_remove_tags_from_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    assert requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).json()["stock"] == 9

def test_create_order_duplicate_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_illegal_transition():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_create_category_duplicate():
    name = unique("cat")
    create_test_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_category_with_books():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=30)
    assert r.status_code == 422

def test_delete_tag_in_use():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_list_orders_filter_customer():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Alice", "customer_email": "a@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Ali"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1

def test_delete_shipped_order_fails():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_get_books_invalid_pagination_params():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=30)
    assert r.status_code == 422

def test_create_order_malformed_json():
    r = requests.post(f"{BASE_URL}/orders", data='{"customer_name": "J",', headers={"Content-Type": "application/json"}, timeout=30)
    assert r.status_code == 422