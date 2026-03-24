import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    return r.json()

def create_category():
    name = unique("Cat")
    payload = {"name": name, "description": "Desc"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    return r.json()

def create_book(author_id, category_id):
    isbn = f"978{uuid.uuid4().hex[:7]}"
    payload = {
        "title": unique("Book"),
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_name():
    payload = {"name": ""}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_pagination():
    r = requests.get(f"{BASE_URL}/authors?limit=1", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()) <= 1

def test_get_author_by_id():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_nonexistent():
    r = requests.get(f"{BASE_URL}/authors/99999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_success():
    author = create_author()
    new_name = unique("AuthorUpdate")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_author_invalid_birth_year():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"born_year": 2030}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_create_category_success():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_empty():
    r = requests.post(f"{BASE_URL}/categories", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_category_exists():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat["id"]

def test_update_category_valid():
    cat = create_category()
    new_name = unique("CatUpd")
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_category_success():
    cat = create_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    a = create_author()
    c = create_category()
    isbn = f"978{uuid.uuid4().hex[:7]}"
    payload = {"title": "Book1", "isbn": isbn, "price": 10.0, "published_year": 2000, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    payload = {"title": "B", "isbn": "1234567890", "price": -1, "published_year": 2000, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_invalid_year():
    a = create_author()
    c = create_category()
    payload = {"title": "B", "isbn": "1234567890", "price": 10, "published_year": 999, "author_id": a["id"], "category_id": c["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_default():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    r = requests.get(f"{BASE_URL}/books?search=nonexistent", timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_list_books_price_filter():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_details():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_update_book_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"stock": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 6, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_book_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_book_avg_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_valid_discount():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_too_high_discount():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_quantity():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_stock_negative():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock?quantity=-1", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()
    assert r.json()["detail"] is not None

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_tag_by_id():
    r_c = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    t_id = r_c.json()["id"]
    r = requests.get(f"{BASE_URL}/tags/{t_id}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_success():
    r_c = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    t_id = r_c.json()["id"]
    r = requests.put(f"{BASE_URL}/tags/{t_id}", json={"name": unique("NewTag")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag_success():
    r_c = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    t_id = r_c.json()["id"]
    r = requests.delete(f"{BASE_URL}/tags/{t_id}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r_t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    t_id = r_t.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t_id]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_tags_empty_list():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_remove_tags_from_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r_t = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    t_id = r_t.json()["id"]
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t_id]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t_id]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    payload = {
        "customer_name": "Test",
        "customer_email": "test@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_invalid_email():
    payload = {"customer_name": "Test", "customer_email": "", "items": []}
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_paginated():
    r = requests.get(f"{BASE_URL}/orders?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_status_filter():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_details():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT)
    o_id = o.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{o_id}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_not_found():
    r = requests.get(f"{BASE_URL}/orders/99999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_pending_order():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={"customer_name": "T", "customer_email": "a@b.cz", "items": [{"book_id": b["id"], "quantity": 1}]}, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/orders/{o.json()['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_delivered_order_error():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])

    order_payload = {
        "book_id": book["id"],
        "quantity": 1,
        "status": "delivered"
    }
    order = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT).json()

    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)

    assert r.status_code == 400
    assert "detail" in r.json()
    assert r.json()["detail"] is not None