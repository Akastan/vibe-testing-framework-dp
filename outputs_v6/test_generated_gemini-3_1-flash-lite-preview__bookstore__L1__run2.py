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

def create_book(author_id, category_id, stock=10, published_year=2020):
    data = {
        "title": unique("book"),
        "isbn": unique("isbn"),
        "price": 100.0,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    return requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT).json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    data = {"name": unique("author"), "bio": "test", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_category_success():
    data = {"name": unique("cat"), "description": "desc"}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == data["name"]

def test_create_duplicate_category_fails():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    cat = create_category()
    data = {
        "title": unique("b"), "isbn": unique("i"), "price": 10.0,
        "published_year": 2020, "stock": 10, "author_id": author["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")
    data = {"title": "t", "isbn": isbn, "price": 1, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 409

def test_create_book_nonexistent_author():
    cat = create_category()
    data = {"title": "t", "isbn": "1234567890", "price": 1, "published_year": 2020, "author_id": 999, "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 404

def test_get_book_not_found():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_apply_discount_valid_old_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_apply_discount_over_50_percent():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 51}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_increase():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 10

def test_update_stock_decrease_valid():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_update_stock_negative_result():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_duplicate_tag():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_add_tags_to_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_add_tags_nonexistent_book():
    r = requests.post(f"{BASE_URL}/books/999/tags", json={"tag_ids": [1]}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_remove_tags_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    data = {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    data = {
        "customer_name": "John", "customer_email": "j@e.com",
        "items": [{"book_id": book["id"], "quantity": 100}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_duplicate_book_id():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    data = {
        "customer_name": "J", "customer_email": "j@e.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_pending_to_confirmed():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_status_cancel_returns_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": [{"book_id": book["id"], "quantity": 2}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
    assert updated_book["stock"] == 5

def test_update_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_delete_pending_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_shipped_order_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "J", "customer_email": "j@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 400

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "John"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "John"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_empty():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=2", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books?search=test", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_categories_default():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_tags_default():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_filter_name():
    r = requests.get(f"{BASE_URL}/orders?customer_name=test", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_book_negative_price():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": -10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_author_success():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "New Name"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_category_success():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": unique("cat")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_unused_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_used_tag_fails():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_category_with_books_fails():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_book_cascade():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204