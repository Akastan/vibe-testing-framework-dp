import uuid
import time
import requests
import io

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/authors", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category():
    name = unique("category")
    payload = {"name": name, "description": "Test category"}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/categories", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag():
    name = unique("tag")
    payload = {"name": name}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/tags", json=payload, headers=headers, timeout=30)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()


def test_health_check_returns_ok():
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_create_author_success():
    name = unique("author")
    payload = {"name": name, "bio": "Test bio", "born_year": 1980}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name
    assert data["bio"] == "Test bio"
    assert data["born_year"] == 1980

def test_create_author_missing_name_validation():
    payload = {"bio": "Test bio"}
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=30)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_get_author_by_id_success():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_author_not_found():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=30)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_update_author_with_etag_match():
    author = create_author()
    get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    etag = get_response.headers.get("ETag")
    payload = {"name": unique("updated")}
    headers = {"If-Match": etag}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, headers=headers, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]

def test_update_author_etag_mismatch():
    author = create_author()
    payload = {"name": unique("updated")}
    headers = {"If-Match": '"wrongetag"'}
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json=payload, headers=headers, timeout=30)
    assert response.status_code == 412
    data = response.json()
    assert "detail" in data

def test_delete_author_without_books():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert response.status_code == 204
    assert response.text == ""
    get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=30)
    assert get_response.status_code == 404

def test_delete_author_with_books_conflict():
    book = create_book()
    author_id = book["author_id"]
    response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_create_book_success():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 25.50,
        "published_year": 2021,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] == isbn
    assert data["title"] == payload["title"]

def test_create_book_duplicate_isbn():
    book = create_book()
    author = create_author()
    category = create_category()
    payload = {
        "title": unique("book"),
        "isbn": book["isbn"],
        "price": 30.0,
        "published_year": 2022,
        "stock": 3,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_get_book_success():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book_gone():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert get_response.status_code == 410
    data = get_response.json()
    assert "detail" in data

def test_soft_delete_book_success():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert response.status_code == 204
    assert response.text == ""
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert get_response.status_code == 410

def test_delete_already_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    second_delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert second_delete_response.status_code == 410
    data = second_delete_response.json()
    assert "detail" in data

def test_restore_soft_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert restore_response.status_code == 200
    data = restore_response.json()
    assert data["id"] == book["id"]
    get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert get_response.status_code == 200

def test_restore_not_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_apply_discount_to_old_book():
    book = create_book()
    payload = {"discount_percent": 10.0}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "discounted_price" in data
    expected = round(book["price"] * (1 - 10.0 / 100), 2)
    assert data["discounted_price"] == expected

def test_apply_discount_to_new_book():
    author = create_author()
    category = create_category()
    isbn = f"978{uuid.uuid4().hex[:9]}"
    payload = {
        "title": unique("book"),
        "isbn": isbn,
        "price": 20.0,
        "published_year": 2026,
        "stock": 5,
        "author_id": author["id"],
        "category_id": category["id"]
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=30)
    assert response.status_code == 201
    book = response.json()
    discount_payload = {"discount_percent": 5.0}
    discount_response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=discount_payload, timeout=30)
    assert discount_response.status_code == 400
    data = discount_response.json()
    assert "detail" in data

def test_increase_stock_success():
    book = create_book()
    original_stock = book["stock"]
    increase = 5
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={increase}", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == original_stock + increase

def test_decrease_stock_below_zero():
    book = create_book()
    decrease = book["stock"] + 10
    response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity={-decrease}", timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

def test_upload_valid_cover_image():
    book = create_book()
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    files = {'file': ('cover.jpg', img_byte_arr, 'image/jpeg')}
    headers = {"X-API-Key": API_KEY}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, headers=headers, timeout=30)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    data = response.json()
    assert "book_id" in data
    assert data["book_id"] == book["id"]
    assert "filename" in data

def test_upload_cover_file_too_large():
    book = create_book()
    large_data = b'x' * (2 * 1024 * 1024 + 1)
    files = {'file': ('large.jpg', large_data, 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=30)
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data

def test_create_review_for_book():
    book = create_book()
    payload = {
        "rating": 5,
        "comment": "Great book!",
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5

def test_create_review_for_deleted_book():
    book = create_book()
    delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert delete_response.status_code == 204
    payload = {
        "rating": 3,
        "comment": "Not bad",
        "reviewer_name": unique("reviewer")
    }
    response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=30)
    assert response.status_code == 410
    data = response.json()
    assert "detail" in data

def test_create_tag_success():
    name = unique("tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_tag_duplicate_name():
    tag = create_tag()
    payload = {"name": tag["name"]}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=30)
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data

def test_add_tags_to_book():
    book = create_book()
    tag1 = create_tag()
    tag2 = create_tag()
    payload = {"tag_ids": [tag1["id"], tag2["id"]]}
    response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    tag_ids = [t["id"] for t in data["tags"]]
    assert tag1["id"] in tag_ids
    assert tag2["id"] in tag_ids

def test_create_order_with_sufficient_stock():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": 2}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["customer_name"] == payload["customer_name"]
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == book["id"]
    assert data["items"][0]["quantity"] == 2
    get_book_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    updated_book = get_book_response.json()
    assert updated_book["stock"] == book["stock"] - 2

def test_create_order_insufficient_stock():
    book = create_book()
    payload = {
        "customer_name": unique("customer"),
        "customer_email": f"{unique('email')}@example.com",
        "items": [
            {"book_id": book["id"], "quantity": book["stock"] + 10}
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=30)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data