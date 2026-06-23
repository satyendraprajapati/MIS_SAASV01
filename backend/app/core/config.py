from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "SaaS Sales BI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    FRONTEND_URL: str = "http://localhost:5173"

    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
