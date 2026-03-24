import requests
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # Timeout for all HTTP calls


def unique(prefix: str = "test") -> str:
    """Generuje unikátní string pro názvy entit."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# --- HELPER FUNCTIONS ---
# Tyto helpery vytvářejí entity a vracejí jejich data nebo ID.
# Jsou navrženy tak, aby byly self-contained pro každý test,
# jak je požadováno. Všechny generují unikátní názvy/ISBN.

def create_author_helper(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    """Vytvoří autora a vrátí jeho data."""
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_category_helper(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Vytvoří kategorii a vrátí její data."""
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_tag_helper(name: Optional[str] = None) -> Dict[str, Any]:
    """Vytvoří tag a vrátí jeho data."""
    if name is None:
        name = unique("Tag")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/tags", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_book_helper(
    author_id: int,
    category_id: int,
    title: Optional[str] = None,
    isbn: Optional[str] = None,
    price: float = 299.99,
    published_year: int = None,
    stock: int = 10  # Dle požadavku, výchozí stock pro helper je 10
) -> Dict[str, Any]:
    """Vytvoří knihu a vrátí její data."""
    if title is None:
        title = unique("Book")
    if isbn is None:
        # Generuj platné ISBN (13 znaků, číslice)
        isbn = f"{str(uuid.uuid4().int)[:13]}"
    if published_year is None:
        published_year = datetime.now(timezone.utc).year - 4  # Dle požadavku, starší kniha pro slevy
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id,
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_book_helper(book_id: int) -> Dict[str, Any]:
    """Získá data knihy."""
    response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_review_helper(book_id: int, rating: int = 5, comment: Optional[str] = None, reviewer_name: Optional[str] = None) -> Dict[str, Any]:
    """Vytvoří recenzi pro knihu a vrátí její data."""
    if reviewer_name is None:
        reviewer_name = unique("Reviewer")
    payload = {"rating": rating, "reviewer_name": reviewer_name}
    if comment is not None:
        payload["comment"] = comment
    response = requests.post(f"{BASE_URL}/books/{book_id}/reviews", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def create_order_helper(items: List[Dict[str, Any]], customer_name: Optional[str] = None, customer_email: Optional[str] = None) -> Dict[str, Any]:
    """Vytvoří objednávku a vrátí její data."""
    if customer_name is None:
        customer_name = unique("Customer")
    if customer_email is None:
        customer_email = f"{unique('email')}@example.com"
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    }
    response = requests.post(f"{BASE_URL}/orders", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


# --- PYTEST TESTY ---

class TestAuthors:
    def test_create_author_happy_path(self):
        """Vytvoří nového autora s platnými daty. Ověří, že autor je vytvořen a vrácen s ID a createdAt."""
        author_name = unique("HappyAuthor")
        author_data = create_author_helper(name=author_name, bio="A writer of tales.", born_year=1980)

        assert author_data["name"] == author_name
        assert author_data["bio"] == "A writer of tales."
        assert author_data["born_year"] == 1980
        assert "id" in author_data
        assert "created_at" in author_data
        assert author_data["id"] > 0

    def test_update_author_happy_path(self):
        """Aktualizuje existujícího autora. Ověří, že data byla správně změněna v odpovědi."""
        author = create_author_helper()
        author_id = author["id"]
        new_name = unique("UpdatedAuthor")
        new_bio = "Updated biography."

        response = requests.put(f"{BASE_URL}/authors/{author_id}", json={"name": new_name, "bio": new_bio}, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_author = response.json()

        assert updated_author["id"] == author_id
        assert updated_author["name"] == new_name
        assert updated_author["bio"] == new_bio

        # Ověření přes GET
        get_response = requests.get(f"{BASE_URL}/authors/{author_id}", timeout=TIMEOUT)
        assert get_response.status_code == 200
        fetched_author = get_response.json()
        assert fetched_author["name"] == new_name
        assert fetched_author["bio"] == new_bio

    def test_delete_author_with_books_conflict(self):
        """Pokus o smazání autora, který má přiřazené knihy, by měl vrátit 409 Conflict."""
        author = create_author_helper()
        category = create_category_helper()
        create_book_helper(author_id=author["id"], category_id=category["id"])

        response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        assert "detail" in response.json()
        assert "Cannot delete author with" in response.json()["detail"]


class TestCategories:
    def test_create_category_happy_path(self):
        """Vytvoří novou kategorii s platnými daty. Ověří, že kategorie je vytvořena a vrácena s ID."""
        category_name = unique("HappyCategory")
        category_data = create_category_helper(name=category_name, description="Fiction books.")

        assert category_data["name"] == category_name
        assert category_data["description"] == "Fiction books."
        assert "id" in category_data
        assert category_data["id"] > 0

    def test_create_category_duplicate_name_conflict(self):
        """Pokus o vytvoření kategorie s již existujícím názvem by měl vrátit 409 Conflict."""
        category_name = unique("DuplicateCategory")
        create_category_helper(name=category_name)

        response = requests.post(f"{BASE_URL}/categories", json={"name": category_name}, timeout=TIMEOUT)
        assert response.status_code == 409
        assert "detail" in response.json()
        assert f"Category '{category_name}' already exists" in response.json()["detail"]

    def test_update_category_name_happy_path(self):
        """Aktualizuje název existující kategorie. Ověří, že název byl správně změněn."""
        category = create_category_helper()
        category_id = category["id"]
        new_name = unique("UpdatedCategory")

        response = requests.put(f"{BASE_URL}/categories/{category_id}", json={"name": new_name}, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_category = response.json()

        assert updated_category["id"] == category_id
        assert updated_category["name"] == new_name

        # Ověření přes GET
        get_response = requests.get(f"{BASE_URL}/categories/{category_id}", timeout=TIMEOUT)
        assert get_response.status_code == 200
        fetched_category = get_response.json()
        assert fetched_category["name"] == new_name

    def test_delete_category_with_books_conflict(self):
        """Pokus o smazání kategorie, která má přiřazené knihy, by měl vrátit 409 Conflict."""
        author = create_author_helper()
        category = create_category_helper()
        create_book_helper(author_id=author["id"], category_id=category["id"])

        response = requests.delete(f"{BASE_URL}/categories/{category['id']}", timeout=TIMEOUT)
        assert response.status_code == 409
        assert "detail" in response.json()
        assert "Cannot delete category with" in response.json()["detail"]


class TestTags:
    def test_create_tag_happy_path(self):
        """Vytvoří nový tag s platnými daty. Ověří, že tag je vytvořen a vrácen s ID."""
        tag_name = unique("HappyTag")
        tag_data = create_tag_helper(name=tag_name)

        assert tag_data["name"] == tag_name
        assert "id" in tag_data
        assert "created_at" in tag_data
        assert tag_data["id"] > 0

    def test_delete_tag_with_books_conflict(self):
        """Pokus o smazání tagu, který je přiřazen k alespoň jedné knize, by měl vrátit 409 Conflict."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"])
        tag = create_tag_helper()

        # Přidáme tag ke knize
        add_tags_response = requests.post(
            f"{BASE_URL}/books/{book['id']}/tags",
            json={"tag_ids": [tag["id"]]},
            timeout=TIMEOUT
        )
        assert add_tags_response.status_code == 200
        assert any(t["id"] == tag["id"] for t in add_tags_response.json()["tags"])

        # Pokusíme se smazat tag
        delete_response = requests.delete(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
        assert delete_response.status_code == 409
        assert "detail" in delete_response.json()
        assert "Cannot delete tag with" in delete_response.json()["detail"]


class TestBooks:
    def test_create_book_happy_path(self):
        """Vytvoří novou knihu s platnými daty a počátečním skladem 10 (dle helperu). Ověří, že kniha je vytvořena."""
        author = create_author_helper()
        category = create_category_helper()
        book_title = unique("HappyBook")
        book_isbn = f"{str(uuid.uuid4().int)[:13]}"
        book_price = 499.50
        book_year = 2020
        book_stock = 10  # Dle specifikace helperu

        book_data = create_book_helper(
            author_id=author["id"],
            category_id=category["id"],
            title=book_title,
            isbn=book_isbn,
            price=book_price,
            published_year=book_year,
            stock=book_stock
        )

        assert book_data["title"] == book_title
        assert book_data["isbn"] == book_isbn
        assert book_data["price"] == book_price
        assert book_data["published_year"] == book_year
        assert book_data["stock"] == book_stock
        assert book_data["author_id"] == author["id"]
        assert book_data["category_id"] == category["id"]
        assert "id" in book_data
        assert "created_at" in book_data
        assert "author" in book_data
        assert "category" in book_data
        assert "tags" in book_data
        assert book_data["id"] > 0

    def test_create_book_invalid_author_id_not_found(self):
        """Pokus o vytvoření knihy s neexistujícím author_id by měl vrátit 404 Not Found."""
        category = create_category_helper()
        non_existent_author_id = 999999999  # Předpokládáme, že ID nebude existovat

        response = requests.post(f"{BASE_URL}/books", json={
            "title": unique("BookInvalidAuthor"),
            "isbn": f"{str(uuid.uuid4().int)[:13]}",
            "price": 100.00,
            "published_year": 2020,
            "author_id": non_existent_author_id,
            "category_id": category["id"]
        }, timeout=TIMEOUT)

        assert response.status_code == 404
        assert "detail" in response.json()
        assert f"Author with id {non_existent_author_id} not found" in response.json()["detail"]

    def test_create_book_duplicate_isbn_conflict(self):
        """Pokus o vytvoření knihy s již existujícím ISBN by měl vrátit 409 Conflict."""
        author = create_author_helper()
        category = create_category_helper()
        duplicate_isbn = f"{str(uuid.uuid4().int)[:13]}"

        create_book_helper(author_id=author["id"], category_id=category["id"], isbn=duplicate_isbn)

        response = requests.post(f"{BASE_URL}/books", json={
            "title": unique("BookDuplicateISBN"),
            "isbn": duplicate_isbn,
            "price": 200.00,
            "published_year": 2021,
            "author_id": author["id"],
            "category_id": category["id"]
        }, timeout=TIMEOUT)

        assert response.status_code == 409
        assert "detail" in response.json()
        assert f"Book with ISBN '{duplicate_isbn}' already exists" in response.json()["detail"]

    def test_list_books_with_all_filters(self):
        """Získá seznam knih s použitím všech možných filtrů (search, author_id, category_id,
        min_price, max_price, page, page_size). Ověří, že filtry fungují správně a vrátí relevantní data."""
        author1 = create_author_helper(name=unique("AuthorFilter1"))
        author2 = create_author_helper(name=unique("AuthorFilter2"))
        category1 = create_category_helper(name=unique("CategoryFilter1"))
        category2 = create_category_helper(name=unique("CategoryFilter2"))

        # Vytvoření knih pro filtrování
        book1_data = create_book_helper(author_id=author1["id"], category_id=category1["id"],
                                        title=unique("Test Book A"), isbn=f"{str(uuid.uuid4().int)[:13]}",
                                        price=150.00, published_year=2010)
        book2_data = create_book_helper(author_id=author1["id"], category_id=category2["id"],
                                        title=unique("Another Test Book B"), isbn=f"{str(uuid.uuid4().int)[:13]}",
                                        price=250.00, published_year=2015)
        book3_data = create_book_helper(author_id=author2["id"], category_id=category1["id"],
                                        title=unique("My Special Book C"), isbn=f"{str(uuid.uuid4().int)[:13]}",
                                        price=350.00, published_year=2020)
        # Kniha pro search podle ISBN
        book4_data = create_book_helper(author_id=author2["id"], category_id=category2["id"],
                                        title=unique("Some Other Book D"), isbn=f"1234567890123",
                                        price=450.00, published_year=2022)

        # Test s kombinací filtrů
        filters = {
            "search": "Test",  # Book A, B
            "author_id": author1["id"], # Book A, B
            "category_id": category1["id"], # Book A
            "min_price": 100.00,
            "max_price": 200.00, # Book A
            "page": 1,
            "page_size": 10
        }
        response = requests.get(f"{BASE_URL}/books", params=filters, timeout=TIMEOUT)
        assert response.status_code == 200
        paginated_books = response.json()

        assert "items" in paginated_books
        assert "total" in paginated_books
        assert "page" in paginated_books
        assert "page_size" in paginated_books
        assert "total_pages" in paginated_books

        # Očekáváme pouze book1_data
        assert paginated_books["total"] == 1
        assert len(paginated_books["items"]) == 1
        assert paginated_books["items"][0]["id"] == book1_data["id"]

        # Test search podle ISBN
        filters_isbn = {
            "search": "1234567890123", # Book D
            "page": 1,
            "page_size": 10
        }
        response_isbn = requests.get(f"{BASE_URL}/books", params=filters_isbn, timeout=TIMEOUT)
        assert response_isbn.status_code == 200
        paginated_books_isbn = response_isbn.json()
        assert paginated_books_isbn["total"] == 1
        assert len(paginated_books_isbn["items"]) == 1
        assert paginated_books_isbn["items"][0]["id"] == book4_data["id"]


    def test_get_book_not_found(self):
        """Pokus o získání knihy s neexistujícím ID by měl vrátit 404 Not Found."""
        non_existent_book_id = 999999999  # Předpokládáme, že ID nebude existovat
        response = requests.get(f"{BASE_URL}/books/{non_existent_book_id}", timeout=TIMEOUT)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert f"Book with id {non_existent_book_id} not found" in response.json()["detail"]

    def test_update_book_happy_path(self):
        """Aktualizuje existující knihu s platnými daty. Ověří, že data byla správně změněna v odpovědi."""
        author1 = create_author_helper()
        author2 = create_author_helper() # Pro změnu autora
        category1 = create_category_helper()
        category2 = create_category_helper() # Pro změnu kategorie
        book = create_book_helper(author_id=author1["id"], category_id=category1["id"])
        book_id = book["id"]

        new_title = unique("Updated Book Title")
        new_price = 599.99
        new_stock = 20

        response = requests.put(f"{BASE_URL}/books/{book_id}", json={
            "title": new_title,
            "price": new_price,
            "stock": new_stock,
            "author_id": author2["id"],
            "category_id": category2["id"]
        }, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_book = response.json()

        assert updated_book["id"] == book_id
        assert updated_book["title"] == new_title
        assert updated_book["price"] == new_price
        assert updated_book["stock"] == new_stock
        assert updated_book["author_id"] == author2["id"]
        assert updated_book["category_id"] == category2["id"]

        # Ověření přes GET
        get_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
        assert get_response.status_code == 200
        fetched_book = get_response.json()
        assert fetched_book["title"] == new_title
        assert fetched_book["price"] == new_price
        assert fetched_book["stock"] == new_stock
        assert fetched_book["author"]["id"] == author2["id"] # Zkontrolovat, že se změnil autor
        assert fetched_book["category"]["id"] == category2["id"] # Zkontrolovat, že se změnila kategorie

def test_delete_book_happy_path(self):
    """Smaže existující knihu. Ověří, že kniha a její přidružené recenze/vazby na tagy byly smazány."""
    author = create_author_helper()
    category = create_category_helper()
    book = create_book_helper(author_id=author["id"], category_id=category["id"])
    book_id = book["id"]

    # Vytvoření recenze pro knihu
    review = create_review_helper(book_id=book_id)

    # Vytvoření tagu a přidání ke knize
    tag = create_tag_helper()
    requests.post(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [tag["id"]]}, timeout=TIMEOUT)

    response = requests.delete(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert response.status_code == 204
    assert not response.content # Kontrola, že tělo odpovědi je prázdné

    # Ověření, že kniha již neexistuje
    get_book_response = requests.get(f"{BASE_URL}/books/{book_id}", timeout=TIMEOUT)
    assert get_book_response.status_code == 404

    # Ověření, že recenze pro smazanou knihu již neexistují.
    # Jelikož kniha je smazána, endpoint pro recenze této konkrétní knihy by měl vrátit 404.
    get_reviews_response = requests.get(f"{BASE_URL}/books/{book_id}/reviews", timeout=TIMEOUT)
    assert get_reviews_response.status_code == 404

    # Ověření, že tag stále existuje (jen vazba byla smazána)
    get_tag_response = requests.get(f"{BASE_URL}/tags/{tag['id']}", timeout=TIMEOUT)
    assert get_tag_response.status_code == 200
        # Je těžké přímo ověřit, že vazba byla smazána bez načtení všech knih pro tag,
        # ale předpokládáme, že kaskádové mazání funguje na základě specifikace.


class TestReviews:
    def test_create_review_happy_path(self):
        """Vytvoří novou recenzi pro knihu s platnými daty. Ověří, že recenze je vytvořena a vrácena."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"])
        book_id = book["id"]

        reviewer_name = unique("ReviewerName")
        comment_text = "Absolutely loved this book!"
        rating_value = 4

        review_data = create_review_helper(
            book_id=book_id,
            rating=rating_value,
            comment=comment_text,
            reviewer_name=reviewer_name
        )

        assert review_data["book_id"] == book_id
        assert review_data["rating"] == rating_value
        assert review_data["comment"] == comment_text
        assert review_data["reviewer_name"] == reviewer_name
        assert "id" in review_data
        assert "created_at" in review_data
        assert review_data["id"] > 0

    def test_get_book_rating_no_reviews(self):
        """Získá rating pro knihu bez recenzí. Ověří, že 'average_rating' je null a 'review_count' je 0."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"])
        book_id = book["id"]

        response = requests.get(f"{BASE_URL}/books/{book_id}/rating", timeout=TIMEOUT)
        assert response.status_code == 200
        rating_data = response.json()

        assert rating_data["book_id"] == book_id
        assert rating_data["average_rating"] is None
        assert rating_data["review_count"] == 0


class TestDiscount:
    def test_apply_discount_happy_path(self):
        """Aplikuje slevu na starší knihu (published_year > aktuální_rok - 1). Ověří, že zlevněná cena je správně vypočítána."""
        author = create_author_helper()
        category = create_category_helper()
        # Kniha vydaná před více než 1 rokem (výchozí pro helper)
        book = create_book_helper(author_id=author["id"], category_id=category["id"], price=100.00)
        book_id = book["id"]
        discount_percent = 20.0

        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": discount_percent}, timeout=TIMEOUT)
        assert response.status_code == 200
        discount_data = response.json()

        assert discount_data["book_id"] == book_id
        assert discount_data["original_price"] == 100.00
        assert discount_data["discount_percent"] == discount_percent
        # Ověření správného výpočtu
        expected_discounted_price = round(100.00 * (1 - discount_percent / 100), 2)
        assert discount_data["discounted_price"] == expected_discounted_price

    def test_apply_discount_new_book_error(self):
        """Pokus o aplikaci slevy na knihu vydanou v posledním roce (published_year = aktuální_rok)
        by měl vrátit 400 Bad Request."""
        author = create_author_helper()
        category = create_category_helper()
        current_year = datetime.now(timezone.utc).year
        # Vytvoříme "novou" knihu
        book = create_book_helper(author_id=author["id"], category_id=category["id"], published_year=current_year, price=100.00)
        book_id = book["id"]
        discount_percent = 15.0

        response = requests.post(f"{BASE_URL}/books/{book_id}/discount", json={"discount_percent": discount_percent}, timeout=TIMEOUT)
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Discount can only be applied to books published more than 1 year ago" in response.json()["detail"]


class TestStock:
    def test_update_stock_increase_quantity(self):
        """Zvýší skladovou zásobu knihy s kladnou hodnotou quantity (delta). Ověří, že se stock správně aktualizoval."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"], stock=5)
        book_id = book["id"]
        initial_stock = book["stock"]
        increase_quantity = 10

        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock", params={"quantity": increase_quantity}, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_book = response.json()

        expected_stock = initial_stock + increase_quantity
        assert updated_book["id"] == book_id
        assert updated_book["stock"] == expected_stock

        # Ověření přes GET
        fetched_book = get_book_helper(book_id)
        assert fetched_book["stock"] == expected_stock

    def test_update_stock_insufficient_stock_error(self):
        """Pokus o snížení skladu tak, aby výsledná hodnota byla záporná, by měl vrátit 400 Bad Request."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"], stock=5)
        book_id = book["id"]
        initial_stock = book["stock"]
        decrease_quantity = -10  # Chceme odebrat více, než je k dispozici

        response = requests.patch(f"{BASE_URL}/books/{book_id}/stock", params={"quantity": decrease_quantity}, timeout=TIMEOUT)
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Insufficient stock" in response.json()["detail"]

        # Ověření, že sklad se nezměnil
        fetched_book = get_book_helper(book_id)
        assert fetched_book["stock"] == initial_stock


class TestBookTags:
    def test_add_tags_to_book_happy_path(self):
        """Přidá existující tagy ke knize (pomocí těla požadavku). Ověří, že kniha má přiřazené tagy v odpovědi."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"])
        book_id = book["id"]

        tag1 = create_tag_helper(name=unique("Tag1"))
        tag2 = create_tag_helper(name=unique("Tag2"))

        response = requests.post(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [tag1["id"], tag2["id"]]}, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_book = response.json()

        assert updated_book["id"] == book_id
        assert len(updated_book["tags"]) == 2
        assert any(t["id"] == tag1["id"] for t in updated_book["tags"])
        assert any(t["id"] == tag2["id"] for t in updated_book["tags"])

        # Ověření, že přidání stejných tagů znovu je idempotentní
        response_again = requests.post(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [tag1["id"]]}, timeout=TIMEOUT)
        assert response_again.status_code == 200
        updated_book_again = response_again.json()
        assert len(updated_book_again["tags"]) == 2 # Stále 2 tagy, nepřidaly se duplicitně

    def test_remove_tags_from_book_non_existent_tag_id(self):
        """Pokus o odebrání neexistujícího tag_id z knihy (pomocí těla požadavku)
        by měl vrátit 404 Not Found, pokud tag_id neexistuje."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"])
        book_id = book["id"]

        non_existent_tag_id = 999999999  # Předpokládáme, že ID nebude existovat

        response = requests.delete(f"{BASE_URL}/books/{book_id}/tags", json={"tag_ids": [non_existent_tag_id]}, timeout=TIMEOUT)
        assert response.status_code == 404
        assert "detail" in response.json()
        assert f"Tag with id {non_existent_tag_id} not found" in response.json()["detail"]


class TestOrders:
    def test_create_order_happy_path(self):
        """Vytvoří novou objednávku s více položkami, u kterých je dostatek skladu.
        Ověří, že sklad se snížil a total_price je správně spočítána."""
        author = create_author_helper()
        category = create_category_helper()

        book1_initial_stock = 15
        book2_initial_stock = 20
        book1_price = 100.00
        book2_price = 250.00

        book1 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=book1_initial_stock, price=book1_price)
        book2 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=book2_initial_stock, price=book2_price)

        order_items = [
            {"book_id": book1["id"], "quantity": 5},
            {"book_id": book2["id"], "quantity": 3},
        ]
        customer_name = unique("OrderCustomer")
        customer_email = f"{unique('orderemail')}@example.com"

        order_data = create_order_helper(items=order_items, customer_name=customer_name, customer_email=customer_email)

        assert order_data["customer_name"] == customer_name
        assert order_data["customer_email"] == customer_email
        assert order_data["status"] == "pending"
        assert "id" in order_data
        assert "created_at" in order_data
        assert "updated_at" in order_data
        assert len(order_data["items"]) == 2

        # Ověření total_price
        expected_total_price = (book1_price * 5) + (book2_price * 3)
        assert order_data["total_price"] == round(expected_total_price, 2)

        # Ověření snížení skladu
        book1_after_order = get_book_helper(book1["id"])
        book2_after_order = get_book_helper(book2["id"])

        assert book1_after_order["stock"] == book1_initial_stock - 5
        assert book2_after_order["stock"] == book2_initial_stock - 3

    def test_create_order_insufficient_stock_error(self):
        """Pokus o vytvoření objednávky s nedostatečným skladem pro některou knihu by měl vrátit 400 Bad Request."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"], stock=5) # Stock 5
        book_id = book["id"]

        order_items = [
            {"book_id": book_id, "quantity": 10}, # Žádáme 10, máme 5
        ]

        response = requests.post(f"{BASE_URL}/orders", json={
            "customer_name": unique("StockErrorCustomer"),
            "customer_email": f"{unique('stockerror')}@example.com",
            "items": order_items,
        }, timeout=TIMEOUT)

        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Insufficient stock for book" in response.json()["detail"]

        # Ověření, že sklad se nezměnil
        book_after_attempt = get_book_helper(book_id)
        assert book_after_attempt["stock"] == 5

    def test_create_order_duplicate_book_id_error(self):
        """Pokus o vytvoření objednávky s duplicitním book_id v položkách by měl vrátit 400 Bad Request."""
        author = create_author_helper()
        category = create_category_helper()
        book = create_book_helper(author_id=author["id"], category_id=category["id"], stock=10)
        book_id = book["id"]

        order_items = [
            {"book_id": book_id, "quantity": 2},
            {"book_id": book_id, "quantity": 3}, # Duplicitní book_id
        ]

        response = requests.post(f"{BASE_URL}/orders", json={
            "customer_name": unique("DuplicateBookCustomer"),
            "customer_email": f"{unique('duplicatebook')}@example.com",
            "items": order_items,
        }, timeout=TIMEOUT)

        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Duplicate book_id in order items" in response.json()["detail"]

    def test_list_orders_filter_by_status(self):
        """Získá seznam objednávek filtrovaných podle stavu (např. 'pending'). Ověří, že výsledky odpovídají filtru."""
        author = create_author_helper()
        category = create_category_helper()
        book1 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=10)
        book2 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=10)

        # Vytvoření objednávky v pending
        order_pending = create_order_helper(
            items=[{"book_id": book1["id"], "quantity": 1}],
            customer_name=unique("PendingOrder")
        )

        # Vytvoření objednávky a změna na confirmed
        order_confirmed = create_order_helper(
            items=[{"book_id": book2["id"], "quantity": 1}],
            customer_name=unique("ConfirmedOrder")
        )
        requests.patch(f"{BASE_URL}/orders/{order_confirmed['id']}/status", json={"status": "confirmed"}, timeout=TIMEOUT)

        # Filtrujeme podle status='pending'
        response = requests.get(f"{BASE_URL}/orders", params={"status": "pending"}, timeout=TIMEOUT)
        assert response.status_code == 200
        paginated_orders = response.json()

        assert "items" in paginated_orders
        assert paginated_orders["total"] >= 1 # Může být více pending objednávek z jiných testů, ale minimálně 1
        assert any(o["id"] == order_pending["id"] for o in paginated_orders["items"])
        assert all(o["status"] == "pending" for o in paginated_orders["items"])
        assert not any(o["id"] == order_confirmed["id"] for o in paginated_orders["items"])


    def test_get_order_details_happy_path(self):
        """Získá detaily konkrétní objednávky. Ověří správnost vrácených dat, včetně total_price a položek."""
        author = create_author_helper()
        category = create_category_helper()
        book1_price = 120.00
        book2_price = 300.00
        book1 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=10, price=book1_price)
        book2 = create_book_helper(author_id=author["id"], category_id=category["id"], stock=10, price=book2_price)

        order_items_payload = [
            {"book_id": book1["id"], "quantity": 2},
            {"book_id": book2["id"], "quantity": 1},
        ]
        order = create_order_helper(items=order_items_payload)
        order_id = order["id"]

        response = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=TIMEOUT)
        assert response.status_code == 200
        order_details = response.json()

        assert order_details["id"] == order_id
        assert order_details["customer_name"] == order["customer_name"]
        assert order_details["status"] == "pending"
        assert len(order_details["items"]) == 2

        # Ověření total_price
        expected_total_price = (book1_price * 2) + (book2_price * 1)
        assert order_details["total_price"] == round(expected_total_price, 2)

        # Ověření detailů položek
        item1 = next(item for item in order_details["items"] if item["book_id"] == book1["id"])
        assert item1["quantity"] == 2
        assert item1["unit_price"] == book1_price

        item2 = next(item for item in order_details["items"] if item["book_id"] == book2["id"])
        assert item2["quantity"] == 1
        assert item2["unit_price"] == book2_price

    def test_update_order_status_to_cancelled_returns_stock(self):
        """Změní stav objednávky na 'cancelled'. Ověří, že se skladové zásoby knih, které byly objednány, vrátily."""
        author = create_author_helper()
        category = create_category_helper()
        book_initial_stock = 10
        book = create_book_helper(author_id=author["id"], category_id=category["id"], stock=book_initial_stock)
        book_id = book["id"]
        ordered_quantity = 3

        order = create_order_helper(items=[{"book_id": book_id, "quantity": ordered_quantity}])
        order_id = order["id"]

        # Ověření snížení skladu po vytvoření objednávky
        book_after_order = get_book_helper(book_id)
        assert book_after_order["stock"] == book_initial_stock - ordered_quantity

        # Změna stavu na 'cancelled'
        response = requests.patch(f"{BASE_URL}/orders/{order_id}/status", json={"status": "cancelled"}, timeout=TIMEOUT)
        assert response.status_code == 200
        updated_order = response.json()

        assert updated_order["id"] == order_id
        assert updated_order["status"] == "cancelled"

        # Ověření, že se sklad vrátil
        book_after_cancel = get_book_helper(book_id)
        assert book_after_cancel["stock"] == book_initial_stock