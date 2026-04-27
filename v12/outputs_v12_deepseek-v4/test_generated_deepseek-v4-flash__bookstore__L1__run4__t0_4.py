import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(session, name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session, name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, author_id, category_id, title=None, isbn=None, price=10.0, published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_200():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid_data():
    session = requests.Session()
    data = create_author(session, name=unique("author"), bio="Test bio", born_year=1980)
    assert "id" in data
    assert data["name"].startswith("author_")

def test_create_author_missing_name():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id():
    session = requests.Session()
    author = create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == author["id"]

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_with_if_match():
    session = requests.Session()
    author = create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r.headers.get("ETag")
    assert etag is not None
    new_name = unique("updated")
    r = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_update_author_etag_mismatch():
    session = requests.Session()
    author = create_author(session)
    r = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("x")}, headers={"If-Match": '"wrong-etag"'}, timeout=TIMEOUT)
    assert r.status_code == 412
    assert "detail" in r.json()

def test_delete_author_without_books():
    session = requests.Session()
    author = create_author(session)
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_author_with_books_conflict():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    create_book(session, author["id"], cat["id"])
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_valid():
    session = requests.Session()
    data = create_category(session, name=unique("cat"), description="Test category")
    assert "id" in data
    assert data["name"].startswith("cat_")

def test_create_category_duplicate_name():
    session = requests.Session()
    name = unique("dupcat")
    create_category(session, name=name)
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_get_category_by_id():
    session = requests.Session()
    cat = create_category(session)
    r = session.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == cat["id"]

def test_create_book_valid():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    data = create_book(session, author["id"], cat["id"])
    assert "id" in data
    assert data["title"].startswith("book_")

def test_create_book_duplicate_isbn():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    isbn = uuid.uuid4().hex[:13]
    create_book(session, author["id"], cat["id"], isbn=isbn)
    r = session.post(f"{BASE_URL}/books", json={"title": unique("b"), "isbn": isbn, "price": 10, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_nonexistent_author():
    session = requests.Session()
    cat = create_category(session)
    r = session.post(f"{BASE_URL}/books", json={"title": unique("b"), "isbn": uuid.uuid4().hex[:13], "price": 10, "published_year": 2020, "author_id": 999999, "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_book_by_id():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_soft_delete_book():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_not_deleted_book():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_old_book():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], published_year=2020, price=100.0)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 20.0

def test_apply_discount_new_book():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], published_year=2026, price=50.0)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_exceeds_rate_limit():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], published_year=2020, price=50.0)
    statuses = []
    for _ in range(6):
        r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
        statuses.append(r.status_code)
    assert 429 in statuses

def test_update_stock_positive_delta():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], stock=5)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_insufficient():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], stock=2)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_cover_valid_jpeg():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    files = {"file": ("test.txt", b"fake_text", "text/plain")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_review_valid():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"])
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_create_tag_valid():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"].startswith("tag_")

def test_create_order_valid():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    book = create_book(session, author["id"], cat["id"], stock=5)
    r = session.post(f"{BASE_URL}/orders", json={"customer_name": unique("cust"), "customer_email": "test@test.com", "items": [{"book_id": book["id"], "quantity": 2}]}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2