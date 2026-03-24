import requests
import uuid
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# Helper functions
def create_author():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=TIMEOUT)
    return resp.json()

def create_category():
    name = unique("Cat")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=TIMEOUT)
    return resp.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": f"978{uuid.uuid4().hex[:7]}",
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    return resp.json()

def test_get_health_status():
    resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_create_valid_author():
    name = unique("Author")
    resp = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["name"] == name

def test_create_invalid_author_no_name():
    resp = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    resp = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert resp.status_code == 409

def test_delete_nonexistent_author():
    resp = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_create_valid_category():
    name = unique("Cat")
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["name"] == name

def test_create_duplicate_category():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    resp = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 409

def test_create_valid_book_with_stock():
    auth = create_author()
    cat = create_category()
    data = {"title": "Test", "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "stock": 10, "author_id": auth["id"], "category_id": cat["id"]}
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["stock"] == 10

def test_create_book_invalid_isbn():
    auth = create_author()
    cat = create_category()
    data = {"title": "Test", "isbn": "123", "price": 10.0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_create_book_missing_author():
    cat = create_category()
    data = {"title": "Test", "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "author_id": 999, "category_id": cat["id"]}
    resp = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert resp.status_code == 404

def test_get_existing_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["id"] == book["id"]

def test_get_nonexistent_book():
    resp = requests.get(f"{BASE_URL}/books/9999", timeout=TIMEOUT)
    assert resp.status_code == 404

def test_create_valid_review():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Reviewer"}
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert resp.json()["rating"] == 5

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 10, "reviewer_name": "Reviewer"}
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_get_rating_empty_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["average_rating"] is None

def test_apply_discount_old_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "discounted_price" in resp.json()

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    # Manual create for new year
    data = {"title": "New", "isbn": "9781234567890", "price": 100, "published_year": datetime.now().year, "author_id": auth["id"], "category_id": cat["id"]}
    book = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_apply_discount_over_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_update_stock_positive_delta():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["stock"] == 15

def test_update_stock_negative_delta_insufficient():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -20}, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_create_valid_tag():
    name = unique("Tag")
    resp = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert resp.status_code == 201

def test_create_tag_too_long():
    resp = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_add_tags_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 1

def test_add_invalid_tags():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert resp.status_code == 404

def test_remove_tags_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    resp = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 0

def test_create_valid_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Jmeno", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}
    resp = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert resp.status_code == 201
    assert "total_price" in resp.json()

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Jmeno", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 100}]}
    resp = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}
    resp = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert resp.status_code == 400

def test_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    resp = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

def test_transition_delivered_to_shipped():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()

    # Transition to shipped
    resp = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"

    # Transition to delivered
    resp_del = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "delivered"

    # Try to go back from delivered to shipped (negative test)
    resp2 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert resp2.status_code == 400
    data = resp2.json()
    assert "error" in data or "detail" in data

def test_delete_pending_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    resp = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert resp.status_code == 204

def test_delete_shipped_order_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    resp = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert resp.status_code == 400

def test_list_authors():
    resp = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_list_authors_pagination():
    resp = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 10}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_list_categories():
    resp = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_list_tags():
    resp = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_list_books_paginated():
    resp = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "items" in resp.json()

def test_search_books_by_title():
    resp = requests.get(f"{BASE_URL}/books", params={"search": "test"}, timeout=TIMEOUT)
    assert resp.status_code == 200

def test_filter_books_by_price():
    resp = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=TIMEOUT)
    assert resp.status_code == 200

def test_list_books_negative_page():
    resp = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_update_book_price():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": 150.0}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["price"] == 150.0

def test_update_book_negative_price():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": -1.0}, timeout=TIMEOUT)
    assert resp.status_code == 422

def test_delete_book_cascade_check():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    resp = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert resp.status_code == 204

def test_get_author_details():
    auth = create_author()
    resp = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_get_category_details():
    cat = create_category()
    resp = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_get_tag_details():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    resp = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_list_orders_filtering():
    resp = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Test"}, timeout=TIMEOUT)
    assert resp.status_code == 200

def test_list_orders_no_results():
    resp = requests.get(f"{BASE_URL}/orders", params={"status": "shipped"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "page": 1, "size": 50}

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    resp = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert resp.status_code == 200

def test_get_nonexistent_order():
    resp = requests.get(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert resp.status_code == 404