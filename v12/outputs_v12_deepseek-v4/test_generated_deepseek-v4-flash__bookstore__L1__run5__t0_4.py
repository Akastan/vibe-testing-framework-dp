import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
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
        name = unique("tag")[:30]
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("cust")
    if customer_email is None:
        customer_email = f"{uuid.uuid4().hex[:8]}@test.com"
    if items is None:
        book = create_book()
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("author")
    bio = "Test bio"
    born_year = 1980
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "test"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_with_if_match_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = r.headers.get("ETag")
    new_name = unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_update_author_if_match_mismatch():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("x")}, headers={"If-Match": '"wrong-etag"'}, timeout=30)
    assert r.status_code == 412
    assert "detail" in r.json()

def test_delete_author_with_books_conflict():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_success():
    name = unique("category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_category_duplicate_name():
    name = unique("catdup")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_category_with_books_conflict():
    category = create_category()
    create_book(category_id=category["id"])
    r = requests.delete(f"{BASE_URL}/categories/{category['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_nonexistent_author():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    create_book(author_id=author["id"], category_id=category["id"], price=20.0)
    r = requests.get(f"{BASE_URL}/books?author_id={author['id']}&category_id={category['id']}&min_price=10&max_price=30", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

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
    assert "id" in data

def test_restore_not_deleted_book_returns_400():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_apply_discount_old_book_success():
    book = create_book(published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discount_percent"] == 10

def test_apply_discount_new_book_returns_400():
    book = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_positive_delta():
    book = create_book(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_cover_valid_jpeg():
    book = create_book()
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type():
    book = create_book()
    files = {"file": ("test.txt", b"fake_text", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_tag_success():
    name = unique("tag")[:30]
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_success():
    book = create_book()
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag["id"] in tag_ids

def test_create_order_success():
    book = create_book(stock=10)
    customer_name = unique("cust")
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": f"{uuid.uuid4().hex[:8]}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["customer_name"] == customer_name
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r2.json()["stock"] == 8

def test_create_order_insufficient_stock():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": f"{uuid.uuid4().hex[:8]}@test.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()