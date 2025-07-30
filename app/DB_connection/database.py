
import os
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.utils.console_logger import info, debug, error

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
    debug("Creating new database session.", "[DBManager]")
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        error(f"An error occurred in database session: {e}", "[DBManager]")
        await session.rollback()
        raise
    finally:
        debug("Closing database session.", "[DBManager]")
        await session.close() 