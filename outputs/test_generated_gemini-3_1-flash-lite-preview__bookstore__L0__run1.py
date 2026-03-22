import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    payload = {"name": name or unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    payload = {"name": name or unique("Cat")}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id=None, category_id=None, published_year=2026):
    if not author_id:
        author_id = create_author()["id"]
    if not category_id:
        category_id = create_category()["id"]
    payload = {
        "title": unique("Book"),
        "isbn": unique("ISBN"),
        "price": 100.0,
        "published_year": published_year,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    return r.json()


def test_get_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_category_success():
    name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_book_success():
    book = create_book()
    assert "id" in book
    assert book["stock"] == 10

def test_create_book_invalid_isbn():
    author = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Invalid", "isbn": "123", "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_paginated():
    create_book()
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_filter_price():
    create_book()
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)

def test_update_book_success():
    book = create_book()
    new_title = unique("NewTitle")
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=30)
    assert r.status_code == 200
    assert r.json()["title"] == new_title

def test_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r_check.status_code == 422

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester", "comment": "Great"
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_out_of_range():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_rating_success():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_discount_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discount_percent"] == 20

def test_apply_discount_too_high():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_success():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_create_tag_success():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "A" * 31}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_add_tags_to_book_success():
    book = create_book()
    tag = create_tag_helper()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def create_tag_helper():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    return r.json()

def test_remove_tags_from_book_success():
    book = create_book()
    tag = create_tag_helper()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag['id']]}, timeout=30)
    assert r.status_code == 200

def test_create_order_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0

def test_create_order_invalid_item():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": 9999, "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 422

def test_list_orders_by_status():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_order_details():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]

def test_delete_pending_order():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_invalid_order():
    r = requests.delete(f"{BASE_URL}/orders/9999", timeout=30)
    assert r.status_code == 422

def test_update_order_status_success():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

def test_update_order_status_invalid():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jana", "customer_email": "a@b.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "invalid"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()