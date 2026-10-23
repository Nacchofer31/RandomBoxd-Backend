"""Database configuration and session management."""


from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create async engine (lazy initialization to avoid connection errors in tests)
_engine = None
_async_session = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_async_session():
    """Get or create the async session factory."""
    global _async_session
    if _async_session is None:
        _async_session = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


async def get_db() -> AsyncSession | None:
    """Dependency for getting database sessions.

    Returns None gracefully if the database is unavailable, allowing
    the recommendation endpoint to work without enrichment.
    """
    try:
        async_session = get_async_session()
        session = async_session()
        return session
    except Exception:
        # DB unavailable — return None so enrichment is skipped gracefully
        return None
