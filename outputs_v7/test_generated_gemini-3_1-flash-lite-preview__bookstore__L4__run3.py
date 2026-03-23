import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, isbn=None, stock=10, published_year=2020):
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": isbn, "price": 100.0,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    data = create_test_author()
    assert "id" in data
    assert "created_at" in data

def test_create_author_invalid_name_length():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_list_authors_pagination():
    create_test_author()
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 10}, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_author_success():
    a = create_test_author()
    new_name = unique("new")
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_create_category_valid():
    data = create_test_category()
    assert "id" in data

def test_create_category_duplicate():
    name = unique("cat")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    a = create_test_author()
    c = create_test_category()
    data = create_test_book(a["id"], c["id"], stock=10)
    assert data["stock"] == 10

def test_create_book_missing_author():
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Fail", "isbn": unique("isbn"), "price": 10,
        "published_year": 2020, "author_id": 999, "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_list_books_search_filter():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"], isbn="1234567890")
    r = requests.get(f"{BASE_URL}/books", params={"search": "1234"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) > 0

def test_list_books_invalid_page_number():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=30)
    assert r.status_code == 422

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=30)
    assert r.status_code == 404

def test_create_review_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Test", "comment": "Nice"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Test"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_new_book_fails():
    a = create_test_author()
    c = create_test_category()
    current_year = datetime.now(timezone.utc).year
    b = create_test_book(a["id"], c["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_valid_limit():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 50}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 50.0

def test_update_stock_increase():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_excessive():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_create_tag_valid():
    data = create_test_tag()
    assert "id" in data

def test_add_tags_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_remove_tags_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_full_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_empty_items_array():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com", "items": []
    }, timeout=30)
    assert r.status_code == 422

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "NonExistent"}, timeout=30)
    assert r.status_code == 200

def test_get_order_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == o["id"]

def test_status_transition_pending_to_confirmed():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_status_transition_invalid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_delivered_order_fails():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_delete_author_unused():
    a = create_test_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_category_unused():
    c = create_test_category()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_category_with_books_fails():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_book_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_tag_success():
    t = create_test_tag()
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_tag_attached_fails():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_invalid_isbn_short():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "123", "price": 10, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_create_book_invalid_year_low():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "1234567890", "price": 10, "published_year": 500,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_tag_rename():
    t = create_test_tag()
    new_name = unique("tag")
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_tag_nonexistent():
    r = requests.put(f"{BASE_URL}/tags/9999", json={"name": "new"}, timeout=30)
    assert r.status_code == 404

def test_update_stock_boundary_zero():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 0

def test_list_reviews_empty():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=30)
    assert r.status_code == 200
    assert r.json() == []

def test_update_category_name():
    c = create_test_category()
    new_name = unique("cat")
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_remove_tag_not_present_in_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200

def test_list_orders_pagination_params():
    r = requests.get(f"{BASE_URL}/orders", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_price_filtering():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"], isbn="9876543210")
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=30)
    assert r.status_code == 200

def test_status_cancel_restores_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.json()["stock"] == 10