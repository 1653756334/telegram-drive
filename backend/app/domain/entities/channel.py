"""Telegram channel domain entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TelegramChannel(BaseModel):
    """Telegram channel domain entity."""
    
    id: int
    user_id: UUID
    channel_id: int  # Telegram channel ID (e.g., -100xxxxxxxxxx)
    username: Optional[str] = None  # Channel username (e.g., @channelname)
    title: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    def has_username(self) -> bool:
        """Check if channel has a username."""
        return self.username is not None and self.username.strip() != ""
    
    def get_display_name(self) -> str:
        """Get display name for the channel."""
        if self.title:
            return self.title
        elif self.username:
            return self.username
        else:
            return f"Channel {self.channel_id}"
    
    def get_identifier(self) -> str | int:
        """Get the best identifier for accessing the channel."""
        # Prefer username over ID for better reliability
        if self.has_username():
            return self.username
        return self.channel_id
    
    def update_info(self, title: Optional[str] = None, username: Optional[str] = None) -> None:
        """Update channel information."""
        if title is not None:
            self.title = title
        if username is not None:
            self.username = username
