import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    r = requests.post(f"{BASE_URL}/authors", json={"name": name or unique("author")}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name or unique("cat")}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, isbn=None, stock=10, published_year=2020):
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn or unique("isbn"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    r = requests.post(f"{BASE_URL}/tags", json={"name": name or unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def test_health_check():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_success():
    auth = create_test_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == auth["id"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_duplicate_name():
    name = unique("cat")
    create_test_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_category_success():
    cat = create_test_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_category_with_books_conflict():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Title", "isbn": "1234567890", "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == "Title"

def test_create_book_invalid_isbn_length():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "123", "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_duplicate_isbn():
    auth = create_test_author()
    cat = create_test_category()
    isbn = "9876543210"
    create_test_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"], isbn="1111111111")
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 1}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["page"] == 1

def test_list_books_filter_by_price():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"], isbn="2222222222")
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Reviewer"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 9, "reviewer_name": "Reviewer"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_empty_book():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_new_book_fails():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_above_limit():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_increase():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_update_stock_decrease_invalid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "total_price" in r.json()

def test_create_order_insufficient_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_order_transition_pending_to_confirmed():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_order_transition_invalid():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_order_cancel_restores_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.json()["stock"] == 10

def test_delete_pending_order_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    r = requests.delete(f"{BASE_URL}/orders/{ord_id}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_error():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{ord_id}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{ord_id}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_author_data():
    auth = create_test_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "New Name"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"

def test_update_category_data():
    cat = create_test_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": "New Cat Name"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == "New Cat Name"

def test_update_book_data():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"

def test_update_tag_data():
    tag = create_test_tag()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": "New Tag"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == "New Tag"

def test_delete_author_without_books():
    auth = create_test_author()
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_get_tag_success():
    tag = create_test_tag()
    r = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == tag["id"]

def test_delete_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_get_order_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    ord_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    ord_id = ord_r.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{ord_id}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == ord_id

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_tag_success():
    tag = create_test_tag()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204