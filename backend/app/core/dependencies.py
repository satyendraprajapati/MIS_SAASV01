"""
FastAPI dependency: get_current_user

Usage in any protected route:
    @router.get("/me")
    def me(user: User = Depends(get_current_user)):
        ...

Flow:
1. Extract Bearer token from Authorization header
2. Decode & verify JWT signature / expiry
3. Check token type == "access" (reject refresh tokens used as bearer)
4. Check JTI not in token_blacklist (catches logged-out tokens)
5. Load and return the User row — 404 if deleted between login and now
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist

_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise _UNAUTHORIZED

    # Reject refresh tokens used as access credentials
    if payload.get("type") != "access":
        raise _UNAUTHORIZED

    # Blacklist check — O(1) PK lookup
    jti = payload.get("jti")
    if jti and db.get(TokenBlacklist, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise _UNAUTHORIZED

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise _UNAUTHORIZED

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator.",
        )

    return user


def require_role(*roles: str):
    """
    Factory that returns a dependency checking the user has one of the
    given roles.  Use as:
        Depends(require_role("admin", "manager"))
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user
    return _check
