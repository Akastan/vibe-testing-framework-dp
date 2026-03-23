import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1990}
    return requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT).json()

def create_category():
    data = {"name": unique("cat"), "description": "desc"}
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

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_author_with_books_error():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_category_duplicate():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    data = {"title": unique("b"), "isbn": unique("i"), "price": 10.0, "published_year": 2020, "stock": 10, "author_id": auth["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_invalid_year():
    auth = create_author()
    cat = create_category()
    data = {"title": "x", "isbn": "123", "price": 10.0, "published_year": 900, "author_id": auth["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_no_author():
    cat = create_category()
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": 9999,
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_book_detail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == book["title"]

def test_update_book_isbn_duplicate():
    auth = create_author()
    cat = create_category()
    b1 = create_book(auth["id"], cat["id"])
    b2 = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{b2['id']}", json={"isbn": b1["isbn"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_book_cascade():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_get.status_code == 404

def test_create_review_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Tester", "comment": "Skvele"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "T"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_new_book_error():
    import datetime
    auth = create_author()
    cat = create_category()
    current_year = datetime.datetime.now().year
    book = create_book(auth["id"], cat["id"], year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_over_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_stock_increase():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_decrease_negative():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_stock_exact_zero():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 0

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_assigned_tag_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_idempotent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_tags_nonexistent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [9999]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "Jmeno", "customer_email": "x@x.cz", "items": [{"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    data = {"customer_name": "Jmeno", "customer_email": "x@x.cz", "items": [{"book_id": book["id"], "quantity": 10}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"customer_name": "J", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "b@c.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders?customer_name=NonExistent", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_list_orders_status_filter():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_confirmed_order_forbidden():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_stock_return():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 2}]}, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    book_final = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_final["stock"] == 5

def test_order_status_transit_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_order_status_cancel_returns_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 2}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    book_final = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert book_final["stock"] == 5

def test_order_status_delivered_to_shipped_fail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_order_status_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_order_status_shipped_to_delivered():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_name_too_long():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "a" * 101}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_author_success():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": unique("new")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_category_success():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_duplicate():
    c1 = create_category()
    c2 = create_category()
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": c1["name"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_book_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_order_detail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]