
# ═══ FILE: app/main.py ═══


import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from collections import defaultdict

from fastapi import (
    FastAPI, Depends, Query, Request, Response,
    UploadFile, File, Security, HTTPException,
)
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from . import crud, schemas, models

Base.metadata.create_all(bind=engine)

# ── Configuration ────────────────────────────────────────

API_KEY = os.getenv("API_KEY", "test-api-key")
MAX_COVER_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png"}

# ── In-memory state (cleared on /reset) ─────────────────

maintenance_mode = False
cover_storage: dict[int, dict] = {}        # book_id -> {data, filename, content_type, size}
export_jobs: dict[str, dict] = {}           # job_id -> {status, created_at, complete_after, data}
rate_limit_store: defaultdict = defaultdict(list)  # key -> [timestamps]

# Rate limits: (max_requests, window_seconds)
RATE_LIMITS = {
    "bulk": (3, 30),
    "discount": (5, 10),
}

MAINTENANCE_EXEMPT = {"/health", "/admin/maintenance", "/openapi.json", "/docs", "/redoc"}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


# ── App ──────────────────────────────────────────────────

app = FastAPI(
    title="Bookstore API",
    description=(
        "REST API pro správu knihkupectví – knihy, autoři, kategorie, recenze, "
        "tagy a objednávky.\n\n"
        "**Autentizace:** Některé endpointy vyžadují hlavičku `X-API-Key`.\n\n"
        "**Rate limiting:** Endpoint `/books/bulk` (3 req/30s) a `/books/{id}/discount` "
        "(5 req/10s) mají rate limit. Při překročení vrací 429.\n\n"
        "**Maintenance mode:** Při aktivním maintenance režimu vrací neadmin endpointy 503.\n\n"
        "**Soft delete:** `DELETE /books/{id}` provede soft delete. "
        "`GET /books/{id}` na smazanou knihu vrátí 410 Gone.\n\n"
        "**ETags:** Detail endpointy vrací `ETag` header. `If-None-Match` → 304, "
        "`If-Match` na PUT → 412 při neshodě.\n\n"
        "**Nepoužívejte nepodporované HTTP metody** – vrací 405 Method Not Allowed."
    ),
    version="4.0.0",
)


# ── Middleware (registration order: last registered = first executed) ──

def _get_rate_limit_key(method: str, path: str) -> Optional[str]:
    if method == "POST" and path == "/books/bulk":
        return "bulk"
    if method == "POST" and "/discount" in path and path.startswith("/books/"):
        return "discount"
    return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    key = _get_rate_limit_key(request.method, request.url.path)
    if key and key in RATE_LIMITS:
        max_req, window = RATE_LIMITS[key]
        client_ip = request.client.host if request.client else "unknown"
        store_key = f"{client_ip}:{key}"
        now = time.time()
        rate_limit_store[store_key] = [t for t in rate_limit_store[store_key] if t > now - window]
        if len(rate_limit_store[store_key]) >= max_req:
            oldest = rate_limit_store[store_key][0]
            retry_after = int(window - (now - oldest)) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded for this endpoint. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )
        rate_limit_store[store_key].append(now)
    return await call_next(request)


@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    global maintenance_mode
    if maintenance_mode and request.url.path not in MAINTENANCE_EXEMPT:
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable for maintenance"},
            headers={"Retry-After": "300"},
        )
    return await call_next(request)


# ── ETag helpers ─────────────────────────────────────────

def _check_etag_get(request: Request, response: Response, updated_at) -> Optional[Response]:
    """For GET: set ETag, return 304 if If-None-Match matches."""
    etag = crud.generate_etag(updated_at)
    response.headers["ETag"] = f'"{etag}"'
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})
    return None


def _check_etag_put(request: Request, updated_at):
    """For PUT: check If-Match, raise 412 if mismatch."""
    if_match = request.headers.get("if-match")
    if if_match:
        current_etag = crud.generate_etag(updated_at)
        if if_match.strip('"') != current_etag:
            raise HTTPException(
                status_code=412,
                detail="Precondition Failed: resource has been modified since last read",
            )


# ── Health ───────────────────────────────────────────────

@app.get("/health", tags=["Health"],
         responses={405: {"description": "Method Not Allowed"}})
def health_check():
    return {"status": "ok"}


# ── Authors ──────────────────────────────────────────────

@app.post("/authors", response_model=schemas.AuthorResponse, status_code=201, tags=["Authors"])
def create_author(author: schemas.AuthorCreate, db: Session = Depends(get_db)):
    return crud.create_author(db, author)


@app.get("/authors", response_model=List[schemas.AuthorResponse], tags=["Authors"])
def list_authors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_authors(db, skip=skip, limit=limit)


@app.get("/authors/{author_id}", response_model=schemas.AuthorResponse, tags=["Authors"],
         responses={304: {"description": "Not Modified"}, 404: {"description": "Author not found"}})
def get_author(author_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    author = crud.get_author(db, author_id)
    cached = _check_etag_get(request, response, author.updated_at)
    if cached:
        return cached
    return author


@app.put("/authors/{author_id}", response_model=schemas.AuthorResponse, tags=["Authors"],
         responses={412: {"description": "Precondition Failed – ETag mismatch"}})
def update_author(author_id: int, author: schemas.AuthorUpdate,
                  request: Request, db: Session = Depends(get_db)):
    existing = crud.get_author(db, author_id)
    _check_etag_put(request, existing.updated_at)
    return crud.update_author(db, author_id, author)


@app.delete("/authors/{author_id}", status_code=204, tags=["Authors"])
def delete_author(author_id: int, db: Session = Depends(get_db)):
    crud.delete_author(db, author_id)


@app.get("/authors/{author_id}/books", response_model=schemas.PaginatedBooks, tags=["Authors"])
def list_author_books(
    author_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud.get_author_books(db, author_id, page=page, page_size=page_size)


# ── Categories ───────────────────────────────────────────

@app.post("/categories", response_model=schemas.CategoryResponse, status_code=201, tags=["Categories"])
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, category)


@app.get("/categories", response_model=List[schemas.CategoryResponse], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


@app.get("/categories/{category_id}", response_model=schemas.CategoryResponse, tags=["Categories"],
         responses={304: {"description": "Not Modified"}})
def get_category(category_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    cat = crud.get_category(db, category_id)
    cached = _check_etag_get(request, response, cat.updated_at)
    if cached:
        return cached
    return cat


@app.put("/categories/{category_id}", response_model=schemas.CategoryResponse, tags=["Categories"],
         responses={412: {"description": "Precondition Failed – ETag mismatch"}})
def update_category(category_id: int, category: schemas.CategoryUpdate,
                    request: Request, db: Session = Depends(get_db)):
    existing = crud.get_category(db, category_id)
    _check_etag_put(request, existing.updated_at)
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


@app.get("/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"],
         responses={304: {"description": "Not Modified"}, 410: {"description": "Book has been deleted (soft delete)"}})
def get_book(book_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    book = crud.get_book(db, book_id)
    cached = _check_etag_get(request, response, book.updated_at)
    if cached:
        return cached
    return book


@app.put("/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"],
         responses={412: {"description": "Precondition Failed – ETag mismatch"},
                    410: {"description": "Book has been deleted"}})
def update_book(book_id: int, book: schemas.BookUpdate,
                request: Request, db: Session = Depends(get_db)):
    existing = crud.get_book(db, book_id)
    _check_etag_put(request, existing.updated_at)
    return crud.update_book(db, book_id, book)


@app.delete("/books/{book_id}", status_code=204, tags=["Books"],
            responses={410: {"description": "Book already deleted"}})
def delete_book(book_id: int, db: Session = Depends(get_db)):
    crud.delete_book(db, book_id)


@app.post("/books/{book_id}/restore", response_model=schemas.BookResponse, tags=["Books"],
          responses={400: {"description": "Book is not deleted"}, 404: {"description": "Book not found"}})
def restore_book(book_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted book."""
    return crud.restore_book(db, book_id)


# ── Reviews ──────────────────────────────────────────────

@app.post("/books/{book_id}/reviews", response_model=schemas.ReviewResponse,
          status_code=201, tags=["Reviews"],
          responses={410: {"description": "Book has been deleted"}})
def create_review(book_id: int, review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    return crud.create_review(db, book_id, review)


@app.get("/books/{book_id}/reviews", response_model=List[schemas.ReviewResponse], tags=["Reviews"])
def list_reviews(book_id: int, db: Session = Depends(get_db)):
    return crud.get_reviews(db, book_id)


@app.get("/books/{book_id}/rating", tags=["Reviews"])
def get_book_rating(book_id: int, db: Session = Depends(get_db)):
    return crud.get_book_average_rating(db, book_id)


# ── Discount ─────────────────────────────────────────────

@app.post("/books/{book_id}/discount", response_model=schemas.DiscountResponse, tags=["Books"],
          responses={429: {"description": "Rate limit exceeded (5 req/10s)"}})
def apply_discount(book_id: int, discount: schemas.DiscountRequest, db: Session = Depends(get_db)):
    return crud.apply_discount(db, book_id, discount)


# ── Stock ────────────────────────────────────────────────

@app.patch("/books/{book_id}/stock", response_model=schemas.BookResponse, tags=["Books"])
def update_stock(book_id: int, quantity: int = Query(...), db: Session = Depends(get_db)):
    return crud.update_stock(db, book_id, quantity)


# ── Cover Upload ─────────────────────────────────────────

@app.post("/books/{book_id}/cover", response_model=schemas.CoverUploadResponse, tags=["Books"],
          responses={
              413: {"description": "File too large (max 2 MB)"},
              415: {"description": "Unsupported file type (only JPEG, PNG)"},
              410: {"description": "Book has been deleted"},
          })
async def upload_cover(book_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    crud.get_book(db, book_id)
    if file.content_type not in ALLOWED_COVER_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Allowed: image/jpeg, image/png",
        )
    data = await file.read()
    if len(data) > MAX_COVER_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(data)} bytes. Maximum: {MAX_COVER_SIZE} bytes (2 MB)",
        )
    cover_storage[book_id] = {
        "data": data, "filename": file.filename or "cover",
        "content_type": file.content_type, "size": len(data),
    }
    return schemas.CoverUploadResponse(
        book_id=book_id, filename=file.filename or "cover",
        content_type=file.content_type, size_bytes=len(data),
    )


@app.get("/books/{book_id}/cover", tags=["Books"],
         responses={404: {"description": "No cover uploaded"}, 410: {"description": "Book has been deleted"}})
def get_cover(book_id: int, db: Session = Depends(get_db)):
    crud.get_book(db, book_id)
    if book_id not in cover_storage:
        raise HTTPException(status_code=404, detail="No cover uploaded for this book")
    c = cover_storage[book_id]
    return Response(content=c["data"], media_type=c["content_type"])


@app.delete("/books/{book_id}/cover", status_code=204, tags=["Books"])
def delete_cover(book_id: int, db: Session = Depends(get_db)):
    crud.get_book(db, book_id)
    if book_id not in cover_storage:
        raise HTTPException(status_code=404, detail="No cover uploaded for this book")
    del cover_storage[book_id]


# ── Tags ─────────────────────────────────────────────────

@app.post("/tags", response_model=schemas.TagResponse, status_code=201, tags=["Tags"])
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    return crud.create_tag(db, tag)


@app.get("/tags", response_model=List[schemas.TagResponse], tags=["Tags"])
def list_tags(db: Session = Depends(get_db)):
    return crud.get_tags(db)


@app.get("/tags/{tag_id}", response_model=schemas.TagResponse, tags=["Tags"],
         responses={304: {"description": "Not Modified"}})
def get_tag(tag_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    tag = crud.get_tag(db, tag_id)
    cached = _check_etag_get(request, response, tag.updated_at)
    if cached:
        return cached
    return tag


@app.put("/tags/{tag_id}", response_model=schemas.TagResponse, tags=["Tags"],
         responses={412: {"description": "Precondition Failed – ETag mismatch"}})
def update_tag(tag_id: int, tag: schemas.TagUpdate,
               request: Request, db: Session = Depends(get_db)):
    existing = crud.get_tag(db, tag_id)
    _check_etag_put(request, existing.updated_at)
    return crud.update_tag(db, tag_id, tag)


@app.delete("/tags/{tag_id}", status_code=204, tags=["Tags"])
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    crud.delete_tag(db, tag_id)


@app.post("/books/{book_id}/tags", response_model=schemas.BookResponse, tags=["Tags"])
def add_tags_to_book(book_id: int, action: schemas.BookTagAction, db: Session = Depends(get_db)):
    return crud.add_tags_to_book(db, book_id, action.tag_ids)


@app.delete("/books/{book_id}/tags", response_model=schemas.BookResponse, tags=["Tags"])
def remove_tags_from_book(book_id: int, action: schemas.BookTagAction, db: Session = Depends(get_db)):
    return crud.remove_tags_from_book(db, book_id, action.tag_ids)


# ── Orders ───────────────────────────────────────────────

@app.post("/orders", response_model=schemas.OrderResponse, status_code=201, tags=["Orders"])
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
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
    order_id: int, status_update: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    o = crud.update_order_status(db, order_id, status_update.status)
    return crud.get_order_response(o)


@app.delete("/orders/{order_id}", status_code=204, tags=["Orders"])
def delete_order(order_id: int, db: Session = Depends(get_db)):
    crud.delete_order(db, order_id)


@app.get("/orders/{order_id}/invoice", response_model=schemas.InvoiceResponse, tags=["Orders"])
def get_invoice(order_id: int, db: Session = Depends(get_db)):
    return crud.generate_invoice(db, order_id)


@app.post("/orders/{order_id}/items", response_model=schemas.OrderResponse,
          status_code=201, tags=["Orders"])
def add_item_to_order(order_id: int, data: schemas.OrderAddItem, db: Session = Depends(get_db)):
    order = crud.add_item_to_order(db, order_id, data)
    return crud.get_order_response(order)


# ── Bulk Create Books ────────────────────────────────────

@app.post("/books/bulk", tags=["Books"],
          responses={
              201: {"description": "All books created"},
              207: {"description": "Partial success"},
              401: {"description": "Invalid or missing API key"},
              422: {"description": "All books failed validation"},
              429: {"description": "Rate limit exceeded (3 req/30s)"},
          })
def bulk_create_books(
    data: schemas.BulkBookCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    result = crud.bulk_create_books(db, data)
    if result.failed == 0:
        return JSONResponse(status_code=201, content=result.model_dump(mode="json"))
    elif result.created == 0:
        return JSONResponse(status_code=422, content=result.model_dump(mode="json"))
    else:
        return JSONResponse(status_code=207, content=result.model_dump(mode="json"))


# ── Clone Book ───────────────────────────────────────────

@app.post("/books/{book_id}/clone", response_model=schemas.BookResponse,
          status_code=201, tags=["Books"])
def clone_book(book_id: int, data: schemas.BookCloneRequest, db: Session = Depends(get_db)):
    return crud.clone_book(db, book_id, data)


# ── Async Exports ────────────────────────────────────────

@app.post("/exports/books", status_code=202, tags=["Exports"],
          response_model=schemas.ExportJobCreated,
          responses={401: {"description": "Invalid or missing API key"}})
def create_book_export(db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    """Start async book export. Poll GET /exports/{job_id} for result."""
    job_id = str(uuid.uuid4())
    books = db.query(models.Book).filter(models.Book.is_deleted == False).all()
    data = [
        {"id": b.id, "title": b.title, "isbn": b.isbn, "price": b.price,
         "stock": b.stock, "author_id": b.author_id, "category_id": b.category_id}
        for b in books
    ]
    now = time.time()
    export_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "complete_after": now + 2,  # Simulated 2s processing
        "data": data,
        "total": len(data),
    }
    return schemas.ExportJobCreated(
        job_id=job_id, status="processing",
        created_at=export_jobs[job_id]["created_at"],
    )


@app.post("/exports/orders", status_code=202, tags=["Exports"],
          response_model=schemas.ExportJobCreated,
          responses={401: {"description": "Invalid or missing API key"}})
def create_order_export(db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    """Start async order export. Poll GET /exports/{job_id} for result."""
    job_id = str(uuid.uuid4())
    orders = db.query(models.Order).all()
    data = [
        {"id": o.id, "customer_name": o.customer_name, "status": o.status,
         "total_price": round(sum(i.unit_price * i.quantity for i in o.items), 2),
         "item_count": len(o.items), "created_at": o.created_at.isoformat()}
        for o in orders
    ]
    now = time.time()
    export_jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "complete_after": now + 2,
        "data": data,
        "total": len(data),
    }
    return schemas.ExportJobCreated(
        job_id=job_id, status="processing",
        created_at=export_jobs[job_id]["created_at"],
    )


@app.get("/exports/{job_id}", tags=["Exports"],
         responses={
             200: {"description": "Export completed", "model": schemas.ExportJobResult},
             202: {"description": "Export still processing"},
             404: {"description": "Export job not found"},
         })
def get_export_job(job_id: str):
    job = export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    if time.time() < job["complete_after"]:
        return JSONResponse(
            status_code=202,
            content={"job_id": job_id, "status": "processing", "created_at": job["created_at"]},
        )
    return schemas.ExportJobResult(
        job_id=job_id, status="completed", created_at=job["created_at"],
        completed_at=datetime.now(timezone.utc).isoformat(),
        total=job["total"], data=job["data"],
    )


# ── Admin ────────────────────────────────────────────────

@app.post("/admin/maintenance", response_model=schemas.MaintenanceStatus, tags=["Admin"],
          responses={401: {"description": "Invalid or missing API key"}})
def toggle_maintenance(data: schemas.MaintenanceToggle, _: str = Depends(require_api_key)):
    global maintenance_mode
    maintenance_mode = data.enabled
    msg = "Maintenance mode activated" if data.enabled else "Maintenance mode deactivated"
    return schemas.MaintenanceStatus(maintenance_mode=maintenance_mode, message=msg)


@app.get("/admin/maintenance", response_model=schemas.MaintenanceStatus, tags=["Admin"])
def get_maintenance_status():
    return schemas.MaintenanceStatus(
        maintenance_mode=maintenance_mode,
        message="Maintenance mode is active" if maintenance_mode else "System operational",
    )


# ── Statistics (protected) ───────────────────────────────

@app.get("/statistics/summary", response_model=schemas.StatisticsSummary, tags=["Statistics"],
         responses={401: {"description": "Invalid or missing API key"}})
def get_statistics(db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    return crud.get_statistics(db)


# ── Deprecated Redirect ──────────────────────────────────

@app.get("/catalog", tags=["Deprecated"],
         responses={301: {"description": "Moved Permanently to /books"}},
         status_code=301)
def deprecated_catalog():
    """Deprecated: use GET /books instead."""
    return RedirectResponse(url="/books", status_code=301)


# ── Reset ────────────────────────────────────────────────

@app.post("/reset", tags=["Testing"])
def reset_database(db: Session = Depends(get_db)):
    """Reset all data (DB + in-memory state). For testing only."""
    global maintenance_mode
    db.execute(models.Review.__table__.delete())
    db.execute(models.OrderItem.__table__.delete())
    db.execute(models.Order.__table__.delete())
    db.execute(models.book_tags.delete())
    db.execute(models.Book.__table__.delete())
    db.execute(models.Tag.__table__.delete())
    db.execute(models.Category.__table__.delete())
    db.execute(models.Author.__table__.delete())
    db.commit()
    # Clear in-memory state
    maintenance_mode = False
    cover_storage.clear()
    export_jobs.clear()
    rate_limit_store.clear()
    return {"status": "ok", "message": "Database and state reset complete"}

# ═══ FILE: app/crud.py ═══


import math
import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas


# ═══ ETag helper ═════════════════════════════════════════

def generate_etag(updated_at) -> str:
    return hashlib.md5(str(updated_at).encode()).hexdigest()


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
    author.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(author)
    return author


def delete_author(db: Session, author_id: int):
    author = get_author(db, author_id)
    book_count = db.query(models.Book).filter(
        models.Book.author_id == author_id,
        models.Book.is_deleted == False,
    ).count()
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
    cat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: int):
    cat = get_category(db, category_id)
    book_count = db.query(models.Book).filter(
        models.Book.category_id == category_id,
        models.Book.is_deleted == False,
    ).count()
    if book_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete category with {book_count} associated book(s). Remove books first."
        )
    db.delete(cat)
    db.commit()


# ═══ Books ═══════════════════════════════════════════════

def get_book(db: Session, book_id: int) -> models.Book:
    """Returns 404 if not found, 410 if soft-deleted."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    if book.is_deleted:
        raise HTTPException(status_code=410, detail=f"Book with id {book_id} has been deleted")
    return book


def get_book_include_deleted(db: Session, book_id: int) -> models.Book:
    """Internal: returns book regardless of soft-delete status. 404 only."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    return book


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


def get_books(
    db: Session, page: int = 1, page_size: int = 10,
    search: str = None, author_id: int = None,
    category_id: int = None, min_price: float = None,
    max_price: float = None,
) -> schemas.PaginatedBooks:
    q = db.query(models.Book).filter(models.Book.is_deleted == False)
    if search:
        q = q.filter(or_(
            models.Book.title.ilike(f"%{search}%"),
            models.Book.isbn.ilike(f"%{search}%"),
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
        page_size=page_size, total_pages=total_pages,
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
            models.Book.id != book_id,
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Book with ISBN '{update['isbn']}' already exists")
    for k, v in update.items():
        setattr(book, k, v)
    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int):
    """Soft delete — sets is_deleted=True, preserves reviews and tags."""
    book = get_book(db, book_id)
    book.is_deleted = True
    book.deleted_at = datetime.now(timezone.utc)
    book.updated_at = datetime.now(timezone.utc)
    db.commit()


def restore_book(db: Session, book_id: int) -> models.Book:
    """Restore a soft-deleted book. 404 if not found, 400 if not deleted."""
    book = get_book_include_deleted(db, book_id)
    if not book.is_deleted:
        raise HTTPException(status_code=400, detail=f"Book with id {book_id} is not deleted")
    book.is_deleted = False
    book.deleted_at = None
    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


# ═══ Reviews ═════════════════════════════════════════════

def create_review(db: Session, book_id: int, data: schemas.ReviewCreate):
    get_book(db, book_id)  # 404/410 check
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


# ═══ Discount ════════════════════════════════════════════

def apply_discount(db: Session, book_id: int, data: schemas.DiscountRequest):
    book = get_book(db, book_id)
    current_year = datetime.now(timezone.utc).year
    if current_year - book.published_year < 1:
        raise HTTPException(
            status_code=400,
            detail="Discount can only be applied to books published more than 1 year ago",
        )
    discounted = round(book.price * (1 - data.discount_percent / 100), 2)
    return schemas.DiscountResponse(
        book_id=book.id, title=book.title,
        original_price=book.price,
        discount_percent=data.discount_percent,
        discounted_price=discounted,
    )


# ═══ Stock ═══════════════════════════════════════════════

def update_stock(db: Session, book_id: int, quantity: int):
    book = get_book(db, book_id)
    new_stock = book.stock + quantity
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {book.stock}, requested change: {quantity}",
        )
    book.stock = new_stock
    book.updated_at = datetime.now(timezone.utc)
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
            models.Tag.id != tag_id,
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Tag '{update['name']}' already exists")
    for k, v in update.items():
        setattr(tag, k, v)
    tag.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int):
    tag = get_tag(db, tag_id)
    if len(tag.books) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete tag with {len(tag.books)} associated book(s). Remove tag from books first.",
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
    book_ids = [item.book_id for item in data.items]
    if len(book_ids) != len(set(book_ids)):
        raise HTTPException(status_code=400, detail="Duplicate book_id in order items")

    order_items = []
    for item in data.items:
        book = get_book(db, item.book_id)
        if book.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for book '{book.title}'. "
                       f"Available: {book.stock}, requested: {item.quantity}",
            )
        order_items.append((book, item))

    order = models.Order(
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        status="pending",
    )
    db.add(order)
    db.flush()

    for book, item in order_items:
        oi = models.OrderItem(
            order_id=order.id, book_id=item.book_id,
            quantity=item.quantity, unit_price=book.price,
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
                   f"Allowed transitions: {allowed if allowed else 'none (terminal state)'}",
        )
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
                   f"Only pending or cancelled orders can be deleted.",
        )
    if order.status == "pending":
        for item in order.items:
            book = db.query(models.Book).filter(models.Book.id == item.book_id).first()
            if book:
                book.stock += item.quantity
    db.delete(order)
    db.commit()


def get_order_response(order: models.Order) -> dict:
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
    get_author(db, author_id)
    q = db.query(models.Book).filter(
        models.Book.author_id == author_id,
        models.Book.is_deleted == False,
    )
    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return schemas.PaginatedBooks(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


# ── Bulk Create Books ────────────────────────────────────

def bulk_create_books(db: Session, data: schemas.BulkBookCreate) -> schemas.BulkCreateResponse:
    results = []
    created_count = 0
    failed_count = 0

    for i, book_data in enumerate(data.books):
        try:
            author = db.query(models.Author).filter(models.Author.id == book_data.author_id).first()
            if not author:
                raise ValueError(f"Author with id {book_data.author_id} not found")
            cat = db.query(models.Category).filter(models.Category.id == book_data.category_id).first()
            if not cat:
                raise ValueError(f"Category with id {book_data.category_id} not found")
            if db.query(models.Book).filter(models.Book.isbn == book_data.isbn).first():
                raise ValueError(f"Book with ISBN '{book_data.isbn}' already exists")

            book = models.Book(**book_data.model_dump())
            db.add(book)
            db.flush()
            db.refresh(book)
            results.append(schemas.BulkResultItem(index=i, status="created", book=book))
            created_count += 1
        except (ValueError, Exception) as e:
            results.append(schemas.BulkResultItem(index=i, status="error", error=str(e)))
            failed_count += 1

    if created_count > 0:
        db.commit()
    else:
        db.rollback()

    return schemas.BulkCreateResponse(
        total=len(data.books), created=created_count,
        failed=failed_count, results=results,
    )


# ── Clone Book ───────────────────────────────────────────

def clone_book(db: Session, book_id: int, data: schemas.BookCloneRequest) -> models.Book:
    source = get_book(db, book_id)
    if db.query(models.Book).filter(models.Book.isbn == data.new_isbn).first():
        raise HTTPException(status_code=409, detail=f"Book with ISBN '{data.new_isbn}' already exists")
    clone = models.Book(
        title=data.new_title or f"{source.title} (copy)",
        isbn=data.new_isbn, price=source.price,
        published_year=source.published_year, stock=data.stock,
        author_id=source.author_id, category_id=source.category_id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


# ── Invoice ──────────────────────────────────────────────

def generate_invoice(db: Session, order_id: int) -> schemas.InvoiceResponse:
    order = get_order(db, order_id)
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
            quantity=oi.quantity, unit_price=oi.unit_price, line_total=line_total,
        ))
        subtotal += line_total
    return schemas.InvoiceResponse(
        invoice_number=f"INV-{order.id:06d}", order_id=order.id,
        customer_name=order.customer_name, customer_email=order.customer_email,
        status=order.status, issued_at=datetime.now(timezone.utc).isoformat(),
        items=items, subtotal=round(subtotal, 2), item_count=len(items),
    )


# ── Add Item to Pending Order ────────────────────────────

def add_item_to_order(db: Session, order_id: int, data: schemas.OrderAddItem) -> models.Order:
    order = get_order(db, order_id)
    if order.status != "pending":
        raise HTTPException(
            status_code=403,
            detail=f"Cannot modify order in '{order.status}' state. Only pending orders can be modified.",
        )
    existing_book_ids = {oi.book_id for oi in order.items}
    if data.book_id in existing_book_ids:
        raise HTTPException(
            status_code=409,
            detail=f"Book {data.book_id} is already in this order.",
        )
    book = get_book(db, data.book_id)
    if book.stock < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for book '{book.title}'. "
                   f"Available: {book.stock}, requested: {data.quantity}",
        )
    oi = models.OrderItem(
        order_id=order.id, book_id=data.book_id,
        quantity=data.quantity, unit_price=book.price,
    )
    db.add(oi)
    book.stock -= data.quantity
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


# ── Statistics ───────────────────────────────────────────

def get_statistics(db: Session) -> schemas.StatisticsSummary:
    total_books = db.query(models.Book).filter(models.Book.is_deleted == False).count()
    in_stock = db.query(models.Book).filter(
        models.Book.stock > 0, models.Book.is_deleted == False,
    ).count()

    delivered = db.query(models.Order).filter(models.Order.status == "delivered").all()
    revenue = sum(
        sum(i.unit_price * i.quantity for i in order.items)
        for order in delivered
    )

    avg_price = None
    if total_books > 0:
        prices = [b.price for b in db.query(models.Book).filter(models.Book.is_deleted == False).all()]
        avg_price = round(sum(prices) / len(prices), 2)

    avg_rating = None
    reviews = db.query(models.Review).all()
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 2)

    status_counts = {}
    for status in ["pending", "confirmed", "shipped", "delivered", "cancelled"]:
        status_counts[status] = db.query(models.Order).filter(models.Order.status == status).count()

    return schemas.StatisticsSummary(
        total_authors=db.query(models.Author).count(),
        total_categories=db.query(models.Category).count(),
        total_books=total_books,
        total_tags=db.query(models.Tag).count(),
        total_orders=db.query(models.Order).count(),
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
    updated_at: datetime

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
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Tags ─────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=30)


class TagResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

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
    updated_at: datetime
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
    status: str
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


# ── Cover Upload ─────────────────────────────────────────

class CoverUploadResponse(BaseModel):
    book_id: int
    filename: str
    content_type: str
    size_bytes: int


# ── Export Jobs ──────────────────────────────────────────

class ExportJobCreated(BaseModel):
    job_id: str
    status: str
    created_at: str


class ExportJobResult(BaseModel):
    job_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    total: Optional[int] = None
    data: Optional[list] = None


# ── Maintenance ──────────────────────────────────────────

class MaintenanceToggle(BaseModel):
    enabled: bool


class MaintenanceStatus(BaseModel):
    maintenance_mode: bool
    message: str


# ═══ FILE: app/models.py ═══


from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base
from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey,
    CheckConstraint, DateTime, Table, Boolean,
)


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    born_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    books = relationship("Book", back_populates="author")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    published_year = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_price_positive"),
        CheckConstraint("stock >= 0", name="check_stock_positive"),
    )

    author = relationship("Author", back_populates="books")
    category = relationship("Category", back_populates="books")
    tags = relationship("Tag", secondary=book_tags, back_populates="books")
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
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
