from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.repositories.auth_repo import UserRepository
from app.utils import (
    hash_password,
    hash_token,
    verify_password,
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)
from app.exceptions.auth_exceptions import (
    InvalidCredentials,
    UserInactive,
    UserNotFound,
    UserAlreadyExists,
)
from app.exceptions.db_exceptions import (
    DatabaseConnectionError,
    QueryExecutionError,
    IntegrityError as DBIntegrityError,
)


logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    # ============================================================
    # SIGNUP
    # ============================================================
    async def signup(
        self,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("Starting signup process", extra={"email": email})

        try:
            password_hash: str = hash_password(password)

            user = await self.repo.create_user(
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
            )

            access_token: str = create_access_token(user["id"])
            refresh_token: str = create_refresh_token(user["id"])

            return {
                "user": user,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

        except DBIntegrityError:
            logger.warning("Signup failed - duplicate email", extra={"email": email})
            raise UserAlreadyExists()

        except (DatabaseConnectionError, QueryExecutionError):
            logger.exception("Signup failed - DB error", extra={"email": email})
            raise

        except Exception:
            logger.exception("Signup process failed", extra={"email": email})
            raise

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        logger.info("Login process started", extra={"email": email})

        try:
            user = await self.repo.get_user_by_email(email)

            if not user:
                raise InvalidCredentials()

            if not user["is_active"]:
                raise UserInactive()

            if not verify_password(password, user["password_hash"]):
                raise InvalidCredentials()

            user_id: int = user["id"]

            # ============================================================
            # 1. Generate tokens
            # ============================================================

            access_token: str = create_access_token(user_id)
            refresh_token: str = create_refresh_token(user_id)

            # ============================================================
            # 2. Hash refresh token (for DB storage)
            # ============================================================

            refresh_token_hash: str = hash_token(refresh_token)

            # ============================================================
            # 3. Store session in DB
            # ============================================================

            expires_at = datetime.utcnow() + timedelta(days=7)

            await self.repo.create_session(
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
            )

            logger.info(
                "Login successful",
                extra={"user_id": user_id},
            )

            # ============================================================
            # 4. Return tokens
            # ============================================================

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

        except (DatabaseConnectionError, QueryExecutionError):
            logger.exception("Login failed - DB error", extra={"email": email})
            raise

        except Exception:
            logger.exception("Login process failed", extra={"email": email})
            raise

    # # ============================================================
    # # LOGIN
    # # ============================================================
    # async def login(self, email: str, password: str) -> Dict[str, Any]:
    #     logger.info("Login process started", extra={"email": email})

    #     try:
    #         user = await self.repo.get_user_by_email(email)

    #         if not user:
    #             raise InvalidCredentials()

    #         if not user["is_active"]:
    #             raise UserInactive()

    #         if not verify_password(password, user["password_hash"]):
    #             raise InvalidCredentials()

    #         access_token: str = create_access_token(user["id"])
    #         refresh_token: str = create_refresh_token(user["id"])

    #         return {
    #             "access_token": access_token,
    #             "refresh_token": refresh_token,
    #         }

    #     except (DatabaseConnectionError, QueryExecutionError):
    #         logger.exception("Login failed - DB error", extra={"email": email})
    #         raise

    #     except Exception:
    #         logger.exception("Login process failed", extra={"email": email})
    #         raise

    # ============================================================
    # GET PROFILE
    # ============================================================
    async def get_profile(self, user_id: int) -> Dict[str, Any]:
        logger.info("Fetching user profile", extra={"user_id": user_id})

        try:
            user = await self.repo.get_user_with_profile(user_id)

            if not user:
                raise UserNotFound()

            return user

        except (DatabaseConnectionError, QueryExecutionError):
            logger.exception(
                "Profile fetch failed - DB error", extra={"user_id": user_id}
            )
            raise

        except Exception:
            logger.exception(
                "Failed to fetch profile",
                extra={"user_id": user_id},
            )
            raise

    # ============================================================
    # UPDATE EMAIL
    # ============================================================
    async def update_email(self, user_id: int, email: str) -> Dict[str, Any]:
        logger.info(
            "Updating user email",
            extra={"user_id": user_id, "email": email},
        )

        try:
            user = await self.repo.update_user_email(user_id, email)

            if not user:
                raise UserNotFound()

            return user

        except DBIntegrityError:
            logger.warning(
                "Email update failed - duplicate email",
                extra={"user_id": user_id, "email": email},
            )
            raise UserAlreadyExists()

        except (DatabaseConnectionError, QueryExecutionError):
            logger.exception(
                "Email update failed - DB error", extra={"user_id": user_id}
            )
            raise

        except Exception:
            logger.exception(
                "Failed to update email",
                extra={"user_id": user_id},
            )
            raise

    # ============================================================
    # UPDATE PROFILE
    # ============================================================
    async def update_profile(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("Updating user profile", extra={"user_id": user_id})

        try:
            profile = await self.repo.update_user_profile(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                avatar_url=avatar_url,
                bio=bio,
            )

            if not profile:
                raise UserNotFound()

            return profile

        except (DatabaseConnectionError, QueryExecutionError):
            logger.exception(
                "Profile update failed - DB error", extra={"user_id": user_id}
            )
            raise

        except Exception:
            logger.exception(
                "Failed to update profile",
                extra={"user_id": user_id},
            )
            raise

    async def refresh(self, refresh_token: str) -> Dict[str, Any]:
        # 1. Validate JWT
        payload = validate_refresh_token(refresh_token)
        user_id = int(payload["sub"])

        # 2. Hash token
        token_hash = hash_token(refresh_token)

        # 3. Validate session in DB
        session = await self.repo.get_valid_session(token_hash)

        if not session:
            raise ValueError("Invalid or expired session")

        # 4. Revoke old session
        await self.repo.revoke_session(token_hash)

        # 5. Create new refresh token (ROTATION)
        new_refresh_token = create_refresh_token(user_id)
        new_refresh_hash = hash_token(new_refresh_token)

        expires_at = datetime.utcnow() + timedelta(days=7)

        await self.repo.create_session(
            user_id=user_id,
            refresh_token_hash=new_refresh_hash,
            expires_at=expires_at,
        )

        # 6. Create new access token
        access_token = create_access_token(user_id)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    # ============================================================
    # SIGNOUT
    # ============================================================
    async def signout(self) -> Dict[str, str]:
        logger.info("User signed out (stateless)")
        return {"message": "Successfully signed out"}
