# Main errors: 1) Missing API key in some helpers (categories, tags, books, orders) 2) ISBN length might exceed 10 chars due to unique() prefix
# Fix: Add AUTH header to all helpers that need it, truncate ISBN to exactly 10 chars

import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=1980):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year,
    }, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("Book")
    isbn = isbn or unique("ISBN")[:10]  # Ensure exactly 10 chars
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_with_valid_data():
    data = create_author(name=unique("George"))
    assert data["name"].startswith("George_")
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_required_field():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_with_pagination():
    create_author(name=unique("PageAuthor1"))
    create_author(name=unique("PageAuthor2"))
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_get_author_by_id():
    author = create_author(name=unique("GetAuthor"))
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_with_etag_not_modified():
    author = create_author(name=unique("ETagAuthor"))
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_update_author_with_valid_data():
    author = create_author(name=unique("OldName"))
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("NewName")}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"].startswith("NewName_")

def test_update_author_with_etag_mismatch():
    author = create_author(name=unique("ETagAuthor"))
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    old_etag = r1.headers["ETag"]
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("ChangedName")}, timeout=30)
    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("StaleUpdate")}, headers={"If-Match": old_etag}, timeout=30)
    assert r2.status_code == 412
    assert "detail" in r2.json()

def test_delete_author_without_books():
    author = create_author(name=unique("DeleteAuthor"))
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_author_with_books():
    author = create_author(name=unique("AuthorWithBooks"))
    category = create_category(name=unique("Category"))
    create_book(author["id"], category["id"], title=unique("Book"))
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_with_valid_data():
    data = create_category(name=unique("Fiction"))
    assert data["name"].startswith("Fiction_")
    assert "id" in data

def test_create_duplicate_category():
    name = unique("DuplicateCategory")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_with_valid_data():
    author = create_author(name=unique("BookAuthor"))
    category = create_category(name=unique("BookCategory"))
    book = create_book(author["id"], category["id"], title=unique("ValidBook"))
    assert book["title"].startswith("ValidBook_")
    assert "id" in book
    assert book["author_id"] == author["id"]
    assert book["category_id"] == category["id"]

def test_create_book_with_duplicate_isbn():
    author = create_author(name=unique("DupAuthor"))
    category = create_category(name=unique("DupCategory"))
    isbn = unique("ISBN")[:10]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("DupBook"), "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": author["id"], "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_with_invalid_author():
    category = create_category(name=unique("InvalidAuthorCategory"))
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("InvalidAuthorBook"), "isbn": unique("ISBN")[:10], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": 999999, "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_with_filters():
    author1 = create_author(name=unique("FilterAuthor1"))
    author2 = create_author(name=unique("FilterAuthor2"))
    category1 = create_category(name=unique("FilterCategory1"))
    category2 = create_category(name=unique("FilterCategory2"))
    create_book(author1["id"], category1["id"], title=unique("Book1"), price=10)
    create_book(author1["id"], category2["id"], title=unique("Book2"), price=20)
    create_book(author2["id"], category1["id"], title=unique("Book3"), price=30)

    r = requests.get(f"{BASE_URL}/books", params={"author_id": author1["id"]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2

    r = requests.get(f"{BASE_URL}/books", params={"category_id": category1["id"]}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2

    r = requests.get(f"{BASE_URL}/books", params={"min_price": 15, "max_price": 25}, timeout=30)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

def test_list_books_excludes_soft_deleted():
    author = create_author(name=unique("SoftDeleteAuthor"))
    category = create_category(name=unique("SoftDeleteCategory"))
    book = create_book(author["id"], category["id"], title=unique("SoftDeleteBook"))
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books", timeout=30)
    assert r.status_code == 200
    assert all(item["id"] != book["id"] for item in r.json()["items"])

def test_get_book_by_id():
    author = create_author(name=unique("GetBookAuthor"))
    category = create_category(name=unique("GetBookCategory"))
    book = create_book(author["id"], category["id"], title=unique("GetBook"))
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_get_soft_deleted_book():
    author = create_author(name=unique("DeletedBookAuthor"))
    category = create_category(name=unique("DeletedBookCategory"))
    book = create_book(author["id"], category["id"], title=unique("DeletedBook"))
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_with_valid_data():
    author = create_author(name=unique("UpdateBookAuthor"))
    category = create_category(name=unique("UpdateBookCategory"))
    book = create_book(author["id"], category["id"], title=unique("UpdateBook"))
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("UpdatedBook")}, timeout=30)
    assert r.status_code == 200
    assert r.json()["title"].startswith("UpdatedBook_")

def test_soft_delete_book():
    author = create_author(name=unique("SoftDeleteAuthor"))
    category = create_category(name=unique("SoftDeleteCategory"))
    book = create_book(author["id"], category["id"], title=unique("SoftDeleteBook"))
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    author = create_author(name=unique("RestoreAuthor"))
    category = create_category(name=unique("RestoreCategory"))
    book = create_book(author["id"], category["id"], title=unique("RestoreBook"))
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert r.json()["is_deleted"] is False

def test_restore_non_deleted_book():
    author = create_author(name=unique("NonDeletedAuthor"))
    category = create_category(name=unique("NonDeletedCategory"))
    book = create_book(author["id"], category["id"], title=unique("NonDeletedBook"))
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_to_old_book():
    author = create_author(name=unique("DiscountAuthor"))
    category = create_category(name=unique("DiscountCategory"))
    book = create_book(author["id"], category["id"], title=unique("DiscountBook"), price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 75.0

def test_apply_discount_to_new_book():
    author = create_author(name=unique("NewBookAuthor"))
    category = create_category(name=unique("NewBookCategory"))
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], title=unique("NewBook"), price=50, published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_rate_limit_exceeded():
    author = create_author(name=unique("RateLimitAuthor"))
    category = create_category(name=unique("RateLimitCategory"))
    book = create_book(author["id"], category["id"], title=unique("RateLimitBook"), price=100, published_year=2020)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
        assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers

def test_update_stock_with_valid_quantity():
    author = create_author(name=unique("StockAuthor"))
    category = create_category(name=unique("StockCategory"))
    book = create_book(author["id"], category["id"], title=unique("StockBook"), stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_below_zero():
    author = create_author(name=unique("NegativeStockAuthor"))
    category = create_category(name=unique("NegativeStockCategory"))
    book = create_book(author["id"], category["id"], title=unique("NegativeStockBook"), stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_for_book():
    author = create_author(name=unique("ReviewAuthor"))
    category = create_category(name=unique("ReviewCategory"))
    book = create_book(author["id"], category["id"], title=unique("ReviewBook"))
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": unique("Reviewer")
    }, timeout=30)
    assert r.status_code == 201
    assert "id" in r.json()
    assert r.json()["book_id"] == book["id"]