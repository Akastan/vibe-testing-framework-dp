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