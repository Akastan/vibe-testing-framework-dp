import requests
import uuid
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_category():
    data = {"name": unique("Category"), "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def create_book(author_id, category_id, stock=10, year=2020):
    data = {
        "title": unique("Book"),
        "isbn": unique("97801")[:13],
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_valid_author():
    data = {"name": unique("Author"), "bio": "Test Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
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

def test_create_unique_category():
    data = {"name": unique("Cat"), "description": "D"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_duplicate_category_error():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_with_stock_10():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"], stock=10)
    assert book["stock"] == 10

def test_create_book_with_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1234567890"
    data = {"title": "T", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_nonexistent_author():
    c = create_category()
    data = {"title": "T", "isbn": "0000000000", "price": 10, "published_year": 2020, "author_id": 999, "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_books_pagination():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_search_books_by_title():
    a = create_author()
    c = create_category()
    title = unique("FindMe")
    data = {"title": title, "isbn": unique("i")[:10], "price": 10, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books?search=FindMe", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) > 0

def test_filter_books_by_price():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=9999", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_book_title():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    new_title = "New Title"
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == new_title

def test_update_book_invalid_year():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"published_year": 500}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_happy_path():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_out_of_range():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 6, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_valid_year():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_above_limit():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_stock_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_remove_stock_below_zero_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-11", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_happy_path():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_duplicate_tag_error():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_add_nonexistent_tag_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    data = {"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 10}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    data = {"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_transition_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_invalid_status_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT).json()
    assert b_updated["stock"] == 10

def test_delete_shipped_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_filter_orders_by_name():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_limit_param():
    r = requests.get(f"{BASE_URL}/authors?limit=1", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_name():
    c = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c['id']}", json={"name": unique("NewName")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_name_duplicate():
    c1 = create_category()
    c2 = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": c1["name"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag_used_in_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_reviews_for_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_author_details():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_category_not_empty_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_order_details():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_bio():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"bio": "New Bio"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_name():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("NewName")}, timeout=TIMEOUT)
    assert r.status_code == 200