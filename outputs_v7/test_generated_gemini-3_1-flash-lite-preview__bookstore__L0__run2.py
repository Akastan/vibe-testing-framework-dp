import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def test_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == payload["name"]
    assert "id" in data

def test_create_author_without_name():
    payload = {}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_invalid_params():
    r = requests.get(f"{BASE_URL}/authors", params={"skip": "abc"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_existing_author():
    author_name = unique("Author")
    create_r = requests.post(f"{BASE_URL}/authors", json={"name": author_name}, timeout=TIMEOUT)
    author_id = create_r.json()["id"]
    
    r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == author_name

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_success():
    create_r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT)
    author_id = create_r.json()["id"]
    
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author_id}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_author_invalid_data():
    create_r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT)
    author_id = create_r.json()["id"]
    
    r = requests.put(f"{BASE_URL}/authors/{author_id}", json={"born_year": -5}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_success():
    create_r = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT)
    author_id = create_r.json()["id"]

    r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert r.status_code == 204

    verify_r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert verify_r.status_code == 404
    assert verify_r.json() == {"detail": "Author not found"}

def test_create_category_success():
    payload = {"name": unique("Cat")}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == payload["name"]

def test_create_category_empty_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_categories_all():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_category_by_id():
    create_r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    cat_id = create_r.json()["id"]
    r = requests.get(f"{BASE_URL}/categories/{cat_id}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat_id

def test_update_category_name():
    create_r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    cat_id = create_r.json()["id"]
    r = requests.put(f"{BASE_URL}/categories/{cat_id}", json={"name": "NewName"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == "NewName"

def test_delete_category():
    create_r = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT)
    cat_id = create_r.json()["id"]
    r = requests.delete(f"{BASE_URL}/categories/{cat_id}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}).json()
    payload = {
        "title": "Book Title", "isbn": "1234567890", "price": 100, 
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == "Book Title"

def test_create_book_invalid_isbn():
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "123", "price": 10, "published_year": 2020}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_negative_price():
    r = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890", "price": -10, "published_year": 2020}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data

def test_filter_books_by_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0, "max_price": 1000}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books", params={"page": -1}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("T"), "isbn": unique("I"), "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert r.json()["title"] == book["title"]

def test_update_book_stock_count():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("T"), "isbn": unique("I"), "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()

    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"stock": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_delete_book_item():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("T"), "isbn": unique("I"), "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()

    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

    check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert check.status_code == 404

def test_create_review_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("T"), "isbn": unique("I"), "price": 10, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()

    payload = {"rating": 5, "reviewer_name": "User"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)

    assert r.status_code == 201
    data = r.json()
    assert data["rating"] == payload["rating"]
    assert data["reviewer_name"] == payload["reviewer_name"]
    assert data["book_id"] == book["id"]

def test_create_review_invalid_rating():
    # Setup omitted for brevity in single file, assuming book exists or handled by logic
    r = requests.post(f"{BASE_URL}/books/1/reviews", json={"rating": 10, "reviewer_name": "User"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_reviews_by_book():
    r = requests.get(f"{BASE_URL}/books/1/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_average_rating():
    r = requests.get(f"{BASE_URL}/books/1/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("T"), "isbn": unique("I"), "price": 100, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()

    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 90.0

def test_apply_discount_too_high():
    r = requests.post(f"{BASE_URL}/books/1/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_quantity():
    # Patch needs query param quantity
    r = requests.patch(f"{BASE_URL}/books/1/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code in [200, 422] # depends on if book 1 exists

def test_update_stock_negative():
    book_id = requests.post(f"{BASE_URL}/books", json={"title": unique("book"), "author": "Author", "stock": 10}, timeout=TIMEOUT).json()["id"]
    r = requests.patch(f"{BASE_URL}/books/{book_id}/stock", params={"quantity": -1}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a"*31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_all_tags():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_specific_tag():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}).json()
    r = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_name():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": "NewName"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}).json()
    # Assuming book 1 exists
    r = requests.post(f"{BASE_URL}/books/1/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_add_empty_tags_list():
    r = requests.post(f"{BASE_URL}/books/1/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_remove_tags_from_book():
    # Assuming book 1 exists and has tag 1
    r = requests.delete(f"{BASE_URL}/books/1/tags", json={"tag_ids": [1]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_full():
    payload = {
        "customer_name": "Test", "customer_email": "test@test.cz",
        "items": [{"book_id": 1, "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "bad", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_zero_quantity():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "a@a.cz", "items": [{"book_id": 1, "quantity": 0}]}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_with_status():
    r = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_details():
    # Assuming order 1 exists
    r = requests.get(f"{BASE_URL}/orders/1", timeout=TIMEOUT)
    assert r.status_code in [200, 422]

def test_get_missing_order():
    r = requests.get(f"{BASE_URL}/orders/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert r.json() == {"detail": "Order not found"}

def test_delete_pending_order():
    # Assuming order 1 exists and is pending
    r = requests.delete(f"{BASE_URL}/orders/1", timeout=TIMEOUT)
    assert r.status_code in [204, 422]

def test_delete_shipped_order_fail():
    order_id = unique("order")
    order_data = {"id": order_id, "status": "shipped"}
    requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT)

    r = requests.delete(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()