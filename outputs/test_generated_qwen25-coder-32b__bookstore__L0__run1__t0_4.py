import requests
import uuid

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

BASE_URL = "http://localhost:8000"
timeout = 30

def create_author(name):
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"
    return data["id"]

def update_author(author_id, name):
    response = requests.put(f"{BASE_URL}/authors/{author_id}", json={"name": name}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"

def create_category(name):
    response = requests.post(f"{BASE_URL}/categories", json={"name": unique(name)}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"
    return data["id"]

def update_category(category_id, name):
    response = requests.put(f"{BASE_URL}/categories/{category_id}", json={"name": unique(name)}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"

def create_book(title, author_id, category_id, isbn, price, stock):
    response = requests.post(f"{BASE_URL}/books", json={
        "title": title,
        "author_id": author_id,
        "category_id": category_id,
        "isbn": isbn,
        "price": price,
        "stock": stock
    }, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"
    return data["id"]

def update_book(book_id, title):
    response = requests.put(f"{BASE_URL}/books/{book_id}", json={"title": title}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"

def create_review(book_id, rating, comment):
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={
        "rating": rating,
        "comment": comment
    }, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"

def apply_discount(book_id, percentage):
    response = requests.patch(f"{BASE_URL}/books/{book_id}/discount", json={"percentage": percentage}, timeout=timeout)
    data = response.json()
    assert "discounted_price" in data, f"Response does not contain 'discounted_price': {data}"

def create_tag(name):
    response = requests.post(f"{BASE_URL}/tags", json={"name": unique(name)}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"
    return data["id"]

def update_tag(tag_id, name):
    response = requests.put(f"{BASE_URL}/tags/{tag_id}", json={"name": unique(name)}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"

def create_order(book_id, quantity):
    response = requests.post(f"{BASE_URL}/orders", json={
        "book_id": book_id,
        "quantity": quantity
    }, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"
    return data["id"]

def update_order_status(order_id, status):
    response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": status}, timeout=timeout)
    data = response.json()
    assert "id" in data, f"Response does not contain 'id': {data}"


def test_create_author_happy_path():
    name = unique("author")
    author_id = create_author(name)

def test_update_author_edge_case_invalid_born_year():
    name = unique("author")
    author_id = create_author(name)
    response = requests.put(f"{BASE_URL}/authors/{author_id}", json={"name": name, "born_year": 3000}, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_category_happy_path():
    name = unique("category")
    category_id = create_category(name)

def test_create_category_edge_case_long_name():
    long_name = "a" * 51
    response = requests.post(f"{BASE_URL}/categories", json={"name": long_name}, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_book_happy_path():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=timeout)
    data = response.json()
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    assert "id" in data and data["id"] == book_id, f"Response does not contain correct 'id': {data}"
    assert "title" in data and data["author_id"] == author_id and data["category_id"] == category_id and data["isbn"] == isbn and data["price"] == 19.99 and data["stock"] == 10, f"Response does not contain correct book details: {data}"

def test_create_book_edge_case_invalid_isbn():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    response = requests.post(f"{BASE_URL}/books", json={
        "title": unique("book"),
        "author_id": author_id,
        "category_id": category_id,
        "isbn": 12345678901234,  # Invalid ISBN
        "price": 19.99,
        "stock": 10
    }, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_review_happy_path():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    review_id = create_review(book_id, 5, "Great book!")
    response = requests.get(f"{BASE_URL}/books/{book_id}/reviews", timeout=timeout)
    data = response.json()
    assert any(review["id"] == review_id for review in data), f"Review with id {review_id} not found in reviews: {data}"
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

def test_create_review_edge_case_invalid_rating():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json={
        "rating": 6,
        "comment": "Invalid rating"
    }, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_happy_path():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    response = apply_discount(book_id, 20)
    assert "discounted_price" in response, f"Response does not contain 'discounted_price': {response}"
    expected_discounted_price = 19.99 * (1 - 20 / 100)
    assert abs(response["discounted_price"] - expected_discounted_price) < 0.01, f"Incorrect discounted price: {response['discounted_price']}"

def test_apply_discount_edge_case_invalid_percentage():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    response = requests.patch(f"{BASE_URL}/books/{book_id}/discount", json={"percentage": 120}, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_create_tag_happy_path():
    name = unique("tag")
    tag_id = create_tag(name)

def test_create_tag_edge_case_long_name():
    long_name = "a" * 31
    response = requests.post(f"{BASE_URL}/tags", json={"name": long_name}, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_update_tag_happy_path():
    name = unique("tag")
    tag_id = create_tag(name)
    update_tag(tag_id, unique("updated_tag"))

def test_update_order_status_happy_path():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    order_id = create_order(book_id, 2)
    response = update_order_status(order_id, "completed")
    assert response["status"] == "completed", f"Expected status 'completed', got {response['status']}"

def test_update_order_status_edge_case_invalid_status():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    order_id = create_order(book_id, 2)
    response = requests.patch(f"{base_url}/orders/{order_id}/status", json={"status": "invalid_status"}, timeout=timeout)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_list_reviews_happy_path():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    isbn = unique("isbn")
    book_id = create_book(unique("book"), author_id, category_id, isbn, 19.99, 10)
    review_id = create_review(book_id, 5, "Great book!")
    response = requests.get(f"{base_url}/books/{book_id}/reviews", timeout=timeout)
    data = response.json()
    assert isinstance(data, list)


def test_list_authors_happy_path():
    author_id = create_author(unique("author"))
    response = requests.get(f"{base_url}/authors", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(author["id"] == author_id for author in data)

def test_get_author_happy_path():
    author_id = create_author(unique("author"))
    response = requests.get(f"{base_url}/authors/{author_id}", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id

def test_delete_author_happy_path():
    author_id = create_author(unique("author"))
    response = requests.delete(f"{base_url}/authors/{author_id}", timeout=timeout)
    assert response.status_code == 204

def test_list_categories_happy_path():
    category_id = create_category(unique("category"))
    response = requests.get(f"{base_url}/categories", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(category["id"] == category_id for category in data)

def test_get_category_happy_path():
    category_id = create_category(unique("category"))
    response = requests.get(f"{base_url}/categories/{category_id}", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category_id

def test_delete_category_happy_path():
    category_id = create_category(unique("category"))
    response = requests.delete(f"{base_url}/categories/{category_id}", timeout=timeout)
    assert response.status_code == 204

def test_update_author_happy_path():
    author_id = create_author(unique("author"))
    new_name = unique("new_author")
    update_author(author_id, new_name)
    response = requests.get(f"{base_url}/authors/{author_id}", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_category_happy_path():
    category_id = create_category(unique("category"))
    new_name = unique("new_category")
    update_category(category_id, new_name)
    response = requests.get(f"{base_url}/categories/{category_id}", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_create_book_edge_case_no_stock():
    author_id = create_author(unique("author"))
    category_id = create_category(unique("category"))
    book_id = create_book(unique("book"), author_id, category_id, "978-3-16-148410-0", 29.99, 0)
    response = requests.get(f"{base_url}/books/{book_id}", timeout=timeout)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == 0