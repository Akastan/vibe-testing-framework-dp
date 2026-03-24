import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Desc"}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_book(author_id, category_id):
    title = unique("Book")
    isbn = str(uuid.uuid4().int)[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": 10.0, 
        "published_year": 2020, "stock": 5, 
        "author_id": author_id, "category_id": category_id
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


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

def test_create_invalid_author():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_existing_author():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_name():
    author = create_author()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_create_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    assert "id" in book
    assert book["title"].startswith("Book")

def test_create_book_invalid_isbn():
    author = create_author()
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad ISBN", "isbn": "123", "price": 10.0, 
        "published_year": 2020, "author_id": author['id'], "category_id": cat['id']
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_details():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book['id']

def test_create_book_review():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": "TestUser", "comment": "Great"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_invalid_rating():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 10, "reviewer_name": "Bad"
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_rating_value():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_valid_discount():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["discounted_price"] < r.json()["original_price"]

def test_apply_invalid_discount():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60.0}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_increase_stock_level():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_create_new_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_delete_category_success():
    cat = create_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_valid_tag():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_empty_tag():
    r = requests.post(f"{BASE_URL}/tags", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_add_tags_to_book():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    tag_r = requests.post(f"{BASE_URL}/tags", json={"name": "NewTag"}, timeout=TIMEOUT)
    tag_id = tag_r.json()["id"]
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_create_valid_order():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Client", "customer_email": "c@c.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "total_price" in r.json()

def test_create_order_zero_quantity():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Client", "customer_email": "c@c.cz", 
        "items": [{"book_id": book['id'], "quantity": 0}]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_all_orders():
    r = requests.get(f"{BASE_URL}/orders", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_single_order():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    order_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Client", "customer_email": "c@c.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_id = order_r.json()["id"]
    r = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == order_id

def test_update_order_to_shipped():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    order_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Client", "customer_email": "c@c.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_r.raise_for_status()
    order_id = order_r.json()["id"]

    r = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "shipped"

    get_r = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
    assert get_r.status_code == 200
    assert get_r.json()["status"] == "shipped"
    assert get_r.json()["id"] == order_id

def test_invalid_status_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    order_r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Client", "customer_email": "c@c.cz", 
        "items": [{"book_id": book['id'], "quantity": 1}]
    }, timeout=TIMEOUT)
    order_id = order_r.json()["id"]
    r = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "invalid"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_successful():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_delete_book_successful():
    author = create_author()
    cat = create_category()
    book = create_book(author['id'], cat['id'])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404
    assert r_check.json() == {"detail": "Book not found"}