"""Telegram client management."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pyrogram.client import Client

from ...config import get_settings
from ...core.exceptions import TelegramError


@dataclass
class TelegramClients:
    """Container for Telegram clients."""
    bot: Client
    user: Optional[Client]


class TelegramClientManager:
    """Manage lifecycle of Pyrogram clients (bot + optional user session)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._bot: Optional[Client] = None
        self._user: Optional[Client] = None
        self._lock = asyncio.Lock()

        # Workdir for bot session persistence only
        backend_dir = Path(__file__).resolve().parents[3]
        self._workdir = backend_dir / ".pyrogram"
        self._workdir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> TelegramClients:
        """Start bot client and return clients container."""
        async with self._lock:
            if self._bot is None:
                try:
                    # Persist bot session on disk to avoid FloodWait due to frequent re-authorization
                    self._bot = Client(
                        name="tgdrive-bot",
                        bot_token=self.settings.bot_token,
                        api_id=self.settings.api_id,
                        api_hash=self.settings.api_hash,
                        workdir=str(self._workdir),
                    )
                    await self._bot.start()
                except Exception as e:
                    raise TelegramError(f"Failed to start bot client: {e}")

            # user client started lazily via ensure_user_started()
            return TelegramClients(bot=self._bot, user=self._user)

    async def ensure_user_started(self, session_string: str) -> None:
        """Start a user client in-memory using the provided session string (no local persistence)."""
        async with self._lock:
            if self._user is not None:
                return  # Already started

            try:
                self._user = Client(
                    name="tgdrive-user",
                    api_id=self.settings.api_id,
                    api_hash=self.settings.api_hash,
                    session_string=session_string,
                    in_memory=True,  # No local persistence
                )
                await self._user.start()
            except Exception as e:
                self._user = None
                raise TelegramError(f"Failed to start user client: {e}")

    async def stop(self) -> None:
        """Stop all clients."""
        async with self._lock:
            if self._user:
                try:
                    await self._user.stop()
                except Exception as e:
                    print(f"Warning: Error stopping user client: {e}")
                finally:
                    self._user = None

            if self._bot:
                try:
                    await self._bot.stop()
                except Exception as e:
                    print(f"Warning: Error stopping bot client: {e}")
                finally:
                    self._bot = None

    async def restart_user(self, session_string: str) -> None:
        """Restart user client with new session."""
        async with self._lock:
            # Stop existing user client
            if self._user:
                try:
                    await self._user.stop()
                except Exception:
                    pass
                finally:
                    self._user = None

            # Start new user client
            await self.ensure_user_started(session_string)

    def is_user_started(self) -> bool:
        """Check if user client is started."""
        return self._user is not None

    def is_bot_started(self) -> bool:
        """Check if bot client is started."""
        return self._bot is not None


# Global instance
telegram_client_manager = TelegramClientManager()
