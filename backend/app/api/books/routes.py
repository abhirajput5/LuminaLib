from __future__ import annotations
import logging
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException

from app.async_db import get_pool, PoolType
from app.repositories.book_repo import BookRepository
from app.services.book_service import BookService
from app.services.storage import get_storage
from app.api.books.models import BookResponse, BookListResponse
from app.utils import get_current_user_id

from app.exceptions.book_exceptions import (
    BookAlreadyExists,
    InvalidBookData,
    BookFileUploadFailed,
    BookNotFound,
    BookUpdateConflict,
    BookAlreadyBorrowed,
    InvalidBorrowRequest,
    BorrowRecordNotFound,
    BookReviewConflict,
    InvalidBookReview,
)

from app.exceptions.db_exceptions import DatabaseException


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


# ============================================================
# DEPENDENCY
# ============================================================


def get_book_service(
    pool: Annotated[PoolType, Depends(get_pool)],
) -> BookService:
    repo = BookRepository(pool)
    storage = get_storage()
    return BookService(repo, storage)


# ============================================================
# CREATE BOOK
# ============================================================


@router.post("", response_model=BookResponse)
async def create_book(
    title: Annotated[str, Form(...)],
    author: Annotated[str, Form()],
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[BookService, Depends(get_book_service)],
    file: UploadFile = File(...),
):
    logger.info("Create book request received")

    if file.filename is None:
        raise HTTPException(status_code=400, detail="File is required")

    try:
        file_bytes = await file.read()

        book = await service.create_book(
            title=title,
            author=author,
            file_bytes=file_bytes,
            filename=file.filename,
            uploaded_by=user_id,
        )

        logger.info(
            "Book created successfully",
            extra={"book_id": book.get("id"), "user_id": user_id},
        )

        return book

    except BookAlreadyExists as e:
        raise HTTPException(status_code=409, detail=str(e))

    except InvalidBookData as e:
        raise HTTPException(status_code=400, detail=str(e))

    except BookFileUploadFailed as e:
        raise HTTPException(status_code=500, detail=str(e))

    except DatabaseException:
        logger.exception("DB error in create_book")
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception:
        logger.exception("Unexpected error in create_book")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# LIST BOOKS
# ============================================================


@router.get("", response_model=BookListResponse)
async def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    limit: int = Query(10, le=100),
    offset: int = Query(0),
):
    logger.info(
        "List books request",
        extra={"user_id": user_id, "limit": limit, "offset": offset},
    )

    try:
        items = await service.list_books(limit, offset)

        logger.info(
            "List books success",
            extra={"user_id": user_id, "count": len(items)},
        )

        return {
            "items": items,
            "total": len(items),
        }

    except DatabaseException:
        logger.exception("List books failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# GET BOOK
# ============================================================


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
):
    logger.info(f"Get book request: {book_id}")

    try:
        book = await service.get_book(book_id)

        logger.info(f"Get book success: {book_id}")

        return book

    except BookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    except DatabaseException:
        logger.exception("Get book failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# UPDATE BOOK
# ============================================================


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    service: Annotated[BookService, Depends(get_book_service)],
    book_id: int,
    title: Annotated[str | None, Form()] = None,
    author: Annotated[str | None, Form()] = None,
    file: UploadFile | None = File(None),
):
    logger.info(
        "Update book request",
        extra={
            "book_id": book_id,
            "title": title,
            "author": author,
            "has_file": file is not None,
        },
    )

    data: Dict[str, Any] = {}

    if title is not None:
        data["title"] = title
    if author is not None:
        data["author"] = author

    try:
        file_bytes = await file.read() if file else None
        filename = file.filename if file else None

        book = await service.update_book(
            book_id=book_id,
            data=data,
            file_bytes=file_bytes,
            filename=filename,
        )

        logger.info("Book updated successfully", extra={"book_id": book_id})

        return book

    except BookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    except BookUpdateConflict as e:
        raise HTTPException(status_code=409, detail=str(e))

    except InvalidBookData as e:
        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseException:
        logger.exception("Update failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception:
        logger.exception("Unexpected error in update_book")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# DELETE BOOK
# ============================================================


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
):
    logger.info("Delete book request", extra={"book_id": book_id})

    try:
        await service.delete_book(book_id)

        logger.info("Book deleted successfully", extra={"book_id": book_id})

        return {"message": "Book deleted"}

    except BookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    except DatabaseException:
        logger.exception("Delete failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# BORROW BOOK
# ============================================================


@router.post("/{book_id}/borrow")
async def borrow_book(
    book_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    logger.info(
        "Borrow book request",
        extra={"book_id": book_id, "user_id": user_id},
    )

    try:
        await service.borrow_book(user_id, book_id)

        logger.info(
            "Book borrowed successfully",
            extra={"book_id": book_id, "user_id": user_id},
        )

        return {"message": "Book borrowed"}

    except BookAlreadyBorrowed as e:
        raise HTTPException(status_code=409, detail=str(e))

    except InvalidBorrowRequest as e:
        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseException:
        logger.exception("Borrow failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# RETURN BOOK
# ============================================================


@router.post("/{book_id}/return")
async def return_book(
    book_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    logger.info(
        "Return book request",
        extra={"book_id": book_id, "user_id": user_id},
    )

    try:
        await service.return_book(user_id, book_id)

        logger.info(
            "Book returned successfully",
            extra={"book_id": book_id, "user_id": user_id},
        )

        return {"message": "Book returned"}

    except BorrowRecordNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    except DatabaseException:
        logger.exception("Return failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{book_id}/review")
async def create_book_review(
    book_id: int,
    content: Annotated[str, Form(...)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    logger.info(
        "Create book review request",
        extra={"book_id": book_id, "user_id": user_id},
    )

    try:
        await service.create_book_review(user_id, book_id, content)

        logger.info(
            "Book review created successfully",
            extra={"book_id": book_id, "user_id": user_id},
        )

        return {"message": "Review submitted"}

    except BookNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    except BookReviewConflict as e:
        raise HTTPException(status_code=409, detail=str(e))

    except InvalidBookReview as e:
        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseException:
        logger.exception("Create review failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============
# BOOK ANALYSIS
# =============


@router.get("/{book_id}/analysis")
async def get_book_analysis(
    book_id: int,
    service: BookService = Depends(get_book_service),
) -> Dict[str, Any]:
    try:
        return await service.get_book_analysis(book_id)

    except DatabaseException:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch book analysis",
        )


@router.get("/book/recommendations")
async def get_recommendations(
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: BookService = Depends(get_book_service),
) -> Dict[str, Any]:
    """
    PURPOSE:
    --------
    Fetch personalized recommendations for the logged-in user.

    FLOW:
    -----
    1. Extract user_id from auth dependency
    2. Call service layer
    3. Return ranked recommendations
    """

    try:
        logger.info(f"Get user recommndation for user: {user_id}")
        return await service.get_recommendations(user_id)
    except DatabaseException:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch recommendations",
        )
