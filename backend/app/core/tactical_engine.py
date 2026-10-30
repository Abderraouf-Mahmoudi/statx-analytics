"""Automated spatial and physical insights from persisted tracking points."""

from collections import defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Match, Player, Team, TrackingPoint


@dataclass(frozen=True)
class LaneDistribution:
    left: float
    center: float
    right: float


@dataclass(frozen=True)
class PlayerTelemetry:
    player_id: int
    player_name: str
    team_id: int
    distance_km: float
    max_speed_kmh: float
    samples: int


@dataclass(frozen=True)
class TacticalAnalysis:
    match_id: int
    perspective_team_id: int
    perspective_team_name: str
    opponent_team_id: int
    opponent_team_name: str
    total_opponent_points: int
    lane_distribution: LaneDistribution
    alerts: tuple[str, ...]
    player_telemetry: tuple[PlayerTelemetry, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lane_distribution(points: list[TrackingPoint]) -> LaneDistribution:
    total = len(points)
    if not total:
        return LaneDistribution(left=0.0, center=0.0, right=0.0)
    left = sum(point.x_coord < 35 for point in points)
    center = sum(35 <= point.x_coord <= 70 for point in points)
    right = total - left - center
    return LaneDistribution(
        left=round(left / total * 100, 1),
        center=round(center / total * 100, 1),
        right=round(right / total * 100, 1),
    )


def _alerts(distribution: LaneDistribution) -> tuple[str, ...]:
    alerts: list[str] = []
    for label, share in (
        ("Flanc Gauche", distribution.left),
        ("Flanc Droit", distribution.right),
    ):
        if share > 60:
            alerts.append(
                f"⚠️ Faiblesse Critique : {share:.0f}% des pénétrations ciblent votre {label}"
            )
    return tuple(alerts)


def _player_telemetry(
    points: list[TrackingPoint],
    players: dict[int, Player],
) -> tuple[PlayerTelemetry, ...]:
    by_player: dict[int, list[TrackingPoint]] = defaultdict(list)
    for point in points:
        by_player[point.player_id].append(point)

    metrics: list[PlayerTelemetry] = []
    for player_id, samples in by_player.items():
        samples.sort(key=lambda point: point.timestamp_seconds)
        distance_m = 0.0
        max_speed = max((point.speed_kmh for point in samples), default=0.0)
        for previous, current in zip(samples, samples[1:]):
            elapsed = current.timestamp_seconds - previous.timestamp_seconds
            distance = math.hypot(
                current.x_coord - previous.x_coord,
                current.y_coord - previous.y_coord,
            )
            distance_m += distance
            if elapsed > 0:
                max_speed = max(max_speed, distance / elapsed * 3.6)
        player = players[player_id]
        metrics.append(
            PlayerTelemetry(
                player_id=player_id,
                player_name=player.name,
                team_id=player.team_id,
                distance_km=round(distance_m / 1000, 3),
                max_speed_kmh=round(max_speed, 1),
                samples=len(samples),
            )
        )
    return tuple(sorted(metrics, key=lambda item: item.distance_km, reverse=True))


def analyze_match_tactics(
    match_id: int,
    perspective_team_id: int | None = None,
    *,
    db: Session | None = None,
) -> TacticalAnalysis:
    """Analyze opponent lane occupation and every player's physical telemetry."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        match = session.get(Match, match_id)
        if match is None:
            raise LookupError("Match not found")
        team_id = perspective_team_id or match.home_team_id
        if team_id not in {match.home_team_id, match.away_team_id}:
            raise ValueError("perspective_team_id must belong to the match")
        opponent_id = (
            match.away_team_id if team_id == match.home_team_id else match.home_team_id
        )
        teams = {
            team.id: team
            for team in session.scalars(
                select(Team).where(Team.id.in_({team_id, opponent_id}))
            )
        }
        points = list(
            session.scalars(
                select(TrackingPoint)
                .where(TrackingPoint.match_id == match_id)
                .order_by(TrackingPoint.player_id, TrackingPoint.timestamp_seconds)
            )
        )
        player_ids = {point.player_id for point in points}
        players = {
            player.id: player
            for player in session.scalars(select(Player).where(Player.id.in_(player_ids)))
        }
        opponent_points = [
            point for point in points if players[point.player_id].team_id == opponent_id
        ]
        distribution = _lane_distribution(opponent_points)
        return TacticalAnalysis(
            match_id=match_id,
            perspective_team_id=team_id,
            perspective_team_name=teams[team_id].name,
            opponent_team_id=opponent_id,
            opponent_team_name=teams[opponent_id].name,
            total_opponent_points=len(opponent_points),
            lane_distribution=distribution,
            alerts=_alerts(distribution),
            player_telemetry=_player_telemetry(points, players),
        )
    finally:
        if owns_session:
            session.close()
