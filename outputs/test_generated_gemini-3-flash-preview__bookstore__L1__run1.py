import pytest
import requests

BASE_URL = "http://localhost:8000"

def reset_db():
    requests.post(f"{BASE_URL}/reset", timeout=5)

def create_author(name="John Doe", born_year=1970):
    payload = {"name": name, "born_year": born_year, "bio": "Some bio"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    return r.json()

def create_category(name="Sci-Fi"):
    payload = {"name": name, "description": "Science Fiction books"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    return r.json()

def create_book(title="Dune", isbn="1234567890123", price=299.9, year=1965, author_id=None, category_id=None):
    if author_id is None:
        author_id = create_author()["id"]
    if category_id is None:
        category_id = create_category(name=f"Cat_{isbn}")["id"]
    
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": year,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200

def test_create_author_valid():
    reset_db()
    payload = {"name": "Frank Herbert", "born_year": 1920}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == "Frank Herbert"

def test_create_author_missing_name():
    reset_db()
    payload = {"born_year": 1920}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_born_year_min():
    reset_db()
    payload = {"name": "Ancient One", "born_year": 0}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["born_year"] == 0

def test_create_author_born_year_future():
    reset_db()
    payload = {"name": "Future Man", "born_year": 2027}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    reset_db()
    create_author("Author 1")
    create_author("Author 2")
    r = requests.get(f"{BASE_URL}/authors", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 2

def test_get_author_by_id():
    reset_db()
    author = create_author("Identity Test")
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 200
    assert r.json()["name"] == "Identity Test"

def test_delete_author_with_books():
    reset_db()
    book = create_book(isbn="9999999999999")
    author_id = book["author_id"]
    r = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_author_success():
    reset_db()
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=5)
    assert r.status_code == 204

def test_create_category_valid():
    reset_db()
    payload = {"name": "Historical", "description": "History books"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["name"] == "Historical"

def test_create_category_duplicate_name():
    reset_db()
    create_category("Unique")
    payload = {"name": "Unique"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_category_with_books():
    reset_db()
    book = create_book(isbn="8888888888888")
    category_id = book["category_id"]
    r = requests.delete(f"{BASE_URL}/categories/{category_id}", timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_valid():
    reset_db()
    author = create_author()
    category = create_category()
    payload = {
        "title": "Foundation",
        "isbn": "1111111111111",
        "price": 350.0,
        "published_year": 1951,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["title"] == "Foundation"

def test_create_book_duplicate_isbn():
    reset_db()
    create_book(isbn="1212121212121")
    author = create_author()
    category = create_category()
    payload = {
        "title": "Duplicate ISBN",
        "isbn": "1212121212121",
        "price": 100.0,
        "published_year": 2000,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_invalid_author():
    reset_db()
    category = create_category()
    payload = {
        "title": "No Author",
        "isbn": "0000000000000",
        "price": 100.0,
        "published_year": 2000,
        "author_id": 99999,
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code in [400, 404, 422]
    assert "detail" in r.json()

def test_create_book_published_year_edge_min():
    reset_db()
    author = create_author()
    category = create_category()
    payload = {
        "title": "Old Book",
        "isbn": "3333333333333",
        "price": 100.0,
        "published_year": 1000,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 201

def test_create_book_negative_price():
    reset_db()
    author = create_author()
    category = create_category()
    payload = {
        "title": "Free Book?",
        "isbn": "4444444444444",
        "price": -10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_search_title():
    reset_db()
    create_book(title="Searching for Nemo", isbn="1111111111001")
    create_book(title="The Hobbit", isbn="1111111111002")
    r = requests.get(f"{BASE_URL}/books", params={"search": "Nemo"}, timeout=5)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert "Nemo" in items[0]["title"]

def test_list_books_filter_price_range():
    reset_db()
    create_book(isbn="5555555555001", price=100.0)
    create_book(isbn="5555555555002", price=500.0)
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 400.0}, timeout=5)
    assert r.status_code == 200
    items = r.json()["items"]
    for item in items:
        assert item["price"] >= 400.0

def test_list_books_pagination_max_limit():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"page_size": 100}, timeout=5)
    assert r.status_code == 200
    assert r.json()["page_size"] == 100

def test_list_books_invalid_author_id_zero():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", params={"author_id": 0}, timeout=5)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 0

def test_get_book_not_found():
    reset_db()
    r = requests.get(f"{BASE_URL}/books/99999", timeout=5)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_book_detail():
    reset_db()
    book = create_book(title="Detail Book", isbn="7777777777777")
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "author" in data
    assert "category" in data
    assert data["author"]["id"] == book["author_id"]

def test_delete_book_cascade_reviews():
    reset_db()
    book = create_book(isbn="6666666666666")
    book_id = book["id"]
    requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={"rating": 5, "reviewer_name": "Test"}, timeout=5)
    
    del_r = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=5)
    assert del_r.status_code == 204
    
    r = requests.get(f"{BASE_URL}/books/{book_id}/reviews", timeout=5)
    assert r.status_code == 404 or len(r.json()) == 0

def test_create_review_valid():
    reset_db()
    book = create_book(isbn="1231231231231")
    payload = {"rating": 5, "comment": "Great!", "reviewer_name": "Reviewer"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_create_review_rating_out_of_range():
    reset_db()
    book = create_book(isbn="1231231231232")
    payload = {"rating": 6, "reviewer_name": "Bad Reviewer"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_review_empty_reviewer():
    reset_db()
    book = create_book(isbn="1231231231233")
    payload = {"rating": 3, "reviewer_name": ""}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_rating_with_data():
    reset_db()
    book = create_book(isbn="1231231231234")
    book_id = book["id"]
    requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={"rating": 5, "reviewer_name": "A"}, timeout=5)
    requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={"rating": 1, "reviewer_name": "B"}, timeout=5)
    r = requests.get(f"{BASE_URL}/books/{book_id}/rating", timeout=5)
    assert r.status_code == 200
    assert r.json()["average_rating"] == 3.0

def test_get_rating_no_reviews():
    reset_db()
    book = create_book(isbn="1231231231235")
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=5)
    assert r.status_code == 200
    assert r.json()["average_rating"] is None

def test_apply_discount_valid_old_book():
    reset_db()
    book = create_book(isbn="1234123412341", year=2000, price=1000.0)
    payload = {"discount_percent": 20.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 800.0

def test_apply_discount_new_book():
    reset_db()
    book = create_book(isbn="1234123412342", year=2026, price=1000.0)
    payload = {"discount_percent": 10.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_exceed_max():
    reset_db()
    book = create_book(isbn="1234123412343", year=2000)
    payload = {"discount_percent": 50.1}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_zero_percent():
    reset_db()
    book = create_book(isbn="1234123412344", year=2000)
    payload = {"discount_percent": 0.0}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=5)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_add_quantity():
    reset_db()
    book = create_book(isbn="1112223334445")
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == book["stock"] + 5

def test_update_stock_remove_quantity_valid():
    reset_db()
    book = create_book(isbn="1112223334446")
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -5}, timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == book["stock"] - 5

def test_update_stock_negative_result():
    reset_db()
    book = create_book(isbn="1112223334447")
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -100}, timeout=5)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_zero_quantity():
    reset_db()
    book = create_book(isbn="1112223334448")
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 0}, timeout=5)
    assert r.status_code == 200
    assert r.json()["stock"] == book["stock"]

def test_reset_database_functional():
    create_author()
    reset_db()
    r = requests.get(f"{BASE_URL}/authors", timeout=5)
    assert len(r.json()) == 0

def test_list_books_empty_db():
    reset_db()
    r = requests.get(f"{BASE_URL}/books", timeout=5)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    # Known Issue Check
    assert r.json()["total_pages"] == 1

def test_list_reviews_success():
    reset_db()
    book = create_book(isbn="9876543210123")
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "T"}, timeout=5)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=5)
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_update_category_name_valid():
    reset_db()
    cat = create_category("Original Name")
    payload = {"name": "New Name"}
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json=payload, timeout=5)
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"

def test_update_category_name_duplicate():
    reset_db()
    create_category("Target")
    cat = create_category("To Rename")
    payload = {"name": "Target"}
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json=payload, timeout=5)
    assert r.status_code == 409
    assert "detail" in r.json()