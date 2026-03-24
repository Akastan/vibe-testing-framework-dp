import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def post_resource(endpoint, data):
    response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    if response.status_code == 204:
        return None
    return response.json()

def get_resource(endpoint):
    response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
    response.raise_for_status()
    if response.status_code == 204:
        return None
    return response.json()

def put_resource(endpoint, data):
    response = requests.put(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT)
    response.raise_for_status()
    if response.status_code == 204:
        return None
    return response.json()

def delete_resource(endpoint):
    response = requests.delete(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
    response.raise_for_status()
    return response


def test_check_health_status():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_valid_author():
    name = unique("Author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1990}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert "id" in data

def test_create_invalid_author_empty_name():
    payload = {"name": ""}
    r = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert r.status_code == 422
    assert "detail" in r.json()

def test_list_authors_default_pagination():
    r = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_list_authors_custom_limit():
    r = requests.get(f"{BASE_URL}/authors", params={"limit": 5}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert len(r.json()) <= 5

def test_get_existing_author():
    name = unique("Author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "b", "born_year": 1990}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]

def test_get_nonexistent_author():
    try:
        get_resource("/authors/99999")
    except requests.exceptions.HTTPError as e:
        assert e.response.status_code == 404
        assert "detail" in e.response.json()

def test_update_author_success():
    name = unique("Author")
    author = requests.post(f"{BASE_URL}/authors", json={"name": name, "bio": "old", "born_year": 1990}, timeout=TIMEOUT).json()
    new_name = unique("Updated")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_author_success():
    name = unique("Author")
    author = post_resource("/authors", {"name": name, "bio": "d", "born_year": 1990})
    r = delete_resource(f"/authors/{author['id']}")
    assert r.status_code == 204

    import requests
    check = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert check.status_code == 404

def test_list_categories_success():
    r = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_create_category_success():
    name = unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "desc"}, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["name"] == name

def test_create_category_invalid_input():
    r = requests.post(f"{BASE_URL}/categories", json={"description": "no name"}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_category_success():
    name = unique("Cat")
    cat = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "d"}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == cat["id"]

def test_update_category_name():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    new_name = unique("NewName")
    r = requests.put(f"{BASE_URL}/categories/{cat['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["name"] == new_name

def test_delete_category_success():
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/categories/{cat['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_create_book_success():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("A"), "bio": "b", "born_year": 1990}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    payload = {"title": unique("Book"), "isbn": "1234567890123", "price": 100, "published_year": 2020, "author_id": author["id"], "category_id": cat["id"]}
    r = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["title"] == payload["title"]

def test_create_book_negative_price():
    r = requests.post(f"{BASE_URL}/books", json={"title": "test", "price": -10}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_book_invalid_year():
    r = requests.post(f"{BASE_URL}/books", json={"title": "test", "published_year": 500}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_books_default():
    r = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "items" in r.json()

def test_list_books_filter_price():
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 0}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_list_books_page_overflow():
    response = requests.get(f"{BASE_URL}/books", params={"page": 9999}, timeout=TIMEOUT)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_get_book_detail():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    r = get_resource(f"/books/{book['id']}")
    assert r["id"] == book["id"]
    assert r["title"] == "T"

def test_get_nonexistent_book():
    response = requests.get(f"{BASE_URL}/books/99999", timeout=TIMEOUT)
    assert response.status_code == 404
    assert "detail" in response.json()

def test_update_book_title():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "Old", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    r = put_resource(f"/books/{book['id']}", {"title": "New", "isbn": book["isbn"], "price": book["price"], "published_year": book["published_year"], "author_id": author["id"], "category_id": cat["id"]})

    assert r["title"] == "New"

    updated_book = get_resource(f"/books/{book['id']}")
    assert updated_book["title"] == "New"

def test_delete_book_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    r = delete_resource(f"/books/{book['id']}")
    assert r.status_code == 204

def test_create_review_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 5, "reviewer_name": "Fan"}, timeout=TIMEOUT)

    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Fan"
    assert data["book_id"] == book["id"]

def test_create_review_invalid_rating():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={"rating": 10, "reviewer_name": "Fan"}, timeout=TIMEOUT)

    assert response.status_code == 422
    assert "detail" in response.json()

def test_list_reviews_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    reviews = get_resource(f"/books/{book['id']}/reviews")
    assert isinstance(reviews, list)

def test_get_rating_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": "1234567890123", "price": 10, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    response = get_resource(f"/books/{book['id']}/rating")
    assert response is not None
    assert "average_rating" in response

def test_apply_discount_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20}, timeout=TIMEOUT)

    assert r.status_code == 200
    assert r.json()["discounted_price"] == 80.0

def test_apply_discount_too_high():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": "1234567890123", "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 60}, timeout=TIMEOUT)

    assert response.status_code == 422
    assert "detail" in response.json()

