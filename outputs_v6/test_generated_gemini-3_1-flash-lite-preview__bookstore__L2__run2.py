import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test", "born_year": 1990}, timeout=TIMEOUT)
    return resp.json()

def create_category():
    name = unique("Category")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "test"}, timeout=TIMEOUT)
    return resp.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": unique("978")[0:13],
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    return resp.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "1234567890123", "price": 10, "published_year": 2020, "stock": 10,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1111111111"
    payload = {"title": "B1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={**payload, "title": "B2"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_nonexistent_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": 999, "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books", params={"search": "test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_pagination_params():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_apply_discount_old_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    data = {"title": "New", "isbn": "9876543210987", "price": 10, "published_year": datetime.now().year, "author_id": auth["id"], "category_id": cat["id"]}
    book = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_invalid_percent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_remove_stock_too_much_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -20}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "U"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_empty_body():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_duplicate_tag_fails():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_add_nonexistent_tag_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [9999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tag_from_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "total_price" in r.json()

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 99}]}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_books():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_valid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_returns_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 5}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert b_check["stock"] == 10

def test_update_status_nonexistent_order():
    r = requests.patch(f"{BASE_URL}/orders/999/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_pending_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_category_invalid_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_category_conflict():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_tag_in_use_conflict():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "John"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_book_title():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"

def test_update_book_invalid_isbn_format():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"isbn": "123"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_all_categories():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_book_cascades():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "U"}, timeout=TIMEOUT)
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_reviews_for_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]