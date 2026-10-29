"""Integration tests for SQLite, routes, metrics, and generated graphics."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4


TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"statx_test_{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from sqlalchemy import inspect  # noqa: E402

from app.api.routes import (  # noqa: E402
    EXPORT_ROOT,
    create_events,
    create_match,
    create_player,
    create_team,
    get_match_analytics,
)
from app.api.schemas import EventCreate, MatchCreate, PlayerCreate, TeamCreate  # noqa: E402
from app.db.database import SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


def test_tables_and_api_routes_are_registered() -> None:
    """The startup initializer creates every table and all public routes exist."""
    init_db()

    expected_tables = {"teams", "players", "matches", "events"}
    assert expected_tables.issubset(inspect(engine).get_table_names())
    assert TEST_DATABASE_PATH.exists()

    expected_routes = {
        "/health",
        "/api/teams",
        "/api/players",
        "/api/matches",
        "/api/matches/{match_id}/events",
        "/api/matches/{match_id}/analytics",
    }
    registered_routes = {route.path for route in app.routes}
    assert expected_routes.issubset(registered_routes)


def test_complete_match_analytics_workflow() -> None:
    """Persist a match and validate metrics plus the three PNG outputs."""
    init_db()
    with SessionLocal() as session:
        home = create_team(TeamCreate(name="StatX Home"), session)
        away = create_team(TeamCreate(name="StatX Away"), session)

        home_player = create_player(
            PlayerCreate(
                team_id=home.id,
                name="Home Striker",
                jersey_number=9,
                position="forward",
                preferred_foot="right",
            ),
            session,
        )
        away_player = create_player(
            PlayerCreate(
                team_id=away.id,
                name="Away Midfielder",
                jersey_number=8,
                position="midfielder",
                preferred_foot="left",
            ),
            session,
        )
        match = create_match(
            MatchCreate.model_validate(
                {
                    "home_team_id": home.id,
                    "away_team_id": away.id,
                    "match_date": "2026-10-29T18:00:00Z",
                    "home_score": 1,
                    "away_score": 0,
                    "competition": "StatX Test League",
                }
            ),
            session,
        )

        event_payload = [
            {"player_id": home_player.id, "minute": 12, "type": "shot", "x_start": 108, "y_start": 40, "outcome": "goal", "xg_value": 0.55},
            {"player_id": home_player.id, "minute": 25, "type": "shot", "x_start": 99, "y_start": 32, "outcome": "off_target", "xg_value": 0.15},
            {"player_id": away_player.id, "minute": 31, "type": "shot", "x_start": 103, "y_start": 51, "outcome": "saved", "xg_value": 0.30},
            {"player_id": home_player.id, "minute": 40, "type": "pass", "x_start": 30, "y_start": 20, "x_end": 52, "y_end": 35, "outcome": "complete"},
            {"player_id": home_player.id, "minute": 41, "type": "pass", "x_start": 52, "y_start": 35, "x_end": 78, "y_end": 48, "outcome": "complete"},
            {"player_id": away_player.id, "minute": 55, "type": "pass", "x_start": 60, "y_start": 65, "x_end": 43, "y_end": 52, "outcome": "incomplete"},
            {"player_id": home_player.id, "minute": 62, "type": "recovery", "x_start": 71, "y_start": 25, "outcome": "successful"},
        ]
        records = create_events(
            match.id,
            [EventCreate.model_validate(event) for event in event_payload],
            session,
        )
        assert len(records) == len(event_payload)

        analytics = get_match_analytics(match.id, None, session)
        assert analytics.home.total_xg == 0.7
        assert analytics.away.total_xg == 0.3
        assert analytics.home.shots_on_target == 1
        assert analytics.away.shots_on_target == 1
        assert analytics.home.possession == 66.7
        assert analytics.away.possession == 33.3

        for public_path in analytics.graphics.values():
            image_path = EXPORT_ROOT / public_path.removeprefix("/exports/")
            assert image_path.is_file()
            assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

