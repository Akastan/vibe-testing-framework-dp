import requests
import uuid
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1980}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_test_category():
    data = {"name": unique("cat"), "description": "desc"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

def create_test_book(author_id, category_id, stock=10, year=2020):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_get_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = {"name": unique("auth"), "bio": "test", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_fail():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_duplicate_category():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    a = create_test_author()
    c = create_test_category()
    data = {"title": "Test Book", "isbn": "1234567890123", "price": 10.0, "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == "Test Book"

def test_create_book_duplicate_isbn():
    a = create_test_author()
    c = create_test_category()
    isbn = "1234567890"
    data = {"title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    data["title"] = "B2"
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_year():
    a = create_test_author()
    c = create_test_category()
    data = {"title": "B", "isbn": "1234567890", "price": 10.0, "published_year": 999, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    data = {"rating": 5, "reviewer_name": "Test", "comment": "Good"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "T"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_empty():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_new_book_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_old_book_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_exceed_limit():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_increase():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_decrease_negative_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_duplicate():
    n = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": n}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": n}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_tag_assigned_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_remove_tags_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=1)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 5}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_order_status_invalid_transition():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 5}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10

def test_delete_confirmed_order_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 2}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_book_price_valid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"price": 99.9}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["price"] == 99.9

def test_update_book_invalid_isbn():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"isbn": "short"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_category_success():
    c = create_test_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": unique("upd")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_reviews_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_tags_success():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_book_cascade_check():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_get_author_details():
    a = create_test_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_category_fail_if_books():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_book_non_integer():
    r = requests.get(f"{BASE_URL}/books/abc", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_success():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("upd")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_stock_boundary_zero():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 0

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_already_deleted_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 404

def test_login_with_malformed_json():
    r = requests.post(f"{BASE_URL}/auth/login", data="invalid json", headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()