import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    if not name: name = unique("author")
    return requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1990}, timeout=30).json()

def create_category(name=None):
    if not name: name = unique("category")
    return requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30).json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=payload, timeout=30).json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_valid_author():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_invalid_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_duplicate_category_name():
    name = unique("cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_with_stock_10():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    assert b["stock"] == 10

def test_create_book_invalid_isbn_length():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "t", "isbn": "123", "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_create_book_with_nonexistent_author():
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "t", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": 999, "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_list_books_pagination():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page_number():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=30)
    assert r.status_code == 422

def test_delete_book_cascade_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "test"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204
    assert requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).status_code == 404

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "tester"}, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "test"}, timeout=30)
    assert r.status_code == 422

def test_get_rating_empty_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] < 100.0

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_exceeds_max():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_increase():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_decrease_negative_result():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201

def test_create_duplicate_tag():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_add_multiple_tags_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 100}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=30)
    assert r.status_code == 200

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders?customer_name=test", timeout=30)
    assert r.status_code == 200

def test_change_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_change_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_change_status_cancel_restores_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).json()
    assert b_updated["stock"] == 10

def test_delete_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_get_author_details():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200

def test_get_category_details():
    c = create_category()
    r = requests.get(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 200

def test_get_tag_details():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.get(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 200

def test_update_book_title():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"title": "new"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["title"] == "new"

def test_delete_tag_used_in_books():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_get_order_details():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 200

def test_list_reviews_of_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_all_authors():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200

def test_list_all_categories():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=30)
    assert r.status_code == 404

def test_update_author_name():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "new"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "new"

def test_delete_category_assigned_to_books():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_rename_tag():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("tag")}, timeout=30)
    assert r.status_code == 200