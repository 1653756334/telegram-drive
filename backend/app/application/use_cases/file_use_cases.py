"""File management use cases."""

import io
import mimetypes
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import UploadFile

from ...config.logging import get_logger
from ...domain.entities import Node, NodeType
from ...domain.repositories import UserRepository, NodeRepository, ChannelRepository
from ...infrastructure.telegram import TelegramManager
from ...core.exceptions import NotFoundError, ValidationError, StorageError, ConflictError

logger = get_logger(__name__)


class FileUseCases:
    """File management use cases."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        node_repository: NodeRepository,
        channel_repository: ChannelRepository,
        telegram_manager: TelegramManager
    ):
        self.user_repository = user_repository
        self.node_repository = node_repository
        self.channel_repository = channel_repository
        self.telegram_manager = telegram_manager
    
    async def list_directory(self, path: str = "/") -> Dict[str, Any]:
        """List files and directories in specified path."""
        try:
            path = self._normalize_path(path)
            user = await self.user_repository.get_or_create_single_user()
            
            # Get parent directory ID
            parent_id = None
            if path != "/":
                parent_dir = await self.node_repository.get_by_path(user.id, path, NodeType.FOLDER)
                if not parent_dir:
                    raise NotFoundError(f"Directory not found: {path}")
                parent_id = parent_dir.id
            
            # Get children
            children = await self.node_repository.get_children(user.id, parent_id)
            
            directories = []
            files = []
            total_size = 0
            
            for child in children:
                if child.is_folder():
                    directories.append({
                        "name": child.name,
                        "path": child.path
                    })
                else:
                    files.append({
                        "id": str(child.id),
                        "name": child.name,
                        "size": child.size_bytes,
                        "size_formatted": child.format_size(),
                        "mime_type": child.mime_type,
                        "path": child.path,
                        "created_at": child.created_at.isoformat(),
                        "extension": child.get_file_extension()
                    })
                    total_size += child.size_bytes
            
            return {
                "path": path,
                "directories": directories,
                "files": files,
                "total_files": len(files),
                "total_size": total_size
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to list directory: {e}")
    
    async def upload_file(self, path: str, file: UploadFile) -> Dict[str, Any]:
        """Upload a file to specified path."""
        try:
            logger.info(f"Starting file upload: {file.filename} to {path}")

            # Validate inputs
            if not file.filename:
                raise ValidationError("Filename is required")

            path = self._normalize_path(path)
            user = await self.user_repository.get_or_create_single_user()
            
            # Calculate full file path
            full_path = f"{path}/{file.filename}" if path != "/" else f"/{file.filename}"
            
            # Read file data
            file_data = await file.read()
            file_size = len(file_data)
            
            if file_size == 0:
                raise ValidationError("Cannot upload empty file")
            
            # Calculate checksum
            file_io = io.BytesIO(file_data)
            checksum = self.telegram_manager.calculate_file_checksum(file_io)
            
            # Check for existing file with same path
            existing_same_path = await self.node_repository.get_by_path(user.id, full_path, NodeType.FILE)
            if existing_same_path:
                if existing_same_path.checksum == checksum:
                    logger.info(f"File already exists with same content: {full_path}")
                    return {
                        "file_id": str(existing_same_path.id),
                        "message_id": existing_same_path.telegram_message_id or 0,
                        "via": "exists",
                        "name": existing_same_path.name,
                        "size": existing_same_path.size_bytes,
                        "path": existing_same_path.path
                    }
                else:
                    raise ConflictError(f"File already exists at path: {full_path}")

            # Check for deduplication
            existing_file = await self.node_repository.get_by_checksum(user.id, checksum)
            if existing_file:
                logger.debug(f"File deduplication found for: {file.filename}")
                # Create new node pointing to same Telegram message
                directory_id = await self.node_repository.ensure_directory_path(user.id, path)
                
                new_node = Node(
                    id=uuid4(),
                    user_id=user.id,
                    parent_id=directory_id,
                    name=file.filename,
                    kind=NodeType.FILE,
                    path=full_path,
                    depth=len([p for p in full_path.split("/") if p]),
                    size_bytes=existing_file.size_bytes,
                    mime_type=file.content_type or mimetypes.guess_type(file.filename)[0],
                    checksum=checksum,
                    telegram_channel_id=existing_file.telegram_channel_id,
                    telegram_message_id=existing_file.telegram_message_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                created_node = await self.node_repository.create(new_node)
                
                return {
                    "file_id": str(created_node.id),
                    "message_id": existing_file.telegram_message_id or 0,
                    "via": "dedup",
                    "name": created_node.name,
                    "size": created_node.size_bytes,
                    "path": created_node.path
                }
            
            # Get storage channel
            channel = await self.channel_repository.get_latest_for_user(user.id)
            if not channel:
                raise StorageError("No storage channel configured")
            
            # Ensure directory exists
            directory_id = await self.node_repository.ensure_directory_path(user.id, path)
            
            # Upload to Telegram
            use_user_client = file_size > 50 * 1024 * 1024  # > 50MB
            channel_identifier = channel.get_identifier()

            # INFO level: Basic upload information
            logger.info(f"Uploading file: {file.filename} ({self._format_file_size(file_size)}) to channel {channel_identifier}")

            # DEBUG level: Detailed upload information
            logger.debug(f"Upload details - Path: {full_path}, Client: {'user' if use_user_client else 'bot'}, Channel: {channel.title or 'Unknown'}")

            file_io.seek(0)
            message = await self.telegram_manager.upload_file(
                file_data=file_io,
                filename=file.filename,
                channel_id=channel_identifier,
                caption=f"File: {file.filename}",
                use_user_client=use_user_client
            )

            logger.debug(f"Telegram upload successful: message_id={message.id}")
            
            # Create node record
            new_node = Node(
                id=uuid4(),
                user_id=user.id,
                parent_id=directory_id,
                name=file.filename,
                kind=NodeType.FILE,
                path=full_path,
                depth=len([p for p in full_path.split("/") if p]),
                size_bytes=file_size,
                mime_type=file.content_type or mimetypes.guess_type(file.filename)[0],
                checksum=checksum,
                telegram_channel_id=channel.channel_id,
                telegram_message_id=message.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            created_node = await self.node_repository.create(new_node)
            
            return {
                "file_id": str(created_node.id),
                "message_id": message.id,
                "via": "user" if use_user_client else "bot",
                "name": created_node.name,
                "size": created_node.size_bytes,
                "path": created_node.path
            }
            
        except (ValidationError, ConflictError, StorageError):
            raise
        except Exception as e:
            raise StorageError(f"File upload failed: {e}")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file by ID."""
        # INFO level: Basic download request
        logger.info(f"Download request for file: {file_id}")

        try:
            file_uuid = UUID(file_id)
        except ValueError:
            raise ValidationError("Invalid file ID format")

        try:
            user = await self.user_repository.get_or_create_single_user()
            node = await self.node_repository.get_by_id(file_uuid)

            if node:
                # DEBUG level: File details
                logger.debug(f"Found file: {node.name} ({self._format_file_size(node.size_bytes or 0)}) in {node.path}")

            if not node or node.user_id != user.id:
                raise NotFoundError("File not found")

            if not node.is_file():
                raise ValidationError("Cannot download directory")

            if not node.telegram_channel_id or not node.telegram_message_id:
                raise StorageError("File has no Telegram reference")

            # Get channel info for download
            channel = await self.channel_repository.get_by_user_and_channel_id(
                user.id, node.telegram_channel_id
            )

            if not channel:
                raise StorageError("Storage channel not found")

            # Try download with multiple identifiers
            channel_identifier = channel.get_identifier()
            use_user_client = node.size_bytes > 50 * 1024 * 1024

            logger.info(f"Downloading from Telegram: {node.name} via {'user' if use_user_client else 'bot'} client")

            try:
                # DEBUG level: Download attempt details
                logger.debug(f"Downloading from Telegram - Channel: {channel_identifier}, Message: {node.telegram_message_id}, Client: {'user' if use_user_client else 'bot'}")

                file_data = await self.telegram_manager.download_file(
                    channel_id=channel_identifier,
                    message_id=node.telegram_message_id,
                    use_user_client=use_user_client
                )

                # INFO level: Download success
                logger.info(f"Download completed: {node.name} ({self._format_file_size(len(file_data))})")
                return file_data, node.name

            except Exception as e:
                logger.warning(f"Download failed with {channel_identifier}, trying fallback: {e}")
                # Fallback to channel ID if username fails
                if channel_identifier != channel.channel_id:
                    logger.debug(f"Attempting fallback download with channel ID: {channel.channel_id}")
                    file_data = await self.telegram_manager.download_file(
                        channel_id=channel.channel_id,
                        message_id=node.telegram_message_id,
                        use_user_client=use_user_client
                    )
                    logger.info(f"Fallback download completed: {node.name} ({self._format_file_size(len(file_data))})")
                    return file_data, node.name
                raise

        except (NotFoundError, ValidationError, StorageError):
            raise
        except Exception as e:
            raise StorageError(f"File download failed: {e}")
    
    async def move_file(
        self,
        file_id: str,
        new_name: Optional[str] = None,
        new_dir_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move or rename file."""
        try:
            file_uuid = UUID(file_id)
        except ValueError:
            raise ValidationError("Invalid file ID format")
        
        try:
            user = await self.user_repository.get_or_create_single_user()
            node = await self.node_repository.get_by_id(file_uuid)
            
            if not node or node.user_id != user.id:
                raise NotFoundError("File not found")
            
            # Update name if provided
            if new_name:
                node.rename(new_name)
            
            # Update directory if provided
            if new_dir_path:
                new_dir_path = self._normalize_path(new_dir_path)
                new_parent_id = await self.node_repository.ensure_directory_path(user.id, new_dir_path)
                new_path = f"{new_dir_path}/{node.name}" if new_dir_path != "/" else f"/{node.name}"
                node.move(new_parent_id, new_path, len([p for p in new_path.split("/") if p]))
            
            # Save changes
            updated_node = await self.node_repository.update(node)
            
            return {
                "id": str(updated_node.id),
                "name": updated_node.name,
                "path": updated_node.path
            }
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise StorageError(f"File move failed: {e}")
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by ID (soft delete)."""
        try:
            file_uuid = UUID(file_id)
        except ValueError:
            raise ValidationError("Invalid file ID format")
        
        try:
            user = await self.user_repository.get_or_create_single_user()
            node = await self.node_repository.get_by_id(file_uuid)
            
            if not node or node.user_id != user.id:
                raise NotFoundError("File not found")
            
            return await self.node_repository.soft_delete(file_uuid)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise StorageError(f"File deletion failed: {e}")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize directory path."""
        p = (path or "/").strip()
        if not p.startswith("/"):
            p = "/" + p
        # remove trailing slash except root
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p
