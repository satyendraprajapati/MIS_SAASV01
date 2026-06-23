"""
Auth router — all endpoints under /api/v1/auth

POST /register   — create account
POST /login      — returns JWT pair
GET  /me         — current user profile (protected)
POST /logout     — blacklist current access token
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.db.session import get_db
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.user import (
    RegisterRequest, LoginRequest,
    UserResponse, TokenResponse,
)

router  = APIRouter(prefix="/auth", tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)


# ── POST /register ─────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Creates a new user.  Email must be globally unique — enforced at the DB
    level (unique index) and checked here to return a friendly 400 rather than
    a raw 500 IntegrityError.
    """
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User(
        email           = payload.email,
        full_name       = payload.full_name,
        company_name    = payload.company_name,
        hashed_password = hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── POST /login ────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Validates credentials and returns an access + refresh token pair.
    Deliberately returns the same error for wrong email AND wrong password
    to prevent user enumeration.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    # Constant-time comparison even on miss (verify_password against a dummy hash)
    _DUMMY = "$2b$12$KIXv5rN7Kt9e8bQK3nFqPO2.e3e6xC3t3o4y5r6a7b8c9d0e1f2g3h"
    candidate_hash = user.hashed_password if user else _DUMMY
    password_ok = verify_password(payload.password, candidate_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator.",
        )

    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token,  _  = create_access_token(token_data)
    refresh_token, _  = create_refresh_token(token_data)

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_token,
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── GET /me ────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile. Protected by JWT."""
    return current_user


# ── POST /logout ───────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout — invalidate current access token",
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),   # ensures token is valid before blacklisting
):
    """
    Adds the token's JTI to the blacklist so it is rejected on future requests.
    The frontend should also delete the token from localStorage.
    """
    payload = decode_token(credentials.credentials)
    jti = payload.get("jti") if payload else None

    if jti and not db.get(TokenBlacklist, jti):
        db.add(TokenBlacklist(token_jti=jti))
        db.commit()

    return {"detail": "Logged out successfully."}
