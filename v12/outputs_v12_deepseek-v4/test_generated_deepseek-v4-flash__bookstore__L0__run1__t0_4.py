import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
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

def create_book(session, title=None, isbn=None, price=10.0, published_year=2020, stock=5, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = str(uuid.uuid4().int)[:13]
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
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
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
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_success():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    session = requests.Session()
    name = unique("author")
    bio = "Some bio"
    born_year = 1980
    r = session.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == bio
    assert data["born_year"] == born_year

def test_create_author_missing_name():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    session = requests.Session()
    create_author(session)
    r = session.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_update_author_etag_mismatch():
    session = requests.Session()
    author = create_author(session)
    author_id = author["id"]
    wrong_etag = '"wrong-etag"'
    r = session.put(f"{BASE_URL}/authors/{author_id}", json={"name": "Updated"}, headers={"If-Match": wrong_etag}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_delete_author_success():
    session = requests.Session()
    author = create_author(session)
    author_id = author["id"]
    r = session.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_category_valid():
    session = requests.Session()
    name = unique("cat")
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_get_category_not_modified():
    session = requests.Session()
    category = create_category(session)
    category_id = category["id"]
    r1 = session.get(f"{BASE_URL}/categories/{category_id}", timeout=TIMEOUT)
    etag = r1.headers.get("ETag")
    r2 = session.get(f"{BASE_URL}/categories/{category_id}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 304

def test_create_book_valid():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    title = unique("book")
    isbn = str(uuid.uuid4().int)[:13]
    r = session.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_negative_price():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    r = session.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": -5.0,
        "published_year": 2021,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_books_filter_by_author():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    create_book(session, author_id=author["id"], category_id=category["id"])
    r = session.get(f"{BASE_URL}/books", params={"author_id": author["id"]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_list_books_price_range():
    session = requests.Session()
    create_book(session, price=5.0)
    create_book(session, price=15.0)
    r = session.get(f"{BASE_URL}/books", params={"min_price": 10.0, "max_price": 20.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data

def test_get_soft_deleted_book():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    session.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    r = session.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_update_book_etag_mismatch():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    wrong_etag = '"wrong-etag"'
    r = session.put(f"{BASE_URL}/books/{book_id}", json={"title": "Updated"}, headers={"If-Match": wrong_etag}, timeout=TIMEOUT)
    assert r.status_code == 412

def test_delete_book_already_deleted():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    session.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    r = session.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert r.status_code == 410

def test_restore_not_deleted_book():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    r = session.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_valid():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    reviewer = unique("rev")
    r = session.post(f"{BASE_URL}/books/{book_id}/reviews", json={"rating": 5, "reviewer_name": reviewer}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["reviewer_name"] == reviewer

def test_get_rating_no_reviews():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    r = session.get(f"{BASE_URL}/books/{book_id}/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_rate_limit():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    for _ in range(6):
        r = session.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 429

def test_update_stock_negative_quantity():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    r = session.patch(f"{BASE_URL}/books/{book_id}/stock", json={"quantity": -5}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_upload_cover_unsupported_type():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    files = {"file": ("test.txt", b"fake image content", "text/plain")}
    r = session.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415

def test_get_cover_not_found():
    session = requests.Session()
    book = create_book(session)
    book_id = book["id"]
    r = session.get(f"{BASE_URL}/books/{book_id}/cover", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_tag_name_too_long():
    session = requests.Session()
    long_name = "a" * 31
    r = session.post(f"{BASE_URL}/tags", json={"name": long_name}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_add_tags_to_book_valid():
    session = requests.Session()
    book = create_book(session)
    tag = create_tag(session)
    book_id = book["id"]
    r = session.post(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert any(t["id"] == tag["id"] for t in data["tags"])

def test_create_order_valid():
    session = requests.Session()
    book = create_book(session)
    customer_name = unique("cust")
    customer_email = f"{uuid.uuid4().hex[:8]}@example.com"
    r = session.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["customer_name"] == customer_name

def test_create_order_empty_items():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/orders", json={
        "customer_name": "test",
        "customer_email": "test@example.com",
        "items": []
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_update_order_status_invalid():
    session = requests.Session()
    order = create_order(session)
    order_id = order["id"]
    r = session.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "invalid_status"}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_add_item_to_order_valid():
    session = requests.Session()
    order = create_order(session)
    order_id = order["id"]
    book = create_book(session)
    r = session.post(f"{BASE_URL}/orders/{order_id}/items", json={"book_id": book["id"], "quantity": 1}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_bulk_create_missing_api_key():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    r = session.post(f"{BASE_URL}/books/bulk", json={
        "books": [{
            "title": unique("bulk"),
            "isbn": str(uuid.uuid4().int)[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        }]
    }, timeout=TIMEOUT)
    assert r.status_code == 401