import pytest
import requests
import uuid
import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name or unique("author"),
        "born_year": 1990
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name or unique("cat")}, timeout=30)
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
        "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    r = requests.post(f"{BASE_URL}/tags", json={"name": name or unique("tag")}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_order(customer_name, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": "test@example.com",
        "items": items
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_get_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_delete_author_dependency_conflict():
    author = create_test_author()
    cat = create_test_category()
    create_test_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_category_valid():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_duplicate():
    name = unique("cat")
    create_test_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_update_category_name():
    cat = create_test_category()
    new_name = unique("newcat")
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_create_book_success():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": unique("isbn"), "price": 10.0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_isbn_duplicate():
    auth = create_test_author()
    cat = create_test_category()
    isbn = unique("isbn")
    create_test_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_invalid_year():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "BadYear", "isbn": unique("isbn"), "price": 10.0, "published_year": 999, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books", params={"search": "test"}, timeout=30)
    assert r.status_code == 200

def test_get_book_details():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_create_review_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Reviewer"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_out_of_range():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Bad"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_empty():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_too_new():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=datetime.datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_over_limit():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_add_stock_delta():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_reduce_stock_negative_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_idempotent():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_add_tags_nonexistent():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tags_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_create_order_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=20)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
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

def test_update_status_pending_to_confirmed():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_status_cancel_restores_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 5}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.json()["stock"] == 10

def test_delete_order_pending_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 1}])
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_order_shipped_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_list_orders_filter_by_name():
    create_test_order("UniqueName123", [{"book_id": 1, "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "UniqueName123"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) > 0

def test_list_orders_pagination_check():
    r = requests.get(f"{BASE_URL}/orders", params={"page": 1, "page_size": 2}, timeout=30)
    assert r.status_code == 200

def test_delete_category_conflict():
    cat = create_test_category()
    auth = create_test_author()
    create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_tag_in_use():
    tag = create_test_tag()
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_update_author_name_valid():
    auth = create_test_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "NewName"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "NewName"

def test_update_book_price_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": 99.9}, timeout=30)
    assert r.status_code == 200
    assert r.json()["price"] == 99.9

def test_list_books_min_price_filter():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=30)
    assert r.status_code == 200

def test_list_books_max_price_filter():
    r = requests.get(f"{BASE_URL}/books", params={"max_price": 1000}, timeout=30)
    assert r.status_code == 200

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=30)
    assert r.status_code == 422

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200

def test_get_single_order():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = create_test_order("Test", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]

def test_delete_book_cascade():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_create_order_invalid_payload_structure():
    r = requests.post(f"{BASE_URL}/orders", json={"wrong": "field"}, timeout=30)
    assert r.status_code == 422