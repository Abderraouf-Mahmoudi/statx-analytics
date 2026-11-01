"""Configuration and SQLite behavior at the application boundary."""

from pathlib import Path

from pydantic import SecretStr
from sqlalchemy import text

from app.config import Settings
from app.db.database import create_engine_from_settings
from app.main import create_app


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'statx-test.db').as_posix()}",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        _env_file=None,
    )


def test_sqlite_engine_enforces_integrity_and_concurrency_pragmas(tmp_path: Path) -> None:
    """A wrong engine factory would silently lose FK, WAL, or lock handling."""
    engine = create_engine_from_settings(make_settings(tmp_path))

    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
            assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5_000
    finally:
        engine.dispose()


def test_create_app_uses_supplied_database_instead_of_developer_default(
    tmp_path: Path,
) -> None:
    """Dependency injection must retain the caller-supplied database settings."""
    settings = make_settings(tmp_path)
    app = create_app(settings)
    health_route = next(route for route in app.routes if route.path == "/health")
    health_call = health_route.endpoint()
    try:
        health_call.send(None)
    except StopIteration as completed:
        health_payload = completed.value
    else:  # pragma: no cover - health endpoint must remain immediate
        raise AssertionError("Health endpoint unexpectedly yielded async work")
    finally:
        health_call.close()

    assert health_payload["status"] == "ok"

    assert app.state.settings is settings
    assert app.state.settings.database_url.endswith("statx-test.db")


def test_provider_and_media_settings_keep_credentials_secret(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'settings.db').as_posix()}",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        api_football_key="development-provider-secret",
        _env_file=None,
    )

    assert isinstance(settings.api_football_key, SecretStr)
    assert str(settings.api_football_key) == "**********"
    assert settings.api_football_daily_ceiling == 90
    assert settings.api_football_free_plan_fallback_season == 2024
    assert settings.max_player_photo_bytes == 10 * 1024 * 1024
    assert "development-provider-secret" not in repr(settings)

