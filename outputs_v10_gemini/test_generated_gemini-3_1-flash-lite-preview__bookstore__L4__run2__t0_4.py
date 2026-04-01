import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None, bio=None, born_year=1980):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("book")
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_not_found():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_duplicate():
    name = unique("cat")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_valid():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_year():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad Year", "isbn": "1234567890", "price": 10.0,
        "published_year": 900, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester", "comment": "Great"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 6, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["average_rating"] is None

def test_apply_discount_new_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_invalid_percent():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_add():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_result():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_nonexistent():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [99999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_order_insufficient_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r_post = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_id = r_post.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order_id

def test_update_status_invalid_transition():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r_post = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_id = r_post.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_cancel_restores_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r_post = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    order_id = r_post.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.json()["stock"] == 10

def test_delete_confirmed_order_forbidden():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r_post = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_id = r_post.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_filter_name():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "NonExistent"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_update_tag_duplicate_name():
    t1 = create_test_tag(name="tag1")
    t2 = create_test_tag(name="tag2")
    r = requests.put(f"{BASE_URL}/tags/{t2['id']}", json={"name": "tag1"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_remove_non_existent_tag_from_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_authors_empty_db():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_review_malformed_json():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", data="invalid json", headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    assert r.status_code == 422