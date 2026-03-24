import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, isbn=None, stock=10, year=2020):
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": isbn, "price": 100.0,
        "published_year": year, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    name = unique("auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "missing name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_test_author()
    cat = create_test_category()
    create_test_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": unique("isbn"), "price": 10.0, "published_year": 2020,
        "stock": 10, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    author = create_test_author()
    cat = create_test_category()
    isbn = unique("isbn")
    create_test_book(author["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10.0, "published_year": 2020,
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books", params={"search": "nonexistent"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_apply_discount_valid_old_book():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_new_book_fail():
    author = create_test_author()
    cat = create_test_category()
    current_year = datetime.now(timezone.utc).year
    book = create_test_book(author["id"], cat["id"], year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_over_limit():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_increase():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_insufficient():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 400

def test_add_tags_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    tag = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag_error():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [99999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tags_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_allowed_transition():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_forbidden_transition():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_status_cancel_restores_stock():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.json()["stock"] == 10

def test_delete_pending_order_success():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_confirmed_order_error():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_create_tag_unique():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    assert r.status_code == 201

def test_create_tag_duplicate():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_tag_attached_fail():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_create_review_invalid_rating():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 422

def test_create_review_unauthorized_empty_user():
    author = create_test_author()
    cat = create_test_category()
    book = create_test_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5}, timeout=30)
    assert r.status_code == 422

def test_create_review_nonexistent_book():
    r = requests.post(f"{BASE_URL}/books/99999/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 404