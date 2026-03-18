import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    r = requests.post(f"{BASE_URL}/authors", json={"name": name or unique("Author"), "bio": "Test bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name or unique("Cat"), "description": "Test cat"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None):
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title or unique("Book"),
        "isbn": isbn or unique("123"),
        "price": 100.0,
        "published_year": 2020,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_tag(name=None):
    r = requests.post(f"{BASE_URL}/tags", json={"name": name or unique("Tag")}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author"), "bio": "Test"}, timeout=30)
    assert r.status_code == 201

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200

def test_get_existing_author():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_delete_author_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a['id'], c['id'])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409

def test_create_duplicate_category_error():
    name = unique("Cat")
    create_category(name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": "1234567890", "price": 10, "published_year": 2000, 
        "author_id": a['id'], "category_id": c['id']
    }, timeout=30)
    assert r.status_code == 201

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    create_book(a['id'], c['id'], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10, "published_year": 2000, 
        "author_id": a['id'], "category_id": c['id']
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200

def test_filter_books_by_price():
    r = requests.get(f"{BASE_URL}/books?min_price=10", timeout=30)
    assert r.status_code == 200

def test_update_book_invalid_year():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 500}, timeout=30)
    assert r.status_code == 422

def test_add_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 201

def test_add_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200

def test_apply_discount_too_new_error():
    a = create_author()
    c = create_category()
    # Assuming 2025 is "new" relative to current time logic
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "NewBook", "isbn": unique("isbn"), "price": 100, "published_year": 2025, 
        "author_id": a['id'], "category_id": c['id']
    }, timeout=30)
    b_id = r.json()['id']
    r2 = requests.post(f"{BASE_URL}/books/{b_id}/discount", json={"discount_percent": 10}, timeout=30)
    assert r2.status_code == 400

def test_increase_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200

def test_decrease_stock_below_zero_error():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 400

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    t = create_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t['id']]}, timeout=30)
    assert r.status_code == 200

def test_add_nonexistent_tag_error():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 404

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.cz",
        "items": [{"book_id": b['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.cz",
        "items": [{"book_id": b['id'], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_items_error():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.cz",
        "items": [{"book_id": b['id'], "quantity": 1}, {"book_id": b['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    o = test_create_order_success()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_update_status_invalid_transition():
    o = test_create_order_success()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_success():
    o = test_create_order_success()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_delivered_order_error():
    o = test_create_order_success()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_remove_nonexistent_tag_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [9999]}, timeout=30)
    assert r.status_code == 200

def test_list_orders_filter_customer():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=30)
    assert r.status_code == 200

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=30)
    assert r.status_code == 200

def test_update_author_name_too_long():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": "a" * 101}, timeout=30)
    assert r.status_code == 422

def test_get_category_success():
    c = create_category()
    r = requests.get(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 200

def test_delete_assigned_tag_error():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t['id']]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_search_books_by_title_partial():
    r = requests.get(f"{BASE_URL}/books?search=Book", timeout=30)
    assert r.status_code == 200

def test_delete_book_cascade_check():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_category_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a['id'], c['id'])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_list_reviews_check():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=30)
    assert r.status_code == 200

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200

def test_update_author_born_year_limit():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"born_year": 2026}, timeout=30)
    assert r.status_code == 200

def test_books_pagination_limit_check():
    r = requests.get(f"{BASE_URL}/books?page_size=100", timeout=30)
    assert r.status_code == 200

def test_get_book_detail_with_relations():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200

def test_get_order_detail():
    o = test_create_order_success()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 200

def test_update_tag_name_success():
    t = create_tag()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("NewTag")}, timeout=30)
    assert r.status_code == 200

def test_update_stock_boundary_zero():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -100}, timeout=30) # Assuming enough stock
    assert r.status_code == 200

def test_list_orders_empty_page():
    r = requests.get(f"{BASE_URL}/orders?page=999", timeout=30)
    assert r.status_code == 200

def test_update_author_null_values():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"bio": None}, timeout=30)
    assert r.status_code == 200

def test_create_book_missing_required():
    r = requests.post(f"{BASE_URL}/books", json={"title": "NoFields"}, timeout=30)
    assert r.status_code == 422

def test_get_tag_not_found():
    r = requests.get(f"{BASE_URL}/tags/9999", timeout=30)
    assert r.status_code == 404

def test_apply_discount_boundary_50():
    a = create_author()
    c = create_category()
    b = create_book(a['id'], c['id'])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 50}, timeout=30)
    assert r.status_code == 200