import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=None):
    if name is None:
        name = unique("author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name=None, description=None):
    if name is None:
        name = unique("category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title=None, isbn=None, price=19.99, published_year=2020, stock=10, author_id=None, category_id=None):
    if title is None:
        title = unique("book")
    if isbn is None:
        isbn = str(uuid.uuid4().int)[:13].zfill(10)
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
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(customer_name=None, customer_email=None, items=None):
    if customer_name is None:
        customer_name = unique("customer")
    if customer_email is None:
        customer_email = f"{unique()}@example.com"
    if items is None:
        book = create_book()
        items = [{"book_id": book["id"], "quantity": 1}]
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_success():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_valid_data():
    name = unique("author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_name():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_authors_with_pagination():
    create_author()
    response = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 10}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_author_by_id():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_author_with_etag_mismatch():
    author = create_author()
    response = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("updated")},
        headers={"If-Match": "invalid-etag"},
        timeout=TIMEOUT
    )
    assert response.status_code == 412

def test_create_book_valid_data():
    author = create_author()
    category = create_category()
    title = unique("book")
    isbn = str(uuid.uuid4().int)[:13].zfill(10)
    payload = {
        "title": title,
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == title
    assert data["isbn"] == isbn

def test_create_book_invalid_isbn_length():
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": "123",
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_filters():
    author = create_author()
    book = create_book(author_id=author["id"])
    response = requests.get(
        f"{BASE_URL}/books",
        params={"author_id": author["id"], "min_price": 10},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_get_book_soft_deleted():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_delete_book_soft_delete():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 410

def test_delete_book_already_deleted():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    second_delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert second_delete_response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert get_response.status_code == 200

def test_create_review_for_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert delete_response.status_code == 204
    payload = {
        "rating": 5,
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
    assert response.status_code == 410

def test_apply_discount_rate_limit_exceeded():
    book = create_book()
    payload = {"discount_percent": 10.0}
    for _ in range(6):
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_cover_file_too_large():
    book = create_book()
    large_content = b"x" * (2 * 1024 * 1024 + 1)
    files = {"file": ("large.jpg", large_content, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_upload_cover_unsupported_type():
    book = create_book()
    pdf_content = b"%PDF-1.4 fake pdf"
    files = {"file": ("document.pdf", pdf_content, "application/pdf")}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 415

def test_bulk_create_books_without_api_key():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("bulkbook"),
            "isbn": str(uuid.uuid4().int)[:13].zfill(10),
            "price": 20.0,
            "published_year": 2022,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    payload = {"books": books}
    response = requests.post(f"{BASE_URL}/books/bulk", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401

def test_bulk_create_books_rate_limit_exceeded():
    author = create_author()
    category = create_category()
    books = [
        {
            "title": unique("bulkbook"),
            "isbn": str(uuid.uuid4().int)[:13].zfill(10),
            "price": 20.0,
            "published_year": 2022,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        }
    ]
    payload = {"books": books}
    headers = {"X-API-Key": "testkey"}
    for _ in range(4):
        response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 429

def test_create_order_with_multiple_items():
    book1 = create_book()
    book2 = create_book()
    items = [
        {"book_id": book1["id"], "quantity": 2},
        {"book_id": book2["id"], "quantity": 1}
    ]
    response = requests.post(
        f"{BASE_URL}/orders",
        json={
            "customer_name": unique("customer"),
            "customer_email": f"{unique()}@example.com",
            "items": items
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert len(data["items"]) == 2

def test_create_order_empty_items():
    response = requests.post(
        f"{BASE_URL}/orders",
        json={
            "customer_name": unique("customer"),
            "customer_email": f"{unique()}@example.com",
            "items": []
        },
        timeout=TIMEOUT
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_order_status_invalid_value():
    order = create_order()
    payload = {"status": "invalid_status"}
    response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_book_export_without_api_key():
    response = requests.post(f"{BASE_URL}/exports/books", timeout=TIMEOUT)
    assert response.status_code == 401

def test_get_export_job_not_found():
    response = requests.get(f"{BASE_URL}/exports/nonexistentjob", timeout=TIMEOUT)
    assert response.status_code == 404

def test_toggle_maintenance_without_api_key():
    payload = {"enabled": True}
    response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, timeout=TIMEOUT)
    assert response.status_code == 401

def test_get_statistics_without_api_key():
    response = requests.get(f"{BASE_URL}/statistics/summary", timeout=TIMEOUT)
    assert response.status_code == 401

def test_deprecated_catalog_redirect():
    response = requests.get(f"{BASE_URL}/catalog", timeout=TIMEOUT, allow_redirects=False)
    assert response.status_code == 301
    assert response.headers.get("Location") == "/books"

def test_add_tags_to_book_empty_list():
    book = create_book()
    payload = {"tag_ids": []}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_update_category_name_too_long():
    category = create_category()
    long_name = "a" * 51
    payload = {"name": long_name}
    response = requests.put(f"{BASE_URL}/categories/{category['id']}", json=payload, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data