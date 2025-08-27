"""Node domain entity for files and directories."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Node type enumeration."""
    FILE = "file"
    FOLDER = "folder"


class Node(BaseModel):
    """Node domain entity representing files and directories."""
    
    id: UUID
    user_id: UUID
    parent_id: Optional[UUID] = None
    name: str
    kind: NodeType
    path: str
    depth: int = 0
    sort_key: int = 0
    size_bytes: int = 0
    
    # File-specific fields
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    telegram_channel_id: Optional[int] = None
    telegram_message_id: Optional[int] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    def is_file(self) -> bool:
        """Check if node is a file."""
        return self.kind == NodeType.FILE
    
    def is_folder(self) -> bool:
        """Check if node is a folder."""
        return self.kind == NodeType.FOLDER
    
    def is_deleted(self) -> bool:
        """Check if node is soft-deleted."""
        return self.deleted_at is not None
    
    def is_root(self) -> bool:
        """Check if node is root (no parent)."""
        return self.parent_id is None
    
    def soft_delete(self) -> None:
        """Soft delete the node."""
        self.deleted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore soft-deleted node."""
        self.deleted_at = None
        self.updated_at = datetime.utcnow()
    
    def rename(self, new_name: str) -> None:
        """Rename the node."""
        self.name = new_name
        self.updated_at = datetime.utcnow()
    
    def move(self, new_parent_id: Optional[UUID], new_path: str, new_depth: int) -> None:
        """Move node to new parent."""
        self.parent_id = new_parent_id
        self.path = new_path
        self.depth = new_depth
        self.updated_at = datetime.utcnow()
    
    def get_file_extension(self) -> Optional[str]:
        """Get file extension if it's a file."""
        if not self.is_file():
            return None
        
        if "." not in self.name:
            return None
        
        return self.name.split(".")[-1].lower()
    
    def format_size(self) -> str:
        """Format file size in human readable format."""
        if self.size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
