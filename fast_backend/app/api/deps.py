"""
Dependency injection functions.

This module provides dependency injection functions for
authentication, database access, and other common dependencies.
"""

from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User

# Security scheme
security = HTTPBearer()


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user (optional authentication).
    
    This function allows endpoints to work with or without authentication.
    If no valid token is provided, it returns None.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Optional[User]: Current user or None
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user


def get_current_user(
    current_user: User = Depends(get_current_user_optional)
) -> User:
    """
    Get current user (required authentication).
    
    This function requires valid authentication and raises an
    HTTP exception if no valid user is found.
    
    Args:
        current_user: Current user from optional dependency
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If no valid user is found
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    This function ensures the user account is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user account is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user.
    
    This function ensures the user account is verified.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current verified user
        
    Raises:
        HTTPException: If user account is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account not verified"
        )
    return current_user
