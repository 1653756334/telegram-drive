"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Telegram API
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API Hash")
    bot_token: str = Field(..., description="Telegram Bot Token")

    # Security
    session_secret: str = Field(..., description="Session encryption secret")
    api_token: Optional[str] = Field(None, description="Optional API authentication token")

    # Database
    database_url: str = Field(..., description="Database connection URL")

    # Storage Channel
    storage_channel_id: Optional[int] = Field(None, description="Storage channel ID")
    storage_channel_username: Optional[str] = Field(None, description="Storage channel username")

    # Application
    debug: bool = Field(False, description="Debug mode")
    cors_origins: list[str] = Field(["*"], description="CORS allowed all origins")

    @field_validator('storage_channel_id', mode='before')
    @classmethod
    def validate_storage_channel_id(cls, v) -> Optional[int]:
        """Validate storage channel ID, handle empty strings."""
        if v is None or v == '' or v == 'None':
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator('storage_channel_username', mode='before')
    @classmethod
    def validate_storage_channel_username(cls, v) -> Optional[str]:
        """Validate storage channel username, handle empty strings."""
        if v is None or v == '' or v == 'None':
            return None
        return str(v).strip()

    @field_validator('api_token', mode='before')
    @classmethod
    def validate_api_token(cls, v) -> Optional[str]:
        """Validate API token, handle empty strings."""
        if v is None or v == '' or v == 'None':
            return None
        return str(v).strip()

    class Config:
        env_file = ".env"
        env_prefix = "TGDRIVE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
