import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def api_get(endpoint):
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    return requests.get(url, timeout=TIMEOUT)

def api_post(endpoint, data):
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    return requests.post(url, json=data, timeout=TIMEOUT)

def api_put(endpoint, data):
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    return requests.put(url, json=data, timeout=TIMEOUT)

def api_delete(endpoint):
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    return requests.delete(url, timeout=TIMEOUT)

def create_resource(endpoint, data=None):
    payload = data if data is not None else {"name": unique("item")}
    response = api_post(endpoint, payload)
    response.raise_for_status()
    return response.json()

def delete_resource(endpoint, resource_id):
    full_path = f"{endpoint.rstrip('/')}/{resource_id}"
    response = api_delete(full_path)
    if response.status_code != 204:
        response.raise_for_status()
    return response


def test_health_check_success():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_author_success():
    payload = {"name": unique("Author")}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == payload["name"]

def test_create_author_invalid_data():
    r = requests.post(f"{BASE_URL}/authors", json={"name": ""}, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_pagination():
    r = requests.get(f"{BASE_URL}/authors?skip=0&limit=1", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_author_existing():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_author_non_existent():
    r = api_get("/authors/999999")
    assert r.status_code == 404
    assert "detail" in r.json()

def test_update_author_success():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT).json()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_update_author_invalid_year():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("Author")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"born_year": -5}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_delete_author_success():
    author = create_resource("/authors", {"name": unique("Author")})
    r = api_delete(f"/authors/{author['id']}")
    assert r.status_code == 204
    get_res = api_get(f"/authors/{author['id']}")
    assert get_res.status_code == 404

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_category_success():
    payload = {"name": unique("Cat")}
    r = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == payload["name"]

def test_get_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat["id"]

def test_update_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT).json()
    new_name = unique("CatUpd")
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("Cat")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    payload = {
        "title": unique("Book"),
        "isbn": "1234567890123",
        "price": 100.0,
        "published_year": 2020,
        "author_id": auth["id"],
        "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert "id" in r.json()

def test_create_book_missing_required():
    r = requests.post(f"{BASE_URL}/books", json={"title": "Incomplete"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_negative_price():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    payload = {
        "title": "Bad Price", "isbn": "1234567890", "price": -10, "published_year": 2000,
        "author_id": auth["id"], "category_id": cat["id"]
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_all():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books?min_price=0", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_invalid_page():
    r = requests.get(f"{BASE_URL}/books?page=-1", timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_book_detail():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "1234567890", "price": 10, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]

def test_update_book_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    r = api_put(f"/books/{book['id']}", {"price": 50})
    assert r.status_code == 200
    assert r.json()["price"] == 50

def test_delete_book_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("123"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    response = delete_resource("/books", book["id"])
    assert response.status_code == 204

    check_response = api_get(f"/books/{book['id']}")
    assert check_response.status_code == 404

def test_create_review_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("Book"), 
        "isbn": unique("ISBN"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    r = api_post(f"/books/{book['id']}/reviews", {"rating": 5, "reviewer_name": "Tester"})

    assert r.status_code == 201
    assert "id" in r.json()
    assert r.json()["rating"] == 5

def test_create_review_out_of_range():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    response = api_post(f"/books/{book['id']}/reviews", {"rating": 6, "reviewer_name": "Tester"})

    assert response.status_code == 422
    assert "detail" in response.json()

def test_list_reviews_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("Book"), 
        "isbn": unique("ISBN"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    r = api_get(f"/books/{book['id']}/reviews")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_get_book_rating_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 10, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    api_post(f"/books/{book['id']}/rating", {"score": 5})

    r = api_get(f"/books/{book['id']}/rating")
    assert r.status_code == 200
    assert "rating" in r.json()
    assert isinstance(r.json()["rating"], (int, float))

def test_apply_discount_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })
    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 10})
    assert r.status_code == 200
    assert "discounted_price" in r.json()
    assert r.json()["discounted_price"] == 90

def test_apply_discount_too_high():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    r = api_post(f"/books/{book['id']}/discount", {"discount_percent": 60})

    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_stock_increase():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("Book"), 
        "isbn": unique("123"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    url = f"{BASE_URL.rstrip('/')}/books/{book['id']}/stock?quantity=5"
    r = requests.patch(url, timeout=TIMEOUT)

    assert r.status_code == 200
    assert r.json()["stock"] == 5

def test_update_stock_negative():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": unique("B"), 
        "isbn": unique("I"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })

    r = requests.patch(f"{BASE_URL.rstrip('/')}/books/{book['id']}/stock?quantity=-1", timeout=TIMEOUT)

    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_tags_success():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_tag_success():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_get_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("New")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag_success():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {
        "title": "B", 
        "isbn": unique("ISBN"), 
        "price": 100, 
        "published_year": 2000, 
        "author_id": auth["id"], 
        "category_id": cat["id"]
    })
    tag = create_resource("/tags", {"name": unique("T")})

    r = api_post(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert any(t["id"] == tag["id"] for t in r.json().get("tags", []))

def test_remove_tags_from_book_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {"title": "B", "isbn": unique("isbn"), "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]})
    tag = create_resource("/tags", {"name": unique("T")})

    api_post(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    response = api_delete(f"/books/{book['id']}/tags?tag_ids={tag['id']}")
    assert response.status_code == 200
    assert response.json() == {"id": book["id"], "tags": []}

def test_create_order_success():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {"title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]})

    response = api_post("/orders", {"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    assert response.status_code == 201
    order = response.json()
    assert "id" in order
    assert order["customer_name"] == "C"

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_success():
    r = requests.get(f"{BASE_URL}/orders", timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_orders_by_status():
    r = requests.get(f"{BASE_URL}/orders?status=pending", timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_detail():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {"title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]})
    order = create_resource("/orders", {"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    r = api_get(f"/orders/{order['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]
    assert r.json()["customer_name"] == "C"

def test_delete_pending_order():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {"title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]})
    order = create_resource("/orders", {"customer_name": "C", "customer_email": f"{unique('e')}@e.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    r = delete_resource("/orders", order["id"])
    assert r.status_code == 204

def test_delete_confirmed_order_fail():
    auth = create_resource("/authors", {"name": unique("A")})
    cat = create_resource("/categories", {"name": unique("C")})
    book = create_resource("/books", {"title": unique("B"), "isbn": unique("I"), "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]})
    order = create_resource("/orders", {"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    api_post(f"/orders/{order['id']}/status", {"status": "confirmed"})

    r = api_delete(f"/orders/{order['id']}")

    assert r.status_code == 422
    assert "detail" in r.json()

def test_update_status_success():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "1234567890", "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_status_invalid():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "1234567890", "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "garbage"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_status_logic_flow():
    auth = requests.post(f"{BASE_URL}/authors", json={"name": unique("A")}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C")}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "B", "isbn": "1234567890", "price": 100, "published_year": 2000, "author_id": auth["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "e@e.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "delivered"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_login_rate_limit_exceeded():
    for _ in range(10):
        requests.post(f"{BASE_URL}/auth/login", json={"username": "a", "password": "b"}, timeout=TIMEOUT)
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "a", "password": "b"}, timeout=TIMEOUT)
    assert r.status_code == 429