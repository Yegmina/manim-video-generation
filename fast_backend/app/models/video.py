"""
Video generation models.

This module contains models for video generation requests,
status tracking, and metadata management.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from .base import BaseModel as DBBaseModel, PydanticBase


class VideoStatus(str, Enum):
    """Video generation status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class VideoQuality(str, Enum):
    """Video quality enumeration."""
    LOW_QUALITY = "low_quality"
    MEDIUM_QUALITY = "medium_quality"
    HIGH_QUALITY = "high_quality"
    PRODUCTION_QUALITY = "production_quality"


class VideoFormat(str, Enum):
    """Video format enumeration."""
    MP4 = "mp4"
    GIF = "gif"
    WEBM = "webm"


class VideoGeneration(DBBaseModel):
    """
    Video generation request model.
    
    This model tracks video generation requests, their status,
    and associated metadata.
    """
    
    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Script information
    script_content = Column(Text, nullable=False)
    script_filename = Column(String(255), nullable=True)
    scene_name = Column(String(255), nullable=False)
    
    # Generation parameters
    quality = Column(SQLEnum(VideoQuality), default=VideoQuality.LOW_QUALITY, nullable=False)
    format = Column(SQLEnum(VideoFormat), default=VideoFormat.MP4, nullable=False)
    output_name = Column(String(255), nullable=True)
    
    # Status and progress
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.PENDING, nullable=False, index=True)
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    error_message = Column(Text, nullable=True)
    
    # File paths and metadata
    input_file_path = Column(String(500), nullable=True)
    output_file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes
    duration = Column(Float, nullable=True)  # in seconds
    
    # Processing information
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    
    # User and system information
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    
    # Additional metadata
    video_metadata = Column(JSON, nullable=True)  # Flexible metadata storage
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Relationships
    user = relationship("User", back_populates="video_generations")
    
    def __init__(self, **kwargs):
        """Initialize video generation with default values."""
        super().__init__(**kwargs)
        if not self.status:
            self.status = VideoStatus.PENDING
        if not self.progress:
            self.progress = 0.0
    
    def start_processing(self) -> None:
        """Mark video generation as started."""
        self.status = VideoStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.progress = 0.0
    
    def update_progress(self, progress: float) -> None:
        """
        Update processing progress.
        
        Args:
            progress: Progress value between 0.0 and 1.0
        """
        self.progress = max(0.0, min(1.0, progress))
    
    def complete(self, output_path: str, file_size: Optional[int] = None, duration: Optional[float] = None) -> None:
        """
        Mark video generation as completed.
        
        Args:
            output_path: Path to the generated video file
            file_size: Size of the generated file in bytes
            duration: Duration of the video in seconds
        """
        self.status = VideoStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 1.0
        self.output_file_path = output_path
        self.file_size = file_size
        self.duration = duration
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def fail(self, error_message: str) -> None:
        """
        Mark video generation as failed.
        
        Args:
            error_message: Error message describing the failure
        """
        self.status = VideoStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def cancel(self) -> None:
        """Mark video generation as cancelled."""
        self.status = VideoStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def timeout(self) -> None:
        """Mark video generation as timed out."""
        self.status = VideoStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error_message = "Video generation timed out"
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def is_completed(self) -> bool:
        """Check if video generation is completed."""
        return self.status == VideoStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if video generation failed."""
        return self.status in [VideoStatus.FAILED, VideoStatus.TIMEOUT]
    
    def is_processing(self) -> bool:
        """Check if video generation is in progress."""
        return self.status == VideoStatus.PROCESSING
    
    def is_pending(self) -> bool:
        """Check if video generation is pending."""
        return self.status == VideoStatus.PENDING
    
    def can_be_cancelled(self) -> bool:
        """Check if video generation can be cancelled."""
        return self.status in [VideoStatus.PENDING, VideoStatus.PROCESSING]
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get comprehensive status information.
        
        Returns:
            Dict[str, Any]: Status information dictionary
        """
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
            "output_file_path": self.output_file_path,
            "file_size": self.file_size,
            "duration": self.duration
        }


# Pydantic models for API requests and responses
class VideoGenerationCreate(PydanticBase):
    """Pydantic model for creating video generation requests."""
    
    title: str = Field(..., min_length=1, max_length=255, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    script_content: str = Field(..., min_length=1, description="Manim script content")
    script_filename: Optional[str] = Field(None, max_length=255, description="Original script filename")
    scene_name: str = Field(..., min_length=1, max_length=255, description="Scene class name")
    quality: VideoQuality = Field(VideoQuality.LOW_QUALITY, description="Video quality")
    format: VideoFormat = Field(VideoFormat.MP4, description="Video format")
    output_name: Optional[str] = Field(None, max_length=255, description="Custom output filename")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    video_metadata: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        description="Additional metadata",
    )


class VideoGenerationUpdate(PydanticBase):
    """Pydantic model for updating video generation requests."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    video_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")


class VideoGenerationResponse(PydanticBase):
    """Pydantic model for video generation responses."""
    
    id: int
    title: str
    description: Optional[str]
    status: VideoStatus
    progress: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    processing_time: Optional[float]
    error_message: Optional[str]
    output_file_path: Optional[str]
    file_size: Optional[int]
    duration: Optional[float]
    quality: VideoQuality
    format: VideoFormat
    scene_name: str
    tags: Optional[List[str]]
    video_metadata: Optional[Dict[str, Any]]


class VideoGenerationList(PydanticBase):
    """Pydantic model for video generation list responses."""
    
    items: List[VideoGenerationResponse]
    total: int
    page: int
    size: int
    pages: int
