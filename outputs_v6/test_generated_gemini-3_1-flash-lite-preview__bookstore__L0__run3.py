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

def handle_response(response):
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_valid():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_invalid_query():
    r = requests.get(f"{BASE_URL}/authors?skip=abc", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_get_author_existing():
    name = unique("Author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == name

def test_get_author_invalid_id():
    r = requests.get(f"{BASE_URL}/authors/invalid", timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_author_success():
    name = unique("Author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT).json()
    new_name = unique("NewName")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_author_invalid_year():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique()}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"born_year": 3000}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_success():
    author = handle_response(api_post("/authors", {"name": unique("author")}))
    r = api_delete(f"/authors/{author['id']}")
    assert r.status_code == 204
    r_check = api_get(f"/authors/{author['id']}")
    assert r_check.status_code == 404

def test_create_category_valid():
    name = unique("Cat")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_empty_name():
    r = requests.post(f"{BASE_URL}/categories", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique()}, timeout=TIMEOUT).json()
    new_name = unique("NewCat")
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_category_too_long():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique()}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": "a" * 51}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique()}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique()}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique()}, timeout=TIMEOUT).json()
    payload = {
        "title": unique("Book"),
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "author_id": author["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == payload["title"]

def test_create_book_missing_required():
    r = requests.post(f"{BASE_URL}/books", json={"title": "NoFields"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_pagination():
    r = requests.get(f"{BASE_URL}/books?page=1&page_size=5", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total_pages" in data

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=10", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=0", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique()}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique()}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={
        "title": unique("B"), "isbn": "1234567890", "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_get_book_not_found():
    r = api_get("/books/99999")
    assert r.status_code == 404
    assert handle_response(r) == {"detail": "Book not found"}

def test_update_book_price():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))

    r = api_put(f"/books/{book['id']}", {"price": 50.0})

    assert r.status_code == 200
    assert handle_response(r)["price"] == 50.0

def test_update_book_invalid_isbn():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": "1234567890", "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    r = api_put(f"/books/{book['id']}", {
        "title": book["title"], "isbn": "123", "price": book["price"], 
        "published_year": book["published_year"], "author_id": author["id"], "category_id": cat["id"]
    })
    assert r.status_code == 422
    assert "detail" in r.json()

def test_delete_book_success():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    r = api_delete(f"/books/{book['id']}")
    assert r.status_code == 204

    check = api_get(f"/books/{book['id']}")
    assert check.status_code == 404

def test_create_review_success():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    r = api_post(f"/books/{book['id']}/reviews", {"rating": 5, "reviewer_name": "Tester"})
    assert r.status_code == 201
    data = handle_response(r)
    assert data is not None
    assert "id" in data
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Tester"

def test_create_review_invalid_rating():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    r = api_post(f"/books/{book['id']}/reviews", {"rating": 10, "reviewer_name": "Tester"})
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_reviews_success():
    r = requests.get(f"{BASE_URL}/books/1/reviews", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_rating_success():
    r = requests.get(f"{BASE_URL}/books/1/rating", timeout=TIMEOUT)
    assert r.status_code == 200

def test_apply_discount_success():
    author = api_post("/authors", {"name": unique()}).json()
    cat = api_post("/categories", {"name": unique()}).json()
    book = api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }).json()
    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 10})
    assert r.status_code == 200
    assert handle_response(r)["discounted_price"] == 90.0

def test_apply_discount_over_limit():
    author = api_post("/authors", {"name": unique()}).json()
    cat = api_post("/categories", {"name": unique()}).json()
    book = api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }).json()
    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 60})
    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_success():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))

    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=50", timeout=30)
    data = handle_response(response)

    assert response.status_code == 200
    assert data["stock"] == 50

def test_update_stock_negative():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-5", timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_create_tag_success():
    name = unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_tags_success():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique()}, timeout=TIMEOUT).json()
    new_name = unique("NewTag")
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique()}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book_success():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": "1234567890", "price": 100, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"]
    }))
    tag = handle_response(api_post("/tags", {"name": unique()}))

    r = api_post(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    assert r.status_code == 200
    data = handle_response(r)
    assert data is not None

def test_add_tags_invalid_format():
    r = requests.post(f"{BASE_URL}/books/1/tags", json={"tag_ids": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_remove_tags_from_book_success():
    r = requests.delete(f"{BASE_URL}/books/1/tags", json={"tag_ids": [1]}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_order_success():
    author = handle_response(api_post("/authors", {"name": unique()}))
    cat = handle_response(api_post("/categories", {"name": unique()}))
    book = handle_response(api_post("/books", {
        "title": unique("B"), "isbn": "1234567890", "price": 10, "published_year": 2000, 
        "author_id": author["id"], "category_id": cat["id"], "stock": 10
    }))
    r = api_post("/orders", {
        "customer_name": "Test User", "customer_email": "test@test.com", 
        "items": [{"book_id": book["id"], "quantity": 1}]
    })
    assert r.status_code == 201
    order = handle_response(r)
    assert order is not None
    assert order["customer_name"] == "Test User"

def test_create_order_empty_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "X", "customer_email": "x@x.cz", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_invalid_email():
    response = api_post("/orders", {"customer_name": "X", "customer_email": "invalid", "items": [{"book_id": 1, "quantity": 1}]})
    assert response.status_code == 422
    data = handle_response(response)
    assert data is not None
    assert "detail" in data

def test_list_orders_success():
    r = requests.get(f"{BASE_URL}/orders", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_filtered():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_detail_success():
    data = {"item": "Test Item", "quantity": 1}
    created_order = handle_response(api_post("/orders", data))
    order_id = created_order["id"]

    r = api_get(f"/orders/{order_id}")
    assert r.status_code == 200

    body = handle_response(r)
    assert body["id"] == order_id
    assert body["item"] == "Test Item"

def test_get_order_not_found():
    r = requests.get(f"{BASE_URL}/orders/999999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_pending_order():
    r = requests.delete(f"{BASE_URL}/orders/999999", timeout=TIMEOUT)
    assert r.status_code == 422