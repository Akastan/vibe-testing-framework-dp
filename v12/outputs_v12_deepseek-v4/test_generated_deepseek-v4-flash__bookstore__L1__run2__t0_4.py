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