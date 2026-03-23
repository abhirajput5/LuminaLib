from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr


# ============================================================
# REQUEST MODELS
# ============================================================


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    # Profile fields (optional at signup)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "abhimanyu@example.com",
                "password": "StrongPass123",
                "first_name": "Abhimanyu",
                "last_name": "Singh",
            }
        }
    }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {"email": "abhimanyu@example.com", "password": "StrongPass123"}
        }
    }


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "Abhimanyu",
                "last_name": "Singh",
                "phone": "+919876543210",
                "avatar_url": "https://cdn.yoursaas.com/avatars/user123.png",
                "bio": "Cloud engineer passionate about serverless and SaaS products.",
            }
        }
    }


class UpdateEmailRequest(BaseModel):
    email: EmailStr


# ============================================================
# RESPONSE MODELS
# ============================================================


class UserBase(BaseModel):
    id: int
    email: EmailStr
    is_active: bool


class UserProfile(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]


class UserWithProfileResponse(UserBase, UserProfile):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserBase
    access_token: str


class RefreshRequest(BaseModel):
    refresh_token: str
