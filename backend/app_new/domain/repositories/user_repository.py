"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ..entities import User


class UserRepository(ABC):
    """Abstract user repository interface."""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_first(self) -> Optional[User]:
        """Get first user (for single-user mode)."""
        pass
    
    @abstractmethod
    async def create(self, username: Optional[str] = None) -> User:
        """Create new user."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        pass
    
    @abstractmethod
    async def get_or_create_single_user(self) -> User:
        """Get or create single user for single-user mode."""
        pass
