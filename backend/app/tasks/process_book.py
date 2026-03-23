from __future__ import annotations

import os
import logging
import tempfile
from typing import Dict, Any, List
from typing import List
from pypdf import PdfReader
from app.services.storage import StorageProvider, get_storage
from app.services.llm import LLMProvider, get_llm_provider
from app.sync_db import get_pool

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 HELPER: DOWNLOAD FILE TO TEMP LOCATION
# ============================================================


def download_to_temp_file(storage, key: str) -> str:
    """
    Download a file from storage (MinIO/S3) as a stream and save it to a temp file.

    WHY THIS EXISTS:
    ----------------
    - Avoid loading full file into memory (important for large PDFs)
    - Enables streaming-based processing
    - Works for large files (50MB+)

    HOW IT WORKS:
    -------------
    storage → stream → write chunks → temp file

    Example:
    --------
    key = "abc123.pdf"

    returns:
        "/tmp/tmpxyz123.pdf"
    """

    response = storage.client.get_object(storage.bucket, key)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in response.stream(32 * 1024):  # 32KB chunks
                tmp.write(chunk)

            temp_path: str = tmp.name

        logger.info(f"File downloaded to temp path: {temp_path}")
        return temp_path

    finally:
        # Important to prevent connection leaks
        response.close()
        response.release_conn()


# ============================================================
# 🔹 HELPER: EXTRACT TEXT FROM PDF
# ============================================================


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text using pypdf (lightweight, pure Python).

    PROS:
    - No heavy dependencies
    - Easy to use

    CONS:
    - Less accurate than PyMuPDF
    - Some PDFs may return poor text
    """

    reader = PdfReader(file_path)

    texts: List[str] = []

    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            texts.append(page_text)

        except Exception as e:
            logger.warning(f"Failed to extract page {i + 1}: {e}")

    full_text: str = "\n".join(texts)

    logger.info(f"Extracted {len(texts)} pages, total length={len(full_text)}")

    return full_text


# ============================================================
# 🔹 HELPER: CHUNK TEXT
# ============================================================


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """
    Split text into smaller chunks.

    WHY THIS EXISTS:
    ----------------
    LLMs have token limits.
    We cannot send entire book at once.

    HOW IT WORKS:
    -------------
    Splits text into fixed-size character chunks.

    Example:
    --------
    text = "abcdefghij"
    chunk_size = 4

    output:
        ["abcd", "efgh", "ij"]
    """

    chunks: List[str] = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        chunks.append(chunk)

    logger.info(f"Created {len(chunks)} chunks")

    return chunks


# ============================================================
# 🔹 HELPER: LOG CHUNKS (PREVIEW)
# ============================================================


def log_chunks(chunks: List[str], preview_size: int = 100) -> None:
    """
    Log chunk previews for debugging.

    WHY THIS EXISTS:
    ----------------
    - To verify what is being sent to LLM
    - Avoid logging full content (huge logs)

    HOW IT WORKS:
    -------------
    Logs only first N characters of each chunk.

    Example:
    --------
    chunk = "This is a very long text..."

    log:
        "Chunk 1: This is a very long text..."
    """

    for idx, chunk in enumerate(chunks):
        preview = chunk[:preview_size].replace("\n", " ")
        logger.info(f"Chunk {idx + 1}: {preview}...")


# ============================================================
# 🔹 MAIN TASK
# ============================================================


def process_book(book: Dict[str, Any]) -> str | None:
    logger.info(
        f"Processing book: {book.get('id')} - "
        f"{book.get('title')} by {book.get('author')}"
    )

    file_key = book.get("file_path")

    if not file_key:
        logger.error(f"Book {book.get('id')} has no file path")
        return

    temp_file_path: str | None = None

    try:

        # 0. Get LLM Provider and Storage (Factory)
        llm: LLMProvider = get_llm_provider()
        storage: StorageProvider = get_storage()

        # 1. Download file
        temp_file_path = download_to_temp_file(storage, file_key)

        # 2. Extract text
        text = extract_text_from_pdf(temp_file_path)

        if not text.strip():
            logger.warning(f"No text extracted for book {book.get('id')}")
            return

        # 3. Chunk text
        chunks = chunk_text(text, chunk_size=1000)

        # 4. Log chunks
        log_chunks(chunks)

        # 5. Summarize each chunk
        summaries: List[str] = []

        for idx, chunk in enumerate(chunks):
            try:
                summary = llm.summarize(chunk)
                summaries.append(summary)
                logger.info(f"Summarized chunk {idx + 1}/{len(chunks)}")

            except Exception as e:
                logger.warning(f"Failed to summarize chunk {idx + 1}: {e}")
        if not summaries:
            logger.warning(f"No summaries generated for book {book.get('id')}")
            return "No summaries generated"

        # 6. Combine summaries
        combined_summary = llm.combine(summaries)

        # 7. Save summary to DB
        pool = get_pool()
        with pool.connection() as conn:
            query = """
            UPDATE books
            SET summary = %s
            status = 'processed'
            WHERE id = %s
            RETURNING id;
            """
            with conn.cursor() as cur:
                cur.execute(query, (combined_summary, book.get("id")))
                result = cur.fetchone()

                if not result:
                    logger.error(f"Failed to update summary for book {book.get('id')}")
                    return
        logger.info(f"Finished processing book {book.get('id')}")
        return combined_summary

    except Exception as e:
        logger.exception(f"Failed processing book {book.get('id')}: {str(e)}")

    finally:
        # cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Deleted temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to delete temp file {temp_file_path}: {cleanup_error}"
                )
