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