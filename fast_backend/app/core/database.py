"""
Database configuration and session management.

This module provides database connection setup, session management,
and database utilities for the application.
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from .config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Database engine / session are initialized lazily to keep imports lightweight.
engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_database_url() -> str:
    """
    Get the appropriate database URL based on environment.
    
    Returns:
        str: Database URL
    """
    settings = get_settings()
    if settings.is_testing and settings.database_test_url:
        return settings.database_test_url
    return settings.database_url


def get_engine():
    """Create and cache the database engine on first use."""
    global engine
    if engine is None:
        settings = get_settings()
        database_url = get_database_url()
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.debug,
            # For SQLite in testing
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Yields:
        Session: Database session
    """
    get_engine()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Get database session as context manager.
    
    Yields:
        Session: Database session
    """
    get_engine()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=get_engine())
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_tables():
    """Drop all database tables."""
    try:
        Base.metadata.drop_all(bind=get_engine())
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database information.
    
    Returns:
        dict: Database information
    """
    try:
        with get_db_context() as db:
            if "sqlite" in get_database_url():
                version_stmt = text("SELECT sqlite_version()")
            else:
                version_stmt = text("SELECT version()")
            result = db.execute(version_stmt).fetchone()
            version = result[0] if result else "Unknown"
            
        return {
            "url": get_database_url(),
            "version": version,
            "connected": check_database_connection(),
            "tables": list(Base.metadata.tables.keys())
        }
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            "url": get_database_url(),
            "version": "Unknown",
            "connected": False,
            "tables": [],
            "error": str(e)
        }
