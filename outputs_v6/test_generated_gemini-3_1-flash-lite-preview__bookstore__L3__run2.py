import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author"), "bio": "test bio", "born_year": 1990}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("cat"), "description": "test category"}
    return requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT).json()

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
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_get_health_status_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()
    assert r.json()["name"] == data["name"]

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author_error():
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

def test_create_book_duplicate_isbn_error():
    a = create_author()
    c = create_category()
    isbn = unique("isbn")
    data = {"title": "T1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_invalid_year_error():
    a = create_author()
    c = create_category()
    data = {"title": "T", "isbn": unique("isbn"), "price": 10, "published_year": 900, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_get_nonexistent_book_error():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    data = {"rating": 5, "reviewer_name": "Test User"}
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 6, "reviewer_name": "U"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_average_rating_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 4, "reviewer_name": "U"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] == 4.0

def test_get_rating_empty_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_exceed_limit_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_increase_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_decrease_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_update_stock_negative_result_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    data = {"name": unique("tag")}
    r = requests.post(f"{BASE_URL}/tags", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long_error():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(tag["id"] == t["id"] for tag in r.json()["tags"])

def test_add_nonexistent_tag_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_remove_nonexistent_association_ignore():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 5}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=2)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 5}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_id_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_transition_status_pending_to_confirmed_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_transition_status_invalid_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_transition_status_cancelled_restores_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 5}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10

def test_delete_pending_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_delivered_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_list_authors_default_pagination():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_custom_limit():
    r = requests.get(f"{BASE_URL}/authors", params={"limit": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()) <= 5

def test_list_categories_full_list():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_books_search_query():
    r = requests.get(f"{BASE_URL}/books", params={"search": "title"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price_range():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page_error():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_filtering_name():
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "test"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_orders_pagination_structure():
    r = requests.get(f"{BASE_URL}/orders", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert all(k in data for k in ["items", "total", "page", "page_size", "total_pages"])

def test_update_tag_success():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("t")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("new")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_duplicate_name_error():
    n1 = unique("t")
    n2 = unique("t")
    requests.post(f"{BASE_URL}/tags", json={"name": n1}, timeout=TIMEOUT)
    t2 = requests.post(f"{BASE_URL}/tags", json={"name": n2}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t2['id']}", json={"name": n1}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_unused_tag_success():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("t")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_assigned_tag_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("t")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_book_title_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"

def test_update_book_invalid_isbn_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"isbn": "123"}, timeout=TIMEOUT)
    assert r.status_code == 422