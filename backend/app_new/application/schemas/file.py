"""File and directory related schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    """File information response."""
    id: str = Field(..., description="File ID")
    name: str = Field(..., description="File name")
    size: int = Field(..., description="File size in bytes")
    size_formatted: str = Field(..., description="Human readable file size")
    mime_type: Optional[str] = Field(None, description="MIME type")
    path: str = Field(..., description="File path")
    created_at: str = Field(..., description="Creation timestamp")
    extension: Optional[str] = Field(None, description="File extension")


class DirectoryResponse(BaseModel):
    """Directory information response."""
    name: str = Field(..., description="Directory name")
    path: str = Field(..., description="Directory path")


class DirectoryListResponse(BaseModel):
    """Directory listing response."""
    path: str = Field(..., description="Current directory path")
    directories: List[DirectoryResponse] = Field(..., description="Subdirectories")
    files: List[FileResponse] = Field(..., description="Files")
    total_files: int = Field(..., description="Total number of files")
    total_size: int = Field(..., description="Total size of all files")


class UploadResponse(BaseModel):
    """File upload response."""
    file_id: str = Field(..., description="Uploaded file ID")
    message_id: int = Field(..., description="Telegram message ID")
    via: str = Field(..., description="Upload method (bot/user/dedup/instant)")
    name: str = Field(..., description="File name")
    size: int = Field(..., description="File size")
    path: str = Field(..., description="File path")


class MoveRequest(BaseModel):
    """File/directory move request."""
    new_name: Optional[str] = Field(None, description="New name")
    new_dir_path: Optional[str] = Field(None, description="New directory path")


class MoveResponse(BaseModel):
    """File/directory move response."""
    id: str = Field(..., description="Node ID")
    name: str = Field(..., description="New name")
    path: str = Field(..., description="New path")


class DeleteResponse(BaseModel):
    """File/directory delete response."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
