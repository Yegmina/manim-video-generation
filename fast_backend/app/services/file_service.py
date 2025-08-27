"""
File service for handling file operations.

This module provides file management functionality including
upload handling, validation, and storage operations.
"""

import os
import shutil
import logging
from typing import Optional, List
from pathlib import Path
import aiofiles
from fastapi import UploadFile, HTTPException

from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class FileService:
    """
    Service for file operations and management.
    
    This service handles file uploads, validation, storage,
    and cleanup operations.
    """
    
    def __init__(self):
        """Initialize file service."""
        self.upload_path = settings.upload_path
        self.video_output_path = settings.video_output_path
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = settings.allowed_extensions
    
    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension.
        
        Args:
            filename: File name to validate
            
        Returns:
            bool: True if extension is allowed
        """
        if not filename:
            return False
        
        file_ext = Path(filename).suffix.lower().lstrip('.')
        return file_ext in self.allowed_extensions
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size.
        
        Args:
            file_size: File size in bytes
            
        Returns:
            bool: True if file size is within limits
        """
        return file_size <= self.max_file_size
    
    async def save_upload_file(self, upload_file: UploadFile, filename: Optional[str] = None) -> Path:
        """
        Save uploaded file to storage.
        
        Args:
            upload_file: Uploaded file
            filename: Custom filename (optional)
            
        Returns:
            Path: Path to saved file
            
        Raises:
            HTTPException: If file validation fails
        """
        try:
            # Validate file
            if not self.validate_file_extension(upload_file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"File extension not allowed. Allowed: {', '.join(self.allowed_extensions)}"
                )
            
            # Use provided filename or original filename
            save_filename = filename or upload_file.filename
            file_path = self.upload_path / save_filename
            
            # Ensure unique filename
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = self.upload_path / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await upload_file.read()
                await f.write(content)
            
            logger.info(f"File saved: {file_path}")
            return file_path
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save file")
    
    def delete_file(self, file_path: Path) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_info(self, file_path: Path) -> dict:
        """
        Get file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            dict: File information
        """
        try:
            if not file_path.exists():
                return {"error": "File not found"}
            
            stat = file_path.stat()
            return {
                "filename": file_path.name,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "extension": file_path.suffix,
                "path": str(file_path)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {"error": str(e)}
    
    def cleanup_old_files(self, max_age_days: int = 7) -> int:
        """
        Clean up old files.
        
        Args:
            max_age_days: Maximum age of files in days
            
        Returns:
            int: Number of files deleted
        """
        import time
        from datetime import datetime, timedelta
        
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            deleted_count = 0
            
            # Clean up upload directory
            for file_path in self.upload_path.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    if self.delete_file(file_path):
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0
    
    def get_storage_usage(self) -> dict:
        """
        Get storage usage information.
        
        Returns:
            dict: Storage usage information
        """
        try:
            upload_size = sum(f.stat().st_size for f in self.upload_path.rglob('*') if f.is_file())
            video_size = sum(f.stat().st_size for f in self.video_output_path.rglob('*') if f.is_file())
            
            upload_files = len(list(self.upload_path.rglob('*')))
            video_files = len(list(self.video_output_path.rglob('*')))
            
            return {
                "upload_directory": {
                    "size_bytes": upload_size,
                    "size_mb": upload_size / (1024 * 1024),
                    "file_count": upload_files
                },
                "video_directory": {
                    "size_bytes": video_size,
                    "size_mb": video_size / (1024 * 1024),
                    "file_count": video_files
                },
                "total": {
                    "size_bytes": upload_size + video_size,
                    "size_mb": (upload_size + video_size) / (1024 * 1024),
                    "file_count": upload_files + video_files
                }
            }
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return {"error": str(e)}
    
    def ensure_directory_exists(self, directory: Path) -> bool:
        """
        Ensure directory exists.
        
        Args:
            directory: Directory path
            
        Returns:
            bool: True if directory exists or was created
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False
