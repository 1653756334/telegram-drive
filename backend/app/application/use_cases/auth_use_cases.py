"""DEPRECATED: Authentication use cases.

This module is deprecated. Use:
- UserAuthUseCases for user authentication
- TelegramUseCases for Telegram account management
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AuthUseCases:
    """DEPRECATED: Authentication use cases.

    This class is deprecated. Use:
    - UserAuthUseCases for user authentication
    - TelegramUseCases for Telegram account management
    """

    def __init__(self, user_repository=None, telegram_manager=None):
        """DEPRECATED: Use UserAuthUseCases or TelegramUseCases instead."""
        logger.warning("AuthUseCases is deprecated. Use UserAuthUseCases or TelegramUseCases instead.")
    async def send_login_code(self, phone: str) -> Dict[str, Any]:
        """DEPRECATED: Use TelegramUseCases.send_login_code instead."""
        raise NotImplementedError("Use TelegramUseCases.send_login_code instead")
    
    async def verify_login_code(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """DEPRECATED: Use TelegramUseCases.verify_login_code instead."""
        raise NotImplementedError("Use TelegramUseCases.verify_login_code instead")

