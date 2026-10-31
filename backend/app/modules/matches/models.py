"""Legacy-compatible match, event, and experimental tracking models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def uuid_string() -> str:
    return str(uuid4())


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id != away_team_id", name="ck_match_distinct_teams"),
        CheckConstraint("home_score >= 0 AND away_score >= 0", name="ck_match_scores"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    season_id: Mapped[int | None] = mapped_column(ForeignKey("seasons.id"), nullable=True, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    competition: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    events: Mapped[list["Event"]] = relationship(back_populates="match", cascade="all, delete-orphan")
    tracking_points: Mapped[list["TrackingPoint"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("minute >= 0 AND second >= 0 AND second <= 59", name="ck_event_time"),
        CheckConstraint("type IN ('shot', 'pass', 'recovery')", name="ck_event_type"),
        CheckConstraint("x_start >= 0 AND x_start <= 120", name="ck_event_x_start"),
        CheckConstraint("y_start >= 0 AND y_start <= 80", name="ck_event_y_start"),
        CheckConstraint("x_end IS NULL OR (x_end >= 0 AND x_end <= 120)", name="ck_event_x_end"),
        CheckConstraint("y_end IS NULL OR (y_end >= 0 AND y_end <= 80)", name="ck_event_y_end"),
        CheckConstraint("xg_value IS NULL OR (xg_value >= 0 AND xg_value <= 1)", name="ck_event_xg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    minute: Mapped[int] = mapped_column(Integer)
    second: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(20), index=True)
    x_start: Mapped[float] = mapped_column(Float)
    y_start: Mapped[float] = mapped_column(Float)
    x_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    xg_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    match: Mapped[Match] = relationship(back_populates="events")
    player: Mapped["Player"] = relationship(back_populates="events")


class TrackingPoint(Base):
    __tablename__ = "tracking_points"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", "timestamp_seconds", name="uq_tracking_match_player_timestamp"),
        CheckConstraint("timestamp_seconds >= 0", name="ck_tracking_timestamp"),
        CheckConstraint("x_coord >= 0 AND x_coord <= 105", name="ck_tracking_x"),
        CheckConstraint("y_coord >= 0 AND y_coord <= 68", name="ck_tracking_y"),
        CheckConstraint("speed_kmh >= 0", name="ck_tracking_speed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    timestamp_seconds: Mapped[float] = mapped_column(Float)
    x_coord: Mapped[float] = mapped_column(Float)
    y_coord: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)

    match: Mapped[Match] = relationship(back_populates="tracking_points")
    player: Mapped["Player"] = relationship(back_populates="tracking_points")

