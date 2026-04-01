import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    return r.json()

def create_category():
    payload = {"name": unique("Category"), "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    return r.json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    payload = {
        "title": unique("Book"),
        "isbn": unique("97801")[0:13],
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()
    assert r.json()["name"] == payload["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    assert book["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890123"
    payload = {"title": "B1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    payload = {"rating": 5, "reviewer_name": "Tester", "comment": "Great"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["book_id"] == book["id"]

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() is None or "average_rating" not in r.json() or r.json().get("average_rating") is None

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_too_high():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_increase():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_result():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(t["id"] == tag["id"] for t in r.json()["tags"])

def test_remove_tags_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert not any(t["id"] == tag["id"] for t in r.json()["tags"])

def test_create_category_duplicate():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "d"}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "d"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_delete_assigned_tag_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    payload = {
        "customer_name": "Test",
        "customer_email": "test@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    payload = {
        "customer_name": "Test",
        "customer_email": "test@test.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    payload = {
        "customer_name": "Test",
        "customer_email": "test@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_orders_filter_by_name():
    r = requests.get(f"{BASE_URL}/orders?customer_name=NonExistent", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_confirmed_order_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_returns_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 5}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_get_category_success():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat["id"]

def test_update_book_invalid_year():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 900}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_book_malformed_json():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", data="invalid json", headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()