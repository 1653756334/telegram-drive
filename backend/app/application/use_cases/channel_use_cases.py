"""Channel management use cases."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from ...domain.entities import TelegramChannel
from ...domain.repositories import UserRepository, ChannelRepository
from ...infrastructure.telegram import TelegramManager
from ...core.exceptions import NotFoundError, ValidationError, TelegramError, ConflictError
from ...config import get_settings


class ChannelUseCases:
    """Channel management use cases."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        channel_repository: ChannelRepository,
        telegram_manager: TelegramManager
    ):
        self.user_repository = user_repository
        self.channel_repository = channel_repository
        self.telegram_manager = telegram_manager
        self.settings = get_settings()
    
    async def ensure_storage_channel(self) -> Dict[str, Any]:
        """Ensure storage channel exists and return its info."""
        try:
            user = await self.user_repository.get_or_create_single_user()
            
            # Check if we already have a channel
            existing_channel = await self.channel_repository.get_latest_for_user(user.id)
            if existing_channel:
                return {
                    "id": existing_channel.id,
                    "channel_id": existing_channel.channel_id,
                    "username": existing_channel.username,
                    "title": existing_channel.title,
                    "identifier": existing_channel.get_identifier()
                }
            
            # Try to resolve from configuration
            if self.settings.storage_channel_username:
                return await self._resolve_channel_by_username(user.id, self.settings.storage_channel_username)
            elif self.settings.storage_channel_id:
                return await self._resolve_channel_by_id(user.id, self.settings.storage_channel_id)
            else:
                raise ValidationError("No storage channel configured")
                
        except (ValidationError, TelegramError):
            raise
        except Exception as e:
            raise TelegramError(f"Failed to ensure storage channel: {e}")
    
    async def add_channel(
        self,
        channel_identifier: str | int,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new channel."""
        try:
            user = await self.user_repository.get_or_create_single_user()
            
            if isinstance(channel_identifier, str):
                return await self._resolve_channel_by_username(user.id, channel_identifier, title)
            else:
                return await self._resolve_channel_by_id(user.id, channel_identifier, title)
                
        except (ValidationError, TelegramError, ConflictError):
            raise
        except Exception as e:
            raise TelegramError(f"Failed to add channel: {e}")
    
    async def list_channels(self) -> List[Dict[str, Any]]:
        """List all channels for current user."""
        try:
            user = await self.user_repository.get_or_create_single_user()
            channels = await self.channel_repository.get_all_for_user(user.id)
            
            return [
                {
                    "id": channel.id,
                    "channel_id": channel.channel_id,
                    "username": channel.username,
                    "title": channel.title,
                    "display_name": channel.get_display_name(),
                    "identifier": channel.get_identifier(),
                    "created_at": channel.created_at.isoformat()
                }
                for channel in channels
            ]
            
        except Exception as e:
            raise TelegramError(f"Failed to list channels: {e}")
    
    async def remove_channel(self, channel_id: int) -> bool:
        """Remove a channel."""
        try:
            user = await self.user_repository.get_or_create_single_user()
            
            # Check if channel exists and belongs to user
            channel = await self.channel_repository.get_by_id(channel_id)
            if not channel or channel.user_id != user.id:
                raise NotFoundError("Channel not found")
            
            return await self.channel_repository.delete(channel_id)
            
        except NotFoundError:
            raise
        except Exception as e:
            raise TelegramError(f"Failed to remove channel: {e}")
    
    async def _resolve_channel_by_username(
        self,
        user_id: UUID,
        username: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve channel by username."""
        # Normalize username
        if not username.startswith('@'):
            username = '@' + username
        
        # Get chat info from Telegram
        chat_info = await self.telegram_manager.get_chat_info(username)
        channel_id = chat_info['id']
        resolved_title = title or chat_info.get('title', 'Unknown')
        
        # Check if already exists
        if await self.channel_repository.exists(user_id, channel_id):
            existing = await self.channel_repository.get_by_user_and_channel_id(user_id, channel_id)
            if existing:
                return {
                    "id": existing.id,
                    "channel_id": existing.channel_id,
                    "username": existing.username,
                    "title": existing.title,
                    "identifier": existing.get_identifier()
                }
        
        # Create new channel record
        channel = TelegramChannel(
            id=0,  # Will be set by database
            user_id=user_id,
            channel_id=channel_id,
            username=username,
            title=resolved_title,
            created_at=datetime.utcnow()
        )
        
        created_channel = await self.channel_repository.create(channel)
        
        return {
            "id": created_channel.id,
            "channel_id": created_channel.channel_id,
            "username": created_channel.username,
            "title": created_channel.title,
            "identifier": created_channel.get_identifier()
        }
    
    async def _resolve_channel_by_id(
        self,
        user_id: UUID,
        channel_id: int,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve channel by ID."""
        # Check if already exists
        if await self.channel_repository.exists(user_id, channel_id):
            existing = await self.channel_repository.get_by_user_and_channel_id(user_id, channel_id)
            if existing:
                return {
                    "id": existing.id,
                    "channel_id": existing.channel_id,
                    "username": existing.username,
                    "title": existing.title,
                    "identifier": existing.get_identifier()
                }
        
        # Try to get chat info (may fail if bot doesn't have access)
        try:
            chat_info = await self.telegram_manager.get_chat_info(channel_id)
            resolved_title = title or chat_info.get('title', 'Unknown')
            resolved_username = chat_info.get('username')
            if resolved_username and not resolved_username.startswith('@'):
                resolved_username = '@' + resolved_username
        except Exception:
            resolved_title = title or "Unknown"
            resolved_username = None
        
        # Create new channel record
        channel = TelegramChannel(
            id=0,  # Will be set by database
            user_id=user_id,
            channel_id=channel_id,
            username=resolved_username,
            title=resolved_title,
            created_at=datetime.utcnow()
        )
        
        created_channel = await self.channel_repository.create(channel)
        
        return {
            "id": created_channel.id,
            "channel_id": created_channel.channel_id,
            "username": created_channel.username,
            "title": created_channel.title,
            "identifier": created_channel.get_identifier()
        }