def test_update_stock_increase():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 5}, timeout=TIMEOUT)
    assert response.status_code == 200

    updated_book = get_resource(f"/books/{book['id']}")
    assert updated_book["stock"] == 5

def test_list_tags_all():
    r = requests.get(f"{BASE_URL}/tags", timeout=TIMEOUT)
    assert r.status_code == 200

def test_create_tag_unique():
    r = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT)
    assert r.status_code == 201

def test_create_tag_too_long():
    r = requests.post(f"{BASE_URL}/tags", json={"name": "a" * 31}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_get_tag_detail():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_tag_name():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.put(f"{BASE_URL}/tags/{tag['id']}", json={"name": unique("NewTag")}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_delete_tag_permanent():
    tag = requests.post(f"{BASE_URL}/tags", json={"name": unique("Tag")}, timeout=TIMEOUT).json()
    r = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert r.status_code == 204

def test_add_tags_to_book():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    tag = post_resource("/tags", {"name": unique("Tag")})

    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json() is not None

def test_remove_tags_from_book():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    tag = post_resource("/tags", {"name": unique("Tag")})

    post_resource(f"/books/{book['id']}/tags", {"tag_ids": [tag["id"]]})

    response = delete_resource(f"/books/{book['id']}/tags?tag_ids={tag['id']}")
    assert response.status_code == 200

    tags = get_resource(f"/books/{book['id']}/tags")
    assert all(t["id"] != tag["id"] for t in tags)

def test_create_order_success():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})

    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT)

    assert r.status_code == 201
    data = r.json()
    assert "total_price" in data
    assert data["total_price"] == 100

def test_create_order_no_items():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_create_order_invalid_email():
    r = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "bad", "items": []}, timeout=TIMEOUT)
    assert r.status_code == 422

def test_list_orders_page_1():
    r = requests.get(f"{BASE_URL}/orders", params={"page": 1}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_get_order_detail():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": "1234567890123", "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    order = post_resource("/orders", {"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]})

    order_detail = get_resource(f"/orders/{order['id']}")

    assert order_detail["id"] == order["id"]
    assert order_detail["customer_name"] == "C"
    assert len(order_detail["items"]) == 1
    assert order_detail["items"][0]["book_id"] == book["id"]

def test_delete_pending_order():
    author = post_resource("/authors", {"name": unique("A"), "bio": "b", "born_year": 1990})
    cat = post_resource("/categories", {"name": unique("C"), "description": "d"})
    book = post_resource("/books", {"title": "T", "isbn": unique("123"), "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]})
    order = post_resource("/orders", {"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]})
    r = delete_resource(f"/orders/{order['id']}")
    assert r.status_code == 204

def test_delete_invalid_order_status():
    r = requests.delete(f"{BASE_URL}/orders/9999", timeout=TIMEOUT)
    assert r.status_code == 422

def test_update_order_to_shipped():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("A"), "bio": "b", "born_year": 1990}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890123", "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "shipped"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_order_to_cancelled():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("A"), "bio": "b", "born_year": 1990}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890123", "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
    assert r.status_code == 200

def test_update_order_invalid_transition():
    author = requests.post(f"{BASE_URL}/authors", json={"name": unique("A"), "bio": "b", "born_year": 1990}, timeout=TIMEOUT).json()
    cat = requests.post(f"{BASE_URL}/categories", json={"name": unique("C"), "description": "d"}, timeout=TIMEOUT).json()
    book = requests.post(f"{BASE_URL}/books", json={"title": "T", "isbn": "1234567890123", "price": 100, "published_year": 2000, "author_id": author["id"], "category_id": cat["id"]}, timeout=TIMEOUT).json()
    order = requests.post(f"{BASE_URL}/orders", json={"customer_name": "C", "customer_email": "a@b.com", "items": [{"book_id": book["id"], "quantity": 1}]}, timeout=TIMEOUT).json()
    r = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json={"status": "invalid_status"}, timeout=TIMEOUT)
    assert r.status_code == 422