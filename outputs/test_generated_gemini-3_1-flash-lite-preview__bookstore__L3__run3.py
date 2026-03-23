import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    return requests.post(f"{BASE_URL}/authors", json={
        "name": unique("Author"),
        "bio": "Bio",
        "born_year": 1990
    }, timeout=30).json()

def create_category():
    return requests.post(f"{BASE_URL}/categories", json={
        "name": unique("Category"),
        "description": "Desc"
    }, timeout=30).json()

def create_book(author_id, category_id, stock=10, year=2020):
    return requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": unique("9780"),
        "price": 100.0,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30).json()

def test_get_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=30)
    assert r.status_code == 422

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/9999", timeout=30)
    assert r.status_code == 404

def test_create_book_success():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": "1234567890", "price": 10.0, "published_year": 2020, 
        "stock": 10, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 201

def test_create_book_duplicate_isbn():
    a = create_author()
    c = create_category()
    isbn = "1234567890"
    requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B2", "isbn": isbn, "price": 10.0, "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_nonexistent_author():
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "B", "isbn": "1234567890", "price": 10.0, "published_year": 2020, "author_id": 999, "category_id": c["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_increase_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_insufficient_stock_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -5}, timeout=30)
    assert r.status_code == 400

def test_apply_discount_old_book():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_new_book_error():
    import datetime
    a = create_author()
    c = create_category()
    current_year = datetime.date.today().year
    b = create_book(a["id"], c["id"], year=current_year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400
    assert "error" in r.json()

def test_apply_discount_too_high():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], year=2000)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_add_tags_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 1

def test_add_nonexistent_tag():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999]}, timeout=30)
    assert r.status_code == 404

def test_remove_tag_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) == 0

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30)
    assert r.status_code == 201

def test_create_duplicate_tag():
    name = unique("T")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_delete_tag_in_use_conflict():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201

def test_create_order_duplicate_book_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", 
        "items": [{"book_id": b["id"], "quantity": 1}, {"book_id": b["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 400

def test_create_order_insufficient_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_status_pending_to_confirmed():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200

def test_update_status_cancel_returns_stock():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 5}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "cancelled"}, timeout=30)
    b_updated = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).json()
    assert b_updated["stock"] == 10

def test_update_status_invalid_transition():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 400

def test_delete_pending_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_shipped_order_error():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 400

def test_list_categories_empty():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=30)
    assert r.status_code == 201

def test_update_category_name_collision():
    n1 = unique("C")
    n2 = unique("C")
    requests.post(f"{BASE_URL}/categories", json={"name": n1}, timeout=30)
    c2 = requests.post(f"{BASE_URL}/categories", json={"name": n2}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": n1}, timeout=30)
    assert r.status_code == 409

def test_list_books_pagination_default():
    r = requests.get(f"{BASE_URL}/books", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_search_filter():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books", params={"search": "Book"}, timeout=30)
    assert r.status_code == 200

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": 0}, timeout=30)
    assert r.status_code == 422

def test_get_book_detail():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/9999", timeout=30)
    assert r.status_code == 404

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Test"
    }, timeout=30)
    assert r.status_code == 201

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Test"
    }, timeout=30)
    assert r.status_code == 422

def test_get_rating_no_reviews():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_list_orders_with_filters():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=30)
    assert r.status_code == 200

def test_list_orders_bad_page_size():
    r = requests.get(f"{BASE_URL}/orders", params={"page_size": 999}, timeout=30)
    assert r.status_code == 422

def test_get_author_detail():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200

def test_update_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"price": 150.0}, timeout=30)
    assert r.status_code == 200

def test_get_tag_detail():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    r = requests.get(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 200

def test_delete_category_with_books_error():
    a = create_author()
    c = create_category()
    create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409

def test_delete_book_cascade_check():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "T"}, timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204
    assert requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30).status_code == 404

def test_list_reviews_empty():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/reviews", timeout=30)
    assert r.status_code == 200
    assert r.json() == []

def test_update_author_success():
    a = create_author()
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"bio": "New Bio"}, timeout=30)
    assert r.status_code == 200

def test_update_tag_success():
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=30).json()
    r = requests.put(f"{BASE_URL}/tags/{t['id']}", json={"name": unique("T_new")}, timeout=30)
    assert r.status_code == 200

def test_get_order_detail():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], stock=10)
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=30)
    assert r.status_code == 200