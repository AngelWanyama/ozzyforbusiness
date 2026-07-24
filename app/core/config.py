from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ozzy for Business"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "ozzy"
    DATABASE_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week

    # Payment Integrations
    MTN_UG_API_KEY: Optional[str] = None
    MTN_UG_USER_ID: Optional[str] = None
    MTN_UG_SUBSCRIPTION_KEY: Optional[str] = None
    AIRTEL_UG_CLIENT_ID: Optional[str] = None
    AIRTEL_UG_CLIENT_SECRET: Optional[str] = None
    FLUTTERWAVE_SECRET_KEY: Optional[str] = None
    FLUTTERWAVE_PUBLIC_KEY: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            if "postgresql://" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            if "postgresql+asyncpg://" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            if "sqlite+aiosqlite://" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()