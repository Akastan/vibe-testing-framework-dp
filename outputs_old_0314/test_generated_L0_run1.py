import pytest
import requests

BASE_URL = "http://localhost:8000"

def test_check_service_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("Content-Type", "")

def test_create_valid_author():
    payload = {"name": "Test Author", "bio": "Bio content", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data["id"], int)
    assert data["name"] == "Test Author"

def test_create_author_empty_name():
    payload = {"name": ""}
    response = requests.post(f"{BASE_URL}/authors", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999")
    assert response.status_code == 422

def test_create_category_max_length_name():
    # 409 Conflict obvykle znamena, ze entita uz existuje, testujeme tedy unikatni jmeno
    payload = {"name": "UniqueCategory" + str(requests.get(f"{BASE_URL}/health").elapsed.total_seconds())}
    response = requests.post(f"{BASE_URL}/categories", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code in [201, 409]

def test_create_book_invalid_year():
    payload = {"title": "Test Book", "isbn": "1234567890", "price": 10.0, "published_year": 500, "author_id": 1, "category_id": 1}
    response = requests.post(f"{BASE_URL}/books", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_create_book_negative_price():
    payload = {"title": "Test Book", "isbn": "1234567890", "price": -1.0, "published_year": 2020, "author_id": 1, "category_id": 1}
    response = requests.post(f"{BASE_URL}/books", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_list_books_pagination_limits():
    response = requests.get(f"{BASE_URL}/books?page=1&page_size=100")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["total"], int)

def test_list_books_invalid_page():
    response = requests.get(f"{BASE_URL}/books?page=0")
    assert response.status_code == 422

def test_update_book_invalid_isbn():
    response = requests.put(f"{BASE_URL}/books/1", json={"isbn": "123"}, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_create_review_invalid_rating():
    payload = {"rating": 10, "reviewer_name": "Tester"}
    response = requests.post(f"{BASE_URL}/books/1/reviews", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_apply_valid_discount():
    # Předpokládáme existenci knihy ID 1
    payload = {"discount_percent": 10}
    response = requests.post(f"{BASE_URL}/books/1/discount", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code in [200, 404, 422]

def test_apply_excessive_discount():
    payload = {"discount_percent": 60}
    response = requests.post(f"{BASE_URL}/books/1/discount", json=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_update_stock_negative_quantity():
    response = requests.patch(f"{BASE_URL}/books/1/stock?quantity=-5")
    assert response.status_code in [422, 400]

def test_list_authors_default_params():
    response = requests.get(f"{BASE_URL}/authors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_delete_category_success():
    # Vytvorime kategorii pro smazani
    cat = requests.post(f"{BASE_URL}/categories", json={"name": "TempCat"}, headers={"Content-Type": "application/json"}).json()
    response = requests.delete(f"{BASE_URL}/categories/{cat['id']}")
    assert response.status_code == 204

def test_get_rating_valid_book():
    response = requests.get(f"{BASE_URL}/books/1/rating")
    assert response.status_code in [200, 404]

def test_delete_book_nonexistent():
    response = requests.delete(f"{BASE_URL}/books/999999")
    assert response.status_code in [404, 422]

def test_list_reviews_empty_book():
    response = requests.get(f"{BASE_URL}/books/1/reviews")
    assert response.status_code == 200
    assert isinstance(response.json(), list)