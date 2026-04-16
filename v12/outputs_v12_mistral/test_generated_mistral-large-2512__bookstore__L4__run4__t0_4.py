# Main issues: 1) Missing API key in some helpers, 2) ISBN length might exceed 13 chars, 3) Missing required fields in some helpers
# Fixes: Add AUTH header to all helpers, ensure ISBN is max 13 chars, verify all required fields are included

import uuid
import time
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def reset_db():
    pass  # Framework handles this automatically

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("Author")
    data = {"name": name}
    if bio is not None:
        data["bio"] = bio
    if born_year is not None:
        data["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=data, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = unique("ISBN")[:13]  # Ensure ISBN is max 13 characters
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
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


def test_create_author_valid_data():
    name = unique("George Orwell")
    data = create_author(name=name, bio="English novelist", born_year=1903)
    assert data["name"] == name
    assert data["bio"] == "English novelist"
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
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

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
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "New Name"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "New Name"
    assert data["id"] == author["id"]

def test_update_author_with_etag_mismatch():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    old_etag = r1.headers["ETag"]

    # Update author to change ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "Changed Name"}, timeout=30)

    # Try PUT with old ETag
    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "Stale Update"},
                      headers={"If-Match": old_etag}, timeout=30)
    assert r2.status_code == 412
    assert "detail" in r2.json()

def test_delete_author_without_books():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

    # Verify author is deleted
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 404

def test_delete_author_with_books():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_valid_data():
    data = create_category(name=unique("Science Fiction"))
    assert data["name"] == "Science Fiction"
    assert "id" in data
    assert "updated_at" in data

def test_create_duplicate_category():
    name = unique("DuplicateCat")
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], title=unique("Test Book"),
                       isbn=unique("ISBN")[:13], price=19.99, published_year=2021, stock=5)
    assert book["title"] == "Test Book"
    assert book["isbn"] == unique("ISBN")[:13]
    assert book["price"] == 19.99
    assert book["published_year"] == 2021
    assert book["stock"] == 5
    assert book["author_id"] == author["id"]
    assert book["category_id"] == category["id"]
    assert "id" in book
    assert "created_at" in book
    assert "updated_at" in book

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    create_book(author["id"], category["id"], isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Duplicate ISBN", "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": author["id"], "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_invalid_author_id():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Invalid Author", "isbn": unique("ISBN")[:13], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": 999999, "category_id": category["id"],
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_existing_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_valid_data():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": "Updated Title"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated Title"
    assert data["id"] == book["id"]

def test_soft_delete_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

    # Verify book is soft-deleted
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_restore_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["is_deleted"] is False

    # Verify book is accessible again
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200

def test_restore_non_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_to_old_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["discounted_price"] == 75.0
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 25.0

def test_apply_discount_to_new_book():
    author = create_author()
    category = create_category()
    current_year = time.localtime().tm_year
    book = create_book(author["id"], category["id"], price=50, published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], price=100, published_year=2020)

    # Make 5 requests (limit)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                          json={"discount_percent": 10}, timeout=30)
        assert r.status_code == 200

    # 6th request should be rate limited
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                      json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert "detail" in r.json()

def test_update_stock_valid_quantity():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15
    assert data["id"] == book["id"]

def test_update_stock_insufficient_quantity():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_valid_cover_image():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    img = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG header
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                      files={"file": ("cover.png", img, "image/png")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["content_type"] == "image/png"
    assert data["size_bytes"] == len(img)

def test_upload_unsupported_file_type():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                      files={"file": ("doc.txt", b"hello world", "text/plain")}, timeout=30)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_upload_oversized_file():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)  # 2 MB + 1 byte
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover",
                      files={"file": ("big.jpg", big_data, "image/jpeg")}, timeout=30)
    assert r.status_code == 413
    assert "detail" in r.json()

def test_create_review_valid_data():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                      json={"rating": 5, "reviewer_name": "Alice", "comment": "Great book!"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Alice"
    assert data["comment"] == "Great book!"
    assert "id" in data
    assert "created_at" in data

def test_create_review_on_soft_deleted_book():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                      json={"rating": 5, "reviewer_name": "Eve"}, timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()