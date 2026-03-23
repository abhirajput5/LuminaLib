from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from psycopg.rows import DictRow
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection, errors

from app.exceptions.db_exceptions import (
    DatabaseConnectionError,
    QueryExecutionError,
    IntegrityError as DBIntegrityError,
)

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[DictRow]]) -> None:
        self.pool = pool

    # ============================================================
    # CREATE USER + PROFILE
    # ============================================================
    async def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.debug("Creating user in DB", extra={"email": email})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:

                    await cur.execute(
                        """
                        INSERT INTO users (email, password_hash)
                        VALUES (%s, %s)
                        RETURNING id, email, is_active, created_at;
                        """,
                        (email, password_hash),
                    )
                    user = await cur.fetchone()

                    if not user:
                        raise QueryExecutionError("User insert failed")

                    user_id = user["id"]

                    await cur.execute(
                        """
                        INSERT INTO user_profiles (user_id, first_name, last_name)
                        VALUES (%s, %s, %s);
                        """,
                        (user_id, first_name, last_name),
                    )

                    return dict(user)

        except errors.UniqueViolation:
            logger.warning("Duplicate email", extra={"email": email})
            raise DBIntegrityError("Email already exists")

        except errors.DatabaseError as e:
            logger.exception("Query execution failed", extra={"email": email})
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Database connection error", extra={"email": email})
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # GET USER BY EMAIL
    # ============================================================
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        logger.debug("Fetching user by email", extra={"email": email})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, email, password_hash, is_active
                        FROM users
                        WHERE email = %s;
                        """,
                        (email,),
                    )
                    user = await cur.fetchone()

                    return dict(user) if user else None

        except errors.DatabaseError as e:
            logger.exception("Query failed", extra={"email": email})
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Connection error", extra={"email": email})
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # GET USER WITH PROFILE
    # ============================================================
    async def get_user_with_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        logger.debug("Fetching user with profile", extra={"user_id": user_id})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT
                            u.id,
                            u.email,
                            u.is_active,
                            u.created_at,
                            p.first_name,
                            p.last_name,
                            p.phone,
                            p.avatar_url,
                            p.bio
                        FROM users u
                        LEFT JOIN user_profiles p ON u.id = p.user_id
                        WHERE u.id = %s;
                        """,
                        (user_id,),
                    )
                    user = await cur.fetchone()

                    return dict(user) if user else None

        except errors.DatabaseError as e:
            logger.exception("Query failed", extra={"user_id": user_id})
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Connection error", extra={"user_id": user_id})
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # UPDATE USER EMAIL
    # ============================================================
    async def update_user_email(
        self, user_id: int, new_email: str
    ) -> Optional[Dict[str, Any]]:
        logger.debug("Updating email", extra={"user_id": user_id})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE users
                        SET email = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id, email, updated_at;
                        """,
                        (new_email, user_id),
                    )
                    user = await cur.fetchone()

                    return dict(user) if user else None

        except errors.UniqueViolation:
            raise DBIntegrityError("Email already exists")

        except errors.DatabaseError as e:
            raise QueryExecutionError(str(e))

        except Exception as e:
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # UPDATE USER PROFILE
    # ============================================================
    async def update_user_profile(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        logger.debug("Updating profile", extra={"user_id": user_id})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE user_profiles
                        SET
                            first_name = COALESCE(%s, first_name),
                            last_name = COALESCE(%s, last_name),
                            phone = COALESCE(%s, phone),
                            avatar_url = COALESCE(%s, avatar_url),
                            bio = COALESCE(%s, bio),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        RETURNING *;
                        """,
                        (first_name, last_name, phone, avatar_url, bio, user_id),
                    )
                    profile = await cur.fetchone()

                    return dict(profile) if profile else None

        except errors.DatabaseError as e:
            raise QueryExecutionError(str(e))

        except Exception as e:
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # DEACTIVATE USER
    # ============================================================
    async def deactivate_user(self, user_id: int) -> None:
        logger.debug("Deactivating user", extra={"user_id": user_id})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE users
                        SET is_active = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                        """,
                        (user_id,),
                    )

        except errors.DatabaseError as e:
            raise QueryExecutionError(str(e))

        except Exception as e:
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # CREATE SESSION (REFRESH TOKEN)
    # ============================================================
    async def create_session(
        self,
        user_id: int,
        refresh_token_hash: str,
        expires_at,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        logger.debug("Creating user session", extra={"user_id": user_id})

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO user_sessions (
                            user_id,
                            refresh_token_hash,
                            expires_at,
                            user_agent,
                            ip_address
                        )
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (
                            user_id,
                            refresh_token_hash,
                            expires_at,
                            user_agent,
                            ip_address,
                        ),
                    )

        except errors.DatabaseError as e:
            logger.exception("Session creation failed", extra={"user_id": user_id})
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Session connection error", extra={"user_id": user_id})
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # REVOKE SESSION (LOGOUT)
    # ============================================================
    async def revoke_session(self, refresh_token_hash: str) -> None:
        logger.debug("Revoking session")

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE user_sessions
                        SET is_active = FALSE,
                            revoked_at = CURRENT_TIMESTAMP
                        WHERE refresh_token_hash = %s;
                        """,
                        (refresh_token_hash,),
                    )

        except errors.DatabaseError as e:
            logger.exception("Session revoke failed")
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Session revoke connection error")
            raise DatabaseConnectionError(str(e))

    # ============================================================
    # GET VALID SESSION
    # ============================================================
    async def get_valid_session(self, refresh_token_hash: str):
        logger.debug("Fetching session")

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, user_id
                        FROM user_sessions
                        WHERE refresh_token_hash = %s
                        AND is_active = TRUE
                        AND expires_at > NOW();
                        """,
                        (refresh_token_hash,),
                    )
                    return await cur.fetchone()

        except errors.DatabaseError as e:
            logger.exception("Session fetch failed")
            raise QueryExecutionError(str(e))

        except Exception as e:
            logger.exception("Session connection error")
            raise DatabaseConnectionError(str(e))
