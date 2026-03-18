import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# Helper functions for isolated test data
def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, published_year=2000):
    title = title or unique("Book")
    isbn = isbn or unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": 100.0, 
        "published_year": published_year, "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_order(book_id):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test User",
        "customer_email": "test@test.cz",
        "items": [{"book_id": book_id, "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

# Tests
def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_valid_author():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Auth")}, timeout=30)
    assert r.status_code == 201

def test_create_invalid_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books_conflict():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 409

def test_create_duplicate_category_conflict():
    name = unique("Cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_with_nonexistent_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T", "isbn": "1234567890", "price": 10, "published_year": 2020, 
        "author_id": 99999, "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_create_book_with_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890"
    create_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "T2", "isbn": isbn, "price": 10, "published_year": 2020, 
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=30)
    assert r.status_code == 422

def test_create_valid_review():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Fan"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_out_of_range_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Bad"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_valid_discount():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_to_new_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400

def test_apply_invalid_discount_percent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_increase():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200

def test_update_stock_negative_result():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-99", timeout=30)
    assert r.status_code == 400

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=30)
    assert r.status_code == 422

def test_delete_assigned_tag_conflict():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    tag = r_tag.json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_add_multiple_tags_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    t1 = requests.post(f"{BASE_URL}/tags", json={"name": unique("T1")}, timeout=30).json()
    t2 = requests.post(f"{BASE_URL}/tags", json={"name": unique("T2")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t1["id"], t2["id"]]}, timeout=30)
    assert r.status_code == 200

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "A", "customer_email": "a@a.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "A", "customer_email": "a@a.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_invalid_status_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = create_order(book["id"])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_valid_status_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = create_order(book["id"])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_delete_shipped_order_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = create_order(book["id"])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=30)
    assert r.status_code == 404

def test_update_book_invalid_year():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 500}, timeout=30)
    assert r.status_code == 422

def test_list_authors_default_limit():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200

def test_remove_tag_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_update_category_name_to_existing():
    c1 = create_category()
    c2 = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": c1["name"]}, timeout=30)
    assert r.status_code == 409

def test_filter_orders_by_customer():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=30)
    assert r.status_code == 200

def test_create_book_negative_price():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Neg", "isbn": "1112223334", "price": -5, "published_year": 2020,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_get_author_details():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 200

def test_update_tag_empty_name():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_list_reviews_for_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=30)
    assert r.status_code == 200

def test_filter_books_by_price_range():
    r = requests.get(f"{BASE_URL}/books?min_price=1&max_price=1000", timeout=30)
    assert r.status_code == 200

def test_delete_empty_category():
    cat = create_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 204

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = create_order(book["id"])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 200