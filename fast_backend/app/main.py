"""
Main FastAPI application.

This module contains the main FastAPI application with all routes,
middleware, and configuration.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import os

from .core.config import settings
from .core.database import get_db, create_tables
from .api.v1.api import api_router
from .api.deps import get_current_user_optional
from .models.user import User

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Manim Video Generation API...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    # Create necessary directories
    os.makedirs(settings.upload_path, exist_ok=True)
    os.makedirs(settings.video_output_path, exist_ok=True)
    os.makedirs(settings.log_path.parent, exist_ok=True)
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Manim Video Generation API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A scalable FastAPI backend for generating mathematical animations using Manim",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure based on your domain
    )


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status information
    """
    from .core.database import check_database_connection, get_database_info
    
    db_connected = check_database_connection()
    
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": {
            "connected": db_connected,
            "info": get_database_info()
        },
        "services": {
            "manim": "available",
            "ffmpeg": "available"
        }
    }


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: API information
    """
    return {
        "message": "Welcome to Manim Video Generation API",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "health": "/health"
    }


# Video file serving endpoint
@app.get("/videos/{video_id}")
async def serve_video(
    video_id: int,
    current_user: User = Depends(get_current_user_optional),
    db = Depends(get_db)
):
    """
    Serve generated video files.
    
    Args:
        video_id: Video generation ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        FileResponse: Video file response
    """
    from .services.video_service import VideoGenerationService
    from .services.file_service import FileService
    
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


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url)
        }
    )


# Static files (for development)
if settings.debug:
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1
    )
