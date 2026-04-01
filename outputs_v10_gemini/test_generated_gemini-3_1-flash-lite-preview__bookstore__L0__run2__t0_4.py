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
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_empty_name():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_invalid_price():
    author = create_author()
    cat = create_category()
    data = {
        "title": "Bad Book", "isbn": "1234567890", "price": -10.0,
        "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_invalid_year():
    author = create_author()
    cat = create_category()
    data = {
        "title": "Bad Year", "isbn": "1234567890", "price": 10.0,
        "published_year": 500, "author_id": author["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
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

def test_update_book_invalid_isbn():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"isbn": "123"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_create_review_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Tester"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_rating_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_too_high():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_stock_negative():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()
    assert r.json()["detail"] is not None

def test_create_category_valid():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_too_long_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": "a" * 51}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_tag_valid():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_add_tags_empty_list():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Test", "customer_email": "bad-email", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "Test", "customer_email": "test@test.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

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

def test_update_author_invalid_year():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"born_year": 3000}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_category_not_found():
    r = requests.get(f"{BASE_URL}/categories/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_tag_empty_name():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "TempTag"}, timeout=TIMEOUT)
    tag_id = r.json()["id"]
    r_upd = requests.put(f"{BASE_URL}/tags/{tag_id}", json={"name": ""}, timeout=TIMEOUT)
    assert r_upd.status_code == 422

def test_remove_tags_valid():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [1]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_price_range():
    r = requests.get(f"{BASE_URL}/books?min_price=10&max_price=500", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_author_invalid_id():
    r = requests.delete(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()