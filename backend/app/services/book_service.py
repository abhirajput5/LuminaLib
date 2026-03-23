from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from app.repositories.book_repo import BookRepository
from app.services.storage import StorageProvider
from app.tasks.task_publisher import TaskPublisher

from app.exceptions.db_exceptions import (
    DuplicateRecord,
    RecordNotFound,
    IntegrityError as DBIntegrityError,
    DatabaseException,
)

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

logger = logging.getLogger(__name__)


class BookService:
    def __init__(
        self,
        repo: BookRepository,
        storage: StorageProvider,
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.publisher = TaskPublisher()

    # ============================================================
    # CREATE BOOK
    # ============================================================
    async def create_book(
        self,
        title: str,
        author: Optional[str],
        file_bytes: bytes,
        filename: str,
        uploaded_by: Optional[int],
    ) -> Dict[str, Any]:

        logger.info(
            "Starting book creation",
            extra={
                "title": title,
                "uploaded_by": uploaded_by,
                "book_file_name": filename,
            },
        )

        try:
            # Step 1: Upload file
            file_path: str = await self.storage.upload(file_bytes, filename)
            file_type: str = filename.split(".")[-1]

            logger.info(
                "File uploaded",
                extra={
                    "file_path": file_path,
                    "file_type": file_type,
                },
            )

            # Step 2: Save DB record
            book = await self.repo.create_book(
                title=title,
                author=author,
                file_path=file_path,
                file_type=file_type,
                uploaded_by=uploaded_by,
            )

            logger.info(
                "Book record created",
                extra={
                    "book_id": book.get("id"),
                    "uploaded_by": uploaded_by,
                },
            )

            # Step 3: Trigger async processing
            self.publisher.publish(
                task_name="process_book_task",
                payload=book,
            )

            logger.info(
                "Celery event triggered",
                extra={"book_id": book.get("id")},
            )

            return book

        except DuplicateRecord as exc:
            logger.error(
                "Duplicate book detected during creation",
                extra={"title": title, "uploaded_by": uploaded_by},
            )
            raise BookAlreadyExists(str(exc))

        except DBIntegrityError as exc:
            logger.error(
                "Data integrity error during book creation", extra={"error": str(exc)}
            )
            raise InvalidBookData("Invalid book data")

        except Exception as exc:
            # Temporary heuristic (replace later with proper exception)
            if "upload" in str(exc).lower():
                raise BookFileUploadFailed("File upload failed") from exc

            logger.exception(
                "Create book workflow failed",
                extra={"title": title, "uploaded_by": uploaded_by},
            )
            raise

    # ============================================================
    # GET BOOK
    # ============================================================
    async def get_book(self, book_id: int) -> Dict[str, Any]:

        logger.debug("Fetching book", extra={"book_id": book_id})

        try:
            return await self.repo.get_by_id(book_id)

        except RecordNotFound:
            logger.info(f"Book not found: {book_id}")
            raise BookNotFound(f"Book {book_id} not found")

        except DatabaseException:
            logger.exception("Get book failed", extra={"book_id": book_id})
            raise

    # ============================================================
    # LIST BOOKS
    # ============================================================
    async def list_books(
        self,
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:

        logger.debug(
            "Listing books",
            extra={"limit": limit, "offset": offset},
        )

        try:
            books = await self.repo.list(limit, offset)

            logger.info(
                "Books retrieved",
                extra={
                    "count": len(books),
                    "limit": limit,
                    "offset": offset,
                },
            )

            return books

        except DatabaseException:
            logger.exception(
                "List books failed",
                extra={"limit": limit, "offset": offset},
            )
            raise

    # ============================================================
    # UPDATE BOOK
    # ============================================================
    async def update_book(
        self,
        book_id: int,
        data: Dict[str, Any],
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:

        logger.info(
            "Updating book",
            extra={
                "book_id": book_id,
                "fields": list(data.keys()),
                "file_update": bool(file_bytes and filename),
            },
        )

        try:
            # File update case
            if file_bytes and filename:
                file_path: str = await self.storage.upload(file_bytes, filename)
                file_type: str = filename.split(".")[-1]

                logger.info(
                    "File updated for book",
                    extra={"book_id": book_id, "file_path": file_path},
                )

                data.update(
                    {
                        "file_path": file_path,
                        "file_type": file_type,
                        "status": "processing",
                    }
                )

            book = await self.repo.update(book_id, data)

            logger.info("Book updated successfully", extra={"book_id": book_id})

            return book

        except RecordNotFound:
            raise BookNotFound(f"Book {book_id} not found")

        except DuplicateRecord:
            raise BookUpdateConflict("Update caused duplicate conflict")

        except DBIntegrityError:
            raise InvalidBookData("Invalid update data")

        except Exception:
            logger.exception("Update book workflow failed", extra={"book_id": book_id})
            raise

    # ============================================================
    # DELETE BOOK
    # ============================================================
    async def delete_book(self, book_id: int) -> None:

        logger.info("Deleting book", extra={"book_id": book_id})

        try:
            await self.repo.delete(book_id)

            logger.info("Book deleted successfully", extra={"book_id": book_id})

        except RecordNotFound:
            raise BookNotFound(f"Book {book_id} not found")

        except DatabaseException:
            logger.exception("Delete book failed", extra={"book_id": book_id})
            raise

    # ============================================================
    # BORROW BOOK
    # ============================================================
    async def borrow_book(self, user_id: int, book_id: int) -> None:

        logger.info(
            "Borrow book request",
            extra={"user_id": user_id, "book_id": book_id},
        )

        try:
            await self.repo.borrow(user_id, book_id)

            logger.info(
                "Book borrowed successfully",
                extra={"user_id": user_id, "book_id": book_id},
            )

        except DuplicateRecord:
            raise BookAlreadyBorrowed("Book already borrowed")

        except DBIntegrityError:
            raise InvalidBorrowRequest("Invalid user or book")

        except DatabaseException:
            logger.exception(
                "Borrow book failed",
                extra={"user_id": user_id, "book_id": book_id},
            )
            raise

    # ============================================================
    # RETURN BOOK
    # ============================================================
    async def return_book(self, user_id: int, book_id: int) -> None:

        logger.info(
            "Return book request",
            extra={"user_id": user_id, "book_id": book_id},
        )

        try:
            await self.repo.return_book(user_id, book_id)

            logger.info(
                "Book returned successfully",
                extra={"user_id": user_id, "book_id": book_id},
            )

        except RecordNotFound:
            raise BorrowRecordNotFound("Borrow record not found")

        except DatabaseException:
            logger.exception(
                "Return book failed",
                extra={"user_id": user_id, "book_id": book_id},
            )
            raise

    # ============================================================
    # CREATE BOOK REVIEW
    # ============================================================
    async def create_book_review(
        self, user_id: int, book_id: int, content: str
    ) -> Dict[str, Any]:

        logger.info(
            "Create book review request",
            extra={"user_id": user_id, "book_id": book_id},
        )

        try:
            review = await self.repo.create_book_review(user_id, book_id, content)

            logger.info(
                "Book review created successfully",
                extra={"user_id": user_id, "book_id": book_id},
            )

            self.publisher.publish(
                task_name="process_review_task",
                payload=review,
            )

            return review

        except DuplicateRecord:
            raise BookReviewConflict("User has already reviewed this book")

        except DBIntegrityError:
            raise InvalidBookReview("Invalid review data")

        except DatabaseException:
            logger.exception(
                "Create book review failed",
                extra={"user_id": user_id, "book_id": book_id},
            )
            raise

    # ============================================================
    # GET BOOK REVIEW ANALYSIS
    # ============================================================
    async def get_book_analysis(self, book_id: int) -> Dict[str, Any]:

        logger.debug("Fetching book review analysis", extra={"book_id": book_id})

        try:
            analysis = await self.repo.get_book_review_analysis(book_id)

            if not analysis:
                return {
                    "book_id": book_id,
                    "summary": None,
                    "sentiment_score": None,
                    "status": "not_ready",
                }

            return {
                "book_id": analysis.get("book_id"),
                "summary": analysis.get("summary"),
                "sentiment_score": analysis.get("sentiment_score"),
                "status": "ready",
            }

        except DatabaseException:
            logger.exception(
                "Get book analysis failed",
                extra={"book_id": book_id},
            )
            raise

    # ============================================================
    # GET RECOMMENDATIONS
    # ============================================================
    async def get_recommendations(self, user_id: int) -> Dict[str, Any]:
        """
        PURPOSE:
        --------
        Generate personalized book recommendations for a user.

        INTENT:
        -------
        - Use existing behavioral signals (preferences + borrow history)
        - Rank books based on relevance
        - Keep this operation fast (no LLM, no async tasks)

        STEPS:
        ------
        1. Fetch user preferences
        2. Fetch books already borrowed
        3. Fetch all candidate books
        4. Score each book using preference matching
        5. Exclude already borrowed books
        6. Sort and return top results
        """

        try:
            logger.info(
                "Starting recommendation generation", extra={"user_id": user_id}
            )

            # Step 1: fetch user preference signals (what user likes)
            logger.debug("Fetching user preferences")
            preferences = await self.repo.get_user_preferences(user_id)

            # Step 2: fetch already borrowed books (to avoid recommending again)
            logger.debug("Fetching user borrowed books")
            borrowed_book_ids = set(await self.repo.get_user_borrowed_books(user_id))

            # Step 3: fetch all books (candidate pool)
            logger.debug("Fetching all books for recommendation pool")
            books = await self.repo.get_all_books()

            # Step 4: cold start (user has no preferences yet)
            if not preferences:
                logger.info(
                    "No preferences found → returning default recommendations",
                    extra={"user_id": user_id},
                )

                items = [
                    {
                        "id": book["id"],
                        "title": book["title"],
                        "score": 0.0,
                    }
                    for book in books
                    if book["id"] not in borrowed_book_ids
                ]

                return {"items": items[:10]}

            # Step 5: scoring books based on preferences
            logger.debug("Scoring books based on user preferences")

            scored: List[Dict[str, Any]] = []

            for book in books:
                # Skip already consumed books
                if book["id"] in borrowed_book_ids:
                    continue

                score = 0.0

                for pref in preferences:
                    key = pref["preference_key"].lower()
                    weight = pref["preference_score"]

                    title = (book.get("title") or "").lower()
                    author = (book.get("author") or "").lower()

                    # Match preference with title → strong signal
                    if key in title:
                        score += weight

                    # Match preference with author → weaker signal
                    if key in author:
                        score += weight * 0.5

                # Only include relevant books
                if score > 0:
                    scored.append(
                        {
                            "id": book["id"],
                            "title": book["title"],
                            "score": score,
                        }
                    )

            # Step 6: sort by score (highest relevance first)
            logger.debug(
                "Sorting recommendations by score",
                extra={"total_candidates": len(scored)},
            )

            scored.sort(key=lambda x: x["score"], reverse=True)

            # Step 7: return top N results
            logger.info(
                "Recommendation generation completed",
                extra={
                    "user_id": user_id,
                    "returned_items": len(scored[:10]),
                },
            )

            return {"items": scored[:10]}

        except Exception:
            logger.exception(
                "Recommendation generation failed",
                extra={"user_id": user_id},
            )
            raise
