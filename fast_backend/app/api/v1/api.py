"""
Main API router.

This module contains the main API router that includes all
endpoint routers for the v1 API.
"""

from fastapi import APIRouter

from .endpoints import videos, text2video

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(videos.router, prefix="/manim2video", tags=["manim2video"])
# AI text to video route
api_router.include_router(text2video.router, prefix="/text2video", tags=["text2video"])
