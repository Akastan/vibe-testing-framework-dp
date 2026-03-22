import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# Helpers
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

# Tests
def test_health_check():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_valid_author():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "born_year": 1980}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_author_validation_error():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_duplicate_category_fails():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success_with_stock_10():
    auth = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": unique("isbn"), "price": 10, "published_year": 2020, 
        "stock": 10, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_with_nonexistent_author_fails():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": "1234567890", "price": 10, "published_year": 2020,
        "author_id": 999, "category_id": cat["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_duplicate_isbn_fails():
    auth = create_author()
    cat = create_category()
    isbn = "1234567890"
    data = {"title": "B", "isbn": isbn, "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_pagination_default():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    auth = create_author()
    cat = create_category()
    title = unique("search")
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books", params={"search": title}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_invalid_page_fails():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_post_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "John"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_post_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "J"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_old_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    import datetime
    current_year = datetime.datetime.now().year
    book = create_book(auth["id"], cat["id"], year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "error" in r.json()

def test_apply_discount_too_high():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_stock_delta():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_reduce_stock_too_much_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_nonexistent_tag_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [999]}, timeout=TIMEOUT)
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
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_items_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", 
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_status_invalid_transition():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_pending_order_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT).json()
    requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    b_refreshed = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert b_refreshed["stock"] == 5

def test_list_authors_empty():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_category_not_found():
    r = requests.get(f"{BASE_URL}/categories/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_book_isbn_conflict():
    auth = create_author()
    cat = create_category()
    b1 = create_book(auth["id"], cat["id"])
    b2 = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{b1['id']}", json={"isbn": b2["isbn"]}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_orders_filtering_by_status():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_duplicate_name():
    name1 = unique("t1")
    name2 = unique("t2")
    t1 = requests.post(f"{BASE_URL}/tags", json={"name": name1}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/tags", json={"name": name2}, timeout=TIMEOUT)
    r = requests.put(f"{BASE_URL}/tags/{t1['id']}", json={"name": name2}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_update_author_name_too_long():
    auth = create_author()
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": "a" * 101}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_with_negative_quantity():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_delete_category_assigned_to_book():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_cancel_order_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    b_ref = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert b_ref["stock"] == 5

def test_add_tags_idempotent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag_in_use():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_get_order_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]

def test_list_reviews_pagination_out_of_bounds():
    r = requests.get(f"{BASE_URL}/books/99999/reviews", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_author_sql_injection_attempt():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "'; DROP TABLE users; --"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_zero_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "T", "customer_email": "e@e.cz", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422


def test_patch_book_price_success():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    new_price = 150.5
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/price", json={"price": new_price}, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["price"] == new_price

    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    assert get_response.json()["price"] == new_price

def test_delete_book_removes_it_from_list():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    list_response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert list_response.status_code == 200
    books = list_response.json()
    assert isinstance(books, list)
    assert not any(b["id"] == book["id"] for b in books)

def test_update_author_details_success():
    author = create_author()
    new_name = unique("new_name")
    response = requests.patch(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["name"] == new_name
    get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == new_name

def test_create_category_with_long_description():
    data = {"name": unique("long_cat"), "description": "A" * 500}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert response.status_code == 201
    assert response.json()["description"] == "A" * 500