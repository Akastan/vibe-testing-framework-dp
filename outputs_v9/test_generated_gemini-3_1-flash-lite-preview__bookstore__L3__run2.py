import requests
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert response.status_code == 201
    return response.json()

def create_category():
    data = {"name": unique("Cat"), "description": "Desc"}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    assert response.status_code == 201
    return response.json()

def create_book(author_id, category_id, stock=10, year=2020):
    data = {
        "title": unique("Book"),
        "isbn": unique("97801"),
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert response.status_code == 201
    return response.json()

def update_stock(book_id, quantity):
    response = requests.patch(f"{BASE_URL}/books/{book_id}/stock", params={"quantity": quantity}, timeout=30)
    assert response.status_code == 200
    return response.json()

def delete_book_tags(book_id, tag_ids):
    response = requests.delete(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": tag_ids}, timeout=30)
    assert response.status_code == 204
    return response


def test_create_valid_author():
    data = {"name": unique("Author"), "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_empty_name():
    data = {"name": "", "bio": "Bio"}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books_fails():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 409
    assert isinstance(r.json().get("detail"), str)

def test_create_duplicate_category_fails():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_with_stock_ten():
    auth = create_author()
    cat = create_category()
    data = {
        "title": "B1", "isbn": unique("9781"), "price": 10.0,
        "published_year": 2020, "stock": 10,
        "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert r.json()["stock"] == 10

def test_create_duplicate_isbn_fails():
    auth = create_author()
    cat = create_category()
    isbn = unique("9781")
    data = {
        "title": "B1", "isbn": isbn, "price": 10.0,
        "published_year": 2020, "stock": 10,
        "author_id": auth["id"], "category_id": cat["id"]
    }
    requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 409

def test_create_book_invalid_category():
    auth = create_author()
    data = {
        "title": "B1", "isbn": unique("9781"), "price": 10.0,
        "published_year": 2020, "stock": 10,
        "author_id": auth["id"], "category_id": 99999
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 404

def test_apply_discount_new_book_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], year=datetime.now().year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    response_data = r.json()
    assert "detail" in response_data
    assert response_data["detail"] is not None

def test_apply_discount_old_book_success():
    auth = create_author()
    cat = create_category()
    current_year = datetime.now().year
    book = create_book(auth["id"], cat["id"], year=current_year - 5)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert isinstance(data["discounted_price"], (int, float))
    assert data["discounted_price"] < book["price"]

def test_update_stock_add_quantity():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)
    data = update_stock(book["id"], 5)
    assert data["stock"] == 10

def test_update_stock_negative_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=5)

    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)

    assert response.status_code == 400
    assert "detail" in response.json()

def test_create_review_valid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 5, "reviewer_name": "Fan", "comment": "Great book"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=30)
    assert r.status_code == 201
    response_data = r.json()
    assert response_data["rating"] == data["rating"]
    assert response_data["reviewer_name"] == data["reviewer_name"]
    assert response_data["comment"] == data["comment"]
    assert "id" in response_data

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {"rating": 10, "reviewer_name": "Fan"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=data, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_rating_no_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json() == {"average_rating": 0.0}

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201

def test_create_tag_duplicate_fails():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_add_tags_idempotent():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag_data = {"name": unique("Tag")}
    tag = requests.post(f"{BASE_URL}/tags", json=tag_data, timeout=30).json()

    # První přidání
    r1 = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r1.status_code == 200
    r1_json = r1.json()

    # Druhé přidání (idempotentní)
    r2 = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r2.status_code == 200
    assert r2.json() == r1_json

def test_remove_tag_from_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()

    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)

    r = delete_book_tags(book["id"], [tag["id"]])
    assert r.status_code == 204

def test_create_order_insufficient_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=1)
    data = {
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 100}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 400

def test_create_order_duplicate_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    data = {
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 400

def test_create_order_success():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    data = {
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()
    assert updated_book["stock"] == 8

def test_status_transition_pending_to_confirmed():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_status_transition_invalid():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_status_cancelled_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()
    assert updated_book["stock"] == 10

def test_delete_pending_order_restores_stock():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204
    updated_book = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()
    assert updated_book["stock"] == 10

def test_delete_shipped_order_fails():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"], stock=10)
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "C", "customer_email": "e@e.cz",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 400

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=30)
    assert r.status_code == 422

def test_list_books_malformed_query_params():
    r = requests.get(f"{BASE_URL}/books", params={"page": "abc"}, timeout=30)
    assert r.status_code == 422

def test_check_health():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}