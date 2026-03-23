# app/schemas/book.py
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================
# REQUEST MODELS
# ============================


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Atomic Habits",
                "author": "James Clear",
            }
        }
    )


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Atomic Habits Updated",
                "author": "James Clear",
            }
        }
    )


# ============================
# RESPONSE MODELS
# ============================


class BookResponse(BaseModel):
    id: int
    title: str
    author: Optional[str]
    file_path: str
    file_type: str
    summary: Optional[str]
    status: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Atomic Habits",
                "author": "James Clear",
                "file_path": "/storage/uuid.pdf",
                "file_type": "pdf",
                "summary": "A practical guide to building habits...",
                "status": "ready",
            }
        },
    )


class BookListResponse(BaseModel):
    items: List[BookResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 1,
                        "title": "Atomic Habits",
                        "author": "James Clear",
                        "file_path": "/storage/uuid.pdf",
                        "file_type": "pdf",
                        "summary": "A practical guide to building habits...",
                        "status": "ready",
                    }
                ],
                "total": 1,
            }
        }
    )
