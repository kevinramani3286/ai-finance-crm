from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = 'AI Finance CRM'
    DATABASE_URL: str = 'postgresql://postgres:postgres@localhost:5432/ai_finance_crm'
    JWT_SECRET: str = 'change-this-secret'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = 'uploads'

    class Config:
        env_file = '.env'

settings = Settings()
