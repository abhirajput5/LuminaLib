from __future__ import annotations

import logging
from typing import List

from app.sync_db import get_pool
from app.services.llm import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 HELPER: FETCH REVIEWS
# ============================================================
def fetch_reviews(conn, book_id: int) -> List[str]:
    """
    NOTE:
    -----
    Using dict_row → rows are dict-like, not tuples
    """

    query = """
    SELECT content
    FROM reviews
    WHERE book_id = %s
    ORDER BY created_at ASC;
    """

    with conn.cursor() as cur:
        cur.execute(query, (book_id,))
        rows = cur.fetchall()

    return [row["content"] for row in rows]


# ============================================================
# 🔹 HELPER: UPSERT ANALYSIS
# ============================================================
def upsert_analysis(conn, book_id: int, summary: str, score: float) -> None:
    query = """
    INSERT INTO book_review_analysis (book_id, summary, sentiment_score)
    VALUES (%s, %s, %s)
    ON CONFLICT (book_id)
    DO UPDATE SET
        summary = EXCLUDED.summary,
        sentiment_score = EXCLUDED.sentiment_score,
        updated_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(query, (book_id, summary, score))


# ============================================================
# 🔹 MAIN TASK: PROCESS REVIEW ANALYSIS
# ============================================================
def process_review(book_id: int) -> None:

    logger.info(f"Processing review analysis for book {book_id}")

    try:
        llm: LLMProvider = get_llm_provider()
        pool = get_pool()

        with pool.connection() as conn:

            # Step 1: Fetch reviews
            reviews = fetch_reviews(conn, book_id)

            if not reviews:
                logger.warning(f"No reviews found for book {book_id}")
                return

            # Step 2: Analyze via LLM
            summary, score = llm.analyze_reviews(reviews)

            logger.info("Analysis of reviews completed")

            # Step 3: Save analysis
            upsert_analysis(conn, book_id, summary, score)

            logger.info(f"Review analysis updated for book {book_id}")

    except Exception as e:
        logger.exception(f"Failed processing review analysis for book {book_id}: {e}")
