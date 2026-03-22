import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test bio", "born_year": 1990}, timeout=TIMEOUT)
    return r.json()

def create_category():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "test cat"}, timeout=TIMEOUT)
    return r.json()

def create_book(author_id, category_id, stock=10):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": 2020,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1980}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_author_with_books_error():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_category_duplicate_error():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc2"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("t"), "isbn": unique("i"), "price": 10, "published_year": 2020, "stock": 10,
        "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_missing_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), 
        "isbn": unique("isbn"), 
        "price": 10.0, 
        "published_year": 2020, 
        "stock": 10,
        "author_id": 9999, 
        "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890"
    requests.post(f"{BASE_URL}/books", json={
        "title": "t1", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "t2", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books?search=nonexistent_title", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_delete_book_cascade_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_get.status_code == 404

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "tester"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_empty():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"average_rating": None, "ratings": []}

def test_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    # 2026 is current year as per schema
    r_book = requests.post(f"{BASE_URL}/books", json={
        "title": "new", "isbn": unique("i"), "price": 100, "published_year": 2026, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    book_id = r_book.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_discount_old_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_discount_over_limit_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_increase_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_decrease_stock_too_much_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_duplicate_error():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_idempotent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag_r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    tag_id = tag_r.json()["id"]
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_remove_tag_nonexistent_ignored():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [9999]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"message": "Tags removed successfully"}

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "user", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 10}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "user", "customer_email": "u@u.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "user", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "user", "customer_email": "u@u.cz", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_shipped_order_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "user", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_restocks():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "u", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 3}]
    }, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 5

def test_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "u", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_transition_invalid_path():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "u", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_cancel_order_restocks():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "u", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 3}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 5

def test_tag_bulk_add_limit():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    t1 = requests.post(f"{BASE_URL}/tags", json={"name": unique("t1")}, timeout=TIMEOUT).json()
    t2 = requests.post(f"{BASE_URL}/tags", json={"name": unique("t2")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t1["id"], t2["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_stock_boundary_zero():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.json()["stock"] == 0

def test_stock_large_delta():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=0)
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 999}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.json()["stock"] == 999

def test_create_book_min_price():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("t"), "isbn": unique("i"), "price": 0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201

def test_delete_assigned_tag_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_reviews_pagination_test():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_filter_orders_by_customer_name():
    r = requests.get(f"{BASE_URL}/orders?customer_name=nonexistent", timeout=TIMEOUT)
    assert r.status_code == 200

def test_filter_orders_by_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/9999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_category_name_empty():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_discount_boundary_50():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 50}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_stock_decrement_to_zero():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.json()["stock"] == 0

def test_delete_tags_invalid_body():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"wrong_key": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_detail():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "u", "customer_email": "u@u.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_negative_limit():
    r = requests.get(f"{BASE_URL}/books?page_size=-1", timeout=TIMEOUT)
    assert r.status_code == 422