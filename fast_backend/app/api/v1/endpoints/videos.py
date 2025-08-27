"""
Video generation API endpoints.

This module contains all video generation related API endpoints
including creation, status checking, and file download.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....api.deps import get_current_user_optional
from ....models.user import User
from ....models.video import (
    VideoGenerationCreate,
    VideoGenerationResponse,
    VideoGenerationUpdate,
    VideoGenerationList,
    VideoStatus,
    VideoQuality,
    VideoFormat
)
from ....services.video_service import VideoGenerationService
from ....services.file_service import FileService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=VideoGenerationResponse, status_code=201)
async def create_video_generation(
    *,
    video_data: VideoGenerationCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Create a new video generation request.
    
    This endpoint accepts Manim script code and parameters,
    creates a video generation request, and starts the generation process.
    
    Args:
        video_data: Video generation request data
        request: FastAPI request object
        background_tasks: Background tasks for async processing
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        VideoGenerationResponse: Created video generation information
    """
    try:
        # Initialize services
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        # Get client information
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Create video generation
        video_gen = await video_service.create_video_generation(
            title=video_data.title,
            script_content=video_data.script_content,
            scene_name=video_data.scene_name,
            user=current_user,
            description=video_data.description,
            quality=video_data.quality,
            format=video_data.format,
            output_name=video_data.output_name,
            tags=video_data.tags,
            metadata=video_data.video_metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Start video generation in background
        background_tasks.add_task(video_service.start_video_generation, video_gen.id)
        
        logger.info(f"Created video generation request: {video_gen.id}")
        
        return VideoGenerationResponse.from_orm(video_gen)
        
    except Exception as e:
        logger.error(f"Error creating video generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create video generation request")


@router.get("/{video_id}", response_model=VideoGenerationResponse)
async def get_video_generation(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get video generation by ID.
    
    Args:
        video_id: Video generation ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        VideoGenerationResponse: Video generation information
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        video_gen = await video_service.get_video_generation(video_id)
        
        if not video_gen:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Check access permissions
        if current_user and video_gen.user_id and video_gen.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return VideoGenerationResponse.from_orm(video_gen)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video generation {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video generation")


@router.get("/", response_model=VideoGenerationList)
async def list_video_generations(
    *,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[VideoStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    List video generations with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        VideoGenerationList: Paginated list of video generations
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        # Get video generations
        video_gens = await video_service.get_video_generations(
            user=current_user,
            status=status,
            skip=skip,
            limit=limit
        )
        
        # Get total count for pagination
        total = len(video_gens)  # This could be optimized with a separate count query
        
        return VideoGenerationList(
            items=[VideoGenerationResponse.from_orm(vg) for vg in video_gens],
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error listing video generations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list video generations")


@router.put("/{video_id}", response_model=VideoGenerationResponse)
async def update_video_generation(
    *,
    video_id: int,
    video_data: VideoGenerationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Update video generation metadata.
    
    Args:
        video_id: Video generation ID
        video_data: Update data
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        VideoGenerationResponse: Updated video generation information
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        video_gen = await video_service.get_video_generation(video_id)
        
        if not video_gen:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Check access permissions
        if current_user and video_gen.user_id and video_gen.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Only allow updates if not processing
        if video_gen.is_processing():
            raise HTTPException(status_code=400, detail="Cannot update video generation while processing")
        
        # Update fields
        update_data = video_data.dict(exclude_unset=True)
        video_gen.update(**update_data)
        
        db.commit()
        db.refresh(video_gen)
        
        return VideoGenerationResponse.from_orm(video_gen)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating video generation {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update video generation")


@router.delete("/{video_id}")
async def delete_video_generation(
    *,
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Delete video generation (soft delete).
    
    Args:
        video_id: Video generation ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        dict: Success message
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        success = await video_service.delete_video_generation(video_id, current_user)
        
        if not success:
            raise HTTPException(status_code=404, detail="Video generation not found or access denied")
        
        return {"message": "Video generation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video generation {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete video generation")


@router.post("/{video_id}/cancel")
async def cancel_video_generation(
    *,
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Cancel video generation.
    
    Args:
        video_id: Video generation ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        dict: Success message
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        success = await video_service.cancel_video_generation(video_id, current_user)
        
        if not success:
            raise HTTPException(status_code=404, detail="Video generation not found or cannot be cancelled")
        
        return {"message": "Video generation cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling video generation {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel video generation")


@router.get("/{video_id}/download")
async def download_video(
    *,
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Download generated video file.
    
    Args:
        video_id: Video generation ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        FileResponse: Video file response
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        video_path = await video_service.get_video_file(video_id, current_user)
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found or access denied")
        
        return FileResponse(
            path=video_path,
            media_type=f"video/{video_path.suffix[1:]}",
            filename=f"video_{video_id}{video_path.suffix}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download video")


@router.get("/{video_id}/status")
async def get_video_status(
    *,
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get video generation status.
    
    Args:
        video_id: Video generation ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        dict: Status information
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        video_gen = await video_service.get_video_generation(video_id)
        
        if not video_gen:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Check access permissions
        if current_user and video_gen.user_id and video_gen.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return video_gen.get_status_info()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video status {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video status")


@router.get("/statistics/summary")
async def get_statistics(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get video generation statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        dict: Statistics information
    """
    try:
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        
        stats = await video_service.get_statistics(current_user)
        
        return {
            "statistics": stats,
            "user_id": current_user.id if current_user else None
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")
