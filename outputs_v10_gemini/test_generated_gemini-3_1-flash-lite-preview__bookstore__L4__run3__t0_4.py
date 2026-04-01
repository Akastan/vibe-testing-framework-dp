import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None, bio=None, born_year=1980):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("Book")
    isbn = isbn or unique("ISBN")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "Missing name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_test_author()
    cat = create_test_category()
    create_test_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_category_duplicate_name():
    name = unique("Cat")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Success Book", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_isbn():
    author = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad ISBN", "isbn": "123", "price": 10.0,
        "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/999999", timeout=30)
    assert r.status_code == 404

def test_create_review_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester", "comment": "Great"
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_new_book_fails():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_invalid_percent():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_negative_result():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_update_stock_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_create_tag_success():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422

def test_add_tags_idempotent():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_duplicate_books():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_insufficient_stock():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["status"] == "pending"

def test_update_status_invalid_transition():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_status_cancel_restores_stock():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.json()["stock"] == 10

def test_delete_shipped_order_fails():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_list_books_pagination_default():
    r = requests.get(f"{BASE_URL}/books", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=30)
    assert r.status_code == 422

def test_list_orders_filter_by_name():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "NonExistent"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0