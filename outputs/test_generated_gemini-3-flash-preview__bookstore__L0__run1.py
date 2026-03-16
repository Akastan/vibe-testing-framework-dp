import pytest
import requests

BASE_URL = "http://localhost:8000"

def reset_db():
    requests.post(f"{BASE_URL}/reset", timeout=5)

def create_author_helper(name="John Doe", bio="Writer", born_year=1980):
    payload = {
        "name": name,
        "bio": bio,
        "born_year": born_year
    }
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    return r.json()

def create_category_helper(name="Sci-Fi", description="Science Fiction"):
    payload = {
        "name": name,
        "description": description
    }
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    return r.json()

def create_book_helper(author_id, category_id, title="Test Book", isbn="1234567890", price=100.0, published_year=2020, stock=10):
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    return r.json()

# --- HEALTH ---

def test_health_check_status():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200

# --- AUTHORS ---

def test_create_author_valid():
    reset_db()
    payload = {"name": "Valid Author", "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == "Valid Author"

def test_create_author_missing_name():
    reset_db()
    payload = {"bio": "Missing name"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_future_born_year():
    reset_db()
    payload = {"name": "Future Author", "born_year": 2030}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_null_bio():
    reset_db()
    payload = {"name": "Null Bio Author", "bio": None, "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["bio"] is None

def test_list_authors_default():
    reset_db()
    create_author_helper()
    r = requests.get(f"{BASE_URL}/authors", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_max_limit():
    reset_db()
    r = requests.get(f"{BASE_URL}/authors", params={"limit": 100}, timeout=5)
    assert r.status_code == 200

def test_get_author_detail():
    reset_db()
    author = create_author_helper()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_invalid_id_type():
    reset_db()
    r = requests.get(f"{BASE_URL}/authors/not-an-integer", timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_author_full():
    reset_db()
    author = create_author_helper()
    payload = {"name": "Updated Name", "bio": "Updated Bio", "born_year": 1995}
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"

def test_update_author_name_too_long():
    reset_db()
    author = create_author_helper()
    payload = {"name": "A" * 101}
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_author_success():
    reset_db()
    author = create_author_helper()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 204
    # Verification
    get_r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert get_r.status_code in [400, 404, 422]

# --- CATEGORIES ---

def test_list_categories_standard():
    reset_db()
    create_category_helper()
    r = requests.get(f"{BASE_URL}/categories", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_category_valid():
    reset_db()
    payload = {"name": "History", "description": "Old stuff"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == "History"

def test_create_category_empty_name():
    reset_db()
    payload = {"name": ""}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_category_name():
    reset_db()
    cat = create_category_helper()
    payload = {"name": "New Category Name"}
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["name"] == "New Category Name"

# --- BOOKS ---

def test_create_book_standard():
    reset_db()
    author = create_author_helper()
    cat = create_category_helper()
    payload = {
        "title": "Standard Book",
        "isbn": "1234567890",
        "price": 250.0,
        "published_year": 2022,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["title"] == "Standard Book"

def test_create_book_min_isbn():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    payload = {
        "title": "Min ISBN", "isbn": "1234567890", "price": 10.0,
        "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201

def test_create_book_max_isbn():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    payload = {
        "title": "Max ISBN", "isbn": "1234567890123", "price": 10.0,
        "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201

def test_create_book_negative_price():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    payload = {
        "title": "Neg Price", "isbn": "1234567890", "price": -5.0,
        "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 422

def test_create_book_invalid_year_low():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    payload = {
        "title": "Old Book", "isbn": "1234567890", "price": 10.0,
        "published_year": 999, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 422

def test_create_book_invalid_year_high():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    payload = {
        "title": "Future Book", "isbn": "1234567890", "price": 10.0,
        "published_year": 2027, "author_id": a["id"], "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 422

def test_list_books_pagination_first():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"page": 1, "page_size": 10}, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["page"] == 1

def test_list_books_search_valid():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    create_book_helper(a["id"], c["id"], title="UniqueTitle")
    r = requests.get(f"{BASE_URL}/books", params={"search": "UniqueTitle"}, timeout=5)
    assert r.status_code == 200
    assert any("UniqueTitle" in item["title"] for item in r.json()["items"])

def test_list_books_filter_price_range():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    create_book_helper(a["id"], c["id"], price=50.0)
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 40, "max_price": 60}, timeout=5)
    assert r.status_code == 200
    assert len(r.json()["items"]) > 0

def test_list_books_filter_author():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    create_book_helper(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books", params={"author_id": a["id"]}, timeout=5)
    assert r.status_code == 200
    assert all(item["author_id"] == a["id"] for item in r.json()["items"])

def test_list_books_invalid_page_size():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"page_size": 101}, timeout=5)
    assert r.status_code == 422

def test_list_books_search_special_chars():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"search": "!@#$%^&*()"}, timeout=5)
    assert r.status_code == 200

def test_list_books_zero_price_filter():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=5)
    assert r.status_code == 200

def test_get_book_detail_full():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["author"]["id"] == a["id"]
    assert data["category"]["id"] == c["id"]

def test_update_book_stock():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=10)
    payload = {"stock": 50}
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_delete_book_existing():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=5)
    assert r.status_code == 204

# --- REVIEWS ---

def test_create_review_valid():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    payload = {"rating": 5, "comment": "Great!", "reviewer_name": "Test User"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_rating_too_high():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    payload = {"rating": 6, "comment": "Too high", "reviewer_name": "Bad User"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 422

def test_create_review_rating_too_low():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    payload = {"rating": 0, "comment": "Too low", "reviewer_name": "Bad User"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 422

def test_list_reviews_existing():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": "R1"}, timeout=5)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=5)
    assert r.status_code == 200
    assert len(r.json()) > 0

def test_get_rating_standard():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "U1"}, timeout=5)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 3, "reviewer_name": "U2"}, timeout=5)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=5)
    assert r.status_code == 200

def test_get_rating_no_reviews():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=5)
    assert r.status_code == 200

# --- DISCOUNTS AND STOCK PATCH ---

def test_apply_discount_valid():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"], price=100.0)
    payload = {"discount_percent": 20.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_too_high():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    payload = {"discount_percent": 60.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 422

def test_apply_discount_zero():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    payload = {"discount_percent": 0.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 422

def test_update_stock_increment():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_missing_param():
    reset_db()
    a, c = create_author_helper(), create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", timeout=5)
    assert r.status_code == 422

# --- RESET ---

def test_reset_database_operation():
    r = requests.post(f"{BASE_URL}/reset", timeout=5)
    assert r.status_code == 200