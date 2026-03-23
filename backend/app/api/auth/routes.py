from __future__ import annotations
import logging
from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.async_db import get_pool, PoolType
from app.repositories.auth_repo import UserRepository
from app.services.auth_service import AuthService
from app.api.auth.models import (
    SignupRequest,
    LoginRequest,
    UpdateProfileRequest,
    UserWithProfileResponse,
    AuthResponse,
    TokenResponse,
    RefreshRequest,
)
from app.utils import get_current_user_id
from app.exceptions.auth_exceptions import (
    InvalidCredentials,
    UserInactive,
    UserNotFound,
    UserAlreadyExists,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================
# DEPENDENCY
# ============================================================


def get_auth_service(
    pool: Annotated[PoolType, Depends(get_pool)],
) -> AuthService:
    repo = UserRepository(pool)
    return AuthService(repo)


# ============================================================
# SIGNUP
# ============================================================


@router.post("/signup", response_model=AuthResponse)
async def signup(
    payload: SignupRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info("Signup request received", extra={"email": payload.email})

    try:
        return await service.signup(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )

    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    except Exception:
        logger.exception("Signup failed", extra={"email": payload.email})
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# LOGIN
# ============================================================


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info("Login attempt", extra={"email": payload.email})

    try:
        return await service.login(payload.email, payload.password)

    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    except UserInactive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    except Exception:
        logger.exception("Login failed", extra={"email": payload.email})
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


# ============================================================
# REFRESH TOKEN
# ============================================================


@router.post("/refresh")
async def refresh_token(
    payload: RefreshRequest,
    pool=Depends(get_pool),
):
    repo = UserRepository(pool)
    service = AuthService(repo)

    try:
        return await service.refresh(payload.refresh_token)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ============================================================
# GET PROFILE
# ============================================================


@router.get("/me", response_model=UserWithProfileResponse)
async def get_profile(
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info("Fetch profile request", extra={"user_id": user_id})

    try:
        return await service.get_profile(user_id)

    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        logger.exception("Profile fetch failed", extra={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# UPDATE PROFILE
# ============================================================


@router.put("/me", response_model=UserWithProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info("Update profile request", extra={"user_id": user_id})

    try:
        await service.update_profile(
            user_id=user_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
        )

        return await service.get_profile(user_id)

    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        logger.exception("Profile update failed", extra={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# LIST USERS
# ============================================================


@router.get("/users", response_model=List[UserWithProfileResponse])
async def list_users(
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    raise HTTPException(
        status_code=501,
        detail="Not implemented - move to admin module",
    )
