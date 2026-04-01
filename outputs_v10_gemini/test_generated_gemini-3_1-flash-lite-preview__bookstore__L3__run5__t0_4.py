import requests
import uuid
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("Category"), "description": "Desc"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

def create_book(author_id, category_id, stock=10, published_year=2020):
    data = {
        "title": unique("Book"),
        "isbn": unique("ISBN"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_create_author_success():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
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

def test_create_category_success():
    data = {"name": unique("Cat"), "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_duplicate_category_fails():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    cat = create_category()
    data = {
        "title": "Test Book", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": author["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn_fails():
    author = create_author()
    cat = create_category()
    isbn = unique("ISBN")
    data = {"title": "B1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_nonexistent_author_fails():
    cat = create_category()
    data = {"title": "B1", "isbn": unique("ISBN"), "price": 10, "published_year": 2020, "author_id": 999, "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_old_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_increase_stock_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_insufficient_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    data = {"customer_name": "John", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 2}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0

def test_create_order_duplicate_books_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    data = {"customer_name": "John", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_insufficient_stock_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    data = {"customer_name": "John", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 5}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_valid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 5}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 10

def test_delete_pending_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@j.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long_fails():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_tag_in_use_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination_default():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["page"] == 1
    assert data["page_size"] == 10