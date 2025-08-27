"""User domain entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    """User domain entity."""
    
    id: UUID
    username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    def update_username(self, username: Optional[str]) -> None:
        """Update user's username."""
        self.username = username
        self.updated_at = datetime.utcnow()
    
    def is_anonymous(self) -> bool:
        """Check if user is anonymous (no username)."""
        return self.username is None or self.username == "default_user"
