import json
import os
from functools import lru_cache
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "AI Finance CRM")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/ai_finance_crm")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-this-secret")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    cors_origins: list[str] = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:3000"]'))

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
