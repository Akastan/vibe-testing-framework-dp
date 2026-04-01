import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("Author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    payload = {"bio": "Missing name"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("Auth")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("ISBN"), "price": 100, 
        "published_year": 2020, "stock": 10, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    payload = {
        "title": "Book", "isbn": unique("ISBN"), "price": 100, 
        "published_year": 2020, "stock": 10, "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    isbn = unique("ISBN")
    data = {"title": "B", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_new_book_fails():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": unique("ISBN"), "price": 100, "published_year": 2026, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_valid_book():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "Old", "isbn": unique("ISBN"), "price": 100, "published_year": 2000, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_update_stock_increase():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 5
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_update_stock_negative_result_fails():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 5
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_to_book():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_remove_tags_from_book():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_review_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_get_rating_no_reviews():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_category_duplicate_fails():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long_fails():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_assigned_tag_fails():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_order_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 1
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 99}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_invalid_transition():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_delete_confirmed_order_fails():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_filter_books_by_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_orders_invalid_page():
    r = requests.get(f"{BASE_URL}/orders", params={"page": -1}, timeout=TIMEOUT)
    assert r.status_code == 422