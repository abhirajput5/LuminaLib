from __future__ import annotations

import asyncio
import logging
from celery import Celery
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
    setup_logging,
)

from app.settings import settings
from app.sync_db import init_pool, close_pool
from app.tasks.process_book import process_book
from app.tasks.review_book import process_review
from app.logger import LoggerFactory


# ============================================================
# 🔥 Celery App
# ============================================================

celery_app: Celery = Celery(
    "lumina",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["app.tasks.book_task"])


# ============================================================
# 🔥 Logging Setup (Celery-native way)
# ============================================================


@setup_logging.connect
def setup_celery_logging(**kwargs: object) -> None:
    """
    Configure logging for BOTH main process and workers.
    This overrides Celery's default logging.
    """
    LoggerFactory.configure(
        service_name="celery",
        log_file="/logs/celery.log",
    )


logger: logging.Logger = LoggerFactory.get_logger(__name__)
logger.info("Celery worker starting...")


# ============================================================
# 🔥 Worker Lifecycle Hooks
# ============================================================


@worker_process_init.connect
def init_worker(**kwargs: object) -> None:
    """
    Runs inside EACH worker process.
    """
    logger.info("Worker process initializing...")
    init_pool()
    logger.info("Worker DB pool initialized")


@worker_process_shutdown.connect
def shutdown_worker(**kwargs: object) -> None:
    """
    Runs when worker shuts down.
    """
    logger.info("Worker process shutting down...")
    close_pool()
    logger.info("Worker DB pool closed")


# ============================================================
# 🔥 Task Definition
# ============================================================


@celery_app.task(name="process_book_task")
def process_book_task(book: dict) -> None:
    logger.info(
        "book.processing.started",
        extra={
            "event": "book.processing.started",
            "book_id": book.get("id"),
        },
    )

    process_book(book)

    logger.info(
        "book.processing.completed",
        extra={
            "event": "book.processing.completed",
            "book_id": book.get("id"),
        },
    )


@celery_app.task(name="process_review_task")
def process_review_task(review: dict) -> None:
    logger.info(
        "book.review.processing.started",
        extra={
            "event": "review.processing.started",
            "review_id": review.get("id"),
        },
    )
    book_id = review.get("book_id")
    if book_id:
        process_review(book_id)
    else:
        logger.warning("Book id was not found")

    logger.info(
        "book.review.processing.completed",
        extra={
            "event": "review.processing.completed",
            "review_id": review.get("id"),
        },
    )


logger.info("Celery worker initialized and ready to receive tasks")
