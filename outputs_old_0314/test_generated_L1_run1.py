import pytest
import requests
import time

BASE_URL = "http://localhost:8000"

def test_check_service_availability():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200

def test_create_valid_author():
    payload = {"name": "Test Author", "bio": "Bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test Author"

def test_create_author_with_invalid_born_year():
    payload = {"name": "Invalid Year Author", "born_year": 3000}
    response = requests.post(f"{BASE_URL}/authors", json=payload)
    assert response.status_code == 422

def test_delete_author_with_existing_books():
    # Setup: Create author and book
    auth_resp = requests.post(f"{BASE_URL}/authors", json={"name": "Author with books"})
    auth_id = auth_resp.json()["id"]
    cat_resp = requests.post(f"{BASE_URL}/categories", json={"name": "Cat"})
    cat_id = cat_resp.json()["id"]
    requests.post(f"{BASE_URL}/books", json={
        "title": "Book", "isbn": "1234567890123", "price": 10.0, 
        "published_year": 2020, "author_id": auth_id, "category_id": cat_id
    })
    response = requests.delete(f"{BASE_URL}/authors/{auth_id}")
    assert response.status_code == 409

def test_create_duplicate_category():
    payload = {"name": "Unique Cat"}
    requests.post(f"{BASE_URL}/categories", json=payload)
    response = requests.post(f"{BASE_URL}/categories", json=payload)
    assert response.status_code == 409

def test_list_books_pagination_on_empty_db():
    response = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["total_pages"] == 1

def test_filter_books_by_invalid_author_id():
    response = requests.get(f"{BASE_URL}/books", params={"author_id": "abc"})
    assert response.status_code == 422

def test_create_book_with_nonexistent_author():
    payload = {
        "title": "Ghost Book", "isbn": "9999999999", "price": 10.0,
        "published_year": 2020, "author_id": 99999, "category_id": 1
    }
    response = requests.post(f"{BASE_URL}/books", json=payload)
    assert response.status_code == 404

def test_delete_book_cascading_reviews():
    # Setup
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "1111111111", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat}).json()["id"]
    requests.post(f"{BASE_URL}/books/{book}/reviews", json={"rating": 5, "reviewer_name": "R"})
    
    del_resp = requests.delete(f"{BASE_URL}/books/{book}")
    assert del_resp.status_code == 204
    
    get_reviews = requests.get(f"{BASE_URL}/books/{book}/reviews")
    assert get_reviews.status_code == 404

def test_create_review_with_invalid_rating():
    response = requests.post(f"{BASE_URL}/books/1/reviews", json={"rating": 10, "reviewer_name": "Bad"})
    assert response.status_code == 422

def test_get_rating_for_book_without_reviews():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "2222222222", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat}).json()["id"]
    response = requests.get(f"{BASE_URL}/books/{book}/rating")
    assert response.status_code == 200
    assert response.json().get("average_rating") is None

def test_apply_discount_to_new_book():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    # Vytvoření knihy z aktuálního roku (2025/2026)
    book = requests.post(f"{BASE_URL}/books", json={"title": "New", "isbn": "3333333333", "price": 100, "published_year": 2025, "author_id": auth, "category_id": cat}).json()["id"]
    response = requests.post(f"{BASE_URL}/books/{book}/discount", json={"discount_percent": 10})
    assert response.status_code == 400

def test_apply_excessive_discount():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    book = requests.post(f"{BASE_URL}/books", json={"title": "Old", "isbn": "4444444444", "price": 100, "published_year": 2000, "author_id": auth, "category_id": cat}).json()["id"]
    response = requests.post(f"{BASE_URL}/books/{book}/discount", json={"discount_percent": 60})
    assert response.status_code == 422

def test_update_stock_resulting_in_negative():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    book = requests.post(f"{BASE_URL}/books", json={"title": "S", "isbn": "5555555555", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat, "stock": 5}).json()["id"]
    response = requests.patch(f"{BASE_URL}/books/{book}/stock?quantity=-10")
    assert response.status_code == 400

def test_update_stock_positive_increment():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    book = requests.post(f"{BASE_URL}/books", json={"title": "S", "isbn": "6666666666", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat, "stock": 5}).json()["id"]
    response = requests.patch(f"{BASE_URL}/books/{book}/stock?quantity=5")
    assert response.status_code == 200
    assert response.json()["stock"] == 10

def test_update_book_with_duplicate_isbn():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "C"}).json()["id"]
    requests.post(f"{BASE_URL}/books", json={"title": "B1", "isbn": "7777777777", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat})
    b2 = requests.post(f"{BASE_URL}/books", json={"title": "B2", "isbn": "8888888888", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat}).json()["id"]
    response = requests.put(f"{BASE_URL}/books/{b2}", json={"isbn": "7777777777"})
    assert response.status_code == 409

def test_delete_category_with_books():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "D"}).json()["id"]
    auth = requests.post(f"{BASE_URL}/authors", json={"name": "A"}).json()["id"]
    requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "9999999999", "price": 1, "published_year": 2020, "author_id": auth, "category_id": cat})
    response = requests.delete(f"{BASE_URL}/categories/{cat}")
    assert response.status_code == 409

def test_list_books_invalid_page_size():
    response = requests.get(f"{BASE_URL}/books", params={"page_size": 200})
    assert response.status_code == 422

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999")
    assert response.status_code == 404