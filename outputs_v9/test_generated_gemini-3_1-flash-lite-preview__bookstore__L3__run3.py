import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Test bio", "born_year": 1980}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("Category"), "description": "Test cat"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    data = {
        "title": unique("Book"),
        "isbn": unique("ISBN"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_create_author_valid():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test"}, timeout=TIMEOUT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    resp = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    resp = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert resp.status_code == 409
    assert "detail" in resp.json()

def test_create_category_duplicate_name():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": unique("ISBN"), "price": 10.0, 
        "published_year": 2020, "stock": 10, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = unique("ISBN")
    requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10.0, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_get_nonexistent_book():
    resp = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_get_rating_null_for_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["average_rating"] is None

def test_apply_discount_new_book_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=datetime.now().year)
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "discounted_price" in resp.json()

def test_add_stock_positive_delta():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    resp = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["stock"] == 15

def test_remove_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    resp = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -11}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_create_tag_unique():
    resp = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert resp.status_code == 201

def test_delete_assigned_tag_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    resp = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert resp.status_code == 409

def test_add_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 1

def test_remove_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    resp = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 0

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_delete_order_shipped_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    resp = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert resp.status_code == 400

def test_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

def test_transition_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    resp = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_cancel_order_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@a.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_ref = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert b_ref["stock"] == 10

def test_health_check_ok():
    resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_list_books_pagination():
    resp = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "items" in resp.json()

def test_list_books_invalid_page():
    resp = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_list_orders_filtering():
    resp = requests.get(f"{BASE_URL}/orders", params={"customer_name": "NonExistent"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0

def test_list_authors_default():
    resp = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_list_authors_malformed_query_param():
    resp = requests.get(f"{BASE_URL}/authors", params={"limit": "abc"}, timeout=TIMEOUT)
    assert resp.status_code == 422