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

    # JWT Settings
    jwt_secret_key: Optional[str] = Field(None, description="JWT secret key")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiration in minutes")

    # Admin Configuration
    admin_username: str = Field(..., description="Admin username")

    # Database
    database_url: str = Field(..., description="Database connection URL")

    # Storage Channel
    storage_channel_id: Optional[int] = Field(None, description="Storage channel ID")
    storage_channel_username: Optional[str] = Field(None, description="Storage channel username")

    # Application
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
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

    # API token验证器已移除，因为不再使用API token认证

    @field_validator('log_level', mode='before')
    @classmethod
    def validate_log_level(cls, v) -> str:
        """Validate log level."""
        if isinstance(v, str):
            level = v.upper()
            if level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                return level
        return 'INFO'

    class Config:
        env_file = ".env"
        env_prefix = "TGDRIVE_"
        case_sensitive = False


def _create_settings() -> Settings:
    """Create settings instance from environment variables."""
    return Settings()  # type: ignore[call-arg]


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return _create_settings()
