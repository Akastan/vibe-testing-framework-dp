import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    data = {"name": name, "bio": "bio", "born_year": 1990}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    return response.json()

def create_category():
    name = unique("cat")
    data = {"name": name, "description": "desc"}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    return response.json()

def create_book(author_id, category_id, published_year=2020):
    data = {
        "title": unique("book"),
        "isbn": f"978{uuid.uuid4().hex[:7]}",
        "price": 100.0,
        "published_year": published_year,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    return response.json()

def test_health_check_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    data = {"name": unique("author"), "bio": "bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_error():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=TIMEOUT)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_book_success():
    auth = create_author()
    cat = create_category()
    data = {
        "title": unique("b"), "isbn": "1234567890", "price": 10.0,
        "published_year": 2020, "stock": 5, "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == data["title"]

def test_create_book_duplicate_isbn():
    auth = create_author()
    cat = create_category()
    isbn = "12345678901"
    data = {
        "title": "B1", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }
    requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={**data, "title": "B2"}, timeout=TIMEOUT)
    assert r.status_code == 409

def test_list_books_default_pagination():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_review_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 5, "comment": "great", "reviewer_name": "tester"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "x"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_old_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400

def test_increment_stock_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_to_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_remove_tags_from_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_valid_items():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {
        "customer_name": "Jan", "customer_email": "jan@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=TIMEOUT)
    assert r.status_code == 201

def test_delete_pending_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "J", "customer_email": "j@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_update_book_valid_data():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "New Title"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_book_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204


def test_list_authors_pagination_limit():
    create_author()
    create_author()
    response = requests.get(f"{BASE_URL}/authors", params={"limit": 1}, timeout=30)
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_list_authors_skip_parameter():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", params={"skip": 1}, timeout=30)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_category_empty_name_error():
    data = {"name": "", "description": "test"}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert response.status_code == 422

def test_get_category_details():
    cat = create_category()
    response = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert response.status_code == 200
    assert response.json()["name"] == cat["name"]

def test_list_categories():
    create_category()
    response = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_delete_category_success():
    cat = create_category()
    response = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert response.status_code == 204

def test_create_book_with_zero_price_error():
    author = create_author()
    cat = create_category()
    data = {"title": unique("b"), "isbn": "123", "price": 0, "published_year": 2020, "stock": 1, "author_id": author["id"], "category_id": cat["id"]}
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code == 422

def test_list_books_filtering_by_category():
    cat = create_category()
    book = create_book(create_author()["id"], cat["id"])
    response = requests.get(f"{BASE_URL}/books", params={"category_id": cat["id"]}, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == book["id"]
    assert data[0]["category_id"] == cat["id"]

def test_update_stock_negative_delta():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=30)
    assert response.status_code == 200
    assert response.json()["stock"] == 5

def test_update_stock_insufficient_error():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -20}, timeout=400)
    assert response.status_code >= 400

def test_get_book_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    response = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=30)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_review_nonexistent_book():
    data = {"rating": 5, "comment": "good"}
    response = requests.post(f"{BASE_URL}/books/999999/reviews", json=data, timeout=30)
    assert response.status_code == 404
    assert isinstance(response.json().get("detail"), str)

def test_list_tags():
    response = requests.get(f"{BASE_URL}/tags", timeout=30)
    assert response.status_code == 200

def test_delete_tag():
    tag_name = unique("tag")
    post_res = requests.post(f"{BASE_URL}/tags", json={"name": tag_name}, timeout=30)
    tag_id = post_res.json()["id"]
    response = requests.delete(f"{BASE_URL}/tags/{tag_id}", timeout=30)
    assert response.status_code == 204

def test_get_orders_list():
    response = requests.get(f"{BASE_URL}/orders", timeout=30)
    assert response.status_code == 200

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    data = {"items": [{"book_id": book["id"], "quantity": 1}]}
    response = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_get_nonexistent_order():
    response = requests.get(f"{BASE_URL}/orders/99999", timeout=30)
    assert response.status_code == 404

def test_update_author_name():
    auth = create_author()
    new_name = unique("author_updated")
    data = {"name": new_name}
    response = requests.patch(f"{BASE_URL}/authors/{auth['id']}", json=data, timeout=30)
    assert response.status_code == 200
    updated_auth = response.json()
    assert updated_auth["name"] == new_name
    assert updated_auth["id"] == auth["id"]

    response_get = requests.get(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert response_get.status_code == 200
    assert response_get.json()["name"] == new_name

def test_apply_discount_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], published_year=2010)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"percentage": 10}, timeout=30)
    assert response.status_code == 200
    assert response.json()["price"] == 90.0

def test_create_book_invalid_isbn_format():
    auth = create_author()
    cat = create_category()
    data = {"title": "x", "isbn": "", "price": 10, "author_id": auth["id"], "category_id": cat["id"]}
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code == 422

def test_delete_nonexistent_tag():
    response = requests.delete(f"{BASE_URL}/tags/9999", timeout=30)
    assert response.status_code == 404

def test_get_author_books():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    response = requests.get(f"{BASE_URL}/authors/{auth['id']}/books", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(b["id"] == book["id"] for b in data)

def test_add_duplicate_tag_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("t")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert response.status_code == 200

def test_create_order_empty_items():
    response = requests.post(f"{BASE_URL}/orders", json={"items": []}, timeout=30)
    assert response.status_code == 422

def test_list_books_invalid_pagination():
    response = requests.get(f"{BASE_URL}/books", params={"limit": -1}, timeout=30)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert isinstance(response.json()["detail"], list)

def test_get_category_books_empty():
    cat = create_category()
    response = requests.get(f"{BASE_URL}/categories/{cat['id']}/books", timeout=30)
    assert response.status_code == 200
    assert response.json() == []

def test_create_book_missing_required_fields():
    response = requests.post(f"{BASE_URL}/books", json={"title": "Missing"}, timeout=30)
    assert response.status_code == 422