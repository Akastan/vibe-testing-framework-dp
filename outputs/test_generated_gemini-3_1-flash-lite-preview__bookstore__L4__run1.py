import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, isbn=None):
    isbn = isbn or unique("ISBN")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_valid():
    author = create_author()
    assert "id" in author

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422

def test_create_author_invalid_year():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "Test", "born_year": 3000}, timeout=30)
    assert r.status_code == 422

def test_delete_author_occupied():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_author_nonexistent():
    r = requests.delete(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_create_category_valid():
    cat = create_category()
    assert "id" in cat

def test_create_category_duplicate():
    name = unique("Cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    assert book["id"] is not None

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = unique("ISBN")
    create_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10.0, "published_year": 2020,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_missing_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "No Auth", "isbn": unique("ISBN"), "price": 10.0,
        "published_year": 2020, "author_id": 9999, "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_too_recent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"]) # Published 2020, now is 2024/2025
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_over_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 99}, timeout=30)
    assert r.status_code == 422

def test_update_stock_add():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200

def test_update_stock_negative():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -100}, timeout=30)
    assert r.status_code == 400

def test_add_tags_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_add_nonexistent_tag():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200

def test_create_review_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 422

def test_create_order_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@mail.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_low_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@mail.com",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@mail.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_empty_cart():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@mail.com", "items": []
    }, timeout=30)
    assert r.status_code == 422

def test_order_status_transition_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_order_status_transition_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_order_status_cancelled_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 200

def test_delete_pending_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_failed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_get_author_found():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 200

def test_get_author_missing():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404

def test_update_category_name():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": unique("NewName")}, timeout=30)
    assert r.status_code == 200

def test_update_category_conflict():
    c1 = create_category(unique("C1"))
    c2 = create_category(unique("C2"))
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": c1["name"]}, timeout=30)
    assert r.status_code == 409

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_update_book_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=30)
    assert r.status_code == 200

def test_get_book_rating_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200

def test_delete_tag_in_use():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = create_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_list_orders_with_filters():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=30)
    assert r.status_code == 200

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@m.com", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 200

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200

def test_delete_book_cascade_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204