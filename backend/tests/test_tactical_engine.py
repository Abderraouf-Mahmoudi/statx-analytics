"""Tests for automated spatial alerts and physical player telemetry."""

from datetime import datetime, timezone
from uuid import uuid4

from app.core.tactical_engine import analyze_match_tactics
from app.db.database import SessionLocal, init_db
from app.db.ingestion import bulk_insert_tracking
from app.db.models import Match, Player, Team


def test_tactical_engine_detects_right_flank_overload_and_player_metrics() -> None:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as session:
        home = Team(name=f"Tactical Home {suffix}")
        away = Team(name=f"Tactical Away {suffix}")
        session.add_all([home, away])
        session.flush()
        home_player = Player(
            team_id=home.id,
            name="Home Defender",
            jersey_number=4,
            position="defender",
            preferred_foot="right",
        )
        away_player = Player(
            team_id=away.id,
            name="Away Winger",
            jersey_number=11,
            position="winger",
            preferred_foot="left",
        )
        session.add_all([home_player, away_player])
        session.flush()
        match = Match(
            home_team_id=home.id,
            away_team_id=away.id,
            match_date=datetime.now(timezone.utc),
            home_score=0,
            away_score=0,
            competition="Tactical Engine Test",
        )
        session.add(match)
        session.commit()

        away_x = [10, 50, 55, 72, 75, 78, 81, 84, 87, 90]
        points = [
            {
                "player_id": away_player.id,
                "timestamp": index + 1,
                "x": x_coord,
                "y": 20 + index,
            }
            for index, x_coord in enumerate(away_x)
        ] + [
            {"player_id": home_player.id, "timestamp": 1, "x": 25, "y": 30},
            {"player_id": home_player.id, "timestamp": 2, "x": 26, "y": 31},
        ]
        bulk_insert_tracking(match.id, points, db=session)

        analysis = analyze_match_tactics(match.id, home.id, db=session)
        assert analysis.total_opponent_points == 10
        assert analysis.lane_distribution.left == 10.0
        assert analysis.lane_distribution.center == 20.0
        assert analysis.lane_distribution.right == 70.0
        assert analysis.alerts == (
            "⚠️ Faiblesse Critique : 70% des pénétrations ciblent votre Flanc Droit",
        )
        winger = next(
            metric
            for metric in analysis.player_telemetry
            if metric.player_id == away_player.id
        )
        assert winger.distance_km > 0
        assert winger.max_speed_kmh > 0
        assert winger.samples == 10
