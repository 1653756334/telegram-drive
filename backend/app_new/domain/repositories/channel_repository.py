"""Channel repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from ..entities import TelegramChannel


class ChannelRepository(ABC):
    """Abstract channel repository interface."""
    
    @abstractmethod
    async def get_by_id(self, channel_id: int) -> Optional[TelegramChannel]:
        """Get channel by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_and_channel_id(self, user_id: UUID, channel_id: int) -> Optional[TelegramChannel]:
        """Get channel by user and channel ID."""
        pass
    
    @abstractmethod
    async def get_latest_for_user(self, user_id: UUID) -> Optional[TelegramChannel]:
        """Get latest channel for user."""
        pass
    
    @abstractmethod
    async def get_all_for_user(self, user_id: UUID) -> List[TelegramChannel]:
        """Get all channels for user."""
        pass
    
    @abstractmethod
    async def create(self, channel: TelegramChannel) -> TelegramChannel:
        """Create new channel."""
        pass
    
    @abstractmethod
    async def update(self, channel: TelegramChannel) -> TelegramChannel:
        """Update existing channel."""
        pass
    
    @abstractmethod
    async def delete(self, channel_id: int) -> bool:
        """Delete channel."""
        pass
    
    @abstractmethod
    async def exists(self, user_id: UUID, channel_id: int) -> bool:
        """Check if channel exists for user."""
        pass
