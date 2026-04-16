# The main issues are:
# 1. Missing API key in create_category and create_book helpers (required by some endpoints)
# 2. Potential string length issues with unique() function for ISBN (13 chars max)
# 3. Missing /categories endpoint in the API spec (should be /categories not /categories/)

import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

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
    isbn = isbn or f"ISBN{uuid.uuid4().hex[:10]}"[:13]  # Ensure max 13 chars
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_create_author_valid_data():
    data = create_author(name=unique("George Orwell"), born_year=1903)
    assert data["name"] == f"George Orwell_{data['name'].split('_')[-1]}"
    assert data["born_year"] == 1903
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_required_field():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "name"] for error in r.json()["detail"])

def test_get_existing_author():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]
    assert r.json()["name"] == author["name"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_with_etag_not_modified():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    etag = r.headers.get("ETag")
    assert etag is not None

    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_update_author_with_valid_data():
    author = create_author(name=unique("Old Name"))
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("New Name")}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"].startswith("New Name_")
    assert r.json()["id"] == author["id"]

def test_update_author_with_stale_etag():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    old_etag = r1.headers["ETag"]

    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("Updated Name")}, timeout=30)

    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("Stale Update")},
                      headers={"If-Match": old_etag}, timeout=30)
    assert r2.status_code == 412
    assert "Precondition Failed" in r2.json()["detail"]

def test_delete_author_without_books():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_author_with_books():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "Cannot delete author with" in r.json()["detail"]

def test_create_category_valid_data():
    data = create_category(name=unique("Science Fiction"))
    assert data["name"].startswith("Science Fiction_")
    assert "id" in data
    assert "updated_at" in data

def test_create_duplicate_category():
    name = unique("Unique Cat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], title=unique("Test Book"),
                       isbn=unique("ISBN")[:13], price=19.99, published_year=2021, stock=5)
    assert book["title"].startswith("Test Book_")
    assert book["price"] == 19.99
    assert book["stock"] == 5
    assert "id" in book
    assert "created_at" in book

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Dup"), "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": author["id"], "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]

def test_create_book_invalid_price():
    author = create_author()
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Cheap"), "isbn": unique("ISBN")[:13], "price": -5,
        "published_year": 2020, "author_id": author["id"], "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "price"] for error in r.json()["detail"])

def test_get_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert r.json()["title"] == book["title"]

def test_get_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "has been deleted" in r.json()["detail"]

def test_soft_delete_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_already_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "Gone" in r.json()["detail"]

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert r.json()["is_deleted"] is False

def test_restore_non_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "is not deleted" in r.json()["detail"]

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 75.0
    assert r.json()["book_id"] == book["id"]

def test_apply_discount_to_new_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "more than 1 year ago" in r.json()["detail"]

def test_discount_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=100, published_year=2020)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                          json={"discount_percent": 10}, timeout=30)
        assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers

def test_increase_book_stock():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_decrease_stock_below_zero():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "Insufficient stock" in r.json()["detail"]

def test_upload_valid_cover_image():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    img = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files={"file": ("cover.png", img, "image/png")},
        timeout=30
    )
    assert r.status_code == 200
    assert r.json()["content_type"] == "image/png"
    assert r.json()["book_id"] == book["id"]

def test_upload_unsupported_file_type():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        timeout=30
    )
    assert r.status_code == 415
    assert "Unsupported file type" in r.json()["detail"]

def test_upload_file_too_large():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(
        f"{BASE_URL}/books/{book['id']}/cover",
        files={"file": ("big.jpg", big_data, "image/jpeg")},
        timeout=30
    )
    assert r.status_code == 413
    assert "File too large" in r.json()["detail"]

def test_create_review_for_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                      json={"rating": 5, "reviewer_name": unique("Alice")}, timeout=30)
    assert r.status_code == 201
    assert r.json()["book_id"] == book["id"]
    assert r.json()["rating"] == 5
    assert "id" in r.json()

def test_create_review_for_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                      json={"rating": 5, "reviewer_name": unique("Eve")}, timeout=30)
    assert r.status_code == 410
    assert "has been deleted" in r.json()["detail"]