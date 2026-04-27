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