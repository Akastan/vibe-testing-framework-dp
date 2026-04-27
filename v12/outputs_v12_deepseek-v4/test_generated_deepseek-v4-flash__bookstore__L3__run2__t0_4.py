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