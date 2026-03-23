import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    return r.json()

def create_category():
    data = {"name": unique("cat"), "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    return r.json()

def create_book(author_id, category_id, stock=10, year=2020):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    return r.json()

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = {"name": unique("author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()
    assert r.json()["name"] == data["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_success():
    data = {"name": unique("cat"), "description": "test"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_duplicate_category_error():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    a = create_author()
    c = create_category()
    data = {
        "title": "Title", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_isbn_length():
    a = create_author()
    c = create_category()
    data = {
        "title": "Title", "isbn": "123", "price": 10.0,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_nonexistent_author():
    data = {
        "title": "Title", 
        "isbn": unique("isbn"), 
        "price": 10.0,
        "published_year": 2020, 
        "stock": 10,
        "author_id": 999, 
        "category_id": 999
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_book_detail():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]
    assert "tags" in r.json()

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "comment": "Good", "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 10, "reviewer_name": "Tester"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_insufficient_stock_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    tr = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = tr.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(t["id"] == tag_id for t in r.json()["tags"])

def test_remove_tags_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    tr = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = tr.json()["id"]
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert not any(t["id"] == tag_id for t in r.json()["tags"])

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {
        "customer_name": "John",
        "customer_email": "john@test.com",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0
    br = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert br.json()["stock"] == 9

def test_order_duplicate_book_id_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {
        "customer_name": "John",
        "customer_email": "a@b.com",
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    br = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert br.json()["stock"] == 10

def test_delete_confirmed_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "a@b.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_tag_used_in_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    tr = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = tr.json()["id"]
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag_id}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_category_success():
    c = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"description": "Updated"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["description"] == "Updated"

def test_list_orders_filtering_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_update_book_invalid_price():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"price": -50.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_nonexistent_tag():
    r = requests.get(f"{BASE_URL}/tags/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_category_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_year():
    a = create_author()
    c = create_category()
    data = {
        "title": "T", "isbn": unique("isbn"), "price": 10.0,
        "published_year": 500, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_missing_author():
    data = {"title": "T", "isbn": unique("isbn"), "price": 10.0, "published_year": 2020}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_nonexistent():
    r = requests.get(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_decrease_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_list_books_by_author():
    a = create_author()
    r = requests.get(f"{BASE_URL}/books?author_id={a['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_search_term():
    r = requests.get(f"{BASE_URL}/books?search=test", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_price_range():
    r = requests.get(f"{BASE_URL}/books?min_price=10&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_success():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"bio": "New bio"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["bio"] == "New bio"

def test_list_reviews_empty():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == []

def test_delete_book_cascade_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "X"}, timeout=TIMEOUT)
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_orders_customer_name_filter():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_duplicate_name_error():
    t1 = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    t2 = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t1['id']}", json={"name": t2["name"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_review_empty_content_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "comment": "", "reviewer_name": ""}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 422