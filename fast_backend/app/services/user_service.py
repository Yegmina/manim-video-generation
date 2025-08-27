"""
User service for managing user operations.

This module provides business logic for user management,
authentication, and authorization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..models.user import User, UserCreate, UserUpdate, UserResponse
from ..core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service class for user management operations."""
    
    def __init__(self):
        """Initialize the user service."""
        pass
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """
        Hash a password.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            str: JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Optional[Dict[str, Any]]: Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    async def create_user(self, db: Session, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            user_data: User creation data
            
        Returns:
            User: Created user object
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise ValueError("Username already registered")
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise ValueError("Email already registered")
        
        # Create user object
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False
        )
        
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError:
            db.rollback()
            raise ValueError("User creation failed")
    
    async def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Optional[User]: User object or None if not found
        """
        return db.query(User).filter(User.id == user_id).first()
    
    async def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            db: Database session
            username: Username
            
        Returns:
            Optional[User]: User object or None if not found
        """
        return db.query(User).filter(User.username == username).first()
    
    async def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            db: Database session
            email: Email address
            
        Returns:
            Optional[User]: User object or None if not found
        """
        return db.query(User).filter(User.email == email).first()
    
    async def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            db: Database session
            username: Username or email
            password: Plain text password
            
        Returns:
            Optional[User]: Authenticated user or None if authentication fails
        """
        # Try to find user by username or email
        user = await self.get_user_by_username(db, username)
        if not user:
            user = await self.get_user_by_email(db, username)
        
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db.commit()
        
        return user
    
    async def update_user(self, db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        Args:
            db: Database session
            user_id: User ID
            user_data: User update data
            
        Returns:
            Optional[User]: Updated user object or None if not found
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValueError("User update failed")
    
    async def delete_user(self, db: Session, user_id: int) -> bool:
        """
        Delete a user (soft delete).
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            bool: True if user was deleted, False if not found
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.soft_delete()
        db.commit()
        return True
    
    async def list_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """
        List users with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[User]: List of user objects
        """
        return db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    
    async def get_user_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Args:
            db: Database session
            
        Returns:
            Dict[str, Any]: User statistics
        """
        total_users = db.query(User).filter(User.is_active == True).count()
        verified_users = db.query(User).filter(User.is_active == True, User.is_verified == True).count()
        active_users = db.query(User).filter(User.is_active == True, User.last_login.isnot(None)).count()
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "active_users": active_users,
            "verification_rate": (verified_users / total_users * 100) if total_users > 0 else 0
        }


# Create service instance
user_service = UserService()
