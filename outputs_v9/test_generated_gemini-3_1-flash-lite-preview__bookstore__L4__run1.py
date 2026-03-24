import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    if name is None: name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    if name is None: name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, isbn=None, stock=10, year=2020):
    if isbn is None: isbn = unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": isbn, "price": 100.0,
        "published_year": year, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_author_valid():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 2000}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_conflict():
    author = create_test_author()
    cat = create_test_category()
    create_test_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "New Book", "isbn": unique("isbn"), "price": 50.0,
        "published_year": 2020, "stock": 10, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    auth = create_test_author()
    cat = create_test_category()
    isbn = unique("isbn")
    create_test_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_apply_discount_old_book():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_new_book_fails():
    import datetime
    auth = create_test_author()
    cat = create_test_category()
    current_year = datetime.datetime.now().year
    book = create_test_book(auth["id"], cat["id"], year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "error" in r.json()

def test_update_stock_add_positive():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_update_stock_negative_below_zero():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 400

def test_create_tag_valid():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422

def test_add_tags_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["total_price"] == 200.0

def test_create_order_insufficient_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_change_status_valid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_change_status_invalid_transition():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.json()["stock"] == 10

def test_delete_pending_order_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books", params={"search": "nothing"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["total"] == 0

def test_list_books_invalid_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_create_duplicate_category():
    name = unique("cat")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_tag_attached_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_nonexistent_tag():
    r = requests.delete(f"{BASE_URL}/tags/999999", timeout=30)
    assert r.status_code == 404