import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author")}
    response = requests.post(f"{BASE_URL}/authors", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

def create_category():
    data = {"name": unique("Cat")}
    response = requests.post(f"{BASE_URL}/categories", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

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
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
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
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_category_success():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_update_category_invalid_name():
    cat = create_category()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": "a" * 51}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_book_success():
    a = create_author()
    c = create_category()
    title = unique("Book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": "1234567890", "price": 10.0, 
        "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == title

def test_create_book_invalid_isbn():
    r = requests.post(f"{BASE_URL}/books", json={"title": "Test", "isbn": "123"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == b["id"]

def test_update_book_price_negative():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.put(f"{BASE_URL}/books/{b['id']}", json={"price": -10.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_invalid_rating():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Tester"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_rating_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] < b["price"]

def test_apply_discount_too_high():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 50}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_delete_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "John", "customer_email": "j@test.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_success():
    r = requests.get(f"{BASE_URL}/orders", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_order_details():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == o["id"]

def test_delete_order_invalid_status():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r.raise_for_status()
    r_del = requests.delete(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 422
    assert isinstance(r_del.json().get("detail"), (str, list, dict))

def test_update_order_status_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()

    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    r.raise_for_status()

    assert r.status_code == 200
    assert r.json()["status"] == "shipped"

    get_response = requests.get(f"{BASE_URL}/orders/{o['id']}", timeout=TIMEOUT)
    get_response.raise_for_status()
    assert get_response.json()["status"] == "shipped"

def test_update_order_status_invalid():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    o = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz",
        "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{o['id']}/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422