"""Legacy-safe foundation migration tests."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import UUID

from tests.factories import create_legacy_database


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def upgrade_database(path: Path) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def foreign_keys(connection: sqlite3.Connection, table: str) -> set[tuple[str, str]]:
    return {
        (row[3], row[2])
        for row in connection.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    }


def test_upgrade_preserves_legacy_rows_and_builds_imported_roster(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    create_legacy_database(database)

    upgrade_database(database)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        for table, expected_id, expected_count in (
            ("teams", 11, 2),
            ("players", 21, 1),
            ("matches", 31, 1),
            ("events", 41, 1),
            ("tracking_points", 51, 1),
        ):
            row = connection.execute(
                f"SELECT id FROM {table} WHERE id=?", (expected_id,)
            ).fetchone()
            assert row is not None and row["id"] == expected_id
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == expected_count

        organization = connection.execute("SELECT * FROM organizations").fetchone()
        season = connection.execute("SELECT * FROM seasons").fetchone()
        team = connection.execute("SELECT * FROM teams WHERE id=11").fetchone()
        player = connection.execute("SELECT * FROM players WHERE id=21").fetchone()
        match = connection.execute("SELECT * FROM matches WHERE id=31").fetchone()
        registration = connection.execute(
            "SELECT * FROM player_registrations WHERE player_id=21"
        ).fetchone()

        assert organization is not None and organization["name"] == "Imported organization"
        assert season is not None and season["name"] == "Imported season"
        for root in (organization, season, team, player, match, registration):
            UUID(root["public_id"])

        assert team["organization_id"] == organization["id"]
        assert player["organization_id"] == organization["id"]
        assert match["season_id"] == season["id"]
        assert ("organization_id", "organizations") in foreign_keys(connection, "teams")
        assert ("organization_id", "organizations") in foreign_keys(connection, "players")
        assert ("season_id", "seasons") in foreign_keys(connection, "matches")

        public_ids = [
            row[0]
            for table in ("teams", "players", "matches", "events")
            for row in connection.execute(f"SELECT public_id FROM {table}")
        ]
        assert all(UUID(value) for value in public_ids)
        assert len(public_ids) == len(set(public_ids))

        expected_registration = {
            "player_id": 21,
            "team_id": 11,
            "season_id": season["id"],
            "shirt_number": 8,
            "position": "midfielder",
            "preferred_foot": "left",
        }
        assert expected_registration.items() <= dict(registration).items()
    finally:
        connection.close()


def test_upgrade_empty_database_creates_complete_foundation_schema(tmp_path: Path) -> None:
    database = tmp_path / "fresh.db"

    upgrade_database(database)

    connection = sqlite3.connect(database)
    try:
        assert {
            "organizations",
            "users",
            "memberships",
            "seasons",
            "teams",
            "team_seasons",
            "players",
            "player_registrations",
            "consents",
            "system_state",
            "audit_logs",
            "matches",
            "events",
            "tracking_points",
        }.issubset(table_names(connection))
        assert connection.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0
    finally:
        connection.close()


def test_model_registry_and_audit_writer_share_the_caller_transaction(tmp_path: Path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.model_registry import Base
    from app.modules.organizations.models import Organization
    from app.modules.platform.audit import write_audit

    engine = create_engine(f"sqlite:///{(tmp_path / 'models.db').as_posix()}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Audit Club")
        session.add(organization)
        session.flush()
        record = write_audit(
            session,
            actor_id=None,
            organization_id=organization.id,
            action="organization.created",
            entity_type="organization",
            entity_public_id=organization.public_id,
            after={"name": organization.name},
        )
        assert record.id is not None
        session.rollback()

    with Session(engine) as session:
        assert session.query(Organization).count() == 0
