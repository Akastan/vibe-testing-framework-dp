import pytest
import requests

BASE_URL = "http://localhost:8000"

def test_create_author_success():
    payload = {"name": "Test Author", "bio": "Bio text", "born_year": 1990}
    response = requests.post(f"{BASE_URL}/authors", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test Author"

def test_delete_author_with_books_conflict():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "Auth1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "Cat1"}).json()
    requests.post(f"{BASE_URL}/books", json={
        "title": "Book1", "isbn": "1234567890", "price": 10.0,
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    })
    response = requests.delete(f"{BASE_URL}/authors/{auth['id']}")
    assert response.status_code == 409

def test_create_duplicate_category_conflict():
    requests.post(f"{BASE_URL}/categories", json={"name": "Dupe"})
    response = requests.post(f"{BASE_URL}/categories", json={"name": "Dupe"})
    assert response.status_code == 409

def test_create_book_with_nonexistent_author():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "1234567890123", "price": 10.0,
        "published_year": 2020, "author_id": 99999, "category_id": cat["id"]
    })
    assert response.status_code == 404

def test_create_book_duplicate_isbn():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book_data = {"title": "B1", "isbn": "1111111111", "price": 10.0, "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"]}
    requests.post(f"{BASE_URL}/books", json=book_data)
    response = requests.post(f"{BASE_URL}/books", json=book_data)
    assert response.status_code == 409

def test_create_book_invalid_year():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "2222222222", "price": 10.0,
        "published_year": 999, "author_id": auth["id"], "category_id": cat["id"]
    })
    assert response.status_code == 422

def test_list_books_pagination_default():
    response = requests.get(f"{BASE_URL}/books")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page_size():
    response = requests.get(f"{BASE_URL}/books?page_size=101")
    assert response.status_code == 422

def test_update_stock_negative_result():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "3333333333", "price": 10.0,
        "published_year": 2020, "author_id": auth["id"], "category_id": cat["id"], "stock": 5
    }).json()
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10")
    assert response.status_code == 400

def test_apply_discount_too_recent_book():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "New Book", "isbn": "4444444444", "price": 100.0,
        "published_year": 2025, "author_id": auth["id"], "category_id": cat["id"]
    }).json()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10})
    assert response.status_code == 400

def test_apply_discount_limit_exceeded():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "Old Book", "isbn": "5555555555", "price": 100.0,
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }).json()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 51})
    assert response.status_code == 422

def test_create_review_invalid_rating():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "6666666666", "price": 10.0,
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }).json()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "reviewer_name": "Anon"})
    assert response.status_code == 422

def test_get_rating_no_reviews():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "7777777777", "price": 10.0,
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }).json()
    response = requests.get(f"{BASE_URL}/books/{book['id']}/rating")
    assert response.status_code == 200
    assert response.json()["average_rating"] is None

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999")
    assert response.status_code == 404

def test_update_category_to_existing_name():
    c1 = requests.post(f"{BASE_URL}/categories", json={"name": "Unique1"}).json()
    c2 = requests.post(f"{BASE_URL}/categories", json={"name": "Unique2"}).json()
    response = requests.put(f"{BASE_URL}/categories/{c2['id']}", json={"name": "Unique1"})
    assert response.status_code == 409

def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_delete_book_cascade_check():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A1"}).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C1"}).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": "B1", "isbn": "8888888888", "price": 10.0,
        "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]
    }).json()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert response.status_code == 204

def test_get_book_not_found():
    response = requests.get(f"{BASE_URL}/books/999999")
    assert response.status_code == 404

def test_list_authors_empty():
    response = requests.get(f"{BASE_URL}/authors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)