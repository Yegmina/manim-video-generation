"""
User model for authentication and user management.

This module contains the User model and related functionality
for user authentication and management.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, EmailStr

from .base import BaseModel as DBBaseModel, PydanticBase


class User(DBBaseModel):
    """
    User model for authentication and user management.
    
    This model handles user accounts, authentication, and
    relationship to video generations.
    """
    
    # Basic user information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Account information
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    video_generations = relationship("VideoGeneration", back_populates="user")
    
    def __init__(self, **kwargs):
        """Initialize user with default values."""
        super().__init__(**kwargs)
        if not self.is_active:
            self.is_active = True
        if not self.is_verified:
            self.is_verified = False
        if not self.login_count:
            self.login_count = 0
    
    def update_last_login(self) -> None:
        """Update last login timestamp and increment login count."""
        self.last_login = datetime.utcnow()
        self.login_count += 1
    
    def verify_account(self) -> None:
        """Mark user account as verified."""
        self.is_verified = True
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
    
    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
    
    def get_video_generations_count(self) -> int:
        """Get the number of video generations for this user."""
        return len([vg for vg in self.video_generations if vg.is_active])
    
    def get_recent_video_generations(self, limit: int = 10) -> List['VideoGeneration']:
        """
        Get recent video generations for this user.
        
        Args:
            limit: Maximum number of video generations to return
            
        Returns:
            List[VideoGeneration]: Recent video generations
        """
        active_generations = [vg for vg in self.video_generations if vg.is_active]
        return sorted(active_generations, key=lambda x: x.created_at, reverse=True)[:limit]


# Pydantic models for API requests and responses
class UserCreate(PydanticBase):
    """Pydantic model for creating users."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, description="Password")


class UserUpdate(PydanticBase):
    """Pydantic model for updating users."""
    
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(PydanticBase):
    """Pydantic model for user responses."""
    
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    login_count: int


class UserInDB(UserResponse):
    """Pydantic model for user in database (includes hashed password)."""
    
    hashed_password: str


class UserLogin(PydanticBase):
    """Pydantic model for user login."""
    
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class UserPasswordChange(PydanticBase):
    """Pydantic model for password change."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
