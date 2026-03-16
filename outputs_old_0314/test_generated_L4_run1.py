import pytest
import requests

BASE_URL = "http://localhost:8000"

def headers():
    return {"Content-Type": "application/json"}

def create_test_author(name="Author", bio="Bio", born_year=1990):
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, headers=headers())
    assert r.status_code == 201
    return r.json()

def create_test_category(name="Category"):
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=headers())
    assert r.status_code == 201
    return r.json()

def create_test_book(author_id, category_id, title="Book", isbn="1234567890", price=10.0, year=2020, stock=5):
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price, "published_year": year, 
        "stock": stock, "author_id": author_id, "category_id": category_id
    }, headers=headers())
    assert r.status_code == 201
    return r.json()

def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_valid():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "Valid Author", "born_year": 1990}, headers=headers())
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_author_invalid_birth_year():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "Old Author", "born_year": 3000}, headers=headers())
    assert r.status_code == 422

def test_create_duplicate_category_name():
    name = "UniqueCat"
    create_test_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=headers())
    assert r.status_code == 409

def test_create_book_with_nonexistent_author():
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Ghost", "isbn": "1234567890", "price": 10, "published_year": 2020,
        "author_id": 9999, "category_id": cat["id"]
    }, headers=headers())
    assert r.status_code == 404

def test_create_book_invalid_isbn_length():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad ISBN", "isbn": "123", "price": 10, "published_year": 2020,
        "author_id": auth["id"], "category_id": cat["id"]
    }, headers=headers())
    assert r.status_code == 422

def test_list_books_pagination_boundaries():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=1")
    assert r.status_code == 200
    assert "items" in r.json()
    assert r.json()["page"] == 1

def test_list_books_filter_by_price_range():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000")
    assert r.status_code == 200

def test_delete_book_cascade_reviews():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001112")
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Fan"}, headers=headers())
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

def test_create_review_invalid_rating():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001113")
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Bad"}, headers=headers())
    assert r.status_code == 422

def test_get_rating_no_reviews():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001114")
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating")
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_max_allowed_discount():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001115", year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 50}, headers=headers())
    assert r.status_code == 200

def test_apply_discount_too_high():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001116", year=2000)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 51}, headers=headers())
    assert r.status_code == 422

def test_update_stock_invalid_quantity():
    auth = create_test_author()
    cat = create_test_category()
    book = create_test_book(auth["id"], cat["id"], isbn="9990001117", stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", headers=headers())
    assert r.status_code == 400

def test_delete_author_with_linked_books():
    auth = create_test_author()
    cat = create_test_category()
    create_test_book(auth["id"], cat["id"], isbn="9990001118")
    r = requests.delete(f"{BASE_URL}/authors/{auth['id']}")
    assert r.status_code == 409

def test_update_category_name_to_existing():
    c1 = create_test_category(name="C1")
    create_test_category(name="C2")
    r = requests.put(f"{BASE_URL}/categories/{c1['id']}", json={"name": "C2"}, headers=headers())
    assert r.status_code == 409

def test_get_nonexistent_book():
    r = requests.get(f"{BASE_URL}/books/999999")
    assert r.status_code == 404

def test_create_book_zero_price():
    auth = create_test_author()
    cat = create_test_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Free", "isbn": "9990001119", "price": 0, "published_year": 2020,
        "author_id": auth["id"], "category_id": cat["id"]
    }, headers=headers())
    assert r.status_code == 201

def test_list_books_invalid_page_number():
    r = requests.get(f"{BASE_URL}/books?page=-1")
    assert r.status_code == 422