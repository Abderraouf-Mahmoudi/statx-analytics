"""Account, club-import, and enriched-player migration acceptance tests."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def upgrade_to(path: Path, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_upgrade_adds_job_title_profile_overrides_snapshots_and_sync_stages(
    tmp_path: Path,
) -> None:
    database = tmp_path / "fresh-enrichment.db"

    upgrade_to(database, "head")

    with sqlite3.connect(database) as connection:
        assert "job_title" in columns(connection, "users")
        assert {
            "display_name",
            "birth_place",
            "birth_country",
            "primary_position",
            "secondary_positions",
            "player_field_overrides",
        } <= columns(connection, "players")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "player_season_snapshots",
            "provider_sync_stages",
            "provider_request_leases",
        } <= tables


def test_upgrade_preserves_existing_admin_and_manual_players(tmp_path: Path) -> None:
    database = tmp_path / "existing-enrichment.db"
    upgrade_to(database, "20261031_02")
    organization_public_id = str(uuid4())
    user_public_id = str(uuid4())
    team_public_id = str(uuid4())
    player_public_id = str(uuid4())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO organizations "
            "(public_id,name,default_locale,timezone,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (organization_public_id, "Legacy Club", "fr", "Africa/Tunis", "2026-01-01", "2026-01-01"),
        )
        organization_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO users "
            "(public_id,email,display_name,password_hash,active,default_locale,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (user_public_id, "owner@example.test", "Owner", "hash", 1, "fr", "2026-01-01", "2026-01-01"),
        )
        user_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO memberships "
            "(public_id,user_id,organization_id,role,active,created_at) VALUES (?,?,?,?,?,?)",
            (str(uuid4()), user_id, organization_id, "admin", 1, "2026-01-01"),
        )
        connection.execute(
            "INSERT INTO teams "
            "(public_id,organization_id,name,source,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (team_public_id, organization_id, "Legacy XI", "manual", "2026-01-01", "2026-01-01"),
        )
        team_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO players "
            "(public_id,organization_id,first_name,last_name,team_id,name,position,source,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                player_public_id,
                organization_id,
                "Amina",
                "Ben Salah",
                team_id,
                "Amina Ben Salah",
                "CM",
                "manual",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        connection.commit()

    upgrade_to(database, "head")

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        user = connection.execute(
            "SELECT public_id,job_title FROM users WHERE email='owner@example.test'"
        ).fetchone()
        player = connection.execute(
            "SELECT public_id,display_name,primary_position,secondary_positions,player_field_overrides "
            "FROM players WHERE public_id=?",
            (player_public_id,),
        ).fetchone()
        assert dict(user) == {"public_id": user_public_id, "job_title": "other"}
        assert player["public_id"] == player_public_id
        assert player["display_name"] == "Amina Ben Salah"
        assert player["primary_position"] == "CM"
        assert json.loads(player["secondary_positions"]) == []
        assert json.loads(player["player_field_overrides"]) == {}

