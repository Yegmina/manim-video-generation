"""
Video generation service.

This module provides the video generation service that handles
video creation, status tracking, and file management.
"""

import os
import asyncio
import tempfile
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from sqlalchemy.orm import Session
import aiofiles
import shutil

from ..core.config import settings
from ..models.video import VideoGeneration, VideoStatus, VideoQuality, VideoFormat
from ..models.user import User
from .file_service import FileService
from .manim_code_converter import convert_manim_code, validate_manim_code

# Configure logging
logger = logging.getLogger(__name__)


class VideoGenerationService:
    """
    Service for video generation operations.
    
    This service handles video generation requests, status tracking,
    and integration with the Manim video generator.
    """
    
    def __init__(self, db: Session, file_service: FileService):
        """
        Initialize video generation service.
        
        Args:
            db: Database session
            file_service: File service instance
        """
        self.db = db
        self.file_service = file_service
        self._manim_generator = None
    
    @property
    def manim_generator(self):
        """Get or create Manim video generator instance."""
        if self._manim_generator is None:
            # Import here to avoid circular imports
            import sys
            sys.path.append(str(Path(__file__).parent.parent.parent.parent))
            from manim_video_generator import ManimVideoGenerator
            
            self._manim_generator = ManimVideoGenerator(
                output_dir=str(settings.video_output_path),
                manim_path=settings.manim_path
            )
        return self._manim_generator
    
    async def create_video_generation(
        self,
        title: str,
        script_content: str,
        scene_name: str,
        user: Optional[User] = None,
        description: Optional[str] = None,
        quality: VideoQuality = VideoQuality.LOW_QUALITY,
        format: VideoFormat = VideoFormat.MP4,
        output_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> VideoGeneration:
        """
        Create a new video generation request.
        
        Args:
            title: Video title
            script_content: Manim script content
            scene_name: Scene class name
            user: User who created the request
            description: Video description
            quality: Video quality
            format: Video format
            output_name: Custom output filename
            tags: List of tags
            metadata: Additional metadata
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            VideoGeneration: Created video generation instance
        """
        try:
            # Create video generation record
            video_gen = VideoGeneration(
                title=title,
                description=description,
                script_content=script_content,
                scene_name=scene_name,
                quality=quality,
                format=format,
                output_name=output_name,
                tags=tags,
                metadata=metadata,
                user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Save to database
            self.db.add(video_gen)
            self.db.commit()
            self.db.refresh(video_gen)
            
            logger.info(f"Created video generation request: {video_gen.id}")
            return video_gen
            
        except Exception as e:
            logger.error(f"Error creating video generation: {e}")
            self.db.rollback()
            raise
    
    async def start_video_generation(self, video_gen_id: int) -> bool:
        """
        Start video generation process.
        
        Args:
            video_gen_id: Video generation ID
            
        Returns:
            bool: True if started successfully
        """
        try:
            # Get video generation record
            video_gen = self.db.query(VideoGeneration).filter(
                VideoGeneration.id == video_gen_id,
                VideoGeneration.is_active == True
            ).first()
            
            if not video_gen:
                logger.error(f"Video generation not found: {video_gen_id}")
                return False
            
            if not video_gen.is_pending():
                logger.warning(f"Video generation {video_gen_id} is not pending")
                return False
            
            # Mark as processing
            video_gen.start_processing()
            self.db.commit()
            
            # Start async generation
            asyncio.create_task(self._generate_video_async(video_gen_id))
            
            logger.info(f"Started video generation: {video_gen_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting video generation {video_gen_id}: {e}")
            return False
    
    async def _generate_video_async(self, video_gen_id: int) -> None:
        """
        Generate video asynchronously.
        
        Args:
            video_gen_id: Video generation ID
        """
        try:
            # Get video generation record
            video_gen = self.db.query(VideoGeneration).filter(
                VideoGeneration.id == video_gen_id,
                VideoGeneration.is_active == True
            ).first()
            
            if not video_gen:
                logger.error(f"Video generation not found: {video_gen_id}")
                return
            
            # Convert script content for Manim v0.19.0+ compatibility
            logger.info(f"Converting script content for Manim v0.19.0+ compatibility")
            converted_script_content = convert_manim_code(video_gen.script_content)
            
            # Log if conversion was needed
            if converted_script_content != video_gen.script_content:
                logger.info("Script content was converted for compatibility")
            else:
                logger.info("Script content was already compatible")
            
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(converted_script_content)
                temp_script_path = temp_file.name
            
            try:
                # Generate video using Manim
                output_name = video_gen.output_name or f"video_{video_gen_id}"
                
                video_path = self.manim_generator.generate_video(
                    script_path=temp_script_path,
                    scene_name=video_gen.scene_name,
                    quality=video_gen.quality.value,
                    format=video_gen.format.value,
                    output_name=output_name
                )
                
                if video_path:
                    # Get file information
                    file_size = os.path.getsize(video_path) if os.path.exists(video_path) else None
                    
                    # Update video generation record
                    video_gen.complete(
                        output_path=str(video_path),
                        file_size=file_size
                    )
                    
                    logger.info(f"Video generation completed: {video_gen_id}")
                else:
                    video_gen.fail("Video generation failed - no output file produced")
                    logger.error(f"Video generation failed: {video_gen_id}")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_script_path):
                    os.unlink(temp_script_path)
            
            # Save changes
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error in video generation {video_gen_id}: {e}")
            
            # Update status to failed
            try:
                video_gen = self.db.query(VideoGeneration).filter(
                    VideoGeneration.id == video_gen_id,
                    VideoGeneration.is_active == True
                ).first()
                
                if video_gen:
                    video_gen.fail(str(e))
                    self.db.commit()
            except Exception as commit_error:
                logger.error(f"Error updating failed status: {commit_error}")
    
    async def get_video_generation(self, video_gen_id: int) -> Optional[VideoGeneration]:
        """
        Get video generation by ID.
        
        Args:
            video_gen_id: Video generation ID
            
        Returns:
            Optional[VideoGeneration]: Video generation instance
        """
        return self.db.query(VideoGeneration).filter(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.is_active == True
        ).first()
    
    async def get_video_generations(
        self,
        user: Optional[User] = None,
        status: Optional[VideoStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[VideoGeneration]:
        """
        Get video generations with filters.
        
        Args:
            user: Filter by user
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[VideoGeneration]: List of video generations
        """
        query = self.db.query(VideoGeneration).filter(VideoGeneration.is_active == True)
        
        if user:
            query = query.filter(VideoGeneration.user_id == user.id)
        
        if status:
            query = query.filter(VideoGeneration.status == status)
        
        return query.order_by(VideoGeneration.created_at.desc()).offset(skip).limit(limit).all()
    
    async def cancel_video_generation(self, video_gen_id: int, user: Optional[User] = None) -> bool:
        """
        Cancel video generation.
        
        Args:
            video_gen_id: Video generation ID
            user: User requesting cancellation
            
        Returns:
            bool: True if cancelled successfully
        """
        try:
            video_gen = self.db.query(VideoGeneration).filter(
                VideoGeneration.id == video_gen_id,
                VideoGeneration.is_active == True
            ).first()
            
            if not video_gen:
                logger.error(f"Video generation not found: {video_gen_id}")
                return False
            
            # Check if user can cancel this generation
            if user and video_gen.user_id != user.id:
                logger.warning(f"User {user.id} cannot cancel video generation {video_gen_id}")
                return False
            
            if not video_gen.can_be_cancelled():
                logger.warning(f"Video generation {video_gen_id} cannot be cancelled")
                return False
            
            video_gen.cancel()
            self.db.commit()
            
            logger.info(f"Cancelled video generation: {video_gen_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling video generation {video_gen_id}: {e}")
            return False
    
    async def delete_video_generation(self, video_gen_id: int, user: Optional[User] = None) -> bool:
        """
        Delete video generation (soft delete).
        
        Args:
            video_gen_id: Video generation ID
            user: User requesting deletion
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            video_gen = self.db.query(VideoGeneration).filter(
                VideoGeneration.id == video_gen_id,
                VideoGeneration.is_active == True
            ).first()
            
            if not video_gen:
                logger.error(f"Video generation not found: {video_gen_id}")
                return False
            
            # Check if user can delete this generation
            if user and video_gen.user_id != user.id:
                logger.warning(f"User {user.id} cannot delete video generation {video_gen_id}")
                return False
            
            video_gen.soft_delete()
            self.db.commit()
            
            logger.info(f"Deleted video generation: {video_gen_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting video generation {video_gen_id}: {e}")
            return False
    
    async def get_video_file(self, video_gen_id: int, user: Optional[User] = None) -> Optional[Path]:
        """
        Get video file path if generation is completed.
        
        Args:
            video_gen_id: Video generation ID
            user: User requesting the file
            
        Returns:
            Optional[Path]: Path to video file
        """
        try:
            video_gen = await self.get_video_generation(video_gen_id)
            
            if not video_gen:
                return None
            
            # Check if user can access this file
            if user and video_gen.user_id != user.id:
                logger.warning(f"User {user.id} cannot access video generation {video_gen_id}")
                return None
            
            if not video_gen.is_completed():
                logger.warning(f"Video generation {video_gen_id} is not completed")
                return None
            
            if not video_gen.output_file_path:
                logger.warning(f"Video generation {video_gen_id} has no output file path")
                return None
            
            video_path = Path(video_gen.output_file_path)
            
            if not video_path.exists():
                logger.error(f"Video file not found: {video_path}")
                return None
            
            return video_path
            
        except Exception as e:
            logger.error(f"Error getting video file for {video_gen_id}: {e}")
            return None
    
    async def get_statistics(self, user: Optional[User] = None) -> Dict[str, Any]:
        """
        Get video generation statistics.
        
        Args:
            user: Filter statistics by user
            
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        try:
            query = self.db.query(VideoGeneration).filter(VideoGeneration.is_active == True)
            
            if user:
                query = query.filter(VideoGeneration.user_id == user.id)
            
            total = query.count()
            completed = query.filter(VideoGeneration.status == VideoStatus.COMPLETED).count()
            failed = query.filter(VideoGeneration.status.in_([VideoStatus.FAILED, VideoStatus.TIMEOUT])).count()
            processing = query.filter(VideoGeneration.status == VideoStatus.PROCESSING).count()
            pending = query.filter(VideoGeneration.status == VideoStatus.PENDING).count()
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "pending": pending,
                "success_rate": (completed / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "processing": 0,
                "pending": 0,
                "success_rate": 0
            }
