import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None, bio=None, born_year=1980):
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name or unique("author"), "bio": bio, "born_year": born_year
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name or unique("cat")}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title or unique("book"), 
        "isbn": isbn or unique("isbn"), 
        "price": price,
        "published_year": published_year, 
        "stock": stock,
        "author_id": author_id, 
        "category_id": category_id,
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    r = requests.post(f"{BASE_URL}/tags", json={"name": name or unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    name = unique("auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_authors_default():
    create_test_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_found():
    a = create_test_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == a["id"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_author_name():
    a = create_test_author()
    new_name = unique("new_name")
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_author_conflict():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_duplicate():
    name = unique("dup")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_category_conflict():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("isbn"), "price": 10, "published_year": 2020, "stock": 10,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    a = create_test_author()
    c = create_test_category()
    isbn = unique("isbn")
    create_test_book(a["id"], c["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_book_invalid_year():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 500}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_reviews_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_rating_empty():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=2000, price=100)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_new_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=2024, price=100)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "error" in r.json()

def test_add_stock_delta():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_insufficient():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_tag_in_use():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_tags_nonexistent():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    t = create_test_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_duplicate_book():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_stock_shortage():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Test"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_details():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = create_test_order("Test", "t@t.cz", [{"book_id": b["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_status_pending_to_confirmed():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = create_test_order("Test", "t@t.cz", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = create_test_order("Test", "t@t.cz", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_returns_stock():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = create_test_order("Test", "t@t.cz", [{"book_id": b["id"], "quantity": 5}])
    requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    b_check = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert b_check.json()["stock"] == 10

def test_delete_delivered_order_denied():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    o = create_test_order("Test", "t@t.cz", [{"book_id": b["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_book_min_price():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Zero", "isbn": unique("i"), "price": 0.0, "published_year": 2020,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_book_max_published_year():
    a = create_test_author()
    c = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Future", "isbn": unique("i"), "price": 10, "published_year": 2026,
        "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_update_stock_huge_delta():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10000}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_tags_empty():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == []

    tag = create_test_tag()

    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    tags = r.json()
    assert isinstance(tags, list)
    assert len(tags) == 1
    assert tags[0]["id"] == tag["id"]
    assert tags[0]["name"] == tag["name"]

def test_create_review_min_rating():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 1, "reviewer_name": "T"
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_apply_discount_max_percent():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], published_year=2000, price=100)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 50.0

def test_create_order_long_email():
    a = create_test_author()
    c = create_test_category()
    b = create_test_book(a["id"], c["id"], stock=10)
    email = "a" * 190 + "@test.cz"
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": email,
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_list_books_search_case_insensitive():
    a = create_test_author()
    c = create_test_category()
    create_test_book(a["id"], c["id"], title="MiXeDcAsE")
    r = requests.get(f"{BASE_URL}/books", params={"search": "mixed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1

def test_update_category_name_same():
    c = create_test_category(name="same")
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": "same"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_empty_payload():
    c = create_test_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={}, timeout=TIMEOUT)
    assert r.status_code == 200