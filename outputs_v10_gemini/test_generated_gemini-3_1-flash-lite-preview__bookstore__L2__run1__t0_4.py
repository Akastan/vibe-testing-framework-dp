import requests
import uuid
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# --- Helpers ---

def create_author():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1990}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("cat"), "description": "desc"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def create_tag():
    data = {"name": unique("tag")}
    return requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT).json()

# --- Tests ---

def test_health_check_returns_200():
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
    assert "detail" in r.json()

def test_create_duplicate_category_fails():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {
        "title": "Book", "isbn": "1234567890123", "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_nonexistent_author():
    c = create_category()
    data = {
        "title": "Book", "isbn": "1234567890123", "price": 10.0,
        "published_year": 2020, "author_id": 9999, "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total_pages" in data

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "comment": "Great", "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 10, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
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
    b = create_book(a["id"], c["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_update_stock_increase():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_result_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = create_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_remove_tags_from_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {
        "customer_name": "John", "customer_email": "john@test.com",
        "items": [{"book_id": b["id"], "quantity": 2}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    data = {
        "customer_name": "John", "customer_email": "john@test.com",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {
        "customer_name": "John", "customer_email": "john@test.com",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.com", "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10

def test_delete_pending_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.com", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_tag_in_use_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_invalid_payload_schema():
    r = requests.post(f"{BASE_URL}/books", json={"title": "Incomplete"}, timeout=TIMEOUT)
    assert r.status_code == 422