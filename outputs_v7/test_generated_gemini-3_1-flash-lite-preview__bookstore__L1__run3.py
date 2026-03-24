import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    return r.json()

def create_category():
    payload = {"name": unique("Cat")}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    return r.json()

def create_book(author_id, category_id, stock=10, year=2020):
    payload = {
        "title": unique("Book"),
        "isbn": f"{uuid.uuid4().hex[:10]}",
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_fails():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_duplicate_name():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_with_default_stock():
    a = create_author()
    c = create_category()
    payload = {
        "title": unique("Book"), "isbn": "1234567890", "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 0 # API schema default is 0

def test_create_book_invalid_isbn():
    r = requests.post(f"{BASE_URL}/books", json={"isbn": "123"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_nonexistent_author():
    c = create_category()
    payload = {
        "title": "Title", "isbn": "1234567890", "price": 10.0,
        "published_year": 2020, "author_id": 999, "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_price_filter():
    r = requests.get(f"{BASE_URL}/books?min_price=0", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_invalid_query_params():
    r = requests.get(f"{BASE_URL}/books?unknown=true", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_add_stock_positive_delta():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_negative_delta():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_reduce_stock_below_zero():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_old_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_new_book_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2025)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "error" in r.json()

def test_discount_exceeding_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_valid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {"rating": 5, "reviewer_name": "Test User"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_out_of_range():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "A"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_tags_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_nonexistent_tag():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tag_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    payload = {
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 10}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    payload = {
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    payload = {
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_malformed_json():
    r = requests.post(f"{BASE_URL}/orders", data="{invalid}", headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_delete_shipped_order_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    updated_book = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_create_duplicate_tag_name():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_tag_in_use_fails():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_book_invalid_year():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 500}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders?customer_name=NonExistent", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_author_data():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_category_data():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_book_cascade_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "A"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_update_tag_data():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("NewTag")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_empty_name():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_detail():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_reviews_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "A"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_empty():
    # Předpokládáme, že reset proběhl
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_categories_full():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_book_stock_nullable():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {
        "title": b["title"],
        "isbn": b["isbn"],
        "price": b["price"],
        "published_year": b["published_year"],
        "stock": None,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] is None

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_name_length():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "a"*101}, timeout=TIMEOUT)
    assert r.status_code == 422