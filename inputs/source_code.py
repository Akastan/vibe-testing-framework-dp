
# ═══ FILE: app/main.py ═══

from typing import Optional, List

from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from . import crud, schemas
from . import models

from fastapi.responses import JSONResponse

# Vytvoření tabulek při startu
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bookstore API",
    description="REST API pro správu knihkupectví – knihy, autoři, kategorie, recenze, tagy a objednávky.",
    version="2.0.0",
)


# ── Health ───────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


# ── Authors ──────────────────────────────────────────────

@app.post("/authors", response_model=schemas.AuthorResponse, status_code=201, tags=["Authors"])
def create_author(author: schemas.AuthorCreate, db: Session = Depends(get_db)):
    return crud.create_author(db, author)


@app.get("/authors", response_model=List[schemas.AuthorResponse], tags=["Authors"])
def list_authors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_authors(db, skip=skip, limit=limit)


@app.get("/authors/{author_id}", response_model=schemas.AuthorResponse, tags=["Authors"])
def get_author(author_id: int, db: Session = Depends(get_db)):
    return crud.get_author(db, author_id)


@app.put("/authors/{author_id}", response_model=schemas.AuthorResponse, tags=["Authors"])
def update_author(author_id: int, author: schemas.AuthorUpdate, db: Session = Depends(get_db)):
    return crud.update_author(db, author_id, author)


@app.delete("/authors/{author_id}", status_code=204, tags=["Authors"])
def delete_author(author_id: int, db: Session = Depends(get_db)):
    crud.delete_author(db, author_id)


# ── Categories ───────────────────────────────────────────

@app.post("/categories", response_model=schemas.CategoryResponse, status_code=201, tags=["Categories"])
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, category)


@app.get("/categories", response_model=List[schemas.CategoryResponse], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


@app.get("/categories/{category_id}", response_model=schemas.CategoryResponse, tags=["Categories"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    return crud.get_category(db, category_id)


@app.put("/categories/{category_id}", response_model=schemas.CategoryResponse, tags=["Categories"])
def update_category(category_id: int, category: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    return crud.update_category(db, category_id, category)


@app.delete("/categories/{category_id}", status_code=204, tags=["Categories"])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    crud.delete_category(db, category_id)


# ── Books ────────────────────────────────────────────────

@app.post("/books", response_model=schemas.BookResponse, status_code=201, tags=["Books"])
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db)):
    return crud.create_book(db, book)


@app.get("/books", response_model=schemas.PaginatedBooks, tags=["Books"])
def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    return crud.get_books(
        db, page=page, page_size=page_size, search=search,
        author_id=author_id, category_id=category_id,
        min_price=min_price, max_price=max_price,
    )


@app.get("/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"])
def get_book(book_id: int, db: Session = Depends(get_db)):
    return crud.get_book(db, book_id)


@app.put("/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"])
def update_book(book_id: int, book: schemas.BookUpdate, db: Session = Depends(get_db)):
    return crud.update_book(db, book_id, book)


@app.delete("/books/{book_id}", status_code=204, tags=["Books"])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    crud.delete_book(db, book_id)


# ── Reviews ──────────────────────────────────────────────

@app.post("/books/{book_id}/reviews", response_model=schemas.ReviewResponse, status_code=201, tags=["Reviews"])
def create_review(book_id: int, review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    return crud.create_review(db, book_id, review)


@app.get("/books/{book_id}/reviews", response_model=List[schemas.ReviewResponse], tags=["Reviews"])
def list_reviews(book_id: int, db: Session = Depends(get_db)):
    return crud.get_reviews(db, book_id)


@app.get("/books/{book_id}/rating", tags=["Reviews"])
def get_book_rating(book_id: int, db: Session = Depends(get_db)):
    return crud.get_book_average_rating(db, book_id)


# ── Discount ─────────────────────────────────────────────

@app.post("/books/{book_id}/discount", response_model=schemas.DiscountResponse, tags=["Books"])
def apply_discount(book_id: int, discount: schemas.DiscountRequest, db: Session = Depends(get_db)):
    return crud.apply_discount(db, book_id, discount)


# ── Stock ────────────────────────────────────────────────

@app.patch("/books/{book_id}/stock", response_model=schemas.BookResponse, tags=["Books"])
def update_stock(book_id: int, quantity: int = Query(...), db: Session = Depends(get_db)):
    return crud.update_stock(db, book_id, quantity)


# ── Tags ─────────────────────────────────────────────────

@app.post("/tags", response_model=schemas.TagResponse, status_code=201, tags=["Tags"])
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    return crud.create_tag(db, tag)


@app.get("/tags", response_model=List[schemas.TagResponse], tags=["Tags"])
def list_tags(db: Session = Depends(get_db)):
    return crud.get_tags(db)


@app.get("/tags/{tag_id}", response_model=schemas.TagResponse, tags=["Tags"])
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    return crud.get_tag(db, tag_id)


@app.put("/tags/{tag_id}", response_model=schemas.TagResponse, tags=["Tags"])
def update_tag(tag_id: int, tag: schemas.TagUpdate, db: Session = Depends(get_db)):
    return crud.update_tag(db, tag_id, tag)


@app.delete("/tags/{tag_id}", status_code=204, tags=["Tags"])
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    crud.delete_tag(db, tag_id)


@app.post("/books/{book_id}/tags", response_model=schemas.BookResponse, tags=["Tags"])
def add_tags_to_book(book_id: int, action: schemas.BookTagAction, db: Session = Depends(get_db)):
    """Přidá tagy ke knize. Již existující vazby se ignorují."""
    return crud.add_tags_to_book(db, book_id, action.tag_ids)


@app.delete("/books/{book_id}/tags", response_model=schemas.BookResponse, tags=["Tags"])
def remove_tags_from_book(book_id: int, action: schemas.BookTagAction, db: Session = Depends(get_db)):
    """Odebere tagy z knihy."""
    return crud.remove_tags_from_book(db, book_id, action.tag_ids)


# ── Orders ───────────────────────────────────────────────

@app.post("/orders", response_model=schemas.OrderResponse, status_code=201, tags=["Orders"])
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Vytvoří objednávku, odečte sklad a zachytí aktuální ceny."""
    o = crud.create_order(db, order)
    return crud.get_order_response(o)


@app.get("/orders", response_model=schemas.PaginatedOrders, tags=["Orders"])
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_orders(db, page=page, page_size=page_size,
                           status=status, customer_name=customer_name)


@app.get("/orders/{order_id}", response_model=schemas.OrderResponse, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = crud.get_order(db, order_id)
    return crud.get_order_response(o)


@app.patch("/orders/{order_id}/status", response_model=schemas.OrderResponse, tags=["Orders"])
def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    """Změní stav objednávky dle povolených přechodů. Při zrušení vrátí sklad."""
    o = crud.update_order_status(db, order_id, status_update.status)
    return crud.get_order_response(o)


@app.delete("/orders/{order_id}", status_code=204, tags=["Orders"])
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Smaže objednávku. Lze smazat pouze pending nebo cancelled objednávky."""
    crud.delete_order(db, order_id)


# ── Reset (pro testovací framework) ──────────────────────

@app.post("/reset", tags=["Testing"])
def reset_database(db: Session = Depends(get_db)):
    """Smaže všechna data z databáze. Pouze pro testovací účely."""
    db.execute(models.Review.__table__.delete())
    db.execute(models.OrderItem.__table__.delete())
    db.execute(models.Order.__table__.delete())
    db.execute(models.book_tags.delete())
    db.execute(models.Book.__table__.delete())
    db.execute(models.Tag.__table__.delete())
    db.execute(models.Category.__table__.delete())
    db.execute(models.Author.__table__.delete())
    db.commit()
    return {"status": "ok", "message": "Database reset complete"}


# ── Author's Books ───────────────────────────────────────

@app.get("/authors/{author_id}/books", response_model=schemas.PaginatedBooks,
         tags=["Authors"])
def list_author_books(
    author_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Seznam knih daného autora s stránkováním."""
    return crud.get_author_books(db, author_id, page=page, page_size=page_size)


# ── Bulk Create Books ────────────────────────────────────

@app.post("/books/bulk", tags=["Books"])
def bulk_create_books(
    data: schemas.BulkBookCreate, db: Session = Depends(get_db),
):
    """
    Hromadné vytvoření knih. Každá kniha se validuje samostatně.
    Vrací 201 pokud všechny uspěly, 207 pokud některé selhaly,
    422 pokud všechny selhaly.
    """
    result = crud.bulk_create_books(db, data)

    if result.failed == 0:
        return JSONResponse(status_code=201, content=result.model_dump())
    elif result.created == 0:
        return JSONResponse(status_code=422, content=result.model_dump())
    else:
        return JSONResponse(status_code=207, content=result.model_dump())


# ── Clone Book ───────────────────────────────────────────

@app.post("/books/{book_id}/clone", response_model=schemas.BookResponse,
          status_code=201, tags=["Books"])
def clone_book(
    book_id: int, data: schemas.BookCloneRequest,
    db: Session = Depends(get_db),
):
    """Vytvoří kopii knihy s novým ISBN. Stock se nekopíruje."""
    return crud.clone_book(db, book_id, data)


# ── Invoice ──────────────────────────────────────────────

@app.get("/orders/{order_id}/invoice", response_model=schemas.InvoiceResponse,
         tags=["Orders"])
def get_invoice(order_id: int, db: Session = Depends(get_db)):
    """
    Vygeneruje fakturu pro objednávku.
    Dostupné pouze pro objednávky ve stavu confirmed, shipped nebo delivered.
    Pending a cancelled → 403.
    """
    return crud.generate_invoice(db, order_id)


# ── Add Item to Order ────────────────────────────────────

@app.post("/orders/{order_id}/items", response_model=schemas.OrderResponse,
          status_code=201, tags=["Orders"])
def add_item_to_order(
    order_id: int, data: schemas.OrderAddItem,
    db: Session = Depends(get_db),
):
    """
    Přidá položku do existující objednávky.
    Pouze pending objednávky lze modifikovat (jinak 403).
    Duplicitní book_id v objednávce → 409.
    """
    order = crud.add_item_to_order(db, order_id, data)
    return crud.get_order_response(order)


# ── Statistics ───────────────────────────────────────────

@app.get("/statistics/summary", response_model=schemas.StatisticsSummary,
         tags=["Statistics"])
def get_statistics(db: Session = Depends(get_db)):
    """Souhrnné statistiky knihkupectví. Obrat se počítá jen z delivered objednávek."""
    return crud.get_statistics(db)

# ═══ FILE: app/crud.py ═══

import math
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas


# ═══ Authors ═════════════════════════════════════════════

def create_author(db: Session, data: schemas.AuthorCreate) -> models.Author:
    author = models.Author(**data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


def get_author(db: Session, author_id: int) -> models.Author:
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail=f"Author with id {author_id} not found")
    return author


def get_authors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Author).offset(skip).limit(limit).all()


def update_author(db: Session, author_id: int, data: schemas.AuthorUpdate):
    author = get_author(db, author_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(author, k, v)
    db.commit()
    db.refresh(author)
    return author


def delete_author(db: Session, author_id: int):
    author = get_author(db, author_id)
    book_count = db.query(models.Book).filter(models.Book.author_id == author_id).count()
    if book_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete author with {book_count} associated book(s). Remove books first."
        )
    db.delete(author)
    db.commit()


# ═══ Categories ══════════════════════════════════════════

def create_category(db: Session, data: schemas.CategoryCreate) -> models.Category:
    if db.query(models.Category).filter(models.Category.name == data.name).first():
        raise HTTPException(status_code=409, detail=f"Category '{data.name}' already exists")
    cat = models.Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def get_category(db: Session, category_id: int) -> models.Category:
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found")
    return cat


def get_categories(db: Session):
    return db.query(models.Category).all()


def update_category(db: Session, category_id: int, data: schemas.CategoryUpdate):
    cat = get_category(db, category_id)
    update = data.model_dump(exclude_unset=True)
    if "name" in update:
        dup = db.query(models.Category).filter(
            models.Category.name == update["name"],
            models.Category.id != category_id
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Category '{update['name']}' already exists")
    for k, v in update.items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: int):
    cat = get_category(db, category_id)
    book_count = db.query(models.Book).filter(models.Book.category_id == category_id).count()
    if book_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete category with {book_count} associated book(s). Remove books first."
        )
    db.delete(cat)
    db.commit()


# ═══ Books ═══════════════════════════════════════════════

def create_book(db: Session, data: schemas.BookCreate) -> models.Book:
    get_author(db, data.author_id)
    get_category(db, data.category_id)
    if db.query(models.Book).filter(models.Book.isbn == data.isbn).first():
        raise HTTPException(status_code=409, detail=f"Book with ISBN '{data.isbn}' already exists")
    book = models.Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def get_book(db: Session, book_id: int) -> models.Book:
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    return book


def get_books(
    db: Session, page: int = 1, page_size: int = 10,
    search: str = None, author_id: int = None,
    category_id: int = None, min_price: float = None,
    max_price: float = None
) -> schemas.PaginatedBooks:
    q = db.query(models.Book)
    if search:
        q = q.filter(or_(
            models.Book.title.ilike(f"%{search}%"),
            models.Book.isbn.ilike(f"%{search}%")
        ))
    if author_id:
        q = q.filter(models.Book.author_id == author_id)
    if category_id:
        q = q.filter(models.Book.category_id == category_id)
    if min_price is not None:
        q = q.filter(models.Book.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Book.price <= max_price)

    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return schemas.PaginatedBooks(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages
    )


def update_book(db: Session, book_id: int, data: schemas.BookUpdate):
    book = get_book(db, book_id)
    update = data.model_dump(exclude_unset=True)
    if "author_id" in update:
        get_author(db, update["author_id"])
    if "category_id" in update:
        get_category(db, update["category_id"])
    if "isbn" in update:
        dup = db.query(models.Book).filter(
            models.Book.isbn == update["isbn"],
            models.Book.id != book_id
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Book with ISBN '{update['isbn']}' already exists")
    for k, v in update.items():
        setattr(book, k, v)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int):
    book = get_book(db, book_id)
    db.delete(book)
    db.commit()


# ═══ Reviews ═════════════════════════════════════════════

def create_review(db: Session, book_id: int, data: schemas.ReviewCreate):
    get_book(db, book_id)
    review = models.Review(book_id=book_id, **data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_reviews(db: Session, book_id: int):
    get_book(db, book_id)
    return db.query(models.Review).filter(models.Review.book_id == book_id).all()


def get_book_average_rating(db: Session, book_id: int) -> dict:
    get_book(db, book_id)
    reviews = db.query(models.Review).filter(models.Review.book_id == book_id).all()
    if not reviews:
        return {"book_id": book_id, "average_rating": None, "review_count": 0}
    avg = sum(r.rating for r in reviews) / len(reviews)
    return {"book_id": book_id, "average_rating": round(avg, 2), "review_count": len(reviews)}


# ═══ Discount (business logika) ══════════════════════════

def apply_discount(db: Session, book_id: int, data: schemas.DiscountRequest):
    book = get_book(db, book_id)
    current_year = datetime.now(timezone.utc).year
    if current_year - book.published_year < 1:
        raise HTTPException(
            status_code=400,
            detail="Discount can only be applied to books published more than 1 year ago"
        )
    discounted = round(book.price * (1 - data.discount_percent / 100), 2)
    return schemas.DiscountResponse(
        book_id=book.id, title=book.title,
        original_price=book.price,
        discount_percent=data.discount_percent,
        discounted_price=discounted
    )


# ═══ Stock management ════════════════════════════════════

def update_stock(db: Session, book_id: int, quantity: int):
    book = get_book(db, book_id)
    new_stock = book.stock + quantity
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {book.stock}, requested change: {quantity}"
        )
    book.stock = new_stock
    db.commit()
    db.refresh(book)
    return book


# ═══ Tags ════════════════════════════════════════════════

def create_tag(db: Session, data: schemas.TagCreate) -> models.Tag:
    if db.query(models.Tag).filter(models.Tag.name == data.name).first():
        raise HTTPException(status_code=409, detail=f"Tag '{data.name}' already exists")
    tag = models.Tag(**data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_tag(db: Session, tag_id: int) -> models.Tag:
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")
    return tag


def get_tags(db: Session):
    return db.query(models.Tag).all()


def update_tag(db: Session, tag_id: int, data: schemas.TagUpdate):
    tag = get_tag(db, tag_id)
    update = data.model_dump(exclude_unset=True)
    if "name" in update:
        dup = db.query(models.Tag).filter(
            models.Tag.name == update["name"],
            models.Tag.id != tag_id
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Tag '{update['name']}' already exists")
    for k, v in update.items():
        setattr(tag, k, v)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int):
    tag = get_tag(db, tag_id)
    book_count = len(tag.books)
    if book_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete tag with {book_count} associated book(s). Remove tag from books first."
        )
    db.delete(tag)
    db.commit()


def add_tags_to_book(db: Session, book_id: int, tag_ids: list[int]):
    book = get_book(db, book_id)
    for tid in tag_ids:
        tag = get_tag(db, tid)
        if tag not in book.tags:
            book.tags.append(tag)
    db.commit()
    db.refresh(book)
    return book


def remove_tags_from_book(db: Session, book_id: int, tag_ids: list[int]):
    book = get_book(db, book_id)
    for tid in tag_ids:
        tag = get_tag(db, tid)
        if tag in book.tags:
            book.tags.remove(tag)
    db.commit()
    db.refresh(book)
    return book


# ═══ Orders ══════════════════════════════════════════════

VALID_STATUS_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


def create_order(db: Session, data: schemas.OrderCreate) -> models.Order:
    # Validace: kontrola duplicitních book_id v položkách
    book_ids = [item.book_id for item in data.items]
    if len(book_ids) != len(set(book_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate book_id in order items"
        )

    # Validace: kontrola existence knih a dostatku skladu
    order_items = []
    for item in data.items:
        book = get_book(db, item.book_id)
        if book.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for book '{book.title}'. "
                       f"Available: {book.stock}, requested: {item.quantity}"
            )
        order_items.append((book, item))

    # Vytvoření objednávky
    order = models.Order(
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        status="pending",
    )
    db.add(order)
    db.flush()  # získáme order.id

    # Vytvoření položek a odečtení skladu
    for book, item in order_items:
        oi = models.OrderItem(
            order_id=order.id,
            book_id=item.book_id,
            quantity=item.quantity,
            unit_price=book.price,  # zachycení ceny v momentě objednávky
        )
        db.add(oi)
        book.stock -= item.quantity

    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: int) -> models.Order:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with id {order_id} not found")
    return order


def get_orders(
    db: Session, page: int = 1, page_size: int = 10,
    status: str = None, customer_name: str = None,
) -> schemas.PaginatedOrders:
    q = db.query(models.Order)
    if status:
        q = q.filter(models.Order.status == status)
    if customer_name:
        q = q.filter(models.Order.customer_name.ilike(f"%{customer_name}%"))

    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    orders = q.order_by(models.Order.created_at.desc()) \
              .offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for o in orders:
        total_price = sum(i.unit_price * i.quantity for i in o.items)
        items.append(schemas.OrderListResponse(
            id=o.id, customer_name=o.customer_name,
            customer_email=o.customer_email, status=o.status,
            total_price=round(total_price, 2), created_at=o.created_at,
        ))

    return schemas.PaginatedOrders(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


def update_order_status(db: Session, order_id: int, new_status: str) -> models.Order:
    order = get_order(db, order_id)
    allowed = VALID_STATUS_TRANSITIONS.get(order.status, [])

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{order.status}' to '{new_status}'. "
                   f"Allowed transitions: {allowed if allowed else 'none (terminal state)'}"
        )

    # Při zrušení objednávky vrátíme sklad
    if new_status == "cancelled":
        for item in order.items:
            book = db.query(models.Book).filter(models.Book.id == item.book_id).first()
            if book:
                book.stock += item.quantity

    order.status = new_status
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int):
    order = get_order(db, order_id)
    if order.status not in ("pending", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete order in '{order.status}' state. "
                   f"Only pending or cancelled orders can be deleted."
        )
    # Pokud je pending, vrátíme sklad
    if order.status == "pending":
        for item in order.items:
            book = db.query(models.Book).filter(models.Book.id == item.book_id).first()
            if book:
                book.stock += item.quantity
    db.delete(order)
    db.commit()


def get_order_response(order: models.Order) -> dict:
    """Helper pro sestavení odpovědi s total_price."""
    total_price = sum(i.unit_price * i.quantity for i in order.items)
    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": order.items,
        "total_price": round(total_price, 2),
    }


# ── Author's Books ───────────────────────────────────────

def get_author_books(db: Session, author_id: int, page: int = 1, page_size: int = 10):
    get_author(db, author_id)  # 404 pokud neexistuje
    q = db.query(models.Book).filter(models.Book.author_id == author_id)
    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return schemas.PaginatedBooks(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


# ── Bulk Create Books ────────────────────────────────────

def bulk_create_books(db: Session, data: schemas.BulkBookCreate) -> schemas.BulkCreateResponse:
    """
    Vytvoří knihy hromadně. Každá se validuje samostatně.
    Úspěšné se commitnou, neúspěšné vrátí chybu.
    Vrací 207 pokud je mix úspěchů a chyb, 201 pokud vše OK, 422 pokud vše selže.
    """
    results = []
    created_count = 0
    failed_count = 0

    for i, book_data in enumerate(data.books):
        try:
            # Validace autora
            author = db.query(models.Author).filter(
                models.Author.id == book_data.author_id
            ).first()
            if not author:
                raise ValueError(f"Author with id {book_data.author_id} not found")

            # Validace kategorie
            cat = db.query(models.Category).filter(
                models.Category.id == book_data.category_id
            ).first()
            if not cat:
                raise ValueError(f"Category with id {book_data.category_id} not found")

            # Validace ISBN unikátnosti
            if db.query(models.Book).filter(
                models.Book.isbn == book_data.isbn
            ).first():
                raise ValueError(f"Book with ISBN '{book_data.isbn}' already exists")

            # Vytvoření
            book = models.Book(**book_data.model_dump())
            db.add(book)
            db.flush()  # získáme ID bez commitu
            db.refresh(book)

            results.append(schemas.BulkResultItem(
                index=i, status="created", book=book,
            ))
            created_count += 1

        except (ValueError, Exception) as e:
            results.append(schemas.BulkResultItem(
                index=i, status="error", error=str(e),
            ))
            failed_count += 1

    if created_count > 0:
        db.commit()  # commit jen úspěšné
    else:
        db.rollback()

    return schemas.BulkCreateResponse(
        total=len(data.books),
        created=created_count,
        failed=failed_count,
        results=results,
    )


# ── Clone Book ───────────────────────────────────────────

def clone_book(db: Session, book_id: int, data: schemas.BookCloneRequest) -> models.Book:
    source = get_book(db, book_id)  # 404 pokud neexistuje

    # ISBN unikátnost
    if db.query(models.Book).filter(models.Book.isbn == data.new_isbn).first():
        raise HTTPException(
            status_code=409,
            detail=f"Book with ISBN '{data.new_isbn}' already exists",
        )

    clone = models.Book(
        title=data.new_title or f"{source.title} (copy)",
        isbn=data.new_isbn,
        price=source.price,
        published_year=source.published_year,
        stock=data.stock,  # stock se NEKOPÍRUJE — explicitně nastavený nebo 0
        author_id=source.author_id,
        category_id=source.category_id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


# ── Invoice ──────────────────────────────────────────────

def generate_invoice(db: Session, order_id: int) -> schemas.InvoiceResponse:
    order = get_order(db, order_id)

    # Faktura jen pro potvrzené+ objednávky
    if order.status in ("pending", "cancelled"):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot generate invoice for order in '{order.status}' state. "
                   f"Order must be confirmed, shipped, or delivered.",
        )

    items = []
    subtotal = 0.0
    for oi in order.items:
        book = db.query(models.Book).filter(models.Book.id == oi.book_id).first()
        line_total = round(oi.unit_price * oi.quantity, 2)
        items.append(schemas.InvoiceItem(
            book_title=book.title if book else "Unknown",
            isbn=book.isbn if book else "N/A",
            quantity=oi.quantity,
            unit_price=oi.unit_price,
            line_total=line_total,
        ))
        subtotal += line_total

    return schemas.InvoiceResponse(
        invoice_number=f"INV-{order.id:06d}",
        order_id=order.id,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        status=order.status,
        issued_at=datetime.now(timezone.utc).isoformat(),
        items=items,
        subtotal=round(subtotal, 2),
        item_count=len(items),
    )


# ── Add Item to Pending Order ────────────────────────────

def add_item_to_order(
    db: Session, order_id: int, data: schemas.OrderAddItem,
) -> models.Order:
    order = get_order(db, order_id)

    # Jen pending objednávky lze modifikovat
    if order.status != "pending":
        raise HTTPException(
            status_code=403,
            detail=f"Cannot modify order in '{order.status}' state. "
                   f"Only pending orders can be modified.",
        )

    # Kontrola duplicitního book_id
    existing_book_ids = {oi.book_id for oi in order.items}
    if data.book_id in existing_book_ids:
        raise HTTPException(
            status_code=409,
            detail=f"Book {data.book_id} is already in this order. "
                   f"Use a separate order or modify the existing item.",
        )

    # Validace knihy a skladu
    book = get_book(db, data.book_id)
    if book.stock < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for book '{book.title}'. "
                   f"Available: {book.stock}, requested: {data.quantity}",
        )

    # Přidání položky + odečtení skladu
    oi = models.OrderItem(
        order_id=order.id,
        book_id=data.book_id,
        quantity=data.quantity,
        unit_price=book.price,
    )
    db.add(oi)
    book.stock -= data.quantity

    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


# ── Statistics ───────────────────────────────────────────

def get_statistics(db: Session) -> schemas.StatisticsSummary:
    total_books = db.query(models.Book).count()
    total_orders = db.query(models.Order).count()

    # Knihy na skladě vs vyprodané
    in_stock = db.query(models.Book).filter(models.Book.stock > 0).count()

    # Celkový obrat (jen z delivered objednávek)
    delivered = db.query(models.Order).filter(
        models.Order.status == "delivered"
    ).all()
    revenue = 0.0
    for order in delivered:
        revenue += sum(i.unit_price * i.quantity for i in order.items)

    # Průměrná cena knih
    avg_price = None
    if total_books > 0:
        prices = [b.price for b in db.query(models.Book).all()]
        avg_price = round(sum(prices) / len(prices), 2)

    # Průměrné hodnocení
    avg_rating = None
    reviews = db.query(models.Review).all()
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 2)

    # Objednávky dle stavu
    status_counts = {}
    for status in ["pending", "confirmed", "shipped", "delivered", "cancelled"]:
        count = db.query(models.Order).filter(
            models.Order.status == status
        ).count()
        status_counts[status] = count

    return schemas.StatisticsSummary(
        total_authors=db.query(models.Author).count(),
        total_categories=db.query(models.Category).count(),
        total_books=total_books,
        total_tags=db.query(models.Tag).count(),
        total_orders=total_orders,
        total_reviews=len(reviews),
        books_in_stock=in_stock,
        books_out_of_stock=total_books - in_stock,
        total_revenue=round(revenue, 2),
        average_book_price=avg_price,
        average_rating=avg_rating,
        orders_by_status=status_counts,
    )

# ═══ FILE: app/schemas.py ═══

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Authors ──────────────────────────────────────────────

class AuthorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = None
    born_year: Optional[int] = Field(None, ge=0, le=2026)


class AuthorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = None
    born_year: Optional[int] = Field(None, ge=0, le=2026)


class AuthorResponse(BaseModel):
    id: int
    name: str
    bio: Optional[str]
    born_year: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Categories ───────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ── Tags (před Books kvůli referenci v BookResponse) ─────

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=30)


class TagResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class BookTagAction(BaseModel):
    tag_ids: List[int] = Field(..., min_length=1)


# ── Books ────────────────────────────────────────────────

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., min_length=10, max_length=13)
    price: float = Field(..., ge=0)
    published_year: int = Field(..., ge=1000, le=2026)
    stock: int = Field(0, ge=0)
    author_id: int
    category_id: int


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13)
    price: Optional[float] = Field(None, ge=0)
    published_year: Optional[int] = Field(None, ge=1000, le=2026)
    stock: Optional[int] = Field(None, ge=0)
    author_id: Optional[int] = None
    category_id: Optional[int] = None


class BookResponse(BaseModel):
    id: int
    title: str
    isbn: str
    price: float
    published_year: int
    stock: int
    author_id: int
    category_id: int
    created_at: datetime
    author: AuthorResponse
    category: CategoryResponse
    tags: List[TagResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    id: int
    title: str
    isbn: str
    price: float
    published_year: int
    stock: int
    author_id: int
    category_id: int

    class Config:
        from_attributes = True


# ── Reviews ──────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    reviewer_name: str = Field(..., min_length=1, max_length=100)


class ReviewResponse(BaseModel):
    id: int
    book_id: int
    rating: int
    comment: Optional[str]
    reviewer_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Discount ─────────────────────────────────────────────

class DiscountRequest(BaseModel):
    discount_percent: float = Field(..., gt=0, le=50)


class DiscountResponse(BaseModel):
    book_id: int
    title: str
    original_price: float
    discount_percent: float
    discounted_price: float


# ── Pagination ───────────────────────────────────────────

class PaginatedBooks(BaseModel):
    items: List[BookListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Orders ───────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(..., ge=1)


class OrderItemResponse(BaseModel):
    id: int
    book_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_email: str = Field(..., min_length=1, max_length=200)
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(confirmed|shipped|delivered|cancelled)$")


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]
    total_price: float

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    status: str
    total_price: float
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedOrders(BaseModel):
    items: List[OrderListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Bulk Create ──────────────────────────────────────────

class BulkBookItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., min_length=10, max_length=13)
    price: float = Field(..., ge=0)
    published_year: int = Field(..., ge=1000, le=2026)
    stock: int = Field(0, ge=0)
    author_id: int
    category_id: int


class BulkBookCreate(BaseModel):
    books: List[BulkBookItem] = Field(..., min_length=1, max_length=20)


class BulkResultItem(BaseModel):
    index: int
    status: str  # "created" | "error"
    book: Optional[BookResponse] = None
    error: Optional[str] = None


class BulkCreateResponse(BaseModel):
    total: int
    created: int
    failed: int
    results: List[BulkResultItem]


# ── Clone ────────────────────────────────────────────────

class BookCloneRequest(BaseModel):
    new_isbn: str = Field(..., min_length=10, max_length=13)
    new_title: Optional[str] = None
    stock: int = Field(0, ge=0)


# ── Invoice ──────────────────────────────────────────────

class InvoiceItem(BaseModel):
    book_title: str
    isbn: str
    quantity: int
    unit_price: float
    line_total: float


class InvoiceResponse(BaseModel):
    invoice_number: str
    order_id: int
    customer_name: str
    customer_email: str
    status: str
    issued_at: str
    items: List[InvoiceItem]
    subtotal: float
    item_count: int


# ── Add Item to Order ────────────────────────────────────

class OrderAddItem(BaseModel):
    book_id: int
    quantity: int = Field(..., ge=1)


# ── Statistics ───────────────────────────────────────────

class StatisticsSummary(BaseModel):
    total_authors: int
    total_categories: int
    total_books: int
    total_tags: int
    total_orders: int
    total_reviews: int
    books_in_stock: int
    books_out_of_stock: int
    total_revenue: float
    average_book_price: Optional[float]
    average_rating: Optional[float]
    orders_by_status: dict

# ═══ FILE: app/models.py ═══

from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, CheckConstraint, DateTime, Table

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    born_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    books = relationship("Book", back_populates="author")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    books = relationship("Book", back_populates="category")

book_tags = Table(
    "book_tags",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    isbn = Column(String(13), nullable=False, unique=True)
    price = Column(Float, nullable=False)
    tags = relationship("Tag", secondary=book_tags, back_populates="books")
    published_year = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_price_positive"),
        CheckConstraint("stock >= 0", name="check_stock_positive"),
    )

    author = relationship("Author", back_populates="books")
    category = relationship("Category", back_populates="books")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    reviewer_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
    )

    book = relationship("Book", back_populates="reviews")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), nullable=False, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    books = relationship("Book", secondary=book_tags, back_populates="tags")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="check_quantity_positive"),
    )

    order = relationship("Order", back_populates="items")
    book = relationship("Book")
