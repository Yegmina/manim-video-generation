"""
Base model with common fields and methods.

This module provides a base model class with common fields like
id, created_at, updated_at, and utility methods.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session
from pydantic import BaseModel as PydanticBaseModel

from ..core.database import Base


class BaseModel(Base):
    """
    Base model with common fields and methods.
    
    This class provides common functionality for all database models
    including timestamps, soft deletes, and utility methods.
    """
    
    __abstract__ = True
    
    # Common fields
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        """
        Update model instance with provided values.
        
        Args:
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete the model instance."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft-deleted model instance."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_by_id(cls, db: Session, id: int) -> Optional['BaseModel']:
        """
        Get model instance by ID.
        
        Args:
            db: Database session
            id: Model ID
            
        Returns:
            Optional[BaseModel]: Model instance or None
        """
        return db.query(cls).filter(cls.id == id, cls.is_active == True).first()
    
    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100) -> list['BaseModel']:
        """
        Get all active model instances.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            list[BaseModel]: List of model instances
        """
        return db.query(cls).filter(cls.is_active == True).offset(skip).limit(limit).all()
    
    @classmethod
    def count(cls, db: Session) -> int:
        """
        Count all active model instances.
        
        Args:
            db: Database session
            
        Returns:
            int: Number of active instances
        """
        return db.query(cls).filter(cls.is_active == True).count()
    
    def save(self, db: Session) -> 'BaseModel':
        """
        Save the model instance to database.
        
        Args:
            db: Database session
            
        Returns:
            BaseModel: Saved model instance
        """
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete(self, db: Session) -> None:
        """
        Delete the model instance from database.
        
        Args:
            db: Database session
        """
        db.delete(self)
        db.commit()


class PydanticBase(PydanticBaseModel):
    """
    Base Pydantic model with common configuration.
    """
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
