from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# psycopg v3 uses "postgresql+psycopg://..." but standard URLs use "postgresql://"
# This normalises both so the same .env works with either driver.
_db_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg://", 1
) if not settings.DATABASE_URL.startswith("postgresql+") else settings.DATABASE_URL

engine = create_engine(_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
