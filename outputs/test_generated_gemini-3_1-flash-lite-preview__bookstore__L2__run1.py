import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    return r.json()

def create_book(author_id=None, category_id=None, isbn=None, year=2000):
    aid = author_id or create_author()["id"]
    cid = category_id or create_category()["id"]
    data = {
        "title": unique("Book"),
        "isbn": isbn or unique("ISBN"),
        "price": 100.0,
        "published_year": year,
        "stock": 10,
        "author_id": aid,
        "category_id": cid
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    return r.json()

def test_get_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_invalid_author_empty():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_with_books_fails():
    auth = create_author()
    create_book(author_id=auth["id"])
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_duplicate_category():
    name = unique("Cat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_missing_author():
    cid = create_category()["id"]
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890", "price": 10, "published_year": 2000, "author_id": 9999, "category_id": cid}, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_with_duplicate_isbn():
    isbn = unique("ISBN")
    create_book(isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={"title": "T2", "isbn": isbn, "price": 10, "published_year": 2000, "author_id": 1, "category_id": 1}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/99999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_review_with_invalid_rating():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_rating_for_book_without_reviews():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["average_rating"] is None

def test_apply_discount_to_new_book_fails():
    book = create_book(year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_over_limit_fails():
    book = create_book(year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_decrease_stock_below_zero_fails():
    book = create_book()
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -100}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_assigned_tag_fails():
    book = create_book()
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    tag_id = r_tag.json()["id"]
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag_id}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_add_tags_idempotency():
    book = create_book()
    r_tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    tid = r_tag.json()["id"]
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tid]}, timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tid]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [99999]}, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_order_with_insufficient_stock():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 999}]
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_order_with_duplicate_books():
    book = create_book()
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_order_validation_error():
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": []
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_status_illegal_transition():
    book = create_book()
    r_o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    oid = r_o.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_status_invalid_value():
    book = create_book()
    r_o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    oid = r_o.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "invalid"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_shipped_order_fails():
    book = create_book()
    r_o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    oid = r_o.json()["id"]
    requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{oid}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{oid}", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_list_books_pagination_out_of_bounds():
    r = requests.get(f"{BASE_URL}/books?page=999", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_orders_filtering():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_author_edge_case_negative_id():
    r = requests.get(f"{BASE_URL}/authors/-1", timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_remove_nonexistent_tag_from_book():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [99999]}, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_category_name_collision():
    c1 = create_category(name="A")
    c2 = create_category(name="B")
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": "A"}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_get_books_by_author_no_books_found():
    auth = create_author()
    r = requests.get(f"{BASE_URL}/books?author_id={auth['id']}", timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0