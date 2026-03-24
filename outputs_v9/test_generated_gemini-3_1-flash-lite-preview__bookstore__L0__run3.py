import requests
import uuid
import pytest

BASE_URL = "http://localhost:8000"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    data = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=data, timeout=30)
    return r.json()

def create_category():
    data = {"name": unique("Category")}
    r = requests.post(f"{BASE_URL}/categories", json=data, timeout=30)
    return r.json()

def create_book(author_id, category_id):
    data = {
        "title": unique("Book"),
        "isbn": str(uuid.uuid4().hex[:10]),
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_existing_author():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_invalid_id():
    r = requests.get(f"{BASE_URL}/authors/abc", timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_bio():
    author = create_author()
    new_bio = "Updated Bio"
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"bio": new_bio}, timeout=30)
    assert r.status_code == 200
    assert r.json()["bio"] == new_bio

def test_delete_existing_author():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204
    r_get = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r_get.status_code == 404
    assert r_get.json() == {"detail": "Author not found"}

def test_create_valid_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_too_long_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": "a" * 51}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_valid_book():
    auth = create_author()
    cat = create_category()
    title = unique("Book")
    data = {
        "title": title, "isbn": "1234567890", "price": 50.0, 
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=30)
    assert r.status_code == 201
    assert r.json()["title"] == title

def test_create_book_negative_price():
    r = requests.post(f"{BASE_URL}/books", json={"price": -10}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_filter_books_by_price():
    auth = create_author()
    cat = create_category()
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=200", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_get_books_page_zero():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=30)
    assert r.status_code == 422

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_update_book_stock_count():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"stock": 50}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_delete_book_successfully():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r_check.status_code == 404

def test_add_valid_review():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester"}, timeout=30)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_add_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Bad"}, timeout=30)
    assert r.status_code == 422

def test_get_book_avg_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_valid_discount():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_apply_discount_too_high():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=30)
    assert r.status_code == 422

def test_update_stock_partial():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])

    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

    r_get = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r_get.status_code == 200
    assert r_get.json()["stock"] == 5

def test_create_new_tag():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()

def test_link_tags_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=30).json()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["tags"]) > 0

def test_link_no_tags_to_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": []}, timeout=30)
    assert r.status_code == 422

def test_create_order_full():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    data = {
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r = requests.post(f"{BASE_URL}/orders", json=data, timeout=30)
    assert r.status_code == 201
    assert r.json()["total_price"] > 0
    # Ověření skladu po objednávce
    book_r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30).json()
    assert book_r["stock"] < 10

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "X", "customer_email": "invalid", "items": []}, timeout=30)
    assert r.status_code == 422

def test_list_orders_with_filter():
    r = requests.get(f"{BASE_URL}/orders?customer_name=John", timeout=30)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_pending_order():
    # Pozn: Vytvoříme objednávku a hned smažeme
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Test", "customer_email": "test@test.cz",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30).json()
    r = requests.delete(f"{BASE_URL}/orders/{order['id']}", timeout=30)
    assert r.status_code == 204