"""Database engine and request-scoped session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class shared by all SQLAlchemy models."""


def create_engine_from_settings(settings: Settings) -> Engine:
    """Build an engine and enforce StatX SQLite integrity pragmas."""
    is_sqlite = settings.database_url.startswith("sqlite")
    configured_engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    if is_sqlite:

        @event.listens_for(configured_engine, "connect")
        def configure_sqlite(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            cursor.close()
    return configured_engine


engine = create_engine_from_settings(get_settings())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create registered tables for tests and local maintenance only.

    Production application startup deliberately does not call this helper;
    deployed schema changes are managed by Alembic migrations.
    """
    from app.db import models  # noqa: F401 - registers legacy model metadata

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a transactional database session for a FastAPI request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

