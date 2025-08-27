from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from pyrogram.client import Client

from .config import get_settings


@dataclass
class TelegramClients:
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
        backend_dir = Path(__file__).resolve().parents[1]
        self._workdir = backend_dir / ".pyrogram"
        self._workdir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> TelegramClients:
        async with self._lock:
            if self._bot is None:
                # Persist bot session on disk to avoid FloodWait due to frequent re-authorization
                self._bot = Client(
                    name="tgdrive-bot",
                    bot_token=self.settings.bot_token,
                    api_id=self.settings.api_id,
                    api_hash=self.settings.api_hash,
                    workdir=str(self._workdir),
                )
                await self._bot.start()

            # user client started lazily via ensure_user_started()
            return TelegramClients(bot=self._bot, user=self._user)

    async def ensure_user_started(self, session_string: str) -> None:
        """Start a user client in-memory using the provided session string (no local persistence)."""
        async with self._lock:
            if self._user is not None:
                return
            if not session_string:
                raise RuntimeError("session_string is required to start user client")
            self._user = Client(
                name="tgdrive-user",
                api_id=self.settings.api_id,
                api_hash=self.settings.api_hash,
                session_string=session_string,
                in_memory=True,  # do NOT persist user session locally; rely on DB
            )
            await self._user.start()

    async def stop(self) -> None:
        async with self._lock:
            if self._user is not None:
                await self._user.stop()
                self._user = None
            if self._bot is not None:
                await self._bot.stop()
                self._bot = None


telegram_manager = TelegramClientManager()

