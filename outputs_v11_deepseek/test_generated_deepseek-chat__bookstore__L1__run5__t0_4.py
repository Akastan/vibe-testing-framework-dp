import pytest
import requests
import uuid
import time
import io
from pathlib import Path

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

class TestBookstoreAPI:
    def test_health_check_returns_200(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200

    def test_create_author_success(self):
        payload = {"name": unique("author"), "bio": "Test bio"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["bio"] == payload["bio"]

    def test_create_author_missing_name_422(self):
        payload = {"bio": "Test bio"}
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_get_author_by_id_success(self):
        payload = {"name": unique("author")}
        create_resp = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        author_id = create_resp.json()["id"]
        response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author_id
        assert data["name"] == payload["name"]

    def test_get_author_not_found_404(self):
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_author_without_books_204(self):
        payload = {"name": unique("author")}
        create_resp = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        author_id = create_resp.json()["id"]
        response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response.status_code == 204
        get_resp = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert get_resp.status_code == 404

    def test_delete_author_with_books_409(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 19.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        response = requests.delete(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_book_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 25.50,
            "published_year": 2021,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 10
        }
        response = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == book_payload["title"]
        assert data["isbn"] == book_payload["isbn"]
        assert data["price"] == book_payload["price"]

    def test_create_book_duplicate_isbn_409(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        isbn = unique("isbn")
        book_payload1 = {
            "title": unique("book"),
            "isbn": isbn,
            "price": 20.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        book_resp1 = requests.post(f"{BASE_URL}/books", json=book_payload1, timeout=TIMEOUT)
        assert book_resp1.status_code == 201
        book_payload2 = {
            "title": unique("book2"),
            "isbn": isbn,
            "price": 30.0,
            "published_year": 2021,
            "author_id": author_id,
            "category_id": category_id
        }
        response = requests.post(f"{BASE_URL}/books", json=book_payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_get_book_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 15.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == book_payload["title"]

    def test_get_soft_deleted_book_410(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 12.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        delete_resp = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert delete_resp.status_code == 204
        response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data

    def test_soft_delete_book_204(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 9.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert response.status_code == 204
        get_resp = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert get_resp.status_code == 410

    def test_restore_soft_deleted_book_200(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 29.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        delete_resp = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert delete_resp.status_code == 204
        restore_resp = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert restore_resp.status_code == 200
        data = restore_resp.json()
        assert data["id"] == book_id
        get_resp = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert get_resp.status_code == 200

    def test_restore_not_deleted_book_400(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 14.99,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        response = requests.post(f"{BASE_URL}/books/{book_id}/restore", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_apply_discount_to_old_book_200(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 100.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        discount_payload = {"discount_percent": 10.0}
        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=discount_payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert data["original_price"] == 100.0
        assert data["discount_percent"] == 10.0
        assert data["discounted_price"] == 90.0

    def test_apply_discount_to_new_book_400(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        current_year = 2026
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 50.0,
            "published_year": current_year,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        discount_payload = {"discount_percent": 5.0}
        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json=discount_payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_increase_stock_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 20.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 5
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=3", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 8

    def test_decrease_stock_below_zero_400(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 15.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 2
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock?quantity=-5", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_upload_cover_jpeg_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 18.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        files = {"file": ("cover.jpg", io.BytesIO(b"fake jpeg data"), "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert data["book_id"] == book_id
        assert "filename" in data

    def test_upload_cover_too_large_413(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 22.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        large_data = b"x" * (2 * 1024 * 1024 + 1)
        files = {"file": ("large.jpg", io.BytesIO(large_data), "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book_id}/cover", files=files, timeout=TIMEOUT)
        assert response.status_code == 413
        data = response.json()
        assert "detail" in data

    def test_create_review_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 30.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        review_payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("reviewer")
        }
        response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=review_payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["book_id"] == book_id
        assert data["rating"] == 5
        assert data["reviewer_name"] == review_payload["reviewer_name"]

    def test_create_review_for_deleted_book_410(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 25.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]
        delete_resp = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert delete_resp.status_code == 204
        review_payload = {
            "rating": 4,
            "reviewer_name": unique("reviewer")
        }
        response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=review_payload, timeout=TIMEOUT)
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data

    def test_create_tag_success(self):
        payload = {"name": unique("tag")}
        response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == payload["name"]

    def test_create_tag_duplicate_name_409(self):
        name = unique("tag")
        payload1 = {"name": name}
        resp1 = requests.post(f"{BASE_URL}/tags", json=payload1, timeout=TIMEOUT)
        assert resp1.status_code == 201
        payload2 = {"name": name}
        response = requests.post(f"{BASE_URL}/tags", json=payload2, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_add_tags_to_book_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 35.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        book_id = book_resp.json()["id"]
        tag_payload1 = {"name": unique("tag")}
        tag_resp1 = requests.post(f"{BASE_URL}/tags", json=tag_payload1, timeout=TIMEOUT)
        assert tag_resp1.status_code == 201
        tag_id1 = tag_resp1.json()["id"]
        tag_payload2 = {"name": unique("tag2")}
        tag_resp2 = requests.post(f"{BASE_URL}/tags", json=tag_payload2, timeout=TIMEOUT)
        assert tag_resp2.status_code == 201
        tag_id2 = tag_resp2.json()["id"]
        add_payload = {"tag_ids": [tag_id1, tag_id2]}
        response = requests.post(f"{BASE_URL}/books/{book_id}/tags", json=add_payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) == 2
        tag_ids = {t["id"] for t in data["tags"]}
        assert tag_id1 in tag_ids
        assert tag_id2 in tag_ids

    def test_create_order_success(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 40.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 10
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        book_id = book_resp.json()["id"]
        order_payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique('email')}@example.com",
            "items": [{"book_id": book_id, "quantity": 2}]
        }
        response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["customer_name"] == order_payload["customer_name"]
        assert data["total_price"] == 80.0
        assert len(data["items"]) == 1
        book_check = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        book_data = book_check.json()
        assert book_data["stock"] == 8

    def test_create_order_insufficient_stock_400(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 20.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 1
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        book_id = book_resp.json()["id"]
        order_payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique('email')}@example.com",
            "items": [{"book_id": book_id, "quantity": 5}]
        }
        response = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_update_order_status_valid_transition(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 30.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 5
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        book_id = book_resp.json()["id"]
        order_payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique('email')}@example.com",
            "items": [{"book_id": book_id, "quantity": 1}]
        }
        order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]
        status_payload = {"status": "confirmed"}
        response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=status_payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    def test_update_order_status_invalid_transition_400(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201
        author_id = author_resp.json()["id"]
        category_payload = {"name": unique("category")}
        category_resp = requests.post(f"{BASE_URL}/categories", json=category_payload, timeout=TIMEOUT)
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]
        book_payload = {
            "title": unique("book"),
            "isbn": unique("isbn"),
            "price": 25.0,
            "published_year": 2020,
            "author_id": author_id,
            "category_id": category_id,
            "stock": 3
        }
        book_resp = requests.post(f"{BASE_URL}/books", json=book_payload, timeout=TIMEOUT)
        assert book_resp.status_code == 201
        book_id = book_resp.json()["id"]
        order_payload = {
            "customer_name": unique("customer"),
            "customer_email": f"{unique('email')}@example.com",
            "items": [{"book_id": book_id, "quantity": 1}]
        }
        order_resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=TIMEOUT)
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]
        status_payload = {"status": "delivered"}
        response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json=status_payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_get_invoice_for_confirmed_order_200(self):
        author_payload = {"name": unique("author")}
        author_resp = requests.post(f"{BASE_URL}/authors", json=author_payload, timeout=TIMEOUT)
        assert author_resp.status_code == 201