"""Authentication use cases."""

from typing import Optional, Dict, Any
from uuid import UUID

from pyrogram.client import Client
from pyrogram.errors import PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded

from ...domain.repositories import UserRepository
from ...infrastructure.telegram import TelegramClientManager
from ...core.exceptions import AuthenticationError, TelegramError
from ...core.security import encrypt, decrypt
from ...config import get_settings


class AuthUseCases:
    """Authentication use cases."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        telegram_manager: TelegramClientManager
    ):
        self.user_repository = user_repository
        self.telegram_manager = telegram_manager
        self.settings = get_settings()
        self._pending_logins: Dict[str, Client] = {}
    
    async def send_login_code(self, phone: str) -> Dict[str, Any]:
        """Send login verification code to phone number."""
        try:
            # Create temporary client for login
            temp_client = Client(
                name=f"temp_{phone}",
                api_id=self.settings.api_id,
                api_hash=self.settings.api_hash,
                in_memory=True
            )
            
            await temp_client.connect()
            
            # Send code
            sent_code = await temp_client.send_code(phone)
            
            # Store client for verification
            self._pending_logins[phone] = temp_client
            
            return {
                "phone": phone,
                "phone_code_hash": sent_code.phone_code_hash,
                "next_type": sent_code.next_type,
                "timeout": sent_code.timeout
            }
            
        except Exception as e:
            # Clean up on error
            if phone in self._pending_logins:
                try:
                    await self._pending_logins[phone].disconnect()
                except Exception:
                    pass
                del self._pending_logins[phone]
            
            raise TelegramError(f"Failed to send login code: {e}")
    
    async def verify_login_code(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify login code and create session."""
        temp_client = self._pending_logins.get(phone)
        if not temp_client:
            raise AuthenticationError("No pending login found for this phone number")
        
        try:
            # Sign in with code
            try:
                signed_in = await temp_client.sign_in(phone, phone_code_hash, code)
            except SessionPasswordNeeded:
                if not password:
                    raise AuthenticationError("Two-factor authentication password required")
                signed_in = await temp_client.check_password(password)
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                raise AuthenticationError(f"Invalid or expired verification code: {e}")
            
            # Get user info
            me = await temp_client.get_me()
            telegram_username = me.username
            
            # Export session string
            session_string = await temp_client.export_session_string()
            encrypted_session = encrypt(session_string, self.settings.session_secret)
            
            # Get or create user
            user = await self.user_repository.get_or_create_single_user()
            
            # Update user with Telegram info
            if telegram_username and user.username != telegram_username:
                user.update_username(telegram_username)
                await self.user_repository.update(user)
            
            # Start user client with new session
            await self.telegram_manager.ensure_user_started(session_string)
            
            return {
                "session_encrypted": encrypted_session,
                "user_id": str(user.id),
                "username": user.username
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise TelegramError(f"Login verification failed: {e}")
        finally:
            # Clean up temporary client
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            self._pending_logins.pop(phone, None)
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        try:
            user = await self.user_repository.get_first()
            if not user:
                return None
            
            return {
                "id": str(user.id),
                "username": user.username,
                "created_at": user.created_at.isoformat(),
                "is_anonymous": user.is_anonymous()
            }
        except Exception as e:
            raise AuthenticationError(f"Failed to get current user: {e}")
    
    async def logout(self) -> bool:
        """Logout current user."""
        try:
            # Stop user client
            await self.telegram_manager.stop()
            return True
        except Exception as e:
            raise AuthenticationError(f"Logout failed: {e}")
