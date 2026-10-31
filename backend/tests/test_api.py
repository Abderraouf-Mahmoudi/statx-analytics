"""Integration tests for SQLite, routes, metrics, and generated graphics."""

import os
from pathlib import Path


TEST_DATABASE_PATH = Path(os.environ["STATX_TEST_DATABASE_PATH"])

from sqlalchemy import inspect  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from app.api.routes import (  # noqa: E402
    create_events,
    create_match,
    create_player,
    create_team,
    download_match_report,
    get_match_analytics,
    list_matches,
    list_teams,
)
from app.api.schemas import EventCreate, MatchCreate, PlayerCreate, TeamCreate  # noqa: E402
from app.db.database import SessionLocal, engine, init_db  # noqa: E402
from app.db.ingestion import bulk_insert_tracking  # noqa: E402
from app.main import app  # noqa: E402


def test_tables_and_api_routes_are_registered() -> None:
    """The startup initializer creates every table and all public routes exist."""
    init_db()

    expected_tables = {"teams", "players", "matches", "events", "tracking_points"}
    assert expected_tables.issubset(inspect(engine).get_table_names())
    assert TEST_DATABASE_PATH.exists()

    expected_routes = {
        "/health",
        "/api/teams",
        "/api/players",
        "/api/matches",
        "/api/matches/{match_id}/events",
        "/api/matches/{match_id}/analytics",
        "/api/matches/{match_id}/pdf",
        "/api/matches/{match_id}/ingest-tracking",
        "/api/matches/{match_id}/tracking-status",
        "/api/matches/{match_id}/tactical-insights",
        "/api/video/upload",
        "/api/video/trim",
        "/api/video/stream/{clip_id}",
        "/api/video/track/{clip_id}",
        "/api/video/track/jobs/{job_id}",
    }
    registered_routes = {route.path for route in app.routes}
    assert expected_routes.issubset(registered_routes)

    cors = next(middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware")
    assert "http://localhost:5173" in cors.kwargs["allow_origins"]
    assert "Content-Disposition" in cors.kwargs["expose_headers"]


def test_complete_match_analytics_workflow(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Persist a match and validate metrics plus the three PNG outputs."""
    output_root = tmp_path / "exports"
    monkeypatch.setattr("app.api.routes.EXPORT_ROOT", output_root)
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
        assert {team.id for team in list_teams(session)} == {home.id, away.id}
        assert match.id in {listed_match.id for listed_match in list_matches(session)}

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
        assert analytics.key_player == "Home Striker"
        assert len(analytics.tactical_insights) == 3

        for public_path in analytics.graphics.values():
            image_path = output_root / public_path.removeprefix("/exports/")
            assert image_path.is_file()
            assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_generate_pdf_report(monkeypatch, tmp_path: Path) -> None:
    """The PDF endpoint returns a valid, non-empty one-page PDF response."""
    monkeypatch.setattr("app.api.routes.EXPORT_ROOT", tmp_path / "exports")
    init_db()
    with SessionLocal() as session:
        home = create_team(TeamCreate(name="PDF Home"), session)
        away = create_team(TeamCreate(name="PDF Away"), session)
        tracked_player = create_player(
            PlayerCreate(
                team_id=away.id,
                name="PDF Away Runner",
                jersey_number=11,
                position="winger",
                preferred_foot="left",
            ),
            session,
        )
        match = create_match(
            MatchCreate.model_validate(
                {
                    "home_team_id": home.id,
                    "away_team_id": away.id,
                    "match_date": "2026-10-29T20:00:00Z",
                    "home_score": 0,
                    "away_score": 0,
                    "competition": "StatX PDF Test",
                }
            ),
            session,
        )
        bulk_insert_tracking(
            match.id,
            [
                {
                    "player_id": tracked_player.id,
                    "timestamp": index + 1,
                    "x": x_coord,
                    "y": 20 + index,
                }
                for index, x_coord in enumerate([40, 50, 60, 72, 76, 80, 84, 88, 92, 96])
            ],
            db=session,
        )
        response = download_match_report(match.id, session)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        pdf_path = Path(response.path)
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 1_000
        assert pdf_path.read_bytes().startswith(b"%PDF-")
        reader = PdfReader(pdf_path)
        assert len(reader.pages) == 1
        text = reader.pages[0].extract_text() or ""
        assert "StatX Analytics" in text
        assert "FLANC DROIT" in text
        assert "TELEMETRIE JOUEUR" in text
        assert "ALERTE - Faiblesse Critique" in text
        assert "PDF Away Runner" in text

