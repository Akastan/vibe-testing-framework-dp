import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("category")
    data = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

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
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_conflict():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_duplicate_name():
    name = unique("cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    assert book["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890123"
    create_book(auth["id"], cat["id"]) # Creates unique ISBN internally
    data = {"title": "x", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_author():
    data = {"title": "x", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": 999, "category_id": 1}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 1}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total_pages" in data

def test_list_books_price_filter():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", 
                      json={"rating": 5, "reviewer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", 
                      json={"rating": 10, "reviewer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                      json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", 
                      json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_stock_increase():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = r_tag.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = r_tag.json()["id"]
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    data = {"customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 10}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_price_capture():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.json()["total_price"] == 100.0

def test_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_transition_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_stock_return():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 2}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    book_updated = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_updated["stock"] == 5

def test_delete_shipped_order_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "x" * 100}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_tag_in_use():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_category_name():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": unique("new")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_duplicate():
    cat1 = create_category(unique("cat1"))
    cat2 = create_category(unique("cat2"))
    r = requests.put(f"{BASE_URL}/categories/{cat2['id']}", json={"name": cat1["name"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_book_price_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": -10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_book_isbn_conflict():
    auth = create_author()
    cat = create_category()
    b1 = create_book(auth["id"], cat["id"])
    b2 = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{b2['id']}", json={"isbn": b1["isbn"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_orders_filter_name():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Nonexistent"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_pagination_bounds():
    r = requests.get(f"{BASE_URL}/orders", params={"page": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_reviews_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999/reviews", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_category_with_books():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_update_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("tagnew")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_invalid_year():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"born_year": 3000}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_boundary():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 0

def test_get_order_nonexistent():
    r = requests.get(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_patch_order_invalid_payload_schema():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"invalid": "payload"}, timeout=TIMEOUT)
    assert r.status_code == 422