import uuid
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        cat = create_category()
        category_id = cat["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Test bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert "name" in data

def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_with_etag_success():
    author = create_author()
    get_resp = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = get_resp.headers.get("etag", "").strip('"')
    new_name = unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_author_without_books_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test category"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_category_by_id_success():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cat["id"]

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    cat = create_category()
    isbn = uuid.uuid4().hex[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2020,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    cat = create_category()
    create_book(author_id=author["id"], category_id=cat["id"], price=5.0)
    create_book(author_id=author["id"], category_id=cat["id"], price=15.0)
    r = requests.get(f"{BASE_URL}/books?min_price=10&max_price=20", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_by_id_success():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_update_book_with_etag_success():
    book = create_book()
    get_resp = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    etag = get_resp.headers.get("etag", "").strip('"')
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"price": 25.0}, headers={"If-Match": etag}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["price"] == 25.0

def test_soft_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_success():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "title" in data

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_get_book_rating_with_reviews():
    book = create_book()
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("rev"),
        "comment": "Excellent"
    }, timeout=30)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 3,
        "reviewer_name": unique("rev2"),
        "comment": "Okay"
    }, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert "review_count" in data
    assert data["review_count"] == 2

def test_apply_discount_to_old_book_success():
    book = create_book(published_year=2010, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_to_new_book_returns_400():
    current_year = datetime.now().year
    book = create_book(published_year=current_year, price=50.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_positive_delta_success():
    book = create_book(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_image_success():
    book = create_book()
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert data["content_type"] == "image/jpeg"

def test_upload_cover_unsupported_type_returns_415():
    book = create_book()
    files = {"file": ("test.txt", b"plain text", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_order_success():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert "total_price" in data

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data