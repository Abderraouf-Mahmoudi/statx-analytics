"""Provider and player-media migration acceptance tests."""

from pathlib import Path
import sqlite3
from uuid import uuid4

from tests.factories import create_legacy_database
from tests.migrations.test_foundation_migration import table_names, upgrade_database


EXPECTED_TABLES = {
    "provider_cache_entries",
    "provider_quota_days",
    "provider_sync_leases",
    "provider_sync_runs",
    "provider_standing_snapshots",
    "player_photos",
}


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def assert_provider_schema(connection: sqlite3.Connection) -> None:
    assert EXPECTED_TABLES <= table_names(connection)
    assert {"primary_team_id"} <= columns(connection, "organizations")
    assert {"source", "provider", "provider_id", "provider_updated_at"} <= columns(
        connection, "teams"
    )
    assert {"provider", "competition_provider_id", "season_year"} <= columns(
        connection, "seasons"
    )
    assert {
        "source",
        "provider",
        "provider_id",
        "provider_updated_at",
        "nationality",
        "height_cm",
        "weight_kg",
        "provider_photo_url",
        "local_override",
        "provider_absent",
    } <= columns(connection, "players")
    assert {"provider", "provider_id", "provider_updated_at"} <= columns(
        connection, "matches"
    )


def test_upgrade_empty_database_creates_provider_and_media_schema(tmp_path: Path) -> None:
    database = tmp_path / "fresh-provider.db"
    upgrade_database(database)
    with sqlite3.connect(database) as connection:
        assert_provider_schema(connection)


def test_upgrade_preserves_release_one_rows(tmp_path: Path) -> None:
    database = tmp_path / "legacy-provider.db"
    create_legacy_database(database)
    upgrade_database(database)
    with sqlite3.connect(database) as connection:
        assert_provider_schema(connection)
        assert connection.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 1
        assert connection.execute("SELECT id, source FROM teams WHERE id=11").fetchone() == (
            11,
            "manual",
        )
        assert connection.execute("SELECT id, source FROM players WHERE id=21").fetchone() == (
            21,
            "manual",
        )


def test_team_names_are_unique_per_organization_not_globally(tmp_path: Path) -> None:
    database = tmp_path / "organization-team-names.db"
    upgrade_database(database)
    with sqlite3.connect(database) as connection:
        for name in ("First", "Second"):
            connection.execute(
                "INSERT INTO organizations (public_id,name,default_locale,timezone,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (str(uuid4()), name, "fr", "Africa/Tunis", "2026-11-01", "2026-11-01"),
            )
        organizations = [row[0] for row in connection.execute("SELECT id FROM organizations ORDER BY id")]
        for organization_id in organizations:
            connection.execute(
                "INSERT INTO teams (public_id,organization_id,name,source,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (str(uuid4()), organization_id, "Espérance ST", "manual", "2026-11-01", "2026-11-01"),
            )
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM teams WHERE name='Espérance ST'").fetchone()[0] == 2

