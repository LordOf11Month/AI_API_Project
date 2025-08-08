"""
Database Management Module

This module provides a centralized system for managing the database connection
using a singleton pattern. It ensures that a single database engine and session
factory are created and shared throughout the application, promoting efficiency
and consistency.

Key Components:
- DatabaseManager: A singleton class that initializes and holds the database
  engine and session factory. It reads connection details from environment
  variables.
- get_db: A FastAPI dependency that provides a database session to API endpoints,
  handling session creation, commit, rollback, and closing automatically.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""

import os
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.utils.console_logger import info, debug, error

class DatabaseManager:
    """
    A singleton class to manage the database connection, engine, and sessions.
    
    This class ensures that only one instance of the database engine and session
    factory is created, providing a single point of access for database operations.
    """
    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        """
        Creates a new instance if one doesn't exist, following the singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Initializes the database engine and session factory using environment variables.
        """
        if self._engine is None:
            info("Initializing DatabaseManager...", "[DBManager]")
            # Get PostgreSQL connection details from environment variables
            DB_USER = os.getenv("DB_USER","postgres")
            DB_PASSWORD = os.getenv("DB_PASSWORD","")
            DB_HOST = os.getenv("DB_HOST", "localhost")
            DB_PORT = os.getenv("DB_PORT", "5432")
            DB_NAME = os.getenv("DB_NAME","AI_api_Center_db")
            debug(f"DB Config: User={DB_USER}, Host={DB_HOST}, Port={DB_PORT}, DB_Name={DB_NAME}", "[DBManager]")
            
            # Construct PostgreSQL URL
            DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

            # Create async engine and session factory
            info("Creating async database engine...", "[DBManager]")
            self._engine = create_async_engine(DATABASE_URL)
            self._SessionLocal = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
                class_=AsyncSession
            )
            info("DatabaseManager initialized successfully.", "[DBManager]")

    @property
    def engine(self):
        """Provides access to the SQLAlchemy engine instance."""
        return self._engine

    @property
    def SessionLocal(self):
        """Provides access to the SQLAlchemy session factory."""
        return self._SessionLocal

# Create a single instance that will be used throughout the application
db_manager = DatabaseManager()

# Export the session factory for use in other modules
SessionLocal = db_manager.SessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get a database session.
    
    This function is used as a dependency in API endpoints to provide a database
    session. It ensures that the session is properly closed and handles rollbacks
    in case of errors.
    
    Yields:
        AsyncSession: An asynchronous database session.
    """
    debug("Creating new database session.", "[DBManager]")
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        error(f"An error occurred in database session at line {e.__traceback__.tb_lineno}: {e}", "[DBManager]")
        await session.rollback()
        raise
    finally:
        debug("Closing database session.", "[DBManager]")
        await session.close() 