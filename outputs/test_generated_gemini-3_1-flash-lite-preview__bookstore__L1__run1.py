import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "test"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id=None, category_id=None, published_year=2020):
    if not author_id:
        author_id = create_author()["id"]
    if not category_id:
        category_id = create_category()["id"]
    
    payload = {
        "title": unique("Book"),
        "isbn": unique("ISBN")[:13],
        "price": 100.0,
        "published_year": published_year,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_invalid_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_duplicate_category_fails():
    name = unique("Category")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_with_nonexistent_author():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Ghost", "isbn": "1234567890", "price": 10, "published_year": 2020,
        "author_id": 99999, "category_id": 1
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_update_stock_negative_results_error():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -100}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_invalid_format():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": "abc"}, timeout=30)
    assert r.status_code == 422

def test_create_review_out_of_range_rating():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_get_rating_no_reviews():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    # API specs imply response is object, check status is 200

def test_apply_discount_too_high():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_apply_discount_new_book_fails():
    book = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_add_nonexistent_tag_to_book():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=30)
    assert r.status_code == 404

def test_add_duplicate_tag_idempotency():
    book = create_book()
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    r1 = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r2 = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r1.status_code == 200
    assert r2.status_code == 200

def test_remove_tag_from_book():
    book = create_book()
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "A" * 31}, timeout=30)
    assert r.status_code == 422

def test_delete_assigned_tag_fails():
    book = create_book()
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Test", "customer_email": "t@t.cz", "items": []}, timeout=30)
    assert r.status_code == 422

def test_create_order_duplicate_books():
    b = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_insufficient_stock():
    b = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400

def test_delete_confirmed_order_fails():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_update_status_illegal_transition():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_update_status_invalid_value():
    b = create_book()
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "invalid"}, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination_params():
    create_book()
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=30)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "Unknown"}, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)

def test_list_orders_page_size_edge_case():
    r = requests.get(f"{BASE_URL}/orders", params={"page_size": 100}, timeout=30)
    assert r.status_code == 200
    assert r.json()["page_size"] <= 100

def test_list_orders_empty_results():
    r = requests.get(f"{BASE_URL}/orders", params={"page": 9999}, timeout=30)
    assert r.status_code == 200
    assert r.json()["items"] == []