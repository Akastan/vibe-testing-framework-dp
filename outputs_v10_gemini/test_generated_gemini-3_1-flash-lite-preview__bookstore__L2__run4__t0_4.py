import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1990}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("cat"), "description": "desc"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

def create_book(author_id, category_id):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_fails():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_duplicate_category_fails():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {
        "title": "Test Book", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn_fails():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    data = {
        "title": "B1", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_nonexistent_book_fails():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "comment": "Good", "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "T"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_new_book_fails():
    a = create_author()
    c = create_category()
    data = {
        "title": "New", "isbn": unique("isbn"), "price": 100.0,
        "published_year": datetime.now().year, "author_id": a["id"], "category_id": c["id"]
    }
    b = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_valid_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 90.0

def test_update_stock_increase():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_result_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -20}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_delete_tag_assigned_to_book_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {
        "customer_name": "John", "customer_email": "j@j.cz",
        "items": [{"book_id": b["id"], "quantity": 2}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["total_price"] == 200.0

def test_create_order_insufficient_stock_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {
        "customer_name": "John", "customer_email": "j@j.cz",
        "items": [{"book_id": b["id"], "quantity": 99}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_books_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {
        "customer_name": "John", "customer_email": "j@j.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_empty_cart_fails():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "e@e.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_pagination():
    r = requests.get(f"{BASE_URL}/orders?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_pending_order_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "e@e.cz",
        "items": [{"book_id": b["id"], "quantity": 2}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10

def test_delete_shipped_order_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "e@e.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "e@e.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "e@e.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "e@e.cz",
        "items": [{"book_id": b["id"], "quantity": 2}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10