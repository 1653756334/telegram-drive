"""Telegram account management use cases."""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID

from pyrogram.client import Client
from pyrogram.errors import PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded

from ...domain.repositories import UserRepository
from ...infrastructure.telegram import TelegramClientManager
from ...core.exceptions import AuthenticationError, TelegramError
from ...core.security import encrypt
from ...core.telegram_state import telegram_state_manager
from ...config import get_settings

logger = logging.getLogger(__name__)


class TelegramUseCases:
    """Use cases for Telegram account management."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        telegram_manager: TelegramClientManager
    ):
        self.user_repository = user_repository
        self.telegram_manager = telegram_manager
        self.settings = get_settings()
        self.state_manager = telegram_state_manager

    async def send_login_code(self, phone: str) -> Dict[str, Any]:
        """Send login code to phone number."""
        try:
            # Create temporary client for verification
            temp_client = Client(
                name=f"temp_{phone}",
                api_id=self.settings.api_id,
                api_hash=self.settings.api_hash,
                in_memory=True,
                no_updates=True  # Disable updates to avoid unnecessary connections
            )

            # Connect without starting (to avoid interactive prompts)
            await temp_client.connect()

            # Send code
            sent_code = await temp_client.send_code(phone)

            # Store client for verification using global state manager
            self.state_manager.add_pending_login(phone, temp_client)

            return {
                "phone_code_hash": sent_code.phone_code_hash,
                "phone": phone,
                "timeout": getattr(sent_code, 'timeout', 60)
            }

        except Exception as e:
            # Clean up on error using state manager
            await self.state_manager.cleanup_pending_login(phone)
            raise TelegramError(f"Failed to send login code: {e}")

    async def verify_login_code(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify login code and create Telegram session."""
        temp_client = self.state_manager.get_pending_login(phone)
        if not temp_client:
            raise AuthenticationError("No pending login found for this phone number")

        try:
            # Sign in with code
            try:
                await temp_client.sign_in(phone, phone_code_hash, code)
            except SessionPasswordNeeded:
                if not password:
                    raise AuthenticationError("Two-factor authentication password required")
                await temp_client.check_password(password)
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                raise AuthenticationError(f"Invalid or expired verification code: {e}")
            
            # Get user info
            me = await temp_client.get_me()
            
            # Export session string
            session_string = await temp_client.export_session_string()
            
            # Encrypt session string
            session_encrypted = encrypt(session_string, self.settings.session_secret)
            
            logger.info(f"Telegram login successful for user: {me.username or me.first_name} (ID: {me.id})")
            
            return {
                "session_encrypted": session_encrypted,
                "user_id": me.id,
                "username": me.username,
                "display_name": f"{me.first_name or ''} {me.last_name or ''}".strip(),
                "phone": phone
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Login verification failed: {e}")
            raise TelegramError(f"Login verification failed: {e}")
        finally:
            # Clean up temporary client using state manager
            await self.state_manager.cleanup_pending_login(phone)

    async def get_user_accounts(self, _user_id: UUID) -> List[Dict[str, Any]]:
        """Get all Telegram accounts for a user."""
        # This would be implemented with a proper TelegramSession repository
        # For now, return empty list as placeholder
        return []

    async def get_active_account(self, _user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the active Telegram account for a user."""
        # This would be implemented with a proper TelegramSession repository
        # For now, return None as placeholder
        return None

    async def activate_account(self, _user_id: UUID, _session_id: int) -> Dict[str, Any]:
        """Activate a Telegram account."""
        # This would be implemented with a proper TelegramSession repository
        # For now, return placeholder
        return {"message": "Account activated successfully"}

    async def delete_account(self, _user_id: UUID, _session_id: int) -> Dict[str, Any]:
        """Delete a Telegram account."""
        # This would be implemented with a proper TelegramSession repository
        # For now, return placeholder
        return {"message": "Account deleted successfully"}
