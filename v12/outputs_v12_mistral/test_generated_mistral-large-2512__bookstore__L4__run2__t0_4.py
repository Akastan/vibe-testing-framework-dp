# Main issues: Missing API key in helpers, incorrect status code checks (200 vs 201), and potential string length issues
# Fix: Add AUTH headers to all helpers, standardize status code checks to (200, 201), and ensure unique strings stay within limits

import uuid
import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name=None, bio=None, born_year=1980):
    name = name or unique("Author")
    payload = {
        "name": name[:50],  # Ensure name doesn't exceed typical limits
        "bio": bio,
        "born_year": born_year,
    }
    r = requests.post(f"{BASE_URL}/authors", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name=None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name[:50]}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id, category_id, title=None, isbn=None, price=29.99, published_year=2020, stock=10):
    title = title or unique("Book")
    isbn = isbn or unique("ISBN")[:13]  # Ensure ISBN doesn't exceed 13 chars
    payload = {
        "title": title[:100],  # Ensure title doesn't exceed typical limits
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    r = requests.post(f"{BASE_URL}/books", json=payload, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name=None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name[:50]}, headers=AUTH, timeout=30)
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()


def test_health_check_returns_ok():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_author_with_valid_data():
    data = create_author(name=unique("George"), born_year=1903)
    assert data["name"].startswith("George_")
    assert data["born_year"] == 1903
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_required_field():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"})
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "name"] for error in r.json()["detail"])

def test_list_authors_with_pagination():
    author1 = create_author(name=unique("Author1"))
    author2 = create_author(name=unique("Author2"))

    r = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 1}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == author1["id"]

    r = requests.get(f"{BASE_URL}/authors", params={"skip": 1, "limit": 1}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == author2["id"]

def test_get_author_by_id():
    author = create_author(name=unique("TestAuthor"))
    r = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999")
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_with_etag_not_modified():
    author = create_author(name=unique("ETagAuthor"))
    r = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 200
    etag = r.headers.get("ETag")

    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag})
    assert r2.status_code == 304

def test_update_author_with_valid_data():
    author = create_author(name=unique("OldName"))
    new_name = unique("NewName")
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == new_name
    assert data["id"] == author["id"]

def test_update_author_with_etag_mismatch():
    author = create_author(name=unique("ETagAuthor"))
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}")
    old_etag = r1.headers["ETag"]

    # Update author to change ETag
    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": unique("ChangedName")})

    # Try to update with old ETag
    r2 = requests.put(
        f"{BASE_URL}/authors/{author['id']}",
        json={"name": unique("StaleUpdate")},
        headers={"If-Match": old_etag}
    )
    assert r2.status_code == 412
    assert "detail" in r2.json()

def test_delete_author_without_books():
    author = create_author(name=unique("DeleteMe"))
    r = requests.delete(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 204

    # Verify author is deleted
    r = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 404

def test_delete_author_with_books_fails():
    author = create_author(name=unique("AuthorWithBooks"))
    category = create_category(name=unique("Category"))
    book = create_book(author["id"], category["id"], title=unique("Book"))

    r = requests.delete(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_category_with_valid_data():
    name = unique("Science")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name, "description": "Science books"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == name
    assert data["description"] == "Science books"
    assert "id" in data

def test_create_duplicate_category_fails():
    name = unique("DuplicateCategory")
    r1 = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert r1.status_code == 201

    r2 = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert r2.status_code == 409
    assert "detail" in r2.json()

def test_list_categories():
    category1 = create_category(name=unique("Category1"))
    category2 = create_category(name=unique("Category2"))

    r = requests.get(f"{BASE_URL}/categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any(cat["id"] == category1["id"] for cat in data)
    assert any(cat["id"] == category2["id"] for cat in data)

def test_create_book_with_valid_data():
    author = create_author(name=unique("BookAuthor"))
    category = create_category(name=unique("BookCategory"))
    title = unique("BookTitle")
    isbn = unique("ISBN")[:13]

    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": 19.99,
        "published_year": 2020, "stock": 10,
        "author_id": author["id"], "category_id": category["id"]
    })
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == title
    assert data["isbn"] == isbn
    assert data["price"] == 19.99
    assert data["author_id"] == author["id"]
    assert data["category_id"] == category["id"]
    assert "id" in data

def test_create_book_with_duplicate_isbn_fails():
    author = create_author(name=unique("DupAuthor"))
    category = create_category(name=unique("DupCategory"))
    isbn = unique("ISBN")[:13]

    r1 = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book1"), "isbn": isbn, "price": 19.99,
        "published_year": 2020, "stock": 10,
        "author_id": author["id"], "category_id": category["id"]
    })
    assert r1.status_code == 201

    r2 = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book2"), "isbn": isbn, "price": 29.99,
        "published_year": 2021, "stock": 5,
        "author_id": author["id"], "category_id": category["id"]
    })
    assert r2.status_code == 409
    assert "detail" in r2.json()

def test_create_book_with_invalid_author_id_fails():
    category = create_category(name=unique("InvalidAuthorCat"))
    r = requests.post(f"{BASE_URL}/books", json={
        "title": unique("Book"), "isbn": unique("ISBN")[:13], "price": 19.99,
        "published_year": 2020, "stock": 10,
        "author_id": 999999, "category_id": category["id"]
    })
    assert r.status_code == 404
    assert "detail" in r.json()

def test_list_books_with_filters():
    author1 = create_author(name=unique("FilterAuthor1"))
    author2 = create_author(name=unique("FilterAuthor2"))
    category1 = create_category(name=unique("FilterCategory1"))
    category2 = create_category(name=unique("FilterCategory2"))

    book1 = create_book(author1["id"], category1["id"], title=unique("Book1"), price=10.00)
    book2 = create_book(author1["id"], category2["id"], title=unique("Book2"), price=20.00)
    book3 = create_book(author2["id"], category1["id"], title=unique("Book3"), price=30.00)

    # Filter by author
    r = requests.get(f"{BASE_URL}/books", params={"author_id": author1["id"]})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert all(book["author_id"] == author1["id"] for book in data["items"])

    # Filter by category
    r = requests.get(f"{BASE_URL}/books", params={"category_id": category1["id"]})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert all(book["category_id"] == category1["id"] for book in data["items"])

    # Filter by price range
    r = requests.get(f"{BASE_URL}/books", params={"min_price": 15, "max_price": 25})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert all(15 <= book["price"] <= 25 for book in data["items"])

def test_list_books_excludes_soft_deleted():
    author = create_author(name=unique("SoftDeleteAuthor"))
    category = create_category(name=unique("SoftDeleteCategory"))
    book = create_book(author["id"], category["id"], title=unique("SoftDeleteBook"))

    # Verify book exists
    r = requests.get(f"{BASE_URL}/books", params={"search": book["title"]})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # Soft delete book
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    # Verify book is excluded from list
    r = requests.get(f"{BASE_URL}/books", params={"search": book["title"]})
    assert r.status_code == 200
    assert r.json()["total"] == 0

def test_get_book_by_id():
    author = create_author(name=unique("GetBookAuthor"))
    category = create_category(name=unique("GetBookCategory"))
    book = create_book(author["id"], category["id"], title=unique("GetBook"))

    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]
    assert data["author"]["id"] == author["id"]
    assert data["category"]["id"] == category["id"]

def test_get_soft_deleted_book_returns_gone():
    author = create_author(name=unique("GoneAuthor"))
    category = create_category(name=unique("GoneCategory"))
    book = create_book(author["id"], category["id"], title=unique("GoneBook"))

    # Soft delete book
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    # Try to get deleted book
    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_with_valid_data():
    author = create_author(name=unique("UpdateAuthor"))
    category = create_category(name=unique("UpdateCategory"))
    book = create_book(author["id"], category["id"], title=unique("OriginalTitle"))

    new_title = unique("UpdatedTitle")
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title})
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == new_title
    assert data["id"] == book["id"]

def test_soft_delete_book():
    author = create_author(name=unique("DeleteAuthor"))
    category = create_category(name=unique("DeleteCategory"))
    book = create_book(author["id"], category["id"], title=unique("DeleteBook"))

    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    # Verify book is soft deleted
    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 410

def test_restore_soft_deleted_book():
    author = create_author(name=unique("RestoreAuthor"))
    category = create_category(name=unique("RestoreCategory"))
    book = create_book(author["id"], category["id"], title=unique("RestoreBook"))

    # Soft delete book
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    # Restore book
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

    # Verify book is accessible again
    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 200

def test_restore_non_deleted_book_fails():
    author = create_author(name=unique("NonDeletedAuthor"))
    category = create_category(name=unique("NonDeletedCategory"))
    book = create_book(author["id"], category["id"], title=unique("NonDeletedBook"))

    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore")
    assert r.status_code == 400
    assert "detail" in r.json()

def test_create_review_for_book():
    author = create_author(name=unique("ReviewAuthor"))
    category = create_category(name=unique("ReviewCategory"))
    book = create_book(author["id"], category["id"], title=unique("ReviewBook"))

    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": unique("Reviewer"), "comment": "Great book!"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["rating"] == 5
    assert data["reviewer_name"].startswith("Reviewer_")
    assert "id" in data

def test_create_review_for_soft_deleted_book_fails():
    author = create_author(name=unique("DeletedReviewAuthor"))
    category = create_category(name=unique("DeletedReviewCategory"))
    book = create_book(author["id"], category["id"], title=unique("DeletedReviewBook"))

    # Soft delete book
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    # Try to create review
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 3, "reviewer_name": unique("Reviewer"), "comment": "Would be good"
    })
    assert r.status_code == 410
    assert "detail" in r.json()

def test_list_reviews_for_book():
    author = create_author(name=unique("ListReviewAuthor"))
    category = create_category(name=unique("ListReviewCategory"))
    book = create_book(author["id"], category["id"], title=unique("ListReviewBook"))

    # Create multiple reviews
    for i in range(3):
        requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
            "rating": i+1, "reviewer_name": unique(f"Reviewer{i}"), "comment": f"Comment {i}"
        })

    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert all(review["book_id"] == book["id"] for review in data)

def test_get_book_rating():
    author = create_author(name=unique("RatingAuthor"))
    category = create_category(name=unique("RatingCategory"))
    book = create_book(author["id"], category["id"], title=unique("RatingBook"))

    # Create reviews
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 5, "reviewer_name": unique("Reviewer1")
    })
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews", json={
        "rating": 3, "reviewer_name": unique("Reviewer2")
    })

    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating")
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["average_rating"] == 4.0
    assert data["review_count"] == 2

def test_apply_discount_to_old_book():
    author = create_author(name=unique("DiscountAuthor"))
    category = create_category(name=unique("DiscountCategory"))
    book = create_book(author["id"], category["id"], title=unique("DiscountBook"), price=100, published_year=2020)

    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount", json={"discount_percent": 20})
    assert r.status_code == 200
    data = r.json()
    assert data["book_id"] == book["id"]
    assert data["original_price"] == 100
    assert data["discount_percent"] == 20
    assert data["discounted_price"] == 80.0