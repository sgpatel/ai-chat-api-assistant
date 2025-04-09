# app/db/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings, logger

# Create the async engine for SQLite using URL from settings
engine = create_async_engine(settings.DATABASE_URL, echo=False) # Set echo=True for SQL logging

# Create a configured "Session" class
# expire_on_commit=False is often useful with async sessions and background tasks
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()

# Dependency to get DB session in API endpoints/services
async def get_db_session() -> AsyncSession:
    """FastAPI dependency that provides a SQLAlchemy AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit transaction if endpoint succeeds
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close() # Ensure session is closed

# Function to initialize the database (create tables)
async def init_db():
    """Initializes the database by creating tables defined by Base's metadata."""
    async with engine.begin() as conn:
        logger.info("Dropping and recreating database tables...") # Optional: for dev
        # await conn.run_sync(Base.metadata.drop_all) # Use with caution!
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if they didn't exist).")

