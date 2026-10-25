# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run1__t0_4.py
# IDENTIFIER: L0_run1
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run2__t0_4.py
# IDENTIFIER: L0_run2
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run3__t0_4.py
# IDENTIFIER: L0_run3
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run4__t0_4.py
# IDENTIFIER: L0_run4
# ===========================================================================

# The main error is likely that the unique function generates strings that exceed field length limits (e.g., ISBN must be exactly 13 digits, but unique returns a string with prefix and underscore). Fix: ensure ISBN is exactly 13 numeric characters without prefix, and ensure other fields respect length constraints.
import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session: requests.Session, name: str = None, bio: str = None, born_year: int = None) -> dict:
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session: requests.Session, name: str = None, description: str = None) -> dict:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session: requests.Session, title: str = None, isbn: str = None, price: float = 10.0, published_year: int = 2000, stock: int = 5, author_id: int = None, category_id: int = None) -> dict:
    if title is None:
        title = unique("Book")
    if isbn is None:
        # ISBN must be exactly 13 numeric digits
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

def create_tag(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("Tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    session = requests.Session()
    name = unique("Author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    session = requests.Session()
    create_author(session)
    r = session.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    session = requests.Session()
    author = create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/9999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_success():
    session = requests.Session()
    author = create_author(session)
    new_name = unique("Updated")
    r = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_author_success():
    session = requests.Session()
    author = create_author(session)
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_category_success():
    session = requests.Session()
    name = unique("Category")
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_get_category_by_id_success():
    session = requests.Session()
    category = create_category(session)
    r = session.get(f"{BASE_URL}/categories/{category['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == category["id"]

def test_update_category_success():
    session = requests.Session()
    category = create_category(session)
    new_name = unique("UpdatedCat")
    r = session.put(f"{BASE_URL}/categories/{category['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_category_success():
    session = requests.Session()
    category = create_category(session)
    r = session.delete(f"{BASE_URL}/categories/{category['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    title = unique("Book")
    isbn = str(uuid.uuid4().int)[:13]
    r = session.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_invalid_price():
    session = requests.Session()
    author = create_author(session)
    category = create_category(session)
    r = session.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": str(uuid.uuid4().int)[:13],
        "price": -5.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_books_with_search_filter():
    session = requests.Session()
    create_book(session)
    r = session.get(f"{BASE_URL}/books?search=Book", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_list_books_invalid_page():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_book_by_id_success():
    session = requests.Session()
    book = create_book(session)
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    session = requests.Session()
    book = create_book(session)
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_success():
    session = requests.Session()
    book = create_book(session)
    new_title = unique("UpdatedBook")
    r = session.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == new_title

def test_delete_book_success():
    session = requests.Session()
    book = create_book(session)
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    session = requests.Session()
    book = create_book(session)
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_success():
    session = requests.Session()
    book = create_book(session)
    reviewer = unique("Reviewer")
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": reviewer
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["reviewer_name"] == reviewer

def test_create_review_invalid_rating():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 6,
        "reviewer_name": unique("Reviewer")
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_success():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == book["price"]

def test_apply_discount_exceeds_max():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60.0}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_success():
    session = requests.Session()
    book = create_book(session)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 20

def test_create_tag_success():
    session = requests.Session()
    name = unique("Tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_get_tag_by_id_success():
    session = requests.Session()
    tag = create_tag(session)
    r = session.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == tag["id"]

def test_delete_tag_success():
    session = requests.Session()
    tag = create_tag(session)
    r = session.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_order_success():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": f"{uuid.uuid4().hex[:8]}@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run5__t0_4.py
# IDENTIFIER: L0_run5
# ===========================================================================

# The main errors likely stem from ISBN length constraints (unique() generates strings that may exceed max length) and missing X-API-Key header for authenticated endpoints. Also, the unique function for ISBN may produce strings >13 chars.
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix):
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

def create_category(session, name=None, description=None):
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, author_id, category_id, title=None, isbn=None, price=10.0, published_year=2020, stock=5):
    if title is None:
        title = unique("book")
    if isbn is None:
        # Ensure ISBN is exactly 13 characters (ISBN-13 standard) and numeric
        isbn = uuid.uuid4().hex[:13]
        # Make sure it's all digits (uuid hex is 0-9a-f, but ISBN should be digits)
        # Replace any non-digit with '0' to keep length 13
        isbn = ''.join(c if c.isdigit() else '0' for c in isbn)
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
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    s = requests.Session()
    name = unique("author")
    r = s.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_default_pagination():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    s = requests.Session()
    author = create_author(s)
    r = s.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == author["id"]

def test_get_author_not_found():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/authors/9999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_with_etag_match():
    s = requests.Session()
    author = create_author(s)
    get_r = s.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = get_r.headers.get("ETag")
    r = s.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("updated")}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data

def test_delete_author_success():
    s = requests.Session()
    author = create_author(s)
    r = s.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_category_success():
    s = requests.Session()
    name = unique("cat")
    r = s.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_get_category_not_found():
    s = requests.Session()
    r = s.get(f"{BASE_URL}/categories/9999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    title = unique("book")
    isbn = unique("isbn")[:13]
    if len(isbn) < 10:
        isbn = isbn.zfill(10)
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = s.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_invalid_price():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": -5.0,
        "published_year": 2021,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    r = s.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    create_book(s, author["id"], category["id"], price=20.0)
    r = s.get(f"{BASE_URL}/books?min_price=10&max_price=30", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_soft_deleted_book_returns_410():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_update_book_etag_mismatch():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.put(f"{BASE_URL}/books/{book['id']}", json={"title": unique("newtitle")}, headers={"If-Match": '"wrongetag"'}, timeout=TIMEOUT)
    assert r.status_code == 412
    data = r.json()
    assert "detail" in data

def test_delete_book_soft_delete():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_already_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_deleted_book():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = s.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_apply_discount_rate_limit_exceeded():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    responses = []
    for _ in range(6):
        r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
        responses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in responses

def test_update_stock_positive_quantity():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock", json={"quantity": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["stock"] == 20

def test_upload_cover_unsupported_type():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"test", "text/plain")}, timeout=TIMEOUT)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    s = requests.Session()
    name = unique("tag")
    r = s.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    tag = create_tag(s)
    r = s.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data

def test_create_order_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"], stock=10)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    r = s.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert "total_price" in data

def test_update_order_status_valid():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"], stock=10)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": f"{unique('email')}@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    order_r = s.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    order = order_r.json()
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "shipped"

def test_bulk_create_books_missing_api_key():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    payload = {
        "books": [
            {
                "title": unique("bulk"),
                "isbn": unique("isbn")[:13],
                "price": 10.0,
                "published_year": 2020,
                "author_id": author["id"],
                "category_id": category["id"]
            }
        ]
    }
    r = s.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_create_book_export_success():
    s = requests.Session()
    author = create_author(s)
    category = create_category(s)
    book = create_book(s, author["id"], category["id"])
    r = s.post(f"{BASE_URL}/exports/books", json={"book_ids": [book["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data

def test_toggle_maintenance_missing_api_key():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/admin/maintenance", json={"enabled": True}, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L0__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run1__t0_4.py
# IDENTIFIER: L1_run1
# ===========================================================================

# Analysis: The main issue is likely that the unique function generates strings that exceed field length limits (e.g., ISBN max 13 chars, name max lengths). Also, the helpers may need to handle API key headers for authenticated endpoints.
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")[:50]  # Truncate to avoid length issues
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
        name = unique("cat")[:50]  # Truncate to avoid length issues
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")[:100]  # Truncate to avoid length issues
    if isbn is None:
        isbn = unique("isbn")[:13]  # ISBN must be exactly 13 chars or less
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
        name = unique("tag")[:30]  # Truncate to avoid length issues
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    book_isbn = unique("isbn")[:13]
    book_title = unique("book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": book_title,
        "isbn": book_isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code in (200, 201)
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    title = unique("book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 201
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_create_book_nonexistent_author_returns_404():
    category = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 404

def test_get_book_returns_200_with_etag():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "ETag" in r.headers or "etag" in r.headers

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book_returns_204():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_not_deleted_book_returns_400():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400

def test_apply_discount_to_old_book_returns_200():
    book = create_book(published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20.0}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 100.0
    assert data["discount_percent"] == 20.0

def test_apply_discount_to_new_book_returns_400():
    current_year = 2026
    book = create_book(published_year=current_year, price=50.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10.0}, timeout=30)
    assert r.status_code == 400

def test_update_stock_positive_delta_returns_200():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_negative_delta_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400

def test_upload_cover_valid_image_returns_200():
    book = create_book()
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type_returns_415():
    book = create_book()
    files = {"file": ("test.txt", b"text data", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5,
        "reviewer_name": unique("rev"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

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
    assert data["total_price"] == book["price"] * 2

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

def test_update_order_status_valid_transition_returns_200():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    assert r.status_code == 200
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 400

def test_get_invoice_for_confirmed_order_returns_200():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data

def test_get_invoice_for_pending_order_returns_403():
    book = create_book(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    assert r.status_code == 201
    order = r.json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403

def test_bulk_create_books_all_success_returns_201():
    author = create_author()
    category = create_category()
    books_data = []
    for i in range(3):
        books_data.append({
            "title": unique("bulk"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        })
    r = requests.post(f"{BASE_URL}/books/bulk", json={"books": books_data}, headers={"X-API-Key": API_KEY}, timeout=30)
    assert r.status_code == 201

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run2__t0_4.py
# IDENTIFIER: L1_run2
# ===========================================================================

# The main error is likely that the unique function generates strings that exceed field length limits (e.g., ISBN max 13 chars, name max lengths). We need to truncate generated values to fit schema constraints.
import uuid
import requests
import io
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")[:50]  # Truncate to reasonable length
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
        name = unique("cat")[:50]  # Truncate to reasonable length
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(title=None, isbn=None, price=10.0, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")[:100]  # Truncate to reasonable length
    if isbn is None:
        isbn = unique("isbn")[:13]  # ISBN must be exactly 13 chars max
        # Ensure ISBN is exactly 13 characters (remove prefix if too long)
        isbn = isbn[:13].ljust(13, '0')  # Pad with zeros if needed
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
        name = unique("tag")[:30]  # Truncate to reasonable length
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_update_author_with_valid_etag_returns_200():
    author = create_author()
    get_r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = get_r.headers.get("etag")
    new_name = unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_update_author_with_wrong_etag_returns_412():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": '"wrong-etag"'}, timeout=30)
    assert r.status_code == 412

def test_delete_author_without_books_returns_204():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_list_categories_returns_200():
    r = requests.get(f"{BASE_URL}/categories", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={"title": "Test Book", "isbn": isbn, "price": 15.0, "published_year": 2020, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={"title": "Book1", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={"title": "Book2", "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}, timeout=30)
    assert r.status_code == 409

def test_list_books_with_filters_returns_200():
    author = create_author()
    cat = create_category()
    create_book(author_id=author["id"], category_id=cat["id"])
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=10&author_id={author['id']}&min_price=0&max_price=100", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_by_id_returns_200():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_update_book_with_valid_etag_returns_200():
    book = create_book()
    get_r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    etag = get_r.headers.get("etag")
    new_title = unique("title")
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, headers={"If-Match": etag}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == new_title

def test_soft_delete_book_returns_204():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Tester", "comment": "Great"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_get_book_rating_returns_200():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert "review_count" in data

def test_apply_discount_to_old_book_returns_200():
    book = create_book(published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_to_new_book_returns_400():
    current_year = 2026
    book = create_book(published_year=current_year, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400

def test_update_stock_positive_delta_returns_200():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400


def test_list_authors_pagination_returns_correct_slice():
    created_ids = []
    for _ in range(5):
        author = create_author()
        created_ids.append(author["id"])
    r = requests.get(f"{BASE_URL}/authors?skip=2&limit=2", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    returned_ids = [a["id"] for a in data]
    created_ids.sort()
    assert returned_ids == created_ids[2:4]

def test_get_author_with_etag_returns_304():
    author = create_author()
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None
    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304

def test_delete_author_with_books_returns_400():
    author = create_author()
    create_book(author_id=author["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 400
    detail = r.json()
    assert "detail" in detail

def test_create_category_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/categories", json={}, timeout=30)
    assert r.status_code == 422
    detail = r.json()
    assert any("name" in str(err.get("loc", [])) for err in detail.get("detail", []))

def test_create_book_invalid_price_returns_422():
    author = create_author()
    cat = create_category()
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": -5.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 422
    detail = r.json()
    assert any("price" in str(err.get("loc", [])) for err in detail.get("detail", []))

def test_create_tag_duplicate_name_returns_409():
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/tags", json={"name": tag["name"]}, timeout=30)
    assert r.status_code == 409
    detail = r.json()
    assert "detail" in detail

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run3__t0_4.py
# IDENTIFIER: L1_run3
# ===========================================================================

import uuid
import requests

BASE_URL = "http://localhost:8000"

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
        name = unique("cat")
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
        isbn = uuid.uuid4().hex[:13]
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
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_200():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Test bio", "born_year": 1980}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_with_pagination():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_returns_200_and_etag():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert "ETag" in r.headers

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404

def test_update_author_with_valid_if_match_returns_200():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = r.headers.get("ETag")
    new_name = unique("updated")
    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=30)
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == new_name

def test_update_author_with_wrong_etag_returns_412():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "new"}, headers={"If-Match": '"wrong-etag"'}, timeout=30)
    assert r.status_code == 412

def test_delete_author_without_books_returns_204():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("catdup")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = uuid.uuid4().hex[:13]
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

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = uuid.uuid4().hex[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book1"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }, timeout=30)
    assert r.status_code == 409

def test_list_books_with_filters_returns_paginated_result():
    create_book()
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_returns_200_and_etag():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "ETag" in r.headers

def test_get_soft_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410

def test_soft_delete_book_returns_204():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("rev")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_get_rating_with_reviews_returns_average():
    book = create_book()
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": "tester"}, timeout=30)
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "tester2"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert data["review_count"] == 2

def test_apply_discount_to_old_book_returns_200():
    book = create_book(published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data

def test_apply_discount_to_new_book_returns_400():
    book = create_book(published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400

def test_update_stock_positive_delta_returns_200():
    book = create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400

def test_upload_cover_valid_image_returns_200():
    book = create_book()
    files = {"file": ("test.jpg", b"fakejpegdata", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type_returns_415():
    book = create_book()
    files = {"file": ("test.txt", b"plaintext", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_returns_200():
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
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == book["price"] * 2

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run4__t0_4.py
# IDENTIFIER: L1_run4
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run5__t0_4.py
# IDENTIFIER: L1_run5
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L1__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run1__t0_4.py
# IDENTIFIER: L2_run1
# ===========================================================================

import requests
import uuid
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _create_author(session: requests.Session, name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
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

def _create_category(session: requests.Session, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_book(session: requests.Session, author_id: int, category_id: int, title: Optional[str] = None, isbn: Optional[str] = None, price: float = 10.0, published_year: int = 2020, stock: int = 5) -> Dict[str, Any]:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_tag(session: requests.Session, name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    session = requests.Session()
    name = unique("author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    session = requests.Session()
    r = session.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    session = requests.Session()
    _create_author(session)
    r = session.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    session = requests.Session()
    author = _create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_with_etag_success():
    session = requests.Session()
    author = _create_author(session)
    r = session.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r.headers.get("ETag", "")
    new_name = unique("updated")
    r2 = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == new_name

def test_update_author_etag_mismatch():
    session = requests.Session()
    author = _create_author(session)
    r = session.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("x")}, headers={"If-Match": '"wrong-etag"'}, timeout=TIMEOUT)
    assert r.status_code == 412
    assert "detail" in r.json()

def test_delete_author_without_books_success():
    session = requests.Session()
    author = _create_author(session)
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_category_success():
    session = requests.Session()
    name = unique("category")
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_name():
    session = requests.Session()
    name = unique("category")
    session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_get_category_by_id_success():
    session = requests.Session()
    cat = _create_category(session)
    r = session.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cat["id"]

def test_create_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    title = unique("book")
    isbn = unique("isbn")[:13]
    r = session.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 10,
        "author_id": author["id"],
        "category_id": cat["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == title

def test_create_book_duplicate_isbn():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    isbn = unique("isbn")[:13]
    session.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }, timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_nonexistent_author():
    session = requests.Session()
    cat = _create_category(session)
    r = session.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": cat["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_with_filters():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    _create_book(session, author["id"], cat["id"], title="UniqueSearchTitle", price=20.0)
    r = session.get(f"{BASE_URL}/books", params={"search": "UniqueSearchTitle", "min_price": 10.0, "max_price": 30.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_by_id_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "author" in data
    assert "category" in data

def test_get_soft_deleted_book_returns_gone():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_soft_delete_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_soft_deleted_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_create_review_for_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    reviewer = unique("reviewer")
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "comment": "Great book",
        "reviewer_name": reviewer,
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["reviewer_name"] == reviewer

def test_get_book_rating_with_reviews():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": unique("r")}, timeout=TIMEOUT)
    session.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 3, "reviewer_name": unique("r")}, timeout=TIMEOUT)
    r = session.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert data["review_count"] == 2

def test_apply_discount_to_old_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"], price=100.0, published_year=2020)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 80.0

def test_apply_discount_to_new_book_error():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    import datetime
    current_year = datetime.datetime.now().year
    book = _create_book(session, author["id"], cat["id"], price=50.0, published_year=current_year)
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_increase_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"], stock=10)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_result():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"], stock=3)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_cover_image_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["content_type"] == "image/jpeg"

def test_upload_cover_unsupported_type():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    files = {"file": ("test.txt", b"fake_text", "text/plain")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_tag_success():
    session = requests.Session()
    name = unique("tag")
    r = session.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_add_tags_to_book_success():
    session = requests.Session()
    author = _create_author(session)
    cat = _create_category(session)
    book = _create_book(session, author["id"], cat["id"])
    tag1 = _create_tag(session)
    tag2 = _create_tag(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag1["id"], tag2["id"]]}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["tags"]) == 2

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run2__t0_4.py
# IDENTIFIER: L2_run2
# ===========================================================================

# The main error is likely ISBN length validation (unique("isbn")[:13] may produce strings >13 chars or invalid format). Also ensure all helper functions handle 201 status codes correctly and generate proper unique values within length constraints.

import uuid
import requests
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def unique(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name=None):
    if name is None:
        name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, isbn=None, stock=10, published_year=2020):
    if isbn is None:
        # ISBN-13 must be exactly 13 digits; generate a valid numeric ISBN
        isbn = ''.join([str(uuid.uuid4().int)[:13]])
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_author_name_too_long_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "x" * 101}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_with_books_returns_409():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
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
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_nonexistent_author_returns_404():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 9.99,
        "published_year": 2021,
        "stock": 5,
        "author_id": 999999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_book_by_id_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_not_deleted_book_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_rating_out_of_range_returns_422():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 6,
        "reviewer_name": unique("reviewer")
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_apply_discount_to_old_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] == 19.99

def test_apply_discount_to_new_book_returns_400():
    author = create_author()
    cat = create_category()
    current_year = datetime.now(timezone.utc).year
    book = create_book(author["id"], cat["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={
        "discount_percent": 10
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_stock_positive_delta_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_upload_cover_unsupported_type_returns_415():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files={
        "file": ("test.txt", b"fake image content", "text/plain")
    }, timeout=30)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"

def test_create_order_insufficient_stock_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_update_order_status_valid_transition_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={
        "status": "confirmed"
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={
        "status": "cancelled"
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_get_invoice_for_pending_order_returns_403():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order_resp = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_resp.json()
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    assert "detail" in r.json()

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run3__t0_4.py
# IDENTIFIER: L2_run3
# ===========================================================================

import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _create_author(name: str = None, bio: str = "Test bio", born_year: int = 1980) -> dict:
    if name is None:
        name = _unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_category(name: str = None, description: str = "Test category") -> dict:
    if name is None:
        name = _unique("cat")
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_book(
    title: str = None,
    isbn: str = None,
    price: float = 19.99,
    published_year: int = 2020,
    stock: int = 10,
    author_id: int = None,
    category_id: int = None,
) -> dict:
    if title is None:
        title = _unique("book")
    if isbn is None:
        isbn = _unique("isbn")[:13]
    if author_id is None:
        author = _create_author()
        author_id = author["id"]
    if category_id is None:
        category = _create_category()
        category_id = category["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_tag(name: str = None) -> dict:
    if name is None:
        name = _unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def _create_order(
    customer_name: str = None,
    customer_email: str = "test@example.com",
    items: list = None,
) -> dict:
    if customer_name is None:
        customer_name = _unique("cust")
    if items is None:
        book = _create_book(stock=10)
        items = [{"book_id": book["id"], "quantity": 2}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

# ── /authors POST ──

def test_create_author_success():
    name = _unique("author")
    payload = {"name": name, "bio": "Bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Bio"
    assert data["born_year"] == 1990

def test_create_author_missing_name():
    payload = {"bio": "No name"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors GET ──

def test_list_authors_with_pagination():
    _create_author()
    _create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=100", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2

# ── /authors/{author_id} GET ──

def test_get_author_by_id_success():
    author = _create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} PUT ──

def test_update_author_name_success():
    author = _create_author()
    new_name = _unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

# ── /authors/{author_id} DELETE ──

def test_delete_author_without_books():
    author = _create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 204

# ── /categories POST ──

def test_create_category_success():
    name = _unique("cat")
    payload = {"name": name, "description": "Test"}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category():
    name = _unique("cat")
    payload = {"name": name}
    r1 = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r1.status_code == 201
    r2 = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

# ── /categories/{category_id} GET ──

def test_get_category_by_id_success():
    cat = _create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cat["id"]

# ── /categories/{category_id} DELETE ──

def test_delete_category_with_books_conflict():
    cat = _create_category()
    author = _create_author()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ──

def test_create_book_success():
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 15,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 25.50

def test_create_book_duplicate_isbn():
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": _unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r1 = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r1.status_code == 201
    payload2 = {
        "title": _unique("book2"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r2 = requests.post(f"{BASE_URL}/books", json=payload2, timeout=30)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

# ── /books GET ──

def test_list_books_with_search_filter():
    title = _unique("searchable")
    author = _create_author()
    cat = _create_category()
    isbn = _unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    r = requests.get(f"{BASE_URL}/books?search={title[:10]}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] >= 1

# ── /books/{book_id} GET ──

def test_get_book_by_id_success():
    book = _create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_soft_deleted_book_returns_410():
    book = _create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ──

def test_soft_delete_book_success():
    book = _create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

# ── /books/{book_id}/restore ──

def test_restore_soft_deleted_book():
    book = _create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r2.status_code == 200

# ── /books/{book_id}/reviews POST ──

def test_create_review_success():
    book = _create_book()
    payload = {"rating": 4, "reviewer_name": _unique("rev"), "comment": "Great book"}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4
    assert data["reviewer_name"] == payload["reviewer_name"]

# ── /books/{book_id}/rating GET ──

def test_get_book_rating_with_reviews():
    book = _create_book()
    payload1 = {"rating": 5, "reviewer_name": _unique("rev"), "comment": "Excellent"}
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload1, timeout=30)
    payload2 = {"rating": 3, "reviewer_name": _unique("rev"), "comment": "Okay"}
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload2, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "average_rating" in data
    assert data["average_rating"] == 4.0
    assert data["review_count"] == 2

# ── /books/{book_id}/discount POST ──

def test_apply_discount_to_old_book():
    book = _create_book(published_year=2020)
    payload = {"discount_percent": 20}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    expected = round(book["price"] * 0.8, 2)
    assert data["discounted_price"] == expected

def test_apply_discount_to_new_book():
    current_year = 2026
    book = _create_book(published_year=current_year)
    payload = {"discount_percent": 10}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ──

def test_update_stock_positive_delta():
    book = _create_book(stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient():
    book = _create_book(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /tags POST ──

def test_create_tag_success():
    name = _unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

# ── /books/{book_id}/tags POST ──

def test_add_tags_to_book_success():
    book = _create_book()
    tag1 = _create_tag()
    tag2 = _create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

# ── /orders POST ──

def test_create_order_success():
    book = _create_book(stock=10)
    payload = {
        "customer_name": _unique("cust"),
        "customer_email": "customer@test.com",
        "items": [{"book_id": book["id"], "quantity": 3}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_price"] == round(book["price"] * 3, 2)
    r2 = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r2.json()["stock"] == 7

def test_create_order_insufficient_stock():
    book = _create_book(stock=2)
    payload = {
        "customer_name": _unique("cust"),
        "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 10}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ──

def test_update_order_status_valid_transition():
    order = _create_order()
    payload = {"status": "confirmed"}
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run4__t0_4.py
# IDENTIFIER: L2_run4
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run5__t0_4.py
# IDENTIFIER: L2_run5
# ===========================================================================

import uuid
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("author")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session: requests.Session, author_id: int = None, category_id: int = None, isbn: str = None, stock: int = 10, published_year: int = 2020, price: float = 29.99) -> dict:
    if author_id is None:
        author = create_author(session)
        author_id = author["id"]
    if category_id is None:
        cat = create_category(session)
        category_id = cat["id"]
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
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

def create_tag(session: requests.Session, name: str = None) -> dict:
    if name is None:
        name = unique("tag")[:30]
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    session = requests.Session()
    name = unique("author")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    session = requests.Session()
    payload = {}
    r = session.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_author_not_found():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    create_book(session, author_id=author["id"], category_id=cat["id"])
    r = session.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_success():
    session = requests.Session()
    name = unique("cat")
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category():
    session = requests.Session()
    name = unique("cat")
    payload = {"name": name}
    r1 = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r1.status_code == 201
    r2 = session.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

def test_delete_category_with_books_conflict():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    create_book(session, author_id=author["id"], category_id=cat["id"])
    r = session.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r1 = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r1.status_code == 201
    r2 = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r2.status_code == 409
    data = r2.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    session = requests.Session()
    cat = create_category(session)
    isbn = unique("isbn")[:13]
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 5,
        "author_id": 999999,
        "category_id": cat["id"]
    }
    r = session.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_get_book_soft_deleted():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    r_get = session.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_get.status_code == 410
    data = r_get.json()
    assert "detail" in data

def test_soft_delete_book_success():
    session = requests.Session()
    book = create_book(session)
    r = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_book_success():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    r_restore = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r_restore.status_code == 200
    data = r_restore.json()
    assert "id" in data
    assert data["id"] == book["id"]

def test_restore_not_deleted_book():
    session = requests.Session()
    book = create_book(session)
    r = session.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    session = requests.Session()
    book = create_book(session)
    payload = {
        "rating": 5,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book!"
    }
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_create_review_soft_deleted_book():
    session = requests.Session()
    book = create_book(session)
    r_del = session.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 204
    payload = {
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Nice"
    }
    r = session.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_apply_discount_success():
    session = requests.Session()
    book = create_book(session, published_year=2020, price=100.0)
    payload = {"discount_percent": 20}
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_new_book():
    session = requests.Session()
    from datetime import datetime
    current_year = datetime.now().year
    book = create_book(session, published_year=current_year, price=50.0)
    payload = {"discount_percent": 10}
    r = session.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_insufficient():
    session = requests.Session()
    book = create_book(session, stock=5)
    r = session.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_unsupported_type():
    session = requests.Session()
    book = create_book(session)
    files = {"file": ("test.txt", b"fake image content", "text/plain")}
    r = session.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    session = requests.Session()
    name = unique("tag")[:30]
    payload = {"name": name}
    r = session.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_delete_tag_with_books_conflict():
    session = requests.Session()
    tag = create_tag(session)
    book = create_book(session)
    r_add = session.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert r_add.status_code == 200
    r_del = session.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r_del.status_code == 409
    data = r_del.json()
    assert "detail" in data

def test_create_order_success():
    session = requests.Session()
    book = create_book(session, stock=10, price=25.0)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == 50.0

def test_create_order_insufficient_stock():
    session = requests.Session()
    book = create_book(session, stock=1, price=10.0)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }
    r = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_invalid_transition():
    session = requests.Session()
    book = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_update = session.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r_update.status_code == 400
    data = r_update.json()
    assert "detail" in data

def test_get_invoice_pending_order():
    session = requests.Session()
    book = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_invoice = session.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=TIMEOUT)
    assert r_invoice.status_code == 403
    data = r_invoice.json()
    assert "detail" in data

def test_add_item_to_non_pending_order():
    session = requests.Session()
    book1 = create_book(session, stock=10)
    book2 = create_book(session, stock=10)
    payload = {
        "customer_name": unique("customer"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book1["id"], "quantity": 1}]
    }
    r_create = session.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r_create.status_code == 201
    order_id = r_create.json()["id"]
    r_confirm = session.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r_confirm.status_code == 200
    r_add = session.post(f"{BASE_URL}/orders/{order_id}/items", json={"book_id": book2["id"], "quantity": 1}, timeout=TIMEOUT)
    assert r_add.status_code == 403
    data = r_add.json()
    assert "detail" in data

def test_bulk_create_no_api_key():
    session = requests.Session()
    author = create_author(session)
    cat = create_category(session)
    payload = {
        "books": [{
            "title": unique("book"),
            "isbn": unique("isbn")[:13],
            "price": 10.0,
            "published_year": 2020,
            "stock": 1,
            "author_id": author["id"],
            "category_id": cat["id"]
        }]
    }
    r = session.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data

def test_clone_book_success():
    session = requests.Session()
    book = create_book(session, stock=5, price=30.0)
    new_isbn = unique("clone")[:13]
    payload = {"new_isbn": new_isbn, "new_title": "Cloned Book", "stock": 3}
    r = session.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == new_isbn
    assert data["stock"] == 3
    assert data["price"] == 30.0

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L2__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run1__t0_4.py
# IDENTIFIER: L3_run1
# ===========================================================================

import uuid
import requests
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("author")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("cat")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id: int, category_id: int, isbn: Optional[str] = None, title: Optional[str] = None, price: float = 10.0, published_year: int = 2020, stock: int = 10) -> Dict[str, Any]:
    if isbn is None:
        isbn = unique("isbn")[:13]
    if title is None:
        title = unique("book")
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_with_etag_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    etag = r.headers.get("etag", "").strip('"')
    new_name = unique("updated")
    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, headers={"If-Match": etag}, timeout=TIMEOUT)
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == new_name

def test_update_author_etag_mismatch_returns_412():
    author = create_author()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("x")}, headers={"If-Match": "wrongetag"}, timeout=TIMEOUT)
    assert r.status_code == 412
    data = r.json()
    assert "detail" in data

def test_delete_author_without_books_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_author_with_books_returns_409():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_category_with_books_returns_409():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("book"), "isbn": isbn, "price": 15.0, "published_year": 2021, "stock": 5, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={"title": unique("b1"), "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 2, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("b2"), "isbn": isbn, "price": 10.0, "published_year": 2020, "stock": 2, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_invalid_author_returns_404():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={"title": unique("b"), "isbn": unique("isbn")[:13], "price": 10.0, "published_year": 2020, "stock": 2, "author_id": 99999, "category_id": cat["id"]}, timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_get_book_success_with_etag():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "ETag" in r.headers or "etag" in r.headers

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_restore_soft_deleted_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 4, "reviewer_name": unique("rev")}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_on_deleted_book_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 3, "reviewer_name": unique("rev")}, timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_apply_discount_to_old_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data

def test_apply_discount_to_new_book_returns_400():
    author = create_author()
    cat = create_category()
    from datetime import datetime
    current_year = datetime.now().year
    book = create_book(author["id"], cat["id"], published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_positive_delta_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_valid_image_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data

def test_upload_cover_unsupported_type_returns_415():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", b"some text", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run2__t0_4.py
# IDENTIFIER: L3_run2
# ===========================================================================

import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: str = None, bio: str = "Bio", born_year: int = 1980) -> dict:
    if name is None:
        name = unique("author")
    payload = {"name": name, "bio": bio, "born_year": born_year}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: str = None, description: str = "Desc") -> dict:
    if name is None:
        name = unique("cat")
    payload = {"name": name, "description": description}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id: int, category_id: int, title: str = None, isbn: str = None, price: float = 10.0, published_year: int = 2020, stock: int = 10) -> dict:
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: str = None) -> dict:
    if name is None:
        name = unique("tag")
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name: str, customer_email: str, items: list) -> dict:
    payload = {"customer_name": customer_name, "customer_email": customer_email, "items": items}
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_missing_name():
    payload = {"bio": "No name"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    author = create_author()
    author_id = author["id"]
    r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author_id

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_etag_mismatch():
    author = create_author()
    author_id = author["id"]
    r = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=30)
    etag = r.headers.get("etag", "").strip('"')
    wrong_etag = "wrongetag"
    payload = {"name": unique("updated")}
    r2 = requests.put(f"{BASE_URL}/authors/{author_id}", json=payload, headers={"If-Match": wrong_etag}, timeout=30)
    assert r2.status_code == 412
    data = r2.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_duplicate_name():
    name = unique("cat")
    create_category(name=name)
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_category_with_books_conflict():
    cat = create_category()
    author = create_author()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    cat = create_category()
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 15.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == payload["title"]
    assert "id" in data

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    create_book(author["id"], cat["id"], isbn=isbn)
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"],
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_invalid_author():
    cat = create_category()
    payload = {
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": 999999,
        "category_id": cat["id"],
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books?search={author['name'][:5]}&author_id={author['id']}&min_price=5&max_price=20", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_soft_deleted_book_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    r = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    assert r.status_code == 204

def test_restore_non_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    r = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    requests.delete(f"{BASE_URL}/books/{book_id}", timeout=30)
    payload = {"rating": 5, "reviewer_name": "Tester", "comment": "Great"}
    r = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_get_rating_no_reviews():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    r = requests.get(f"{BASE_URL}/books/{book_id}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["review_count"] == 0
    assert data["average_rating"] is None

def test_apply_discount_on_new_book():
    author = create_author()
    cat = create_category()
    current_year = 2026
    book = create_book(author["id"], cat["id"], published_year=current_year)
    book_id = book["id"]
    payload = {"discount_percent": 10}
    r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_rate_limited():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020)
    book_id = book["id"]
    payload = {"discount_percent": 10}
    status_codes = []
    for _ in range(6):
        r = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=payload, timeout=30)
        status_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in status_codes

def test_update_stock_insufficient():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    book_id = book["id"]
    r = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_unsupported_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    book_id = book["id"]
    files = {"file": ("test.txt", b"fake content", "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_duplicate_name():
    name = unique("tag")
    create_tag(name=name)
    payload = {"name": name}
    r = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_tag_assigned_to_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = create_tag()
    tag_id = tag["id"]
    requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag_id]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{tag_id}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=2)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 10}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_order_duplicate_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    payload = {
        "customer_name": unique("cust"),
        "customer_email": "test@test.com",
        "items": [{"book_id": book["id"], "quantity": 1}, {"book_id": book["id"], "quantity": 2}],
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = create_order(unique("cust"), "test@test.com", [{"book_id": book["id"], "quantity": 1}])
    order_id = order["id"]
    payload = {"status": "delivered"}
    r = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=payload, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_for_pending_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = create_order(unique("cust"), "test@test.com", [{"book_id": book["id"], "quantity": 1}])
    order_id = order["id"]
    r = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

def test_add_item_to_non_pending_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    order = create_order(unique("cust"), "test@test.com", [{"book_id": book["id"], "quantity": 1}])
    order_id = order["id"]
    requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "confirmed"}, timeout=30)
    payload = {"book_id": book["id"], "quantity": 1}
    r = requests.post(f"{BASE_URL}/orders/{order_id}/items", json=payload, timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run3__t0_4.py
# IDENTIFIER: L3_run3
# ===========================================================================

import uuid
import requests
import io

BASE_URL = "http://localhost:8000"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: str = None, bio: str = "Bio", born_year: int = 1980):
    if name is None:
        name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: str = None, description: str = "Desc"):
    if name is None:
        name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": description}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id: int, category_id: int, title: str = None, isbn: str = None, price: float = 10.0, published_year: int = 2020, stock: int = 10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: str = None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name: str, customer_email: str, items: list):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──────────────────────────────────────────────────────────────

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

# ── /authors POST ─────────────────────────────────────────────────────────

def test_create_author_success():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} GET ──────────────────────────────────────────────

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert "ETag" in r.headers

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} DELETE ───────────────────────────────────────────

def test_delete_author_with_books_conflict():
    author = create_author()
    cat = create_category()
    create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /categories POST ──────────────────────────────────────────────────────

def test_create_category_success():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_duplicate_category_name():
    name = unique("catdup")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ───────────────────────────────────────────────────────────

def test_create_book_success():
    author = create_author()
    cat = create_category()
    title = unique("book")
    isbn = unique("isbn")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == title
    assert "id" in data

def test_create_book_duplicate_isbn():
    author = create_author()
    cat = create_category()
    isbn = unique("isbn")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    cat = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": 999999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} GET ──────────────────────────────────────────────────

def test_get_book_success_with_etag():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert "ETag" in r.headers

def test_get_book_soft_deleted_returns_410():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ───────────────────────────────────────────────

def test_soft_delete_book_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

# ── /books/{book_id}/restore POST ─────────────────────────────────────────

def test_restore_soft_deleted_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

# ── /books/{book_id}/reviews POST ─────────────────────────────────────────

def test_create_review_for_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    reviewer = unique("reviewer")
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "comment": "Great book",
        "reviewer_name": reviewer
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["reviewer_name"] == reviewer
    assert "id" in data

# ── /books/{book_id}/discount POST ────────────────────────────────────────

def test_apply_discount_to_old_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2020, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 80.0
    assert "original_price" in data

def test_apply_discount_to_new_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], published_year=2026, price=100.0)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ──────────────────────────────────────────

def test_update_stock_positive_delta():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=10)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_result():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/cover POST ───────────────────────────────────────────

def test_upload_cover_valid_image():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.jpg", io.BytesIO(b"fake_jpeg_data"), "image/jpeg")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "test.jpg"
    assert "size_bytes" in data

def test_upload_cover_unsupported_type():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    files = {"file": ("test.txt", io.BytesIO(b"text data"), "text/plain")}
    r = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

# ── /tags POST ────────────────────────────────────────────────────────────

def test_create_tag_success():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

# ── /books/{book_id}/tags POST ────────────────────────────────────────────

def test_add_tags_to_book():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"])
    tag = create_tag()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert any(t["id"] == tag["id"] for t in data["tags"])

# ── /orders POST ──────────────────────────────────────────────────────────

def test_create_order_success():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    customer_name = unique("cust")
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["customer_name"] == customer_name
    assert "total_price" in data

def test_create_order_insufficient_stock():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 10}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ───────────────────────────────────────

def test_update_order_status_valid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/invoice GET ────────────────────────────────────────

def test_get_invoice_for_confirmed_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

def test_get_invoice_for_pending_order():
    author = create_author()
    cat = create_category()
    book = create_book(author["id"], cat["id"], stock=5)
    order = create_order(unique("cust"), "a@b.com", [{"book_id": book["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run4__t0_4.py
# IDENTIFIER: L3_run4
# ===========================================================================

import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(session, name=None):
    if name is None:
        name = unique("author")
    r = session.post(f"{BASE_URL}/authors", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(session, name=None):
    if name is None:
        name = unique("cat")
    r = session.post(f"{BASE_URL}/categories", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(session, author_id, category_id, isbn=None, price=10.0, published_year=2020, stock=10, title=None):
    if isbn is None:
        isbn = unique("isbn")[:13]
    if title is None:
        title = unique("book")
    r = session.post(f"{BASE_URL}/books", json={
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(session, name=None):
    if name is None:
        name = unique("tag")[:30]
    r = session.post(f"{BASE_URL}/tags", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

def test_create_author_success():
    r = requests.post(f"{BASE_URL}/authors", json={"name": unique("author")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert "name" in data

def test_create_author_missing_name():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=10", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_author_by_id_success():
    author = create_author(requests.Session())
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_with_books_conflict():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    create_book(s, author["id"], cat["id"])
    r = s.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_success():
    r = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_create_duplicate_category_name():
    name = unique("cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    r = s.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 15.0,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["price"] == 15.0

def test_create_book_duplicate_isbn():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    isbn = unique("isbn")[:13]
    s.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    r = s.post(f"{BASE_URL}/books", json={
        "title": unique("book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_nonexistent_author():
    cat = create_category(requests.Session())
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "isbn": unique("isbn")[:13],
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": 99999,
        "category_id": cat["id"]
    }, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_list_books_with_filters():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    create_book(s, author["id"], cat["id"], price=20.0, published_year=2022)
    r = s.get(f"{BASE_URL}/books?min_price=15&max_price=25&category_id={cat['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

def test_get_book_soft_deleted_returns_410():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = s.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    s.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "reviewer_name": unique("reviewer"),
        "comment": "Great book"
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_apply_discount_old_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], published_year=2020, price=100.0)
    r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["discounted_price"] == 80.0

def test_apply_discount_new_book_fails():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    current_year = 2026
    book = create_book(s, author["id"], cat["id"], published_year=current_year, price=50.0)
    r = s.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_stock_positive_delta():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=10)
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_update_stock_insufficient_negative_delta():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=3)
    r = s.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_upload_cover_valid_image():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.jpg", b"fake_jpeg_data", "image/jpeg")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert data["content_type"] == "image/jpeg"

def test_upload_cover_unsupported_type():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    r = s.post(f"{BASE_URL}/books/{book['id']}/cover", files={"file": ("test.txt", b"text data", "text/plain")}, timeout=30)
    assert r.status_code == 415
    data = r.json()
    assert "detail" in data

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")[:30]}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data

def test_add_tags_to_book_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"])
    tag1 = create_tag(s)
    tag2 = create_tag(s)
    r = s.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag1["id"], tag2["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "tags" in data
    assert len(data["tags"]) == 2

def test_create_order_success():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=10, price=25.0)
    r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}]
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["total_price"] == 50.0

def test_create_order_insufficient_stock():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=1)
    r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 5}]
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_update_order_status_valid_transition():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=5)
    order_r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_r.json()
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition():
    s = requests.Session()
    author = create_author(s)
    cat = create_category(s)
    book = create_book(s, author["id"], cat["id"], stock=5)
    order_r = s.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("cust"),
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }, timeout=30)
    order = order_r.json()
    s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=30)
    r = s.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run5__t0_4.py
# IDENTIFIER: L3_run5
# ===========================================================================

import uuid
import requests
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(
    title: Optional[str] = None,
    isbn: Optional[str] = None,
    price: float = 10.0,
    published_year: int = 2020,
    stock: int = 10,
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = unique("ISBN")[:13]
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
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(
    customer_name: Optional[str] = None,
    customer_email: str = "test@example.com",
    items: Optional[list] = None,
) -> Dict[str, Any]:
    if customer_name is None:
        customer_name = unique("Customer")
    if items is None:
        book = create_book(stock=5)
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    r = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

# ── /health ──────────────────────────────────────────────

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data

# ── /authors POST ────────────────────────────────────────

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1980}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "No name"}, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /authors GET ─────────────────────────────────────────

def test_list_authors_with_pagination():
    create_author()
    create_author()
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=1", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

# ── /authors/{author_id} GET ─────────────────────────────

def test_get_author_by_id_success():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]

def test_get_author_not_found_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ── /authors/{author_id} PUT ─────────────────────────────

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

# ── /authors/{author_id} DELETE ──────────────────────────

def test_delete_author_without_books_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_delete_author_with_books_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /categories POST ─────────────────────────────────────

def test_create_category_success():
    name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("Category")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

# ── /books POST ──────────────────────────────────────────

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 15.0,
        "published_year": 2021,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_duplicate_isbn_returns_409():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": 10.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book2"),
        "isbn": isbn,
        "price": 12.0,
        "published_year": 2021,
        "stock": 2,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_invalid_price_returns_422():
    author = create_author()
    category = create_category()
    isbn = unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"),
        "isbn": isbn,
        "price": -5.0,
        "published_year": 2020,
        "stock": 1,
        "author_id": author["id"],
        "category_id": category["id"],
    }, timeout=TIMEOUT)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

# ── /books GET ───────────────────────────────────────────

def test_list_books_with_filters():
    create_book()
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5&min_price=0&max_price=100", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

# ── /books/{book_id} GET ─────────────────────────────────

def test_get_book_by_id_success():
    book = create_book()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_get_deleted_book_returns_410():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

# ── /books/{book_id} DELETE ──────────────────────────────

def test_soft_delete_book_success():
    book = create_book()
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

# ── /books/{book_id}/restore POST ────────────────────────

def test_restore_soft_deleted_book_success():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book_returns_400():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/reviews POST ────────────────────────

def test_create_review_success():
    book = create_book()
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 4,
        "comment": "Great book",
        "reviewer_name": unique("Reviewer"),
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

# ── /books/{book_id}/discount POST ───────────────────────

def test_apply_discount_to_old_book_success():
    book = create_book(published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "discounted_price" in data
    assert data["original_price"] > data["discounted_price"]

def test_apply_discount_to_new_book_returns_400():
    from datetime import datetime
    current_year = datetime.now().year
    book = create_book(published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 10}, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /books/{book_id}/stock PATCH ─────────────────────────

def test_update_stock_positive_delta_success():
    book = create_book(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=3", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 8

def test_update_stock_negative_delta_insufficient_returns_400():
    book = create_book(stock=2)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders POST ─────────────────────────────────────────

def test_create_order_success():
    book = create_book(stock=5)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "buyer@example.com",
        "items": [{"book_id": book["id"], "quantity": 2}],
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"

def test_create_order_insufficient_stock_returns_400():
    book = create_book(stock=1)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": unique("Customer"),
        "customer_email": "buyer@example.com",
        "items": [{"book_id": book["id"], "quantity": 10}],
    }, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/status PATCH ──────────────────────

def test_update_order_status_valid_transition():
    order = create_order()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_update_order_status_invalid_transition_returns_400():
    order = create_order()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

# ── /orders/{order_id}/invoice GET ───────────────────────

def test_get_invoice_for_confirmed_order_success():
    order = create_order()
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "invoice_number" in data
    assert data["order_id"] == order["id"]

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L3__run5__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run1__t0_4.py
# IDENTIFIER: L4_run1
# ===========================================================================

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

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run1__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run2__t0_4.py
# IDENTIFIER: L4_run2
# ===========================================================================

import uuid
import requests
import time

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
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020, author_name=None, cat_name=None):
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
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
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "test bio", "born_year": 1990}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["born_year"] == 1990

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_existing_author_returns_200():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == a["id"]

def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_delete_author_without_books_returns_204():
    a = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204

def test_create_category_with_valid_name():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_get_existing_category_returns_200():
    c = create_category()
    r = requests.get(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == c["id"]

def test_create_book_with_all_required_fields():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book", "isbn": isbn, "price": 29.99,
        "published_year": 2020, "stock": 10,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad", "isbn": uuid.uuid4().hex[:13], "price": -5,
        "published_year": 2020, "stock": 10,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_existing_book_returns_200():
    _, _, b = setup_book_with_deps()
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_existing_book_returns_204():
    _, _, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_apply_discount_to_old_book_returns_200():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0

def test_apply_discount_to_new_book_returns_400():
    _, _, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_increase_stock_by_positive_quantity():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Alice"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 5

def test_get_rating_for_book_with_reviews():
    _, _, b = setup_book_with_deps()
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 4, "reviewer_name": "Bob"}, timeout=30)
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 2, "reviewer_name": "Eve"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["average_rating"] == 3.0
    assert data["review_count"] == 2

def test_create_tag_with_valid_name():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_delete_tag_not_associated_with_books_returns_204():
    t = create_tag()
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 204

def test_add_tags_to_existing_book():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["tags"]) == 1

def test_create_order_with_valid_items():
    _, _, b = setup_book_with_deps(stock=10, price=50)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@test.com",
        "items": [{"book_id": b["id"], "quantity": 2}],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["total_price"] == 100.0

def test_create_order_with_insufficient_stock_returns_400():
    _, _, b = setup_book_with_deps(stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [{"book_id": b["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_transition_order_from_pending_to_confirmed():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

def test_transition_order_from_pending_to_shipped_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_get_invoice_for_confirmed_order():
    _, _, b = setup_book_with_deps(stock=10, price=50)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 2}])
    requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["subtotal"] == 100.0
    assert data["invoice_number"].startswith("INV-")

def test_get_invoice_for_pending_order_returns_403():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run2__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run3__t0_4.py
# IDENTIFIER: L4_run3
# ===========================================================================

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
        name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020, author_name=None, cat_name=None):
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    a = create_author(name=author_name or unique("auth"))
    c = create_category(name=cat_name or unique("cat"))
    b = create_book(a["id"], c["id"], isbn=isbn, stock=stock, price=price, published_year=published_year)
    return a, c, b

def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_with_valid_data():
    name = unique("author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": "Test bio", "born_year": 1985,
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["born_year"] == 1985

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_author_by_valid_id():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == a["id"]
    assert "name" in data

def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

def test_update_author_name_successfully():
    a = create_author(name=unique("old"))
    new_name = unique("new")
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name

def test_delete_author_without_books_returns_204():
    a = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204

def test_delete_author_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_category_with_valid_name():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Test"}, timeout=30)
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

def test_delete_category_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_with_all_required_fields():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"), "isbn": isbn, "price": 19.99,
        "published_year": 2021, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn

def test_create_book_with_duplicate_isbn_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("dup"), "isbn": b["isbn"], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("neg"), "isbn": uuid.uuid4().hex[:13], "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data

def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_soft_delete_existing_book_returns_204():
    _, _, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204

def test_restore_soft_deleted_book_returns_200():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]

def test_restore_non_deleted_book_returns_400():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_apply_discount_to_old_book_returns_200():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount",
                      json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0
    assert "original_price" in data

def test_apply_discount_to_new_book_returns_400():
    _, _, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount",
                      json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_increase_stock_with_positive_quantity():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    data = r.json()
    assert "detail" in data

def test_create_review_for_existing_book():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews",
                      json={"rating": 4, "reviewer_name": unique("rev")}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4

def test_create_review_for_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews",
                      json={"rating": 5, "reviewer_name": "Eve"}, timeout=30)
    assert r.status_code == 410
    data = r.json()
    assert "detail" in data

def test_get_rating_with_multiple_reviews():
    _, _, b = setup_book_with_deps()
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews",
                  json={"rating": 5, "reviewer_name": "Alice"}, timeout=30)
    requests.post(f"{BASE_URL}/books/{b['id']}/reviews",
                  json={"rating": 3, "reviewer_name": "Bob"}, timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}/rating", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["average_rating"] == 4.0
    assert data["review_count"] == 2

def test_create_tag_with_valid_name():
    name = unique("tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_tag_returns_409():
    name = unique("tag")
    requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_delete_tag_attached_to_book_returns_409():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409
    data = r.json()
    assert "detail" in data

def test_add_tags_to_book_successfully():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["id"] == t["id"]

def test_add_nonexistent_tag_to_book_returns_404():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [999999]}, timeout=30)
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run3__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run4__t0_4.py
# IDENTIFIER: L4_run4
# ===========================================================================

import uuid
import time
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
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    if name is None:
        name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    if name is None:
        name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020, author_name=None, cat_name=None):
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
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
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "A great writer", "born_year": 1900}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "A great writer"
    assert data["born_year"] == 1900

def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_by_valid_id():
    a = create_author()
    r = requests.get(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == a["id"]
    assert "name" in data

def test_get_author_nonexistent_id_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_delete_author_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_with_valid_name():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_duplicate_category_returns_409():
    name = unique("Cat")
    requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_delete_category_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_with_valid_data():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Valid Book", "isbn": isbn, "price": 19.99,
        "published_year": 2021, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 19.99

def test_create_book_negative_price_returns_422():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Bad Price", "isbn": uuid.uuid4().hex[:13], "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_book_duplicate_isbn_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": b["isbn"], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_soft_delete_existing_book():
    _, _, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204
    r2 = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r2.status_code == 410

def test_restore_soft_deleted_book():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]
    r2 = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r2.status_code == 200

def test_restore_non_deleted_book_returns_400():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_to_old_book():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0
    assert "original_price" in data

def test_apply_discount_to_new_book_returns_400():
    current_year = 2026
    _, _, b = setup_book_with_deps(price=50, published_year=current_year)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_increase_book_stock():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15

def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_for_existing_book():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 4, "reviewer_name": "Alice", "comment": "Good"}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["rating"] == 4
    assert data["reviewer_name"] == "Alice"

def test_create_review_for_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Bob"}, timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()

def test_upload_valid_cover_image():
    _, _, b = setup_book_with_deps()
    img = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("cover.png", img, "image/png")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["content_type"] == "image/png"
    assert data["book_id"] == b["id"]

def test_upload_unsupported_file_type_returns_415():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/cover", files={"file": ("doc.txt", b"hello", "text/plain")}, timeout=30)
    assert r.status_code == 415
    assert "detail" in r.json()

def test_create_tag_with_valid_name():
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
    assert "detail" in r.json()

def test_delete_tag_attached_to_book_returns_409():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_order_with_valid_items():
    _, _, b = setup_book_with_deps(stock=10, price=50)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "Jan", "customer_email": "jan@test.com",
        "items": [{"book_id": b["id"], "quantity": 2}],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["total_price"] == 100.0
    assert "id" in data

def test_create_order_insufficient_stock_returns_400():
    _, _, b = setup_book_with_deps(stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [{"book_id": b["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_transition_order_from_pending_to_confirmed():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run4__t0_4.py
# ===========================================================================



# ===========================================================================
# START OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run5__t0_4.py
# IDENTIFIER: L4_run5
# ===========================================================================

import uuid
import time
import pytest
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}


def create_author(name=None, bio=None, born_year=1980):
    if name is None:
        name = f"Author_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": bio, "born_year": born_year}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_category(name=None):
    if name is None:
        name = f"Cat_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    if title is None:
        title = f"Book_{uuid.uuid4().hex[:8]}"
    if isbn is None:
        isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_tag(name=None):
    if name is None:
        name = f"Tag_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def create_order(customer_name, customer_email, items):
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def setup_book_with_deps(isbn=None, stock=10, price=29.99, published_year=2020):
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"], isbn=isbn, stock=stock, price=price, published_year=published_year)
    return a, c, b


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_create_author_with_minimal_data():
    name = f"Min_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name


def test_create_author_missing_name_returns_422():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_create_author_name_too_long_returns_422():
    long_name = "A" * 101
    r = requests.post(f"{BASE_URL}/authors", json={"name": long_name}, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_get_nonexistent_author_returns_404():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_update_author_name_successfully():
    a = create_author()
    new_name = f"Updated_{uuid.uuid4().hex[:8]}"
    r = requests.put(f"{BASE_URL}/authors/{a['id']}", json={"name": new_name}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name


def test_delete_author_without_books_returns_204():
    a = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}", timeout=30)
    assert r.status_code == 204


def test_create_category_with_duplicate_name_returns_409():
    name = f"DupCat_{uuid.uuid4().hex[:8]}"
    create_category(name=name)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_delete_category_with_books_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/categories/{c['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_book_with_all_fields():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Full Book", "isbn": isbn, "price": 19.99,
        "published_year": 2021, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["price"] == 19.99


def test_create_book_with_negative_price_returns_422():
    a = create_author()
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Neg", "isbn": isbn, "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_create_book_with_duplicate_isbn_returns_409():
    a, c, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": b["isbn"], "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_book_with_nonexistent_author_returns_404():
    c = create_category()
    isbn = uuid.uuid4().hex[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "NoAuthor", "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": 999999, "category_id": c["id"],
    }, timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_get_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()


def test_soft_delete_book_returns_204():
    _, _, b = setup_book_with_deps()
    r = requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r.status_code == 204


def test_restore_soft_deleted_book_returns_200():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == b["id"]
    r2 = requests.get(f"{BASE_URL}/books/{b['id']}", timeout=30)
    assert r2.status_code == 200


def test_restore_non_deleted_book_returns_400():
    _, _, b = setup_book_with_deps()
    r = requests.post(f"{BASE_URL}/books/{b['id']}/restore", timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_apply_discount_to_old_book_returns_200():
    _, _, b = setup_book_with_deps(price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 25}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["discounted_price"] == 75.0
    assert "original_price" in data


def test_apply_discount_to_new_book_returns_400():
    _, _, b = setup_book_with_deps(price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_increase_stock_returns_updated_book():
    _, _, b = setup_book_with_deps(stock=5)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": 10}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["stock"] == 15


def test_decrease_stock_below_zero_returns_400():
    _, _, b = setup_book_with_deps(stock=3)
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", params={"quantity": -10}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_upload_cover_with_unsupported_type_returns_415():
    _, _, b = setup_book_with_deps()
    r = requests.post(
        f"{BASE_URL}/books/{b['id']}/cover",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        timeout=30,
    )
    assert r.status_code == 415
    assert "detail" in r.json()


def test_upload_cover_exceeding_size_limit_returns_413():
    _, _, b = setup_book_with_deps()
    big_data = b"\x00" * (2 * 1024 * 1024 + 1)
    r = requests.post(
        f"{BASE_URL}/books/{b['id']}/cover",
        files={"file": ("big.jpg", big_data, "image/jpeg")},
        timeout=30,
    )
    assert r.status_code == 413
    assert "detail" in r.json()


def test_create_review_on_soft_deleted_book_returns_410():
    _, _, b = setup_book_with_deps()
    requests.delete(f"{BASE_URL}/books/{b['id']}", timeout=30)
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={"rating": 5, "reviewer_name": "Eve"}, timeout=30)
    assert r.status_code == 410
    assert "detail" in r.json()


def test_create_tag_with_duplicate_name_returns_409():
    name = f"DupTag_{uuid.uuid4().hex[:8]}"
    create_tag(name=name)
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_delete_tag_attached_to_book_returns_409():
    _, _, b = setup_book_with_deps()
    t = create_tag()
    requests.post(f"{BASE_URL}/books/{b['id']}/tags", json={"tag_ids": [t["id"]]}, timeout=30)
    r = requests.delete(f"{BASE_URL}/tags/{t['id']}", timeout=30)
    assert r.status_code == 409
    assert "detail" in r.json()


def test_create_order_insufficient_stock_returns_400():
    _, _, b = setup_book_with_deps(stock=2)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [{"book_id": b["id"], "quantity": 5}],
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_create_order_with_duplicate_book_ids_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "X", "customer_email": "x@t.com",
        "items": [
            {"book_id": b["id"], "quantity": 1},
            {"book_id": b["id"], "quantity": 2},
        ],
    }, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_transition_order_from_pending_to_shipped_returns_400():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=30)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_get_invoice_for_pending_order_returns_403():
    _, _, b = setup_book_with_deps(stock=10)
    order = create_order("Test", "t@t.com", [{"book_id": b["id"], "quantity": 1}])
    r = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=30)
    assert r.status_code == 403
    assert "detail" in r.json()

# ===========================================================================
# END OF FILE: v12/outputs_v12_deepseek-v4/test_generated_deepseek-v4-flash__bookstore__L4__run5__t0_4.py
# ===========================================================================



