"""Node repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from ..entities import Node, NodeType


class NodeRepository(ABC):
    """Abstract node repository interface."""
    
    @abstractmethod
    async def get_by_id(self, node_id: UUID) -> Optional[Node]:
        """Get node by ID."""
        pass
    
    @abstractmethod
    async def get_by_path(self, user_id: UUID, path: str, kind: Optional[NodeType] = None) -> Optional[Node]:
        """Get node by path."""
        pass
    
    @abstractmethod
    async def get_by_checksum(self, user_id: UUID, checksum: str) -> Optional[Node]:
        """Get file node by checksum."""
        pass
    
    @abstractmethod
    async def get_children(self, user_id: UUID, parent_id: Optional[UUID]) -> List[Node]:
        """Get child nodes."""
        pass
    
    @abstractmethod
    async def create(self, node: Node) -> Node:
        """Create new node."""
        pass
    
    @abstractmethod
    async def update(self, node: Node) -> Node:
        """Update existing node."""
        pass
    
    @abstractmethod
    async def soft_delete(self, node_id: UUID) -> bool:
        """Soft delete node."""
        pass
    
    @abstractmethod
    async def restore(self, node_id: UUID) -> bool:
        """Restore soft-deleted node."""
        pass
    
    @abstractmethod
    async def hard_delete(self, node_id: UUID) -> bool:
        """Permanently delete node."""
        pass
    
    @abstractmethod
    async def ensure_directory_path(self, user_id: UUID, path: str) -> Optional[UUID]:
        """Ensure directory path exists, return leaf directory ID."""
        pass
    
    @abstractmethod
    async def move_node(self, node_id: UUID, new_parent_id: Optional[UUID], new_path: str) -> bool:
        """Move node to new parent."""
        pass
