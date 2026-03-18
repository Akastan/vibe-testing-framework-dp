import pytest
import requests
import uuid
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("ISBN")
    data = {
        "title": unique("Book"),
        "isbn": isbn[:13],
        "price": 100.0,
        "published_year": 2000,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_get_health_check():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_valid():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=30)
    assert r.status_code == 201

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_create_category_valid():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=30)
    assert r.status_code == 201

def test_create_duplicate_category():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_valid():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": unique("ISB"), "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201

def test_create_book_missing_fields():
    r = requests.post(f"{BASE_URL}/books", json={"title": "NoFields"}, timeout=30)
    assert r.status_code == 422

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = unique("ISBN")
    create_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_nonexistent_author():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "NoAuth", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "author_id": 999, "category_id": 1
    }, timeout=30)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=30)
    assert r.status_code == 200

def test_create_review_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 422

def test_get_book_rating_empty():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json().get("average_rating") is None

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    # Upravit rok, aby to nebyla novinka
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 1990}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_too_recent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    # Nastavit rok na aktuální
    requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": datetime.now().year}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_exceed_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_positive():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-50", timeout=30)
    assert r.status_code == 400

def test_add_tags_to_book_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_add_tags_nonexistent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201

def test_create_tag_duplicate():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_tag_in_use():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_create_order_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": []
    }, timeout=30)
    assert r.status_code == 422

def test_update_order_status_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_update_order_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_order_status_restock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 200

def test_delete_order_pending():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_order_shipped_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_get_author_details():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 200

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/9999", timeout=30)
    assert r.status_code == 404

def test_get_category_details():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 200

def test_get_book_full():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_update_book_info():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=30)
    assert r.status_code == 200

def test_update_book_invalid_isbn():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"isbn": "123"}, timeout=30)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=30)
    assert r.status_code == 200

def test_list_orders_customer_name():
    r = requests.get(f"{BASE_URL}/orders?customer_name=Test", timeout=30)
    assert r.status_code == 200

def test_remove_tag_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_update_tag_name():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 200

def test_list_authors_limit():
    r = requests.get(f"{BASE_URL}/authors?limit=5", timeout=30)
    assert r.status_code == 200

def test_delete_book_cascade_check():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204