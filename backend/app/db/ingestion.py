"""High-throughput persistence for vision tracking coordinates."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
from time import perf_counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import TrackingPoint


@dataclass(frozen=True)
class TrackingIngestionResult:
    """Summary returned after one atomic bulk transaction."""

    points_ingested: int
    total_points: int
    duration_ms: float


def _number(point: Mapping[str, Any], *keys: str) -> float:
    for key in keys:
        if key in point and point[key] is not None:
            value = float(point[key])
            if math.isfinite(value):
                return value
            break
    raise ValueError(f"Missing or invalid tracking value: {'/'.join(keys)}")


def _prepare_rows(match_id: int, tracking_data: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for point in tracking_data:
        player_id = int(point["player_id"])
        timestamp = _number(point, "timestamp_seconds", "timestamp")
        x_coord = _number(point, "x_coord", "x")
        y_coord = _number(point, "y_coord", "y")
        if timestamp < 0 or not 0 <= x_coord <= 105 or not 0 <= y_coord <= 68:
            raise ValueError("Tracking coordinates must fit the 105 x 68 metre pitch")
        speed = point.get("speed_kmh")
        rows.append(
            {
                "match_id": int(match_id),
                "player_id": player_id,
                "timestamp_seconds": round(timestamp, 3),
                "x_coord": round(x_coord, 3),
                "y_coord": round(y_coord, 3),
                "speed_kmh": None if speed is None else max(0.0, round(float(speed), 3)),
            }
        )

    by_player: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_player[row["player_id"]].append(row)
    for points in by_player.values():
        points.sort(key=lambda item: item["timestamp_seconds"])
        previous: dict[str, Any] | None = None
        for point in points:
            if point["speed_kmh"] is None:
                speed_kmh = 0.0
                if previous is not None:
                    elapsed = point["timestamp_seconds"] - previous["timestamp_seconds"]
                    if elapsed > 0:
                        distance = math.hypot(
                            point["x_coord"] - previous["x_coord"],
                            point["y_coord"] - previous["y_coord"],
                        )
                        speed_kmh = distance / elapsed * 3.6
                point["speed_kmh"] = round(speed_kmh, 3)
            previous = point
    return rows


def bulk_insert_tracking(
    match_id: int,
    tracking_data: Iterable[Mapping[str, Any]],
    *,
    db: Session | None = None,
    batch_size: int = 5000,
) -> TrackingIngestionResult:
    """Upsert thousands of points using batched executemany in one transaction."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    rows = _prepare_rows(match_id, tracking_data)
    if not rows:
        raise ValueError("At least one tracking point is required")

    started = perf_counter()
    owns_session = db is None
    session = db or SessionLocal()
    statement = sqlite_insert(TrackingPoint).on_conflict_do_update(
        index_elements=["match_id", "player_id", "timestamp_seconds"],
        set_={
            "x_coord": sqlite_insert(TrackingPoint).excluded.x_coord,
            "y_coord": sqlite_insert(TrackingPoint).excluded.y_coord,
            "speed_kmh": sqlite_insert(TrackingPoint).excluded.speed_kmh,
        },
    )
    try:
        for offset in range(0, len(rows), batch_size):
            session.execute(statement, rows[offset : offset + batch_size])
        session.commit()
        total_points = int(
            session.scalar(
                select(func.count(TrackingPoint.id)).where(TrackingPoint.match_id == match_id)
            )
            or 0
        )
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()

    return TrackingIngestionResult(
        points_ingested=len(rows),
        total_points=total_points,
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )
