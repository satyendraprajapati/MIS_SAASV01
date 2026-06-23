from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:        EmailStr
    password:     str
    full_name:    str
    company_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be blank")
        return v.strip()


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ── Responses ─────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:           UUID
    email:        EmailStr
    full_name:    str
    company_name: Optional[str]
    role:         UserRole
    is_active:    bool
    created_at:   datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int  # seconds — convenient for frontend countdown


# ── Legacy alias (used by old auth_service; keep until it's removed) ──────────
UserCreate = RegisterRequest
