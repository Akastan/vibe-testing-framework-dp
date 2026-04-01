import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def api_get(endpoint):
    response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
    return response

def api_post(endpoint, data):
    response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT)
    return response

def api_put(endpoint, data):
    response = requests.put(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT)
    return response

def api_delete(endpoint):
    response = requests.delete(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
    return response

def create_resource(endpoint, data=None):
    payload = data or {"name": unique("item")}
    response = api_post(endpoint, payload)
    response.raise_for_status()
    return response.json()

def delete_resource(endpoint, resource_id):
    response = api_delete(f"{endpoint}/{resource_id}")
    if response.status_code != 204:
        response.raise_for_status()
    return response


def test_check_api_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_invalid_author_missing_name():
    payload = {"bio": "No name provided"}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_existing_author():
    name = unique("author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == name

def test_update_author_name():
    name = unique("author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    new_name = unique("updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_author_success():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("del")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 204
    check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert check.status_code == 404

def test_create_category_valid():
    name = unique("cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_too_long_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": "a" * 51}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_valid():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("auth")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("cat")}, timeout=TIMEOUT).json()
    payload = {
        "title": unique("book"),
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == payload["title"]

def test_create_book_negative_price():
    r = requests.post(f"{BASE_URL}/books", json={"price": -10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_with_filters():
    r = requests.get(f"{BASE_URL}/books?min_price=0&max_price=1000", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page_size():
    r = requests.get(f"{BASE_URL}/books?page_size=999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("a")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("c")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": unique("b"), "isbn": "1234567890", "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_update_book_stock():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })
    r = api_put(f"/books/{book['id']}", {"stock": 50})
    assert r.status_code == 200
    assert r.json()["stock"] == 50

def test_delete_book_success():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })

    response = delete_resource("/books", book["id"])
    assert response.status_code == 204

    get_response = api_get(f"/books/{book['id']}")
    assert get_response.status_code == 404

def test_add_review_valid():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })
    r = api_post(f"/books/{book['id']}/reviews", {"rating": 5, "reviewer_name": "Tester"})
    assert r.status_code == 201
    assert r.json()["rating"] == 5
    assert r.json()["reviewer_name"] == "Tester"

def test_add_review_invalid_rating():
    r = requests.post(f"{BASE_URL}/books/99999/reviews", json={"rating": 10, "reviewer_name": "Bad"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_average_rating():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })

    r = api_get(f"/books/{book['id']}/rating")
    assert r.status_code == 200
    assert "average_rating" in r.json()

def test_apply_valid_discount():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })
    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 20})
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_excessive_discount():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })

    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 60})

    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_quantity():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })

    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)

    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_create_tag_valid():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_add_tags_to_book_success():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {
        "title": unique("b"), 
        "isbn": unique("isbn"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": author["id"], 
        "category_id": cat["id"]
    })
    tag = create_resource("/tags", {"name": unique("t")})

    r = api_post(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert any(t["id"] == tag["id"] for t in data["tags"])

def test_remove_tags_from_book_success():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {"title": unique("b"), "isbn": unique("isbn"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    tag = create_resource("/tags", {"name": unique("t")})

    api_post(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    r = api_delete(f"/books/{book['id']}/tags/{tag['id']}")
    assert r.status_code == 200

    updated_book = api_get(f"/books/{book['id']}").json()
    assert tag["id"] not in [t["id"] for t in updated_book.get("tags", [])]

def test_create_order_success():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {"title": unique("b"), "isbn": unique("isbn"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    payload = {
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "items": [{"book_id": book["id"], "quantity": 1}]
    }

    r = api_post("/orders", payload)
    assert r.status_code == 201
    data = r.json()
    assert data["customer_name"] == "Test User"
    assert data["customer_email"] == "test@example.com"
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    assert data["items"][0]["quantity"] == 1

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "A", "customer_email": "a@a.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_by_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_delete_pending_order():
    author = create_resource("/authors", {"name": unique("a")})
    cat = create_resource("/categories", {"name": unique("c")})
    book = create_resource("/books", {"title": unique("b"), "isbn": unique("isbn"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    order = create_resource("/orders", {"customer_name": "Test", "customer_email": "t@t.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    r = api_delete(f"/orders/{order['id']}")
    assert r.status_code == 204

    check = api_get(f"/orders/{order['id']}")
    assert check.status_code == 404
    assert check.json().get("detail") is not None