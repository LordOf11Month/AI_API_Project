from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if self._engine is None:
            # Get PostgreSQL connection details from environment variables
            DB_USER = os.getenv("DB_USER","postgres")
            print(DB_USER)
            DB_PASSWORD = os.getenv("DB_PASSWORD","")
            print(DB_PASSWORD)
            DB_HOST = os.getenv("DB_HOST", "localhost")
            print(DB_HOST)
            DB_PORT = os.getenv("DB_PORT", "5432")
            print(DB_PORT)
            DB_NAME = os.getenv("DB_NAME","AI_api_Center_db")
            print(DB_NAME)
            # Validate required environment variables
            required_vars = {
                "DB_USER": DB_USER,
                "DB_PASSWORD": DB_PASSWORD,
                "DB_NAME": DB_NAME
            }

            # missing_vars = [var for var, value in required_vars.items() if not value]
            # if missing_vars:
            #     raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

            # Construct PostgreSQL URL
            DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

            # Create async engine and session factory
            self._engine = create_async_engine(DATABASE_URL)
            self._SessionLocal = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
                class_=AsyncSession
            )

    @property
    def engine(self):
        return self._engine

    @property
    def SessionLocal(self):
        return self._SessionLocal

# Create a single instance that will be used throughout the application
db_manager = DatabaseManager()

# Export the session factory for use in other modules
SessionLocal = db_manager.SessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields database sessions
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close() 