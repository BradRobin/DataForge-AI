import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "DataForge AI"
    ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
    API_V1_STR: str = "/api/v1"
    BACKEND_PORT: int = 8000
    
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./dataforge.db",
        description="SQLAlchemy Database connection URL"
    )

    model_config = SettingsConfigDict(
        # Load .env file. Pydantic-settings searches current working directory.
        # We can specify path to root .env if running from workspace root.
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str:
        if v:
            return v
        
        # Fallback to local SQLite if DATABASE_URL is not configured
        return "sqlite+aiosqlite:///./dataforge.db"

settings = Settings()
