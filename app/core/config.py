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
    OPENAI_API_KEY: Optional[str] = None
    # TEMPORARY (2026-08-30): Angel doesn't have an OPENAI_API_KEY on hand yet to test with.
    # Groq is used as a fallback ONLY when OPENAI_API_KEY is unset — see ai_client.py. CLAUDE.md
    # Rule 2 still names OpenAI as the intended provider; this is a stop-gap for local testing,
    # not a reversal of that decision. Remove once OPENAI_API_KEY is set for real.
    GROQ_API_KEY: Optional[str] = None
    # The live Vercel URL of the deployed frontend, set as an env var in Render once known —
    # lets CORS allow the real production site without ever needing a code change.
    FRONTEND_URL: Optional[str] = None
    
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