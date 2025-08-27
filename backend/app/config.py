from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

class Settings(BaseSettings):
    # Telegram API credentials (from my.telegram.org)
    api_id: int = Field(..., alias="TGDRIVE_API_ID")
    api_hash: str = Field(..., alias="TGDRIVE_API_HASH")

    # Bot token (from BotFather)
    bot_token: str = Field(..., alias="TGDRIVE_BOT_TOKEN")

    # Secret used to encrypt session strings, JWT, etc.
    session_secret: str = Field(..., alias="TGDRIVE_SESSION_SECRET")

    # Simple API token for server endpoints (optional). If set, clients must send Authorization: Bearer <token>
    api_token: Optional[str] = Field(default=None, alias="TGDRIVE_API_TOKEN")

    # Database URL (async SQLAlchemy + asyncpg)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_drive",
        alias="TGDRIVE_DATABASE_URL",
    )

    # Single-user temporary support: user session string (optional)
    user_session_string: Optional[str] = Field(default=None, alias="TGDRIVE_USER_SESSION_STRING")

    # Storage channel configuration (choose one):
    # Option 1: Channel ID (like -1001234567890)
    storage_channel_id: Optional[int] = Field(default=None, alias="TGDRIVE_STORAGE_CHANNEL_ID")
    # Option 2: Channel username (like your_channel_name, without @)
    storage_channel_username: Optional[str] = Field(default=None, alias="TGDRIVE_STORAGE_CHANNEL_USERNAME")

    @field_validator("storage_channel_id", mode="before")
    @classmethod
    def _coerce_storage_channel_id(cls, v):
        # Allow empty string or missing env to become None
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        # Coerce to int if provided as string
        return int(v)

    @field_validator("storage_channel_username", mode="before")
    @classmethod
    def _coerce_storage_channel_username(cls, v):
        # Allow empty string or missing env to become None
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v.strip()

    def get_storage_channel_identifier(self) -> str | int | None:
        """Return the preferred channel identifier (username takes priority over ID)"""
        if self.storage_channel_username:
            # Ensure username starts with @
            username = self.storage_channel_username.strip()
            if not username.startswith('@'):
                username = '@' + username
            return username
        return self.storage_channel_id

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

