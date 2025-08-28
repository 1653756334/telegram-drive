"""Telegram state management for maintaining pending logins across requests."""

from typing import Dict, Optional
from pyrogram.client import Client


class TelegramStateManager:
    """Manages Telegram client state across API requests."""
    
    def __init__(self):
        self._pending_logins: Dict[str, Client] = {}
    
    def add_pending_login(self, phone: str, client: Client) -> None:
        """Add a pending login client for a phone number."""
        self._pending_logins[phone] = client
    
    def get_pending_login(self, phone: str) -> Optional[Client]:
        """Get a pending login client for a phone number."""
        return self._pending_logins.get(phone)
    
    def remove_pending_login(self, phone: str) -> Optional[Client]:
        """Remove and return a pending login client for a phone number."""
        return self._pending_logins.pop(phone, None)
    
    def has_pending_login(self, phone: str) -> bool:
        """Check if there's a pending login for a phone number."""
        return phone in self._pending_logins
    
    def get_pending_phones(self) -> list:
        """Get list of phones with pending logins."""
        return list(self._pending_logins.keys())
    
    async def cleanup_pending_login(self, phone: str) -> None:
        """Cleanup a pending login client."""
        client = self.remove_pending_login(phone)
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
    
    async def cleanup_all(self) -> None:
        """Cleanup all pending login clients."""
        for phone in list(self._pending_logins.keys()):
            await self.cleanup_pending_login(phone)


# Global instance
telegram_state_manager = TelegramStateManager()
