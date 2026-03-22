import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id=None, category_id=None, published_year=2020):
    if not author_id: author_id = create_author()["id"]
    if not category_id: category_id = create_category()["id"]
    data = {
        "title": unique("Book"),
        "isbn": unique("ISBN")[-13:],
        "price": 100.0,
        "published_year": published_year,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_get_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_duplicate_name():
    name = unique("Cat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_missing_author():
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890", "price": 10, "published_year": 2000, "author_id": 9999, "category_id": 1}, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_duplicate_isbn():
    isbn = "1234567890123"
    create_book() # base
    # Overwrite by using same isbn - API requires unique index
    author = create_author()
    cat = create_category()
    data = {"title": "T1", "isbn": isbn, "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_list_books_pagination():
    create_book()
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_out_of_range():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "Test"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_rating_empty():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_too_recent_book():
    book = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_invalid_percent():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_negative_result():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -100}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_success():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_delete_assigned_tag_conflict():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    book = create_book()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_add_tags_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_remove_tags_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    book = create_book()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_order_insufficient_stock():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 999}]}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_order_duplicate_book_id():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_order_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=30)
    assert r.status_code == 201
    assert r.json()["status"] == "pending"

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders?customer_name=none", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_update_status_invalid_transition():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_status_shipped_to_delivered():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "delivered"

def test_delete_order_non_pending():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_delete_order_pending_success():
    book = create_book()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.cz", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204

def test_update_book_invalid_year():
    book = create_book()
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"published_year": 900}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_category_not_found():
    r = requests.get(f"{BASE_URL}/categories/9999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_tag_empty_name():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()