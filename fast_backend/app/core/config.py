"""
Configuration management for the Manim Video Generation API.

This module provides centralized configuration management with
environment variable support and validation.
"""

import os
from typing import List, Optional, Union
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from pydantic.types import DirectoryPath, FilePath
import json


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    This class manages all configuration settings with proper
    validation and default values.
    """
    
    # Application Settings
    app_name: str = Field(default="Manim Video Generation API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_test_url: Optional[str] = Field(default=None, env="DATABASE_TEST_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_test_url: Optional[str] = Field(default=None, env="REDIS_TEST_URL")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # File Storage
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    video_output_dir: str = Field(default="generated_videos", env="VIDEO_OUTPUT_DIR")
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_extensions: List[str] = Field(default=["py", "txt", "md"], env="ALLOWED_EXTENSIONS")
    
    # Video Generation
    default_quality: str = Field(default="low_quality", env="DEFAULT_QUALITY")
    default_format: str = Field(default="mp4", env="DEFAULT_FORMAT")
    max_video_duration: int = Field(default=300, env="MAX_VIDEO_DURATION")  # 5 minutes
    max_concurrent_generations: int = Field(default=5, env="MAX_CONCURRENT_GENERATIONS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    
    # External Services
    ffmpeg_path: str = Field(default="/usr/bin/ffmpeg", env="FFMPEG_PATH")
    manim_path: str = Field(default="py", env="MANIM_PATH")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # CORS
    allowed_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"], env="ALLOWED_ORIGINS")
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="ALLOWED_METHODS")
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    
    # LLM Configuration
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    
    # Computed Properties
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment.lower() == "testing"
    
    @property
    def base_dir(self) -> Path:
        """Get the base directory of the application."""
        return Path(__file__).parent.parent.parent
    
    @property
    def upload_path(self) -> Path:
        """Get the upload directory path."""
        return self.base_dir / self.upload_dir
    
    @property
    def video_output_path(self) -> Path:
        """Get the video output directory path."""
        return self.base_dir / self.video_output_dir
    
    @property
    def log_path(self) -> Path:
        """Get the log file path."""
        return self.base_dir / self.log_file
    
    # Validators
    @validator("allowed_extensions")
    def validate_allowed_extensions(cls, v):
        """Validate allowed file extensions."""
        if not v:
            raise ValueError("At least one file extension must be allowed")
        return [ext.lower().strip() for ext in v]
    
    @validator("default_quality")
    def validate_default_quality(cls, v):
        """Validate default video quality."""
        valid_qualities = ["low_quality", "medium_quality", "high_quality", "production_quality"]
        if v not in valid_qualities:
            raise ValueError(f"Quality must be one of: {valid_qualities}")
        return v
    
    @validator("default_format")
    def validate_default_format(cls, v):
        """Validate default video format."""
        valid_formats = ["mp4", "gif", "webm"]
        if v not in valid_formats:
            raise ValueError(f"Format must be one of: {valid_formats}")
        return v
    
    @validator("max_file_size")
    def validate_max_file_size(cls, v):
        """Validate maximum file size."""
        if v <= 0:
            raise ValueError("Maximum file size must be positive")
        return v
    
    @validator("max_video_duration")
    def validate_max_video_duration(cls, v):
        """Validate maximum video duration."""
        if v <= 0:
            raise ValueError("Maximum video duration must be positive")
        return v
    
    @validator("max_concurrent_generations")
    def validate_max_concurrent_generations(cls, v):
        """Validate maximum concurrent generations."""
        if v <= 0:
            raise ValueError("Maximum concurrent generations must be positive")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Parse environment variables with JSON support."""
            if field_name in ["allowed_origins", "allowed_methods", "allowed_headers", "allowed_extensions"]:
                if raw_val.startswith("[") and raw_val.endswith("]"):
                    try:
                        return json.loads(raw_val)
                    except json.JSONDecodeError:
                        pass
                # Handle comma-separated values
                if "," in raw_val:
                    return [item.strip() for item in raw_val.split(",")]
                # Handle single value
                return [raw_val.strip()]
            return raw_val


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: The application settings.
    """
    return settings


def create_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        settings.upload_path,
        settings.video_output_path,
        settings.log_path.parent
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Create directories on import
create_directories()
