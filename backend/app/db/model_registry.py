"""Import all ORM models so Alembic sees complete metadata."""

from app.db.database import Base
from app.db import models as legacy_models  # noqa: F401

__all__ = ["Base"]

