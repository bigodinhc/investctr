"""
Database configuration and session management.

Uses lazy initialization to allow the app to start even without DATABASE_URL.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Lazy engine initialization
_engine = None
_async_session_maker = None


def get_database_url() -> str:
    """Get database URL, converting to async format if needed."""
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please set the DATABASE_URL environment variable."
        )

    url = str(settings.database_url)
    # Convert postgresql:// to postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    # Note: SSL is configured via connect_args in get_engine()
    # Do not add ssl/sslmode to URL as it conflicts with asyncpg ssl context

    return url


def get_engine():
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        _engine = create_async_engine(
            get_database_url(),
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,  # Increased from 5 to handle more concurrent connections
            max_overflow=20,  # Increased from 10 for burst handling
            pool_recycle=1800,  # Recycle connections every 30 minutes
            connect_args={"ssl": ssl_context},
        )
    return _engine


def get_session_maker():
    """Get or create the session maker (lazy initialization)."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def async_session_factory():
    """
    Get async session factory for use in Celery tasks.

    Returns a context manager that provides an AsyncSession.

    Usage:
        async with async_session_factory() as session:
            # Use session
            pass
    """
    return get_session_maker()()


# Alias for backward compatibility with Celery tasks
# Usage: async with async_session_maker() as db:
async_session_maker = get_session_maker
