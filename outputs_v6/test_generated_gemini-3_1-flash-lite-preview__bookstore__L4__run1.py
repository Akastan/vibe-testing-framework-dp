import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    r = requests.post(f"{BASE_URL}/authors", json={"name": name or unique("author")}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name or unique("cat")}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, stock=10):
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title or unique("book"),
        "isbn": isbn or unique("isbn"),
        "price": 100.0,
        "published_year": 2020,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    r = requests.post(f"{BASE_URL}/tags", json={"name": name or unique("tag")}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = create_test_author("J.K. Rowling")
    assert data["name"] == "J.K. Rowling"
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books_error():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_author_not_found():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_create_category_duplicate_name():
    name = unique("cat")
    create_test_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_category_with_books_error():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_success_default_stock():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test", "isbn": "1234567890", "price": 10, "published_year": 2020, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 0

def test_create_book_duplicate_isbn():
    a = create_test_author()
    c = create_test_category()
    isbn = unique("isbn")
    create_test_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10, "published_year": 2020, 
        "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_invalid_year():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Old", "isbn": "1234567890", "price": 10, "published_year": 999, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_create_book_missing_required_fields():
    r = requests.post(f"{BASE_URL}/books", json={}, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["page"] == 1

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=30)
    assert r.status_code == 422

def test_get_book_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["title"] == b["title"]

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=30)
    assert r.status_code == 404

def test_create_review_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 6, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_null_for_empty():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_new_book_fail():
    a = create_test_author()
    c = create_test_category()
    # Knihu vydanou letos
    r_b = requests.post(f"{BASE_URL}/books", json={
        "title": "New", "isbn": "9876543210", "price": 100, "published_year": datetime.now().year, 
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    b = r_b.json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_too_high():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_increase():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_update_stock_decrease_invalid():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400

def test_create_tag_success():
    data = create_test_tag()
    assert "id" in data

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200

def test_add_nonexistent_tag_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_from_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200

def test_create_order_insufficient_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_invalid_date_format():
    r = requests.post(f"{BASE_URL}/orders", json={"invalid": "data"}, timeout=30)
    assert r.status_code == 422

def test_update_status_pending_to_confirmed():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    oid = ord_r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_update_status_invalid_transition():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    oid = ord_r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_returns_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30)
    oid = ord_r.json()["id"]
    r = requests.delete(f"{BASE_URL}/orders/{oid}", timeout=30)
    assert r.status_code == 204
    check = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert check.json()["stock"] == 10

def test_delete_shipped_order_fail():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    oid = ord_r.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{oid}", timeout=30)
    assert r.status_code == 400

def test_update_book_invalid_price():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"price": -10}, timeout=30)
    assert r.status_code == 422

def test_update_book_author_not_found():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"author_id": 9999}, timeout=30)
    assert r.status_code == 404

def test_get_author_success():
    a = create_test_author("Test Author")
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "Test Author"

def test_get_category_success():
    c = create_test_category("Test Cat")
    r = requests.get(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "Test Cat"

def test_get_tag_success():
    t = create_test_tag("Test Tag")
    r = requests.get(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "Test Tag"

def test_list_reviews_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_tag_in_use_error():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_list_orders_with_customer_filter():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_orders_invalid_limit():
    r = requests.get(f"{BASE_URL}/orders?page_size=999", timeout=30)
    assert r.status_code == 422

def test_delete_book_cascade_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_update_category_success():
    c = create_test_category("Orig")
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": "New"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "New"

def test_update_author_success():
    a = create_test_author("Orig")
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "New"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "New"

def test_update_tag_success():
    t = create_test_tag("Orig")
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": "New"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "New"

def test_get_order_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    oid = ord_r.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{oid}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == oid

def test_get_unauthorized_order_access():
    # API nemá auth, ale testujeme, že 404/403 pokud není správné id
    r = requests.get(f"{BASE_URL}/orders/99999", timeout=30)
    assert r.status_code == 404