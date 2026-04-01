import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_empty_name():
    payload = {"name": ""}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_invalid_isbn():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Short ISBN", "isbn": "123", "price": 100, 
        "published_year": 2020, "author_id": 1, "category_id": 1
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_negative_price():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Neg Price", "isbn": "1234567890", "price": -10, 
        "published_year": 2020, "author_id": 1, "category_id": 1
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_book_invalid_year():
    r = requests.put(f"{BASE_URL}/books/1", json={"published_year": 900}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_review_invalid_rating():
    r = requests.post(f"{BASE_URL}/books/1/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_rating_success():
    book_id = unique("book")
    requests.post(f"{BASE_URL}/books", json={"id": book_id, "title": "Test Book"}, timeout=TIMEOUT)
    requests.post(f"{BASE_URL}/books/{book_id}/rating", json={"rating": 5}, timeout=TIMEOUT)

    r = requests.get(f"{BASE_URL}/books/{book_id}/rating", timeout=TIMEOUT)

    assert r.status_code == 200
    data = r.json()
    assert "rating" in data
    assert data["rating"] == 5

def test_apply_discount_too_high():
    r = requests.post(f"{BASE_URL}/books/1/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    book_id = requests.post(f"{BASE_URL}/books", json={"title": unique("book"), "author": "Author", "stock": 0}, timeout=TIMEOUT).json()["id"]
    r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

    check = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert check.status_code == 200
    assert check.json()["stock"] == 5

def test_create_category_success():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_delete_category_success():
    name = unique("CatDel")
    cat = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_empty_list():
    r = requests.post(f"{BASE_URL}/books/1/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.cz", "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", 
        "customer_email": "invalid-email", 
        "items": [{"book_id": 1, "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data
    assert len(data["detail"]) > 0

def test_list_orders_filter_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_order_invalid_id():
    r = requests.delete(f"{BASE_URL}/orders/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_status_invalid_value():
    r = requests.patch(f"{BASE_URL}/orders/1/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_author_success():
    name = unique("Author")
    auth = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{auth['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_author_success():
    name = unique("AuthorDel")
    auth = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_tags_success():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_remove_tags_success():
    tag_name = unique("tag")
    tag_resp = requests.post(f"{BASE_URL}/tags", json={"name": tag_name}, timeout=TIMEOUT)
    tag_id = tag_resp.json()["id"]

    book_resp = requests.post(f"{BASE_URL}/books", json={"title": unique("book"), "tag_ids": [tag_id]}, timeout=TIMEOUT)
    book_id = book_resp.json()["id"]

    r = requests.delete(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"message": "Tags removed successfully"}

def test_delete_book_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT).json()
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("Auth")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "Delete Me", "isbn": unique("123"), "price": 10, 
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    assert requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).status_code == 404

def test_list_reviews_success():
    book_id = unique("book")
    requests.post(f"{BASE_URL}/books", json={"id": book_id, "title": "Test Book"}, timeout=TIMEOUT)
    review_id = unique("review")
    requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={"id": review_id, "text": "Great!"}, timeout=TIMEOUT)

    r = requests.get(f"{BASE_URL}/books/{book_id}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(review.get("id") == review_id for review in data)