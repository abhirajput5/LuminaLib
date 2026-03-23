# app/db.py
from __future__ import annotations

from typing import Optional, TypeAlias
from psycopg.rows import dict_row, DictRow
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection
from app.settings import settings

PoolType: TypeAlias = AsyncConnectionPool[AsyncConnection[DictRow]]

_pool: Optional[PoolType] = None


def create_pool() -> PoolType:
    return AsyncConnectionPool(
        conninfo=settings.db_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )


async def init_pool() -> PoolType:
    global _pool
    if _pool is None:
        _pool = create_pool()
        await _pool.open()
    return _pool


def get_pool() -> PoolType:
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
