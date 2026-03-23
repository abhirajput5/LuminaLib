from __future__ import annotations

import bcrypt
import jwt
import datetime
import hashlib
from typing import Annotated, Dict, Any

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ============================================================
# CONFIG
# ============================================================

SECRET_KEY: str = "your-secret"
ALGORITHM: str = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

security = HTTPBearer()


# ============================================================
# PASSWORD UTILS
# ============================================================


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ============================================================
# TOKEN HASHING (for DB storage)
# ============================================================


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================
# TOKEN CREATION
# ============================================================


def create_access_token(user_id: int) -> str:
    now = datetime.datetime.utcnow()

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    now = datetime.datetime.utcnow()

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ============================================================
# TOKEN DECODING
# ============================================================


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ============================================================
# ACCESS TOKEN DEPENDENCY (NO DB HIT)
# ============================================================


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)],
) -> int:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return int(user_id)


# ============================================================
# REFRESH TOKEN VALIDATION (JWT LEVEL ONLY)
# ============================================================


def validate_refresh_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token type",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    return payload
