"""High-level Telegram operations manager."""

import hashlib
import json
import mimetypes
import os
import subprocess
import tempfile
from typing import Optional, Tuple, BinaryIO

from pyrogram.client import Client
from pyrogram.types import Message

from ...core.exceptions import TelegramError, StorageError
from .client import TelegramClientManager


class TelegramManager:
    """High-level Telegram operations manager."""
    
    def __init__(self, client_manager: TelegramClientManager):
        self.client_manager = client_manager
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        channel_id: int | str,
        caption: Optional[str] = None,
        use_user_client: bool = False
    ) -> Message:
        """Upload file to Telegram channel."""
        try:
            clients = await self.client_manager.start()
            client = clients.user if use_user_client and clients.user else clients.bot
            
            if not client:
                raise TelegramError("No available client for upload")
            
            # Determine file type and upload method
            mime_type = mimetypes.guess_type(filename)[0]
            is_image = mime_type and mime_type.startswith('image/')
            is_video = mime_type and mime_type.startswith('video/')
            is_audio = mime_type and mime_type.startswith('audio/')
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_path = temp_file.name
                file_data.seek(0)
                temp_file.write(file_data.read())
            
            try:
                if is_image:
                    message = await client.send_photo(
                        chat_id=channel_id,
                        photo=temp_path,
                        caption=caption
                    )
                elif is_video:
                    # Extract video metadata for better preview
                    video_meta = self._extract_video_metadata(temp_path)
                    thumb_path = self._generate_video_thumbnail(temp_path)
                    
                    try:
                        video_kwargs = {
                            'chat_id': channel_id,
                            'video': temp_path,
                            'caption': caption,
                        }
                        
                        if video_meta.get('duration'):
                            video_kwargs['duration'] = video_meta['duration']
                        if video_meta.get('width'):
                            video_kwargs['width'] = video_meta['width']
                        if video_meta.get('height'):
                            video_kwargs['height'] = video_meta['height']
                        if thumb_path:
                            video_kwargs['thumb'] = thumb_path
                        
                        message = await client.send_video(**video_kwargs)
                    finally:
                        # Clean up thumbnail
                        if thumb_path and os.path.exists(thumb_path):
                            try:
                                os.remove(thumb_path)
                            except Exception:
                                pass
                elif is_audio:
                    message = await client.send_audio(
                        chat_id=channel_id,
                        audio=temp_path,
                        caption=caption
                    )
                else:
                    message = await client.send_document(
                        chat_id=channel_id,
                        document=temp_path,
                        file_name=filename,
                        caption=caption
                    )
                
                return message
                
            finally:
                # Clean up temporary file
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                    
        except Exception as e:
            raise StorageError(f"Failed to upload file: {e}")
    
    async def download_file(
        self,
        channel_id: int | str,
        message_id: int,
        use_user_client: bool = False
    ) -> bytes:
        """Download file from Telegram."""
        try:
            clients = await self.client_manager.start()
            client = clients.user if use_user_client and clients.user else clients.bot

            if not client:
                raise TelegramError("No available client for download")

            # Get message
            message = await client.get_messages(chat_id=channel_id, message_ids=message_id)
            if isinstance(message, list):
                message = message[0]

            # Download media to temporary file first, then read
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                # Download to temporary file
                downloaded_path = await client.download_media(message, file_name=temp_path)

                # Read file content
                with open(downloaded_path, 'rb') as f:
                    file_data = f.read()

                return file_data

            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass

        except Exception as e:
            raise StorageError(f"Failed to download file: {e}")
    
    async def get_chat_info(self, chat_id: int | str) -> dict:
        """Get chat information."""
        try:
            clients = await self.client_manager.start()
            chat = await clients.bot.get_chat(chat_id)
            
            return {
                'id': chat.id,
                'title': getattr(chat, 'title', None),
                'username': getattr(chat, 'username', None),
                'type': str(chat.type) if hasattr(chat, 'type') else None
            }
        except Exception as e:
            raise TelegramError(f"Failed to get chat info: {e}")
    
    def calculate_file_checksum(self, file_data: BinaryIO) -> str:
        """Calculate SHA256 checksum of file."""
        file_data.seek(0)
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: file_data.read(4096), b""):
            hash_sha256.update(chunk)
        file_data.seek(0)
        return hash_sha256.hexdigest()
    
    def _extract_video_metadata(self, video_path: str) -> dict:
        """Extract video metadata using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"DEBUG: ffprobe failed: {result.stderr}")
                return {}
            
            data = json.loads(result.stdout)
            video_stream = None
            
            # Find the first video stream
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return {}
            
            # Extract metadata
            duration = float(data.get('format', {}).get('duration', 0))
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            return {
                'duration': int(duration),
                'width': width,
                'height': height,
            }
        except Exception as e:
            print(f"DEBUG: Video metadata extraction failed: {e}")
            return {}
    
    def _generate_video_thumbnail(self, video_path: str) -> Optional[str]:
        """Generate video thumbnail using ffmpeg."""
        try:
            thumb_path = video_path + "_thumb.jpg"
            cmd = [
                'ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', 
                '-f', 'image2', '-y', thumb_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and os.path.exists(thumb_path):
                return thumb_path
            else:
                print(f"DEBUG: Thumbnail generation failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"DEBUG: Thumbnail generation error: {e}")
            return None
