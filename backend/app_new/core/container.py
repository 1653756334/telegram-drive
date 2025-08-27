"""Dependency injection container."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..application.use_cases import AuthUseCases, FileUseCases, ChannelUseCases
from ..infrastructure.database.repositories import UserRepositoryImpl, NodeRepositoryImpl, ChannelRepositoryImpl
from ..infrastructure.telegram.client import telegram_client_manager
from ..infrastructure.telegram.manager import TelegramManager


class Container:
    """Dependency injection container."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._telegram_manager = None
        self._user_repository = None
        self._node_repository = None
        self._channel_repository = None
    
    @property
    def telegram_manager(self) -> TelegramManager:
        """Get Telegram manager instance."""
        if self._telegram_manager is None:
            self._telegram_manager = TelegramManager(telegram_client_manager)
        return self._telegram_manager
    
    @property
    def user_repository(self) -> UserRepositoryImpl:
        """Get user repository instance."""
        if self._user_repository is None:
            self._user_repository = UserRepositoryImpl(self.db_session)
        return self._user_repository
    
    @property
    def node_repository(self) -> NodeRepositoryImpl:
        """Get node repository instance."""
        if self._node_repository is None:
            self._node_repository = NodeRepositoryImpl(self.db_session)
        return self._node_repository
    
    @property
    def channel_repository(self) -> ChannelRepositoryImpl:
        """Get channel repository instance."""
        if self._channel_repository is None:
            self._channel_repository = ChannelRepositoryImpl(self.db_session)
        return self._channel_repository
    
    def get_auth_use_cases(self) -> AuthUseCases:
        """Get auth use cases."""
        return AuthUseCases(
            user_repository=self.user_repository,
            telegram_manager=telegram_client_manager
        )
    
    def get_file_use_cases(self) -> FileUseCases:
        """Get file use cases."""
        return FileUseCases(
            user_repository=self.user_repository,
            node_repository=self.node_repository,
            channel_repository=self.channel_repository,
            telegram_manager=self.telegram_manager
        )
    
    def get_channel_use_cases(self) -> ChannelUseCases:
        """Get channel use cases."""
        return ChannelUseCases(
            user_repository=self.user_repository,
            channel_repository=self.channel_repository,
            telegram_manager=self.telegram_manager
        )
