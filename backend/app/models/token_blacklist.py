from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class TokenBlacklist(Base):
    """
    Stores JTI (JWT ID) of invalidated tokens so /auth/me rejects them.
    Indexed on token_jti for O(1) lookup on every protected request.
    Old entries can be purged by a nightly cron once their JWT exp has passed.
    """
    __tablename__ = "token_blacklist"

    token_jti      = Column(String, primary_key=True, index=True)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
