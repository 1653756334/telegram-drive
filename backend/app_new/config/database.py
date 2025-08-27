"""Database configuration and connection management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .settings import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
    
    def initialize(self, database_url: str) -> None:
        """Initialize database engine and session factory."""
        self._engine = create_async_engine(
            database_url,
            echo=get_settings().debug,
            future=True
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized")
        return self._session_factory()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()


# Global database manager instance
_db_manager = DatabaseManager()


def get_database() -> DatabaseManager:
    """Get database manager instance."""
    return _db_manager


async def get_db_session():
    """FastAPI dependency for database session."""
    db_manager = get_database()
    session = await db_manager.get_session()
    try:
        yield session
    finally:
        await session.close()
