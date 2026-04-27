import time
import uuid
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020, author_name=None, cat_name=None):
    if isbn is None:
        isbn = unique("ISBN")[:13]
    a = create_author(name=author_name or unique("Author"))
    c = create_category(name=cat_name or unique("Cat"))
    b = create_book(a["id"], c["id"], isbn=isbn, stock=stock, price=price, published_year=published_year)
    return a, c, b

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Test bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1990

def test_create_author_without_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_existing_author_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_name_successfully():
    author = create_author()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_author_without_books_returns_204():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_author_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_with_valid_name():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test desc"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["description"] == "Test desc"

def test_create_duplicate_category_returns_409():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_category_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_with_valid_data():
    a = create_author()
    c = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": isbn, "price": 19.99,
        "published_year": 2021, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 19.99
    assert data["stock"] == 5

def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": unique("ISBN")[:13], "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_create_book_with_duplicate_isbn_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": b["isbn"], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_existing_book_returns_200():
    a, c, b = setup_book_with_deps()
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_get_soft_deleted_book_returns_410():
    a, c, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_returns_204():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    a, c, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_restore_non_deleted_book_returns_400():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_to_old_book_returns_200():
    a, c, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0
    assert data["original_price"] == 100.0

def test_apply_discount_to_new_book_returns_400():
    a, c, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_increase_stock_successfully():
    a, c, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    a, c, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_valid_cover_image_returns_200():
    a, c, b = setup_book_with_deps()
    img = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("cover.png", img, "image/png")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["content_type"] == "image/png"
    assert data["book_id"] == b["id"]

def test_upload_unsupported_file_type_returns_415():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("doc.txt", b"hello world", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_upload_file_too_large_returns_413():
    a, c, b = setup_book_with_deps()
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("big.jpg", big_data, "image/jpeg")}, timeout=30)
    assert r.status_code == 413
    data = r.json()
    assert "detail" in data

def test_create_review_for_existing_book_returns_201():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 4, "reviewer_name": unique("Reviewer"), "comment": "Great"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_for_soft_deleted_book_returns_410():
    a, c, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": unique("Reviewer")}, timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_create_tag_with_valid_name_returns_201():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_tag_returns_409():
    name = unique("Tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data