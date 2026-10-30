"""Integration tests for high-throughput tracking persistence."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.api import routes
from app.api.schemas import TrackingIngestRequest
from app.db.database import SessionLocal, init_db
from app.db.ingestion import bulk_insert_tracking
from app.db.models import Match, Player, Team, TrackingPoint


def test_bulk_insert_2450_points_is_fast_and_idempotent() -> None:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as session:
        home = Team(name=f"Bulk Home {suffix}")
        away = Team(name=f"Bulk Away {suffix}")
        session.add_all([home, away])
        session.flush()
        player = Player(
            team_id=home.id,
            name="Tracked Player",
            jersey_number=10,
            position="midfielder",
            preferred_foot="right",
        )
        session.add(player)
        session.flush()
        match = Match(
            home_team_id=home.id,
            away_team_id=away.id,
            match_date=datetime.now(timezone.utc),
            home_score=0,
            away_score=0,
            competition="Bulk Test",
        )
        session.add(match)
        session.commit()

        points = [
            {
                "player_id": player.id,
                "timestamp": index * 0.04,
                "x": (index % 1050) / 10,
                "y": (index % 680) / 10,
            }
            for index in range(2450)
        ]
        first = bulk_insert_tracking(match.id, points, db=session)
        assert first.points_ingested == 2450
        assert first.total_points == 2450
        assert first.duration_ms < 1000

        second = bulk_insert_tracking(match.id, points, db=session)
        assert second.total_points == 2450
        sample = session.scalar(
            select(TrackingPoint)
            .where(TrackingPoint.match_id == match.id)
            .order_by(TrackingPoint.timestamp_seconds.desc())
        )
        assert sample is not None
        assert sample.speed_kmh >= 0


def test_completed_vision_job_is_ingested_with_player_mapping(monkeypatch) -> None:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as session:
        home = Team(name=f"Vision Home {suffix}")
        away = Team(name=f"Vision Away {suffix}")
        session.add_all([home, away])
        session.flush()
        player = Player(
            team_id=home.id,
            name="Mapped Player",
            jersey_number=7,
            position="winger",
            preferred_foot="left",
        )
        session.add(player)
        session.flush()
        match = Match(
            home_team_id=home.id,
            away_team_id=away.id,
            match_date=datetime.now(timezone.utc),
            home_score=0,
            away_score=0,
            competition="Vision Ingestion Test",
        )
        session.add(match)
        session.commit()

        monkeypatch.setattr(
            routes,
            "read_tracking_job",
            lambda _: {
                "status": "completed",
                "result": {
                    "trajectories": [
                        {"player_id": 91, "frame": 1, "timestamp": 0.04, "x": 10, "y": 20},
                        {"player_id": 91, "frame": 2, "timestamp": 0.08, "x": 10.2, "y": 20.1},
                    ]
                },
            },
        )
        payload = TrackingIngestRequest.model_validate(
            {"job_id": "vision-job", "player_mapping": {"91": player.id}}
        )
        response = routes.ingest_match_tracking(match.id, payload, session)

        assert response.status == "completed"
        assert response.points_ingested == 2
        assert response.total_points == 2
        assert response.progress == 100
        status = routes.get_tracking_ingestion_status(match.id, session)
        assert status.total_points == 2
