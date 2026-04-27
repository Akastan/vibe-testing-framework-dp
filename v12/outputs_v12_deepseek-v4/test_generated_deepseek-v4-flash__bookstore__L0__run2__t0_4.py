# The main error is likely due to ISBN length exceeding the allowed limit (13 characters). The unique function generates prefix + 8 hex chars, so "isbn_" + 8 chars = 13 characters, but the API might expect exactly 13 characters or less. Also, the unique function generates strings like "isbn_abc12345" which is 13 characters total, but the underscore might not be valid for ISBN format. Fix: generate ISBN without prefix, just 13 hex characters.

import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

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

def create_book(session, title=None, isbn=None, price=10.0, published_year=2020, stock=5, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        # Generate ISBN as exactly 13 hex characters without prefix to avoid length issues
        isbn = uuid.uuid4().hex[:13]
    if author_id is None:
        author = create_author(session)
        author_id = author["id"]
    if category_id is None:
        cat = create_category(session)
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
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
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

def create_tag(session, name=None):
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(session, customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("cust")
    if customer_email is None:
        customer_email = f"{uuid.uuid4().hex[:8]}@example.com"
    if items is None:
        book = create_book(session)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

session = requests.Session()


def test_health_check_success():
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("author")
    bio = "Test bio"
    born_year = 1980
    r = session.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    r = session.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    create_author(session)
    r = session.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_existing():
    author = create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found():
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_author_valid():
    author = create_author(session)
    new_name = unique("updated")
    r = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_author_existing():
    author = create_author(session)
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_valid():
    book = create_book(session)
    assert "id" in book
    assert book["price"] == 10.0

def test_create_book_invalid_price_negative():
    author = create_author(session)
    cat = create_category(session)
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": -5.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_with_search():
    title = unique("searchbook")
    create_book(session, title=title)
    r = session.get(f"{BASE_URL}/books", params={"search": title[:10]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] >= 1

def test_list_books_invalid_page_zero():
    r = session.get(f"{BASE_URL}/books", params={"page": 0}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_existing():
    book = create_book(session)
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_book_soft_deleted():
    book = create_book(session)
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_update_book_valid():
    book = create_book(session)
    new_title = unique("updated")
    r = session.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == new_title

def test_delete_book_existing():
    book = create_book(session)
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    book = create_book(session)
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_valid():
    book = create_book(session)
    payload = {"rating": 4, "reviewer_name": unique("reviewer")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_rating_out_of_range():
    book = create_book(session)
    payload = {"rating": 6, "reviewer_name": unique("reviewer")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_valid():
    book = create_book(session, price=100.0)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 90.0

def test_apply_discount_exceeds_max():
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_valid():
    book = create_book(session, stock=10)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 5

def test_upload_cover_valid_jpeg():
    book = create_book(session)
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_format():
    book = create_book(session)
    files = {"file": ("test.gif", b"fake_gif_data", "image/gif")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_create_category_valid():
    name = unique("cat")
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name

def test_create_tag_valid():
    name = unique("tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name

def test_create_order_valid():
    order = create_order(session)
    assert "id" in order
    assert order["status"] == "pending"

def test_create_order_empty_items():
    r = session.post(f"{BASE_URL}/orders", json={"customer_name": unique("cust"), "customer_email": "a@b.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_order_existing():
    order = create_order(session)
    r = session.get(f"{BASE_URL}/orders/{order['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == order["id"]

def test_update_order_status_valid():
    order = create_order(session)
    r = session.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "shipped"