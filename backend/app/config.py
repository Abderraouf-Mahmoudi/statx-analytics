"""Application settings shared by API, database, and migrations."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Validated runtime configuration with local-first defaults."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'statx.db').as_posix()}"
    session_secret: str = Field(default="dev-only-change-me-before-production", min_length=16)
    session_ttl_seconds: int = Field(default=28_800, gt=0)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    data_root: Path = PROJECT_ROOT / "data"
    default_locale: str = "fr"
    sqlite_busy_timeout_ms: int = Field(default=5_000, ge=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings object."""
    return Settings()

