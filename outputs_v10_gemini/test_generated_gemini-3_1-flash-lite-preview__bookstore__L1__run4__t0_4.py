import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author")}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("cat")}
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

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    data = {"name": unique("author")}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_category_duplicate_fails():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    cat = create_category()
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 10.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_year():
    author = create_author()
    cat = create_category()
    data = {
        "title": "Bad Year",
        "isbn": "1234567890",
        "price": 10.0,
        "published_year": 999,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_new_book_fails():
    import datetime
    current_year = datetime.datetime.now().year
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_valid_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_update_stock_increase():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_result_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_to_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_remove_tags_from_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Tester", "comment": "Great"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_get_rating_no_reviews():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_delete_tag_in_use_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    data = {
        "customer_name": "John",
        "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    data = {
        "customer_name": "John",
        "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    data = {
        "customer_name": "John",
        "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_orders_pagination():
    r = requests.get(f"{BASE_URL}/orders?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_order_detail():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_pending_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_returns_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_list_authors_default_params():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_category_not_found():
    r = requests.get(f"{BASE_URL}/categories/99999", timeout=TIMEOUT)
    assert r.status_code == 404