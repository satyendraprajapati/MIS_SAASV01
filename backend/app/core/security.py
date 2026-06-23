"""
Security utilities: password hashing, JWT creation / decoding.

Token design
------------
Every token carries a `jti` (JWT ID) — a random UUID used for blacklisting
on logout.  The `type` claim distinguishes access vs refresh tokens so a
refresh token can never be used as a bearer credential.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
    """
    Returns (encoded_jwt, jti).
    Caller stores jti so it can be blacklisted on logout.
    Access tokens live for ACCESS_TOKEN_EXPIRE_MINUTES (default 24 h via .env).
    """
    jti = str(uuid.uuid4())
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "jti": jti, "type": "access"})
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_refresh_token(data: dict) -> tuple[str, str]:
    """Returns (encoded_jwt, jti) for the refresh token."""
    jti = str(uuid.uuid4())
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "jti": jti, "type": "refresh"})
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT.  Returns the payload dict or None if invalid /
    expired.  Does NOT check the blacklist — that is the caller's job so that
    the DB lookup only happens on protected routes, not here.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None
