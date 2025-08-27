"""
FastAPI application startup script.

This script starts the Manim Video Generation API server.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the parent directory to Python path to import the manim_video_generator
sys.path.append(str(Path(__file__).parent.parent))

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Import settings
    from app.core.config import settings
    
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    print(f"Host: {settings.host}")
    print(f"Port: {settings.port}")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
        log_level=settings.log_level.lower()
    )
