from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from psycopg.rows import dict_row, DictRow
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection, errors
from psycopg import sql

from app.exceptions.db_exceptions import (
    DatabaseConnectionError,
    QueryExecutionError,
    IntegrityError as DBIntegrityError,
    RecordNotFound,
    DuplicateRecord,
)

logger = logging.getLogger(__name__)


class BookRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[DictRow]]) -> None:
        self.pool = pool

    # ============================
    # INTERNAL: UPSERT USER PREF
    # ============================
    async def _upsert_user_preference(
        self,
        conn,
        user_id: int,
        key: str,
        score: float,
    ) -> None:

        query: str = """
        INSERT INTO user_preferences (user_id, preference_key, preference_score)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, preference_key)
        DO UPDATE SET
            preference_score = user_preferences.preference_score + EXCLUDED.preference_score;
        """

        async with conn.cursor() as cur:
            await cur.execute(query, (user_id, key, score))

    # ============================
    # CREATE BOOK
    # ============================
    async def create_book(
        self,
        title: str,
        author: Optional[str],
        file_path: str,
        file_type: str,
        uploaded_by: Optional[int],
        file_size: Optional[int] = None,
        page_count: Optional[int] = None,
    ) -> Dict[str, Any]:

        query: str = """
        INSERT INTO books (
            title, author, file_path, file_type,
            uploaded_by, file_size, page_count
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        query,
                        (
                            title,
                            author,
                            file_path,
                            file_type,
                            uploaded_by,
                            file_size,
                            page_count,
                        ),
                    )
                    result = await cur.fetchone()

                    if not result:
                        raise QueryExecutionError("Failed to create book")

                    return result

        except errors.UniqueViolation as exc:
            raise DuplicateRecord("book already exists for the author") from exc

        except errors.ForeignKeyViolation as exc:
            raise DBIntegrityError("Invalid foreign key") from exc

        except errors.NotNullViolation as exc:
            raise DBIntegrityError("Missing required field") from exc

        except errors.CheckViolation as exc:
            raise DBIntegrityError("Constraint check failed") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Create book failed")
            raise QueryExecutionError("Create book query failed") from exc

    # ============================
    # GET BOOK BY ID
    # ============================
    async def get_by_id(self, book_id: int) -> Dict[str, Any]:

        query: str = """
        SELECT * FROM books
        WHERE id = %s AND is_deleted = FALSE;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (book_id,))
                    result = await cur.fetchone()
                    if not result:
                        raise RecordNotFound(f"Book {book_id} not found")
                    return result
        except RecordNotFound:
            raise
        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc
        except Exception as exc:
            logger.exception("Get book failed")
            raise QueryExecutionError("Fetch book failed") from exc

    # ============================
    # LIST BOOKS
    # ============================
    async def list(self, limit: int, offset: int) -> List[Dict[str, Any]]:

        query: str = """
        SELECT * FROM books
        WHERE is_deleted = FALSE
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (limit, offset))
                    return await cur.fetchall()

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("List books failed")
            raise QueryExecutionError("List query failed") from exc

    # ============================
    # UPDATE BOOK
    # ============================
    async def update(
        self,
        book_id: int,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        columns = [sql.Identifier(k) for k in data.keys()]
        values = list(data.values())

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(col) for col in columns
        )

        query = sql.SQL(
            """
            UPDATE books
            SET {set_clause},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND is_deleted = FALSE
            RETURNING *;
            """
        ).format(set_clause=set_clause)

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (*values, book_id))
                    result = await cur.fetchone()

                    if not result:
                        raise RecordNotFound(f"Book {book_id} not found")

                    return result

        except errors.UniqueViolation as exc:
            raise DuplicateRecord("Duplicate data") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Update failed")
            raise QueryExecutionError("Update query failed") from exc

    # ============================
    # DELETE BOOK
    # ============================
    async def delete(self, book_id: int) -> None:

        query: str = """
        UPDATE books
        SET is_deleted = TRUE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (book_id,))

                    if cur.rowcount == 0:
                        raise RecordNotFound(f"Book {book_id} not found")

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Delete failed")
            raise QueryExecutionError("Delete query failed") from exc

    # ============================
    # BORROW BOOK
    # ============================
    async def borrow(self, user_id: int, book_id: int) -> None:

        insert_query: str = """
        INSERT INTO user_books (user_id, book_id)
        VALUES (%s, %s);
        """

        book_query: str = """
        SELECT title, author
        FROM books
        WHERE id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:

                    await cur.execute(insert_query, (user_id, book_id))

                    await cur.execute(book_query, (book_id,))
                    book = await cur.fetchone()

                    if book:
                        await self._upsert_user_preference(
                            conn, user_id, book["title"], 1.0
                        )
                        if book.get("author"):
                            await self._upsert_user_preference(
                                conn, user_id, book["author"], 0.5
                            )

        except errors.UniqueViolation as exc:
            raise DuplicateRecord("Book already borrowed") from exc

        except errors.ForeignKeyViolation as exc:
            raise DBIntegrityError("Invalid book_id") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Borrow failed")
            raise QueryExecutionError("Borrow query failed") from exc

    # ============================
    # RETURN BOOK
    # ============================
    async def return_book(self, user_id: int, book_id: int) -> None:

        query: str = """
        UPDATE user_books
        SET returned_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
          AND book_id = %s
          AND returned_at IS NULL;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id, book_id))

                    if cur.rowcount == 0:
                        raise RecordNotFound("Borrow record not found")

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Return failed")
            raise QueryExecutionError("Return query failed") from exc

    # ============================
    # CHECK BORROWED
    # ============================
    async def has_borrowed(self, user_id: int, book_id: int) -> bool:

        query: str = """
        SELECT 1 FROM user_books
        WHERE user_id = %s
          AND book_id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id, book_id))
                    return (await cur.fetchone()) is not None

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Check borrowed failed")
            raise QueryExecutionError("Check query failed") from exc

    # ============================
    # CREATE BOOK REVIEW
    # ============================
    async def create_book_review(
        self,
        user_id: int,
        book_id: int,
        content: str,
    ) -> Dict[str, Any]:

        insert_query: str = """
        INSERT INTO reviews (user_id, book_id, content, created_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING *;
        """

        book_query: str = """
        SELECT title, author
        FROM books
        WHERE id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:

                    await cur.execute(insert_query, (user_id, book_id, content))
                    result = await cur.fetchone()

                    if not result:
                        raise QueryExecutionError("Failed to create review")

                    await cur.execute(book_query, (book_id,))
                    book = await cur.fetchone()

                    if book:
                        await self._upsert_user_preference(
                            conn, user_id, book["title"], 1.5
                        )
                        if book.get("author"):
                            await self._upsert_user_preference(
                                conn, user_id, book["author"], 0.75
                            )

                    return result

        except errors.UniqueViolation as exc:
            raise DuplicateRecord("User has already reviewed this book") from exc

        except errors.ForeignKeyViolation as exc:
            raise DBIntegrityError("Invalid user_id or book_id") from exc

        except errors.NotNullViolation as exc:
            raise DBIntegrityError("Missing required field") from exc

        except errors.CheckViolation as exc:
            raise DBIntegrityError("Constraint check failed") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Create review failed")
            raise QueryExecutionError("Create review query failed") from exc

    # ============================
    # UPSERT REVIEW ANALYSIS
    # ============================
    async def upsert_review_analysis(
        self,
        book_id: int,
        summary: str,
        sentiment_score: float,
    ) -> Dict[str, Any]:

        query: str = """
        INSERT INTO book_review_analysis (book_id, summary, sentiment_score)
        VALUES (%s, %s, %s)
        ON CONFLICT (book_id)
        DO UPDATE SET
            summary = EXCLUDED.summary,
            sentiment_score = EXCLUDED.sentiment_score,
            updated_at = CURRENT_TIMESTAMP
        RETURNING *;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (book_id, summary, sentiment_score))
                    result = await cur.fetchone()

                    if not result:
                        raise QueryExecutionError("Failed to upsert review analysis")

                    return result

        except errors.ForeignKeyViolation as exc:
            raise DBIntegrityError("Invalid book_id") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Upsert review analysis failed")
            raise QueryExecutionError("Upsert analysis failed") from exc

    # ============================
    # GET REVIEW ANALYSIS
    # ============================
    async def get_book_review_analysis(self, book_id: int) -> Optional[Dict[str, Any]]:
        query: str = """
        SELECT book_id, summary, sentiment_score, updated_at
        FROM book_review_analysis
        WHERE book_id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (book_id,))
                    return await cur.fetchone()

        except errors.ForeignKeyViolation as exc:
            raise DBIntegrityError("Invalid book reference") from exc

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Get review analysis failed")
            raise QueryExecutionError("Fetch analysis query failed") from exc

    # ============================
    # GET USER PREFERENCES
    # ============================
    async def get_user_preferences(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        PURPOSE:
        --------
        Fetch accumulated user preference signals.

        INTENT:
        -------
        - Used by recommendation engine
        - Represents user's interests derived from behavior
        """

        query: str = """
        SELECT preference_key, preference_score
        FROM user_preferences
        WHERE user_id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (user_id,))
                    return await cur.fetchall()

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Fetch user preferences failed")
            raise QueryExecutionError("Fetch preferences failed") from exc

    async def get_user_borrowed_books(
        self,
        user_id: int,
    ) -> List[int]:
        """
        Fetch all borrowed book IDs for a given user.

        Flow:
        - Executes a SELECT query on user_books
        - Extracts book_id from result rows
        - Returns list of integers

        Raises:
        - DatabaseConnectionError: if DB connection fails
        - QueryExecutionError: if query execution fails
        """

        query: str = """
        SELECT book_id
        FROM user_books
        WHERE user_id = %s;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id,))
                    rows = await cur.fetchall()

                    # Using dict_row → access via key
                    return [row["book_id"] for row in rows]

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except errors.Error as exc:
            logger.exception("Fetch borrowed books query failed")
            raise QueryExecutionError("Fetch borrowed failed") from exc

    # ============================
    # GET ALL BOOKS (FOR RECOMMENDATION)
    # ============================
    async def get_all_books(self) -> List[Dict[str, Any]]:

        query: str = """
        SELECT id, title, author
        FROM books
        WHERE is_deleted = FALSE;
        """

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query)
                    return await cur.fetchall()

        except errors.ConnectionException as exc:
            raise DatabaseConnectionError("DB connection failed") from exc

        except Exception as exc:
            logger.exception("Fetch all books failed")
            raise QueryExecutionError("Fetch books failed") from exc
