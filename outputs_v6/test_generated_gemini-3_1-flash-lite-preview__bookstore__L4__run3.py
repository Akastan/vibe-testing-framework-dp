import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_test_author(name=None, bio=None, born_year=1980):
    name = name or unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_category(name=None):
    name = name or unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("book")
    isbn = isbn or unique("isbn")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id
    }, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_test_tag(name=None):
    name = name or unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_health_check_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    data = create_test_author()
    assert "id" in data
    assert "name" in data

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422

def test_list_authors_default():
    create_test_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_dependency_conflict():
    author = create_test_author()
    cat = create_test_category()
    create_test_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_category_success():
    data = create_test_category()
    assert "id" in data

def test_create_category_duplicate_name():
    name = unique("dup_cat")
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_test_author()
    cat = create_test_category()
    data = create_test_book(auth["id"], cat["id"], stock=10)
    assert data["stock"] == 10

def test_create_book_isbn_duplicate():
    auth = create_test_author()
    cat = create_test_category()
    isbn = "1234567890123"
    create_test_book(auth["id"], cat["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10, "published_year": 2020,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_invalid_year():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "BadYear", "isbn": "1111111111", "price": 10, "published_year": 900,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 422

def test_list_books_pagination():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"], price=100)
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 50}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) > 0

def test_get_book_detail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["title"] == book["title"]

def test_create_review_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Reviewer"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Reviewer"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_empty():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] < book["price"]

def test_apply_discount_new_book_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=datetime.now(timezone.utc).year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_above_50_pct():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_increase():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_negative_excess():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400

def test_create_tag_success():
    data = create_test_tag()
    assert "id" in data

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422

def test_delete_tag_in_use():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409

def test_add_tags_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_add_tags_idempotency():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_remove_tags_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    tag = create_test_tag()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Tester", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Tester", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Tester", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Tester", "customer_email": "t@t.cz", "items": []
    }, timeout=30)
    assert r.status_code == 422

def test_list_orders_filter_customer():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "UniqueName", "customer_email": "a@a.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    r = requests.get(f"{BASE_URL}/orders", params={"customer_name": "UniqueName"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

def test_get_order_detail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "DetailTest", "customer_email": "d@d.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]

def test_delete_pending_order_restores_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Del", "customer_email": "d@d.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()["stock"] == 10

def test_delete_confirmed_order_fail():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Conf", "customer_email": "c@c.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_update_order_status_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Stat", "customer_email": "s@s.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Inv", "customer_email": "i@i.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_cancel_order_restores_stock():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Canc", "customer_email": "c@c.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()["stock"] == 10

def test_update_author_success():
    auth = create_test_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "NewName"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "NewName"

def test_get_category_not_found():
    r = requests.get(f"{BASE_URL}/categories/99999", timeout=30)
    assert r.status_code == 404

def test_update_category_success():
    cat = create_test_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": "NewCat"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "NewCat"

def test_delete_category_dependency():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 409

def test_update_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "NewTitle"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["title"] == "NewTitle"

def test_update_book_duplicate_isbn():
    auth = create_test_author()
    cat = create_test_category()
    b1 = create_test_book(auth["id"], cat["id"], isbn="1111111111")
    b2 = create_test_book(auth["id"], cat["id"], isbn="2222222222")
    r = requests.put(f"{BASE_URL}/books/{b2['id']}", json={"isbn": "1111111111"}, timeout=30)
    assert r.status_code == 409

def test_delete_book_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_get_tag_success():
    tag = create_test_tag()
    r = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == tag["id"]

def test_update_tag_success():
    tag = create_test_tag()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": "NewTag"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "NewTag"

def test_list_tags_success():
    create_test_tag()
    r = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_reviews_success():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "A"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=30)
    assert r.status_code == 200
    assert len(r.json()) > 0