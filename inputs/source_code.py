
# ═══ FILE: app/main.py ═══

from typing import Optional, List

from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from . import crud, schemas
from . import models

# Vytvoření tabulek při startu
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bookstore API",
    description="REST API pro správu knihkupectví – knihy, autoři, kategorie a recenze.",
    version="1.0.0",
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

# ── Reset (pro testovací framework) ──────────────────────

@app.post("/reset", tags=["Testing"])
def reset_database(db: Session = Depends(get_db)):
    """Smaže všechna data z databáze. Pouze pro testovací účely."""
    db.execute(models.Review.__table__.delete())
    db.execute(models.Book.__table__.delete())
    db.execute(models.Category.__table__.delete())
    db.execute(models.Author.__table__.delete())
    db.commit()
    return {"status": "ok", "message": "Database reset complete"}

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
