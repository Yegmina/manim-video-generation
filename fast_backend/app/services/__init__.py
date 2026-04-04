"""
Services for the Manim Video Generation API.

This package contains business logic services including video generation,
file management, and user management.
"""

__all__ = ["VideoGenerationService", "FileService", "UserService"]


def __getattr__(name):
    """Lazily import service classes to avoid heavyweight import side effects."""
    if name == "VideoGenerationService":
        from .video_service import VideoGenerationService

        return VideoGenerationService
    if name == "FileService":
        from .file_service import FileService

        return FileService
    if name == "UserService":
        from .user_service import UserService

        return UserService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
