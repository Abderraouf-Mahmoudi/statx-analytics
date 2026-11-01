"""Application settings shared by API, database, and migrations."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_key: SecretStr | None = None
    api_football_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    api_football_read_timeout_seconds: float = Field(default=20.0, gt=0)
    api_football_daily_ceiling: int = Field(default=90, ge=1, le=100)
    api_football_cache_days: int = Field(default=7, ge=1)
    api_football_fixture_cache_minutes: int = Field(default=30, ge=1)
    api_football_free_plan_fallback_season: int = Field(default=2024, ge=2000, le=2200)
    api_football_media_hosts: list[str] = Field(
        default_factory=lambda: ["media.api-sports.io"]
    )
    max_player_photo_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    max_player_photo_pixels: int = Field(default=24_000_000, ge=1)
    player_photo_model: str = "u2net_human_seg"
    provider_worker_poll_seconds: float = Field(default=2.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("api_football_media_hosts", mode="before")
    @classmethod
    def split_media_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [host.strip().lower() for host in value.split(",") if host.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings object."""
    return Settings()

