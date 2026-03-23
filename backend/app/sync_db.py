# app/db/sync_db.py

from __future__ import annotations

from typing import Optional, TypeAlias
from psycopg.rows import dict_row, DictRow
from psycopg_pool import ConnectionPool
from psycopg import Connection

from app.settings import settings

PoolType: TypeAlias = ConnectionPool[Connection[DictRow]]

_pool: Optional[PoolType] = None


def create_pool() -> PoolType:
    return ConnectionPool(
        conninfo=settings.db_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )


def init_pool() -> PoolType:
    global _pool
    if _pool is None:
        _pool = create_pool()
        _pool.open()
    return _pool


def get_pool() -> PoolType:
    if _pool is None:
        raise RuntimeError("Sync DB pool not initialized")
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
