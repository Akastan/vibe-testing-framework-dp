import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "Bio", "born_year": 1990}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_category():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Desc"}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_book(author_id, category_id):
    title = unique("Book")
    isbn = str(uuid.uuid4().int)[:13]
    data = {
        "title": title,
        "isbn": isbn,
        "price": 100.0,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_resource(url):
    r = requests.delete(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    name = unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_pagination():
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_by_id():
    author = create_author()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_invalid_id():
    r = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_success():
    author = create_author()
    new_name = unique("NewName")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_author_success():
    author = create_author()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_list_categories():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_category_success():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_missing_name():
    r = requests.post(f"{BASE_URL}/categories", json={}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_success():
    a = create_author()
    c = create_category()
    title = unique("Book")
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": "1234567890", "price": 10.0, "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == title

def test_create_book_invalid_price():
    a = create_author()
    c = create_category()
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Fail", "isbn": "1234567890", "price": -1.0, "published_year": 2000, "author_id": a["id"], "category_id": c["id"]
    }, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_default():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_create_review_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/reviews", json={
        "rating": 5, "reviewer_name": "Tester", "comment": "Great"
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["rating"] == 5

def test_apply_discount_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/books/{b['id']}/discount", json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "discounted_price" in r.json()

def test_update_stock_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.patch(f"{BASE_URL}/books/{b['id']}/stock", json={"stock": 50}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_create_order_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_update_order_status_success():
    a = create_author()
    c = create_category()
    b = create_book(a["id"], c["id"])
    order = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": "John", "customer_email": "j@test.cz", "items": [{"book_id": b["id"], "quantity": 1}]
    }, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


def test_create_author_with_empty_bio():
    name = unique("Auth")
    r = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "", "born_year": 1980}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["bio"] == ""

def test_list_authors_empty_limit():
    r = requests.get(f"{BASE_URL}/authors", params={"limit": 0}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == []

def test_update_author_name_only():
    author = create_author()
    new_name = unique("NewName")
    r = requests.patch(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    updated_author = r.json()
    assert updated_author["name"] == new_name
    assert updated_author["bio"] == author["bio"]
    assert updated_author["born_year"] == author["born_year"]
    delete_resource(f"{BASE_URL}/authors/{author['id']}")

def test_delete_nonexistent_author():
    r = requests.delete(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_create_category_with_special_chars():
    name = "Cat!@#$"
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Spec"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_get_category_by_id():
    cat = create_category()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat["id"]

def test_delete_category():
    cat = create_category()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    r_check = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r_check.status_code == 404

def test_create_book_invalid_isbn_length():
    auth = create_author()
    cat = create_category()
    data = {"title": "Book", "isbn": "123", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_details():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == book["title"]

def test_delete_book():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_review_invalid_rating():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 6, "comment": "Too high"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_book_reviews():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    review_data = {"rating": 5, "comment": "Great"}
    post_res = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=review_data, timeout=TIMEOUT)
    post_res.raise_for_status()

    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(item["rating"] == 5 and item["comment"] == "Great" for item in data)

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_order_nonexistent():
    r = requests.get(f"{BASE_URL}/orders/999999", timeout=TIMEOUT)
    assert r.status_code == 404

def test_book_price_update():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    new_price = 250.0
    r = requests.patch(f"{BASE_URL}/books/{book['id']}", json={"price": new_price}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    updated_book = r.json()
    assert updated_book["price"] == new_price

    r_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    r_check.raise_for_status()
    assert r_check.json()["price"] == new_price

def test_create_category_duplicate_name():
    name = unique("Dup")
    requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "D1"}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "D2"}, timeout=TIMEOUT)
    assert r.status_code == 400
    assert "detail" in r.json()

def test_author_born_year_validation():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "Test", "bio": "Bio", "born_year": -100}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_filter_by_author():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books", params={"author_id": auth["id"]}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    books = r.json()
    assert isinstance(books, list)
    assert len(books) > 0
    assert all(b["author_id"] == auth["id"] for b in books)

def test_create_book_no_category():
    auth = create_author()
    data = {"title": "NoCat", "isbn": "0000000000000", "price": 10.0, "published_year": 2020, "stock": 1, "author_id": auth["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_status_invalid():
    author = create_author()
    category = create_category()
    book = create_book(author["id"], category["id"])

    order_data = {
        "items": [{"book_id": book["id"], "quantity": 1}],
        "customer_email": "test@example.com"
    }
    r_order = requests.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT)
    r_order.raise_for_status()
    order = r_order.json()

    r = requests.patch(f"{BASE_URL}/orders/{order['id']}", json={"status": "INVALID_STATUS"}, timeout=TIMEOUT)

    assert r.status_code == 422
    assert "detail" in r.json()
    assert r.json()["detail"] is not None

def test_get_books_pagination_limit():
    author = create_author()
    category = create_category()
    create_book(author["id"], category["id"])
    create_book(author["id"], category["id"])

    r = requests.get(f"{BASE_URL}/books", params={"limit": 1}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1

def test_delete_book_invalid_id():
    r = requests.delete(f"{BASE_URL}/books/abc", timeout=TIMEOUT)
    assert r.status_code == 422

def test_search_books_by_title():
    auth = create_author()
    cat = create_category()
    title = unique("SearchMe")
    create_book(auth["id"], cat["id"])
    r = requests.get(f"{BASE_URL}/books", params={"title": title}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_health_check_response_body():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)

def test_create_author_missing_required_fields():
    r = requests.post(f"{BASE_URL}/authors", json={"name": "OnlyName"}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_category_description():
    cat = create_category()
    new_desc = "New Description"
    r = requests.patch(f"{BASE_URL}/categories/{cat['id']}", json={"description": new_desc}, timeout=TIMEOUT)
    r.raise_for_status()
    assert r.status_code == 200
    assert r.json()["description"] == new_desc

    r_get = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    r_get.raise_for_status()
    assert r_get.json()["description"] == new_desc

def test_create_review_for_nonexistent_book():
    r = requests.post(f"{BASE_URL}/books/999999/reviews", json={"rating": 5, "comment": "Ok"}, timeout=TIMEOUT)
    assert r.status_code == 404

def test_book_stock_cannot_be_negative():
    auth = create_author()
    cat = create_category()
    data = {"title": "Neg", "isbn": "1111111111111", "price": 10.0, "published_year": 2020, "stock": -5, "author_id": auth["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=data, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_authors_verify_structure():
    create_author()
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "id" in r.json()[0]
    assert "name" in r.json()[0]

def test_patch_book_partial_update():
    auth = create_author()
    cat = create_category()
    book = create_book(auth["id"], cat["id"])
    r = requests.patch(f"{BASE_URL}/books/{book['id']}", json={"stock": 99}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["stock"] == 99
    assert r.json()["title"] == book["title"]