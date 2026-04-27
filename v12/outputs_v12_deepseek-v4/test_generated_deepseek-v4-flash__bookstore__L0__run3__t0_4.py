# The main error is likely due to ISBN length validation - the unique function generates strings that may exceed the ISBN field length limit (typically 13 characters). The unique function creates strings like "isbn_abc12345" which is longer than 13 chars. Fix by truncating ISBN to exactly 13 characters.
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

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
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session, name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, title=None, isbn=None, price=10.0, published_year=2020, stock=5, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        # Generate a valid ISBN-like string of exactly 13 characters (digits only)
        isbn = uuid.uuid4().hex[:13]
    if author_id is None:
        author = create_author(session)
        author_id = author["id"]
    if category_id is None:
        category = create_category(session)
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
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_valid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("author"), "bio": "bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"].startswith("author_")

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_found():
    author = create_author(requests.Session())
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_by_id_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_valid_data():
    author = create_author(requests.Session())
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("updated")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"].startswith("updated_")

def test_delete_author_existing():
    author = create_author(requests.Session())
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_list_author_books_valid():
    author = create_author(requests.Session())
    book = create_book(requests.Session(), author_id=author["id"])
    r = requests.get(f"{BASE_URL}/authors/{author['id']}/books", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_create_category_valid():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_get_category_by_id_found():
    cat = create_category(requests.Session())
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cat["id"]

def test_delete_category_existing():
    cat = create_category(requests.Session())
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 204

def test_create_book_valid():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 15.0,
        "published_year": 2021,
        "author_id": create_author(requests.Session())["id"],
        "category_id": create_category(requests.Session())["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_create_book_invalid_price_negative():
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": -5.0,
        "published_year": 2021,
        "author_id": create_author(requests.Session())["id"],
        "category_id": create_category(requests.Session())["id"]
    }, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_books_with_search_and_filters():
    author = create_author(requests.Session())
    cat = create_category(requests.Session())
    create_book(requests.Session(), author_id=author["id"], category_id=cat["id"])
    r = requests.get(f"{BASE_URL}/books?search=&author_id={author['id']}&category_id={cat['id']}&min_price=0&max_price=100", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data

def test_get_book_by_id_active():
    book = create_book(requests.Session())
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_book_by_id_soft_deleted():
    book = create_book(requests.Session())
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_update_book_valid():
    book = create_book(requests.Session())
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("updated")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["title"].startswith("updated_")

def test_delete_book_soft():
    book = create_book(requests.Session())
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    book = create_book(requests.Session())
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_valid():
    book = create_book(requests.Session())
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_list_reviews_for_book():
    book = create_book(requests.Session())
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": unique("rev")}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_book_rating():
    book = create_book(requests.Session())
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 3, "reviewer_name": unique("rev")}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200

def test_apply_discount_valid():
    book = create_book(requests.Session())
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data

def test_apply_discount_rate_limit_exceeded():
    book = create_book(requests.Session())
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 5}, timeout=30)
    assert r.status_code == 429
    data = r.json()
    assert "detail" in data

def test_update_stock_valid():
    session = requests.Session()
    book = create_book(session)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=10", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 10

def test_upload_cover_valid_jpeg():
    book = create_book(requests.Session())
    files = {"file": ("test.jpg", b"fakejpegdata", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type():
    book = create_book(requests.Session())
    files = {"file": ("test.gif", b"fakegifdata", "image/gif")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_get_cover_no_cover():
    book = create_book(requests.Session())
    r = requests.get(f"{BASE_URL}/books/{book['id']}/cover", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data