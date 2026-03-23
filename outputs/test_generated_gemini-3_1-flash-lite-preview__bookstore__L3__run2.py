import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# --- Helpers ---

def create_author(name=None):
    name = name or unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("cat")
    data = {"name": name, "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, isbn=None, year=2020, stock=10):
    isbn = isbn or unique("isbn")
    data = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_tag(name=None):
    name = name or unique("tag")
    data = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

# --- Tests ---

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_author_success():
    name = unique("auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_duplicate_category_fails():
    name = unique("cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "1234567890", "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"], "stock": 10
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "9876543210"
    create_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_missing_relation():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B3", "isbn": "1111111111", "price": 10, "published_year": 2020, "author_id": 999, "category_id": 999
    }, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["page"] == 1

def test_filter_books_by_price():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?min_price=1&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_book_title():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"

def test_update_book_invalid_year():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 500}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    import datetime
    year = datetime.datetime.now().year
    book = create_book(auth["id"], cat["id"], year=year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_exceed_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_increase_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_decrease_stock_below_zero_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("t")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_duplicate_tag_fails():
    name = unique("t")
    create_tag(name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_assigned_tag_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["status"] == "pending"

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_transition_invalid_state():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    book_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_check["stock"] == 10

def test_delete_pending_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_delivered_order_fails():
    # Pozn: Pro test musime vytvorit order a posunout ho do stavu delivered
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "j@test.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_nonexistent_category():
    r = requests.get(f"{BASE_URL}/categories/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_nonexistent_order():
    r = requests.get(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_nonexistent_tag():
    r = requests.get(f"{BASE_URL}/tags/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_nonexistent_book():
    r = requests.put(f"{BASE_URL}/books/9999", json={"title": "test"}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_nonexistent_order():
    r = requests.delete(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_add_tags_nonexistent_book():
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/9999/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_nonexistent_book():
    r = requests.post(f"{BASE_URL}/books/9999/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_rating_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999/rating", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_stock_nonexistent_book():
    r = requests.patch(f"{BASE_URL}/books/9999/stock?quantity=1", timeout=TIMEOUT)
    assert r.status_code == 404

def test_patch_order_status_nonexistent():
    r = requests.patch(f"{BASE_URL}/orders/9999/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_tag_nonexistent():
    r = requests.put(f"{BASE_URL}/tags/9999", json={"name": "new"}, timeout=TIMEOUT)
    assert r.status_code == 404