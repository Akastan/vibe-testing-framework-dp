import pytest
import requests
import uuid
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author() -> Dict[str, Any]:
    payload = {
        "name": unique("Author"),
        "bio": "Test bio",
        "born_year": 1980
    }
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category() -> Dict[str, Any]:
    payload = {
        "name": unique("Category"),
        "description": "Test category"
    }
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(author_id: int, category_id: int, **kwargs) -> Dict[str, Any]:
    payload = {
        "title": unique("Book"),
        "isbn": unique("978"),
        "price": 19.99,
        "published_year": 2020,
        "stock": 10,
        "author_id": author_id,
        "category_id": category_id
    }
    payload.update(kwargs)
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_tag() -> Dict[str, Any]:
    payload = {
        "name": unique("Tag")
    }
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_order(book_id: int, quantity: int = 1) -> Dict[str, Any]:
    payload = {
        "customer_name": unique("Customer"),
        "customer_email": f"{unique('test')}@example.com",
        "items": [
            {
                "book_id": book_id,
                "quantity": quantity
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

class TestHealth:
    def test_health_check_returns_200(self):
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200

class TestAuthorsPost:
    def test_create_author_success(self):
        payload = {
            "name": unique("Author"),
            "bio": "Test bio",
            "born_year": 1980
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["bio"] == payload["bio"]
        assert data["born_year"] == payload["born_year"]

    def test_create_author_missing_name_422(self):
        payload = {
            "bio": "Test bio",
            "born_year": 1980
        }
        response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestAuthorsGetById:
    def test_get_author_by_id_success(self):
        author = create_author()
        response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == author["id"]
        assert data["name"] == author["name"]

    def test_get_author_not_found_404(self):
        response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

class TestAuthorsDelete:
    def test_delete_author_without_books_204(self):
        author = create_author()
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        get_response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 404

    def test_delete_author_with_books_409(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestBooksPost:
    def test_create_book_success(self):
        author = create_author()
        category = create_category()
        payload = {
            "title": unique("Book"),
            "isbn": unique("978"),
            "price": 25.50,
            "published_year": 2020,
            "stock": 5,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == payload["title"]
        assert data["isbn"] == payload["isbn"]
        assert data["author_id"] == author["id"]
        assert data["category_id"] == category["id"]

    def test_create_book_duplicate_isbn_409(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        payload = {
            "title": unique("AnotherBook"),
            "isbn": book["isbn"],
            "price": 30.00,
            "published_year": 2021,
            "stock": 2,
            "author_id": author["id"],
            "category_id": category["id"]
        }
        response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

class TestBooksGet:
    def test_list_books_with_filters(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], price=15.0)
        response = requests.get(
            f"{BASE_URL}/books",
            params={"author_id": author["id"], "min_price": 10.0, "page": 1, "page_size": 10},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

class TestBooksGetById:
    def test_get_book_success(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book["id"]
        assert data["title"] == book["title"]

    def test_get_soft_deleted_book_410(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert delete_response.status_code == 204
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 410
        data = get_response.json()
        assert "detail" in data

class TestBooksDelete:
    def test_soft_delete_book_204(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert response.status_code == 204
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 410

class TestBooksRestore:
    def test_restore_soft_deleted_book_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        delete_response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert delete_response.status_code == 204
        restore_response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
        assert restore_response.status_code == 200
        data = restore_response.json()
        assert data["id"] == book["id"]
        get_response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
        assert get_response.status_code == 200

class TestBooksDiscount:
    def test_apply_discount_to_old_book_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], published_year=2020)
        payload = {
            "discount_percent": 10.0
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert "title" in data
        assert "original_price" in data
        assert "discount_percent" in data
        assert "discounted_price" in data
        assert data["discounted_price"] == book["price"] * (1 - payload["discount_percent"] / 100)

    def test_apply_discount_to_new_book_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], published_year=2026)
        payload = {
            "discount_percent": 10.0
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksStock:
    def test_increase_book_stock_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=5", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    def test_decrease_stock_below_zero_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=3)
        response = requests.patch(f"{BASE_URL}/books/{book['id']}/stock?quantity=-10", timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestBooksReviewsPost:
    def test_create_review_for_book_201(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        payload = {
            "rating": 5,
            "comment": "Great book!",
            "reviewer_name": unique("Reviewer")
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["book_id"] == book["id"]
        assert data["rating"] == payload["rating"]
        assert data["reviewer_name"] == payload["reviewer_name"]

class TestBooksTagsPost:
    def test_add_tags_to_book_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        tag1 = create_tag()
        tag2 = create_tag()
        payload = {
            "tag_ids": [tag1["id"], tag2["id"]]
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/tags", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        tag_ids = [t["id"] for t in data["tags"]]
        assert tag1["id"] in tag_ids
        assert tag2["id"] in tag_ids

class TestOrdersPost:
    def test_create_order_success_201(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        payload = {
            "customer_name": unique("Customer"),
            "customer_email": f"{unique('test')}@example.com",
            "items": [
                {
                    "book_id": book["id"],
                    "quantity": 2
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["customer_name"] == payload["customer_name"]
        assert data["customer_email"] == payload["customer_email"]
        assert data["status"] == "pending"
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["book_id"] == book["id"]
        assert data["items"][0]["quantity"] == 2
        assert "total_price" in data
        book_check = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT).json()
        assert book_check["stock"] == 8

    def test_create_order_insufficient_stock_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=1)
        payload = {
            "customer_name": unique("Customer"),
            "customer_email": f"{unique('test')}@example.com",
            "items": [
                {
                    "book_id": book["id"],
                    "quantity": 5
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

class TestOrdersStatusPatch:
    def test_update_order_status_valid_transition_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        order = create_order(book["id"], quantity=2)
        payload = {
            "status": "confirmed"
        }
        response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    def test_update_order_status_invalid_transition_400(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        order = create_order(book["id"], quantity=2)
        payload1 = {
            "status": "confirmed"
        }
        response1 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload1, timeout=TIMEOUT)
        assert response1.status_code == 200
        payload2 = {
            "status": "pending"
        }
        response2 = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=payload2, timeout=TIMEOUT)
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data

class TestOrdersInvoiceGet:
    def test_get_invoice_for_confirmed_order_200(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        order = create_order(book["id"], quantity=1)
        confirm_payload = {
            "status": "confirmed"
        }
        confirm_response = requests.patch(f"{BASE_URL}/orders/{order['id']}/status", json=confirm_payload, timeout=TIMEOUT)
        assert confirm_response.status_code == 200
        invoice_response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
        assert invoice_response.status_code == 200
        data = invoice_response.json()
        assert "invoice_number" in data
        assert data["order_id"] == order["id"]
        assert "items" in data
        assert "subtotal" in data

    def test_get_invoice_for_pending_order_403(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"], stock=10)
        order = create_order(book["id"], quantity=1)
        invoice_response = requests.get(f"{BASE_URL}/orders/{order['id']}/invoice", timeout=TIMEOUT)
        assert invoice_response.status_code == 403
        data = invoice_response.json()
        assert "detail" in data

class TestBooksBulkPost:
    def test_bulk_create_books_partial_success_207(self):
        author = create_author()
        category = create_category()
        existing_book = create_book(author_id=author["id"], category_id=category["id"])
        payload = {
            "books": [
                {
                    "title": unique("BulkBook1"),
                    "isbn": unique("978"),
                    "price": 20.0,
                    "published_year": 2020,
                    "stock": 5,
                    "author_id": author["id"],
                    "category_id": category["id"]
                },
                {
                    "title": unique("BulkBook2"),
                    "isbn": existing_book["isbn"],
                    "price": 30.0,
                    "published_year": 2021,
                    "stock": 3,
                    "author_id": author["id"],
                    "category_id": category["id"]
                }
            ]
        }
        headers = {"X-API-Key": "test-api-key"}
        response = requests.post(f"{BASE_URL}/books/bulk", json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 207
        data = response.json()
        assert "total" in data
        assert "created" in data
        assert "failed" in data
        assert "results" in data
        assert isinstance(data["results"], list)

class TestBooksClonePost:
    def test_clone_book_with_new_isbn_201(self):
        author = create_author()
        category = create_category()
        book = create_book(author_id=author["id"], category_id=category["id"])
        payload = {
            "new_isbn": unique("978"),
            "new_title": "Cloned Book",
            "stock": 7
        }
        response = requests.post(f"{BASE_URL}/books/{book['id']}/clone", json=payload, timeout=TIMEOUT)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["isbn"] == payload["new_isbn"]
        assert data["title"] == payload["new_title"]
        assert data["stock"] == payload["stock"]
        assert data["author_id"] == book["author_id"]
        assert data["category_id"] == book["category_id"]

class TestExportsBooksPost:
    def test_start_book_export_with_api_key_202(self):
        headers = {"X-API-Key": "test-api-key"}
        response = requests.post(f"{BASE_URL}/exports/books", headers=headers, timeout=TIMEOUT)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert "created_at" in data

class TestAdminMaintenancePost:
    def test_enable_maintenance_mode_200(self):
        headers = {"X-API-Key": "test-api-key"}
        payload = {
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/admin/maintenance", json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["maintenance_mode"] is True
        disable_payload = {
            "enabled": False
        }
        disable_response = requests.post(f"{BASE_URL}/admin/maintenance", json=disable_payload, headers=headers, timeout=TIMEOUT)
        assert disable_response.status_code == 200