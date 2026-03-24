import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_category():
    data = {"name": unique("Category")}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def test_check_service_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_invalid_id():
    r = requests.get(f"{BASE_URL}/authors/abc", timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_existing_author():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_create_valid_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_valid_book():
    a = create_author()
    c = create_category()
    title = unique("Book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": "1234567890", "price": 10.0, 
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == title

def test_create_book_missing_fields():
    r = requests.post(f"{BASE_URL}/books", json={"title": "Missing"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_negative_price():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "BadPrice", "isbn": "1234567890", "price": -1.0, 
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_create_valid_review():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["book_id"] == book["id"]

def test_create_review_out_of_bounds_rating():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_rating():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_valid_discount():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] < r.json()["original_price"]

def test_apply_discount_too_high():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"stock": 50}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_valid_tag():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_add_tags_to_book_empty_list():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_valid_tags_to_book():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    t = requests.post(f"{BASE_URL}/tags", json={"name": unique("T")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "N", "customer_email": "e@e.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_valid_items():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_update_order_status_valid():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

def test_update_order_status_invalid():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_pending_order():
    a = create_author()
    c = create_category()
    book = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "t@t.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_non_existent_order():
    r = requests.delete(f"{BASE_URL}/orders/99999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()