import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, title=None):
    title = title or unique("Book")
    data = {
        "title": title,
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_valid():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=30)
    assert r.status_code == 201

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_create_author_long_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "x" * 101}, timeout=30)
    assert r.status_code == 422

def test_create_author_invalid_year():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("A"), "born_year": -5}, timeout=30)
    assert r.status_code == 422

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200

def test_list_authors_pagination():
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200

def test_get_author_existing():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 200

def test_get_author_nonexistent():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code in [404, 422]

def test_update_author_success():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"bio": "updated bio"}, timeout=30)
    assert r.status_code == 200

def test_delete_author_success():
    auth = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 204

def test_create_book_valid():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("B"), "isbn": "1234567890", "price": 10, "published_year": 2000, "author_id": auth['id'], "category_id": cat['id']}, timeout=30)
    assert r.status_code == 201

def test_create_book_negative_price():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("B"), "isbn": "1234567890", "price": -1, "published_year": 2000, "author_id": auth['id'], "category_id": cat['id']}, timeout=30)
    assert r.status_code == 422

def test_create_book_invalid_year():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("B"), "isbn": "1234567890", "price": 10, "published_year": 500, "author_id": auth['id'], "category_id": cat['id']}, timeout=30)
    assert r.status_code == 422

def test_create_book_missing_isbn():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("B"), "price": 10, "published_year": 2000, "author_id": auth['id'], "category_id": cat['id']}, timeout=30)
    assert r.status_code == 422

def test_list_books_search():
    r = requests.get(f"{BASE_URL}/books", params={"search": "test"}, timeout=30)
    assert r.status_code == 200

def test_list_books_price_range():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=30)
    assert r.status_code == 200

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=30)
    assert r.status_code == 422

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_update_book_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"stock": 50}, timeout=30)
    assert r.status_code == 200

def test_update_book_invalid_data():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": -10}, timeout=30)
    assert r.status_code == 422

def test_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_add_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "tester"}, timeout=30)
    assert r.status_code == 201

def test_add_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "tester"}, timeout=30)
    assert r.status_code == 422

def test_list_reviews_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=30)
    assert r.status_code == 200

def test_get_rating_calculation():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_too_high():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    assert r.status_code == 200

def test_remove_tags_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    tag = create_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    assert r.status_code == 200

def test_create_category_valid():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=30)
    assert r.status_code == 201

def test_create_category_duplicate_name():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 422

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200

def test_update_category_name():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": unique("NewName")}, timeout=30)
    assert r.status_code == 200

def test_delete_category_success():
    cat = create_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 204

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200

def test_update_tag_name():
    tag = create_tag()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 200

def test_delete_tag_success():
    tag = create_tag()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 204

def test_create_order_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 999}]}, timeout=30)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=30)
    assert r.status_code == 200

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 200

def test_delete_pending_order():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 422

def test_update_status_to_shipped():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 200

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth['id'], cat['id'])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book['id'], "quantity": 1}]}, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "invalid_status"}, timeout=30)
    assert r.status_code == 422