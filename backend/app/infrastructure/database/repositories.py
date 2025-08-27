"""Repository implementations using SQLAlchemy."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.logging import get_logger
from ...domain.entities import User, Node, NodeType, TelegramChannel
from ...domain.repositories import UserRepository, NodeRepository, ChannelRepository
from ...core.exceptions import NotFoundError
from .models import UserModel, NodeModel, TelegramChannelModel

logger = get_logger(__name__)


class UserRepositoryImpl(UserRepository):
    """User repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_first(self) -> Optional[User]:
        """Get first user (for single-user mode)."""
        result = await self.session.execute(
            select(UserModel).limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def create(self, username: Optional[str] = None) -> User:
        """Create new user."""
        model = UserModel(username=username or "default_user")
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        await self.session.commit()
        return self._to_entity(model)
    
    async def update(self, user: User) -> User:
        """Update existing user."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                username=user.username,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        return user
    
    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        result = await self.session.execute(
            delete(UserModel).where(UserModel.id == user_id)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_or_create_single_user(self) -> User:
        """Get or create single user for single-user mode."""
        user = await self.get_first()
        if user:
            return user
        return await self.create()
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity."""
        return User(
            id=model.id,
            username=model.username,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class NodeRepositoryImpl(NodeRepository):
    """Node repository implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, node_id: UUID) -> Optional[Node]:
        """Get node by ID."""
        result = await self.session.execute(
            select(NodeModel).where(
                and_(NodeModel.id == node_id, NodeModel.deleted_at.is_(None))
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_path(self, user_id: UUID, path: str, kind: Optional[NodeType] = None) -> Optional[Node]:
        """Get node by path."""
        query = select(NodeModel).where(
            and_(
                NodeModel.user_id == user_id,
                NodeModel.path == path,
                NodeModel.deleted_at.is_(None)
            )
        )
        if kind:
            query = query.where(NodeModel.kind == kind.value)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_checksum(self, user_id: UUID, checksum: str) -> Optional[Node]:
        """Get file node by checksum."""
        result = await self.session.execute(
            select(NodeModel).where(
                and_(
                    NodeModel.user_id == user_id,
                    NodeModel.kind == NodeType.FILE.value,
                    NodeModel.checksum == checksum,
                    NodeModel.deleted_at.is_(None)
                )
            ).limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_children(self, user_id: UUID, parent_id: Optional[UUID]) -> List[Node]:
        """Get child nodes."""
        result = await self.session.execute(
            select(NodeModel).where(
                and_(
                    NodeModel.user_id == user_id,
                    NodeModel.parent_id == parent_id,
                    NodeModel.deleted_at.is_(None)
                )
            ).order_by(NodeModel.kind.desc(), NodeModel.sort_key, NodeModel.name)
        )
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def create(self, node: Node) -> Node:
        """Create new node."""
        model = NodeModel(
            user_id=node.user_id,
            parent_id=node.parent_id,
            name=node.name,
            kind=node.kind.value,
            path=node.path,
            depth=node.depth,
            sort_key=node.sort_key,
            size_bytes=node.size_bytes,
            mime_type=node.mime_type,
            checksum=node.checksum,
            telegram_channel_id=node.telegram_channel_id,
            telegram_message_id=node.telegram_message_id
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        await self.session.commit()
        return self._to_entity(model)

    async def update(self, node: Node) -> Node:
        """Update existing node."""
        await self.session.execute(
            update(NodeModel)
            .where(NodeModel.id == node.id)
            .values(
                name=node.name,
                parent_id=node.parent_id,
                path=node.path,
                depth=node.depth,
                sort_key=node.sort_key,
                size_bytes=node.size_bytes,
                mime_type=node.mime_type,
                checksum=node.checksum,
                telegram_channel_id=node.telegram_channel_id,
                telegram_message_id=node.telegram_message_id,
                updated_at=datetime.utcnow(),
                deleted_at=node.deleted_at
            )
        )
        await self.session.commit()
        return node

    async def soft_delete(self, node_id: UUID) -> bool:
        """Soft delete node."""
        result = await self.session.execute(
            update(NodeModel)
            .where(NodeModel.id == node_id)
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0

    async def restore(self, node_id: UUID) -> bool:
        """Restore soft-deleted node."""
        result = await self.session.execute(
            update(NodeModel)
            .where(NodeModel.id == node_id)
            .values(deleted_at=None, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0

    async def hard_delete(self, node_id: UUID) -> bool:
        """Permanently delete node."""
        result = await self.session.execute(
            delete(NodeModel).where(NodeModel.id == node_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def ensure_directory_path(self, user_id: UUID, path: str) -> Optional[UUID]:
        """Ensure directory path exists, return leaf directory ID."""
        path = self._normalize_path(path)
        if path == "/":
            return None

        # Check if directory already exists
        existing = await self.get_by_path(user_id, path, NodeType.FOLDER)
        if existing:
            return existing.id

        # Create directory tree
        parts = [p for p in path.split("/") if p]
        current_path = ""
        parent_id = None

        for i, part in enumerate(parts):
            current_path = "/" + "/".join(parts[:i+1])

            # Check if this level exists
            existing = await self.get_by_path(user_id, current_path, NodeType.FOLDER)
            if existing:
                parent_id = existing.id
            else:
                # Create this directory level
                from uuid import uuid4
                node = Node(
                    id=uuid4(),
                    user_id=user_id,
                    parent_id=parent_id,
                    name=part,
                    kind=NodeType.FOLDER,
                    path=current_path,
                    depth=i + 1,
                    sort_key=0,
                    size_bytes=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                created_node = await self.create(node)
                parent_id = created_node.id

        return parent_id

    async def move_node(self, node_id: UUID, new_parent_id: Optional[UUID], new_path: str) -> bool:
        """Move node to new parent."""
        # Calculate new depth
        new_depth = len([p for p in new_path.split("/") if p])

        result = await self.session.execute(
            update(NodeModel)
            .where(NodeModel.id == node_id)
            .values(
                parent_id=new_parent_id,
                path=new_path,
                depth=new_depth,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    def _normalize_path(self, path: str) -> str:
        """Normalize directory path."""
        p = (path or "/").strip()
        if not p.startswith("/"):
            p = "/" + p
        # remove trailing slash except root
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p

    def _to_entity(self, model: NodeModel) -> Node:
        """Convert model to entity."""
        return Node(
            id=model.id,
            user_id=model.user_id,
            parent_id=model.parent_id,
            name=model.name,
            kind=NodeType(model.kind),
            path=model.path,
            depth=model.depth or 0,
            sort_key=model.sort_key,
            size_bytes=model.size_bytes,
            mime_type=model.mime_type,
            checksum=model.checksum,
            telegram_channel_id=model.telegram_channel_id,
            telegram_message_id=model.telegram_message_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at
        )


class ChannelRepositoryImpl(ChannelRepository):
    """Channel repository implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, channel_id: int) -> Optional[TelegramChannel]:
        """Get channel by ID."""
        result = await self.session.execute(
            select(TelegramChannelModel).where(TelegramChannelModel.id == channel_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_user_and_channel_id(self, user_id: UUID, channel_id: int) -> Optional[TelegramChannel]:
        """Get channel by user and channel ID."""
        result = await self.session.execute(
            select(TelegramChannelModel).where(
                and_(
                    TelegramChannelModel.user_id == user_id,
                    TelegramChannelModel.channel_id == channel_id
                )
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_latest_for_user(self, user_id: UUID) -> Optional[TelegramChannel]:
        """Get latest channel for user."""
        result = await self.session.execute(
            select(TelegramChannelModel)
            .where(TelegramChannelModel.user_id == user_id)
            .order_by(TelegramChannelModel.id.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_for_user(self, user_id: UUID) -> List[TelegramChannel]:
        """Get all channels for user."""
        result = await self.session.execute(
            select(TelegramChannelModel)
            .where(TelegramChannelModel.user_id == user_id)
            .order_by(TelegramChannelModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def create(self, channel: TelegramChannel) -> TelegramChannel:
        """Create new channel."""
        model = TelegramChannelModel(
            user_id=channel.user_id,
            channel_id=channel.channel_id,
            username=channel.username,
            title=channel.title
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        await self.session.commit()
        return self._to_entity(model)

    async def update(self, channel: TelegramChannel) -> TelegramChannel:
        """Update existing channel."""
        await self.session.execute(
            update(TelegramChannelModel)
            .where(TelegramChannelModel.id == channel.id)
            .values(
                username=channel.username,
                title=channel.title
            )
        )
        await self.session.commit()
        return channel

    async def delete(self, channel_id: int) -> bool:
        """Delete channel."""
        result = await self.session.execute(
            delete(TelegramChannelModel).where(TelegramChannelModel.id == channel_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def exists(self, user_id: UUID, channel_id: int) -> bool:
        """Check if channel exists for user."""
        result = await self.session.execute(
            select(TelegramChannelModel.id).where(
                and_(
                    TelegramChannelModel.user_id == user_id,
                    TelegramChannelModel.channel_id == channel_id
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _to_entity(self, model: TelegramChannelModel) -> TelegramChannel:
        """Convert model to entity."""
        return TelegramChannel(
            id=model.id,
            user_id=model.user_id,
            channel_id=model.channel_id,
            username=model.username,
            title=model.title,
            created_at=model.created_at
        )
