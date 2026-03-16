import pytest
import requests
import time

BASE_URL = "http://localhost:8000"

# --- HELPERS ---

def reset_db():
    requests.post(f"{BASE_URL}/reset", timeout=5)

def create_author_helper(name="John Doe", bio="Bio", born_year=1970):
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    return r.json()

def create_category_helper(name="Fiction", description="Story books"):
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    return r.json()

def create_book_helper(author_id, category_id, title="Test Book", isbn="1234567890", price=19.99, year=2020, stock=10):
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    return r.json()

# --- TESTS ---

def test_health_check_status_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_author_valid():
    reset_db()
    payload = {"name": "Valid Author", "bio": "Some bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Valid Author"
    assert "id" in data

def test_create_author_empty_name():
    reset_db()
    payload = {"name": "", "bio": "Some bio"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_max_length_name():
    reset_db()
    long_name = "A" * 100
    payload = {"name": long_name}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == long_name

def test_create_author_future_born_year():
    reset_db()
    payload = {"name": "Future Man", "born_year": 2026}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["born_year"] == 2026

def test_list_authors_default():
    reset_db()
    create_author_helper(name="Author 1")
    create_author_helper(name="Author 2")
    r = requests.get(f"{BASE_URL}/authors", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 2

def test_get_author_by_id():
    reset_db()
    author = create_author_helper(name="Find Me")
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 200
    assert r.json()["name"] == "Find Me"

def test_get_author_not_found():
    reset_db()
    r = requests.get(f"{BASE_URL}/authors/9999", timeout=5)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_with_books():
    reset_db()
    author = create_author_helper()
    category = create_category_helper()
    create_book_helper(author["id"], category["id"])
    
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_author_success():
    reset_db()
    author = create_author_helper()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 204

def test_create_category_valid():
    reset_db()
    payload = {"name": "Sci-Fi", "description": "Science Fiction"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == "Sci-Fi"

def test_create_category_duplicate_name():
    reset_db()
    create_category_helper(name="Duplicate")
    payload = {"name": "Duplicate"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_category_with_books():
    reset_db()
    author = create_author_helper()
    category = create_category_helper()
    create_book_helper(author["id"], category["id"])
    
    r = requests.delete(f"{BASE_URL}/categories/{category['id']}", timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_valid():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    payload = {
        "title": "Valid Book",
        "isbn": "111222333444",
        "price": 25.50,
        "published_year": 2022,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["title"] == "Valid Book"

def test_create_book_duplicate_isbn():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    isbn = "1234567890123"
    create_book_helper(a["id"], c["id"], isbn=isbn)
    
    payload = {
        "title": "Book 2",
        "isbn": isbn,
        "price": 10,
        "published_year": 2020,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_invalid_author():
    reset_db()
    c = create_category_helper()
    payload = {
        "title": "Ghost Book",
        "isbn": "1234567890",
        "price": 10,
        "published_year": 2020,
        "author_id": 999,
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_create_book_zero_price():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    payload = {
        "title": "Free Book",
        "isbn": "1234567890",
        "price": 0,
        "published_year": 2020,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["price"] == 0

def test_create_book_isbn_min_length():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    isbn = "1" * 10
    payload = {
        "title": "Short ISBN",
        "isbn": isbn,
        "price": 10,
        "published_year": 2020,
        "author_id": a["id"],
        "category_id": c["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["isbn"] == isbn

def test_list_books_pagination():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    for i in range(12):
        create_book_helper(a["id"], c["id"], title=f"Book {i}", isbn=f"ISBN{i:05d}7890")
    
    r = requests.get(f"{BASE_URL}/books?page=2&page_size=5", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 5
    assert data["page"] == 2
    assert data["total"] == 12

def test_list_books_search_title():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    create_book_helper(a["id"], c["id"], title="Unique Treasure", isbn="1111111111")
    create_book_helper(a["id"], c["id"], title="Common Item", isbn="2222222222")
    
    r = requests.get(f"{BASE_URL}/books?search=Treasure", timeout=5)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Unique Treasure"

def test_list_books_filter_price():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    create_book_helper(a["id"], c["id"], price=10, isbn="1111111111")
    create_book_helper(a["id"], c["id"], price=50, isbn="2222222222")
    create_book_helper(a["id"], c["id"], price=100, isbn="3333333333")
    
    r = requests.get(f"{BASE_URL}/books?min_price=40&max_price=60", timeout=5)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["price"] == 50

def test_list_books_author_id_zero():
    reset_db()
    r = requests.get(f"{BASE_URL}/books?author_id=0", timeout=5)
    assert r.status_code == 200
    assert r.json()["items"] == []

def test_list_books_page_size_max():
    reset_db()
    r = requests.get(f"{BASE_URL}/books?page_size=100", timeout=5)
    assert r.status_code == 200
    assert r.json()["page_size"] == 100

def test_list_books_invalid_page():
    reset_db()
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_book_partial():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], price=20.0)
    
    payload = {"price": 99.99}
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["price"] == 99.99
    assert r.json()["title"] == book["title"]

def test_update_book_invalid_published_year():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    
    payload = {"published_year": 999}
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_review_valid():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    
    payload = {"rating": 5, "reviewer_name": "Critic", "comment": "Great!"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_rating_out_of_range():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    
    payload = {"rating": 6, "reviewer_name": "Hater"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_reviews_for_book():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": "A"}, timeout=5)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 2, "reviewer_name": "B"}, timeout=5)
    
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=5)
    assert r.status_code == 200
    assert len(r.json()) == 2

def test_get_rating_existing_reviews():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "A"}, timeout=5)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 1, "reviewer_name": "B"}, timeout=5)
    
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=5)
    assert r.status_code == 200
    assert r.json()["average_rating"] == 3.0
    assert r.json()["review_count"] == 2

def test_get_rating_no_reviews():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=5)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_valid_old_book():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    # Assuming current year is >= 2025, 2020 is old enough
    book = create_book_helper(a["id"], c["id"], price=100.0, year=2020)
    
    payload = {"discount_percent": 20}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_too_high():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], year=2020)
    
    payload = {"discount_percent": 51}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_new_book():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    current_year = time.gmtime().tm_year
    book = create_book_helper(a["id"], c["id"], year=current_year)
    
    payload = {"discount_percent": 10}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_add():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=10)
    
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_subtract():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=10)
    
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-3", timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == 7

def test_update_stock_negative_result():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=5)
    
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=5)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_zero_change():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"], stock=5)
    
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=0", timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_delete_book_cascade_reviews():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    book = create_book_helper(a["id"], c["id"])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "X"}, timeout=5)
    
    # Verify review exists
    rev_check = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=5)
    assert len(rev_check.json()) == 1
    
    # Delete book
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=5)
    
    # Verify review is gone (endpoint returns 404 because book is gone)
    rev_after = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=5)
    assert rev_after.status_code == 404

def test_reset_database_full():
    reset_db()
    a = create_author_helper()
    c = create_category_helper()
    create_book_helper(a["id"], c["id"])
    
    r_reset = requests.post(f"{BASE_URL}/reset", timeout=5)
    assert r_reset.status_code == 200
    
    r_books = requests.get(f"{BASE_URL}/books", timeout=5)
    assert r_books.json()["total"] == 0
    
    r_authors = requests.get(f"{BASE_URL}/authors", timeout=5)
    assert r_authors.json() == []

if __name__ == "__main__":
    pytest.main([__file__])