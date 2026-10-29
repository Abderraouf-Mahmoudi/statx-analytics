"""Relational models used by the StatX Analytics data engine."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Team(Base):
    """A football team."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    players: Mapped[list["Player"]] = relationship(back_populates="team")


class Player(Base):
    """A registered player belonging to one team."""

    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint("jersey_number >= 0 AND jersey_number <= 99", name="ck_player_jersey"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    jersey_number: Mapped[int] = mapped_column(Integer)
    position: Mapped[str] = mapped_column(String(50))
    preferred_foot: Mapped[str | None] = mapped_column(String(20), nullable=True)

    team: Mapped[Team] = relationship(back_populates="players")
    events: Mapped[list["Event"]] = relationship(back_populates="player")


class Match(Base):
    """A match between a home team and an away team."""

    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id != away_team_id", name="ck_match_distinct_teams"),
        CheckConstraint("home_score >= 0 AND away_score >= 0", name="ck_match_scores"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    competition: Mapped[str] = mapped_column(String(120))

    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    events: Mapped[list["Event"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
    )


class Event(Base):
    """A geolocated match action on a StatsBomb-sized pitch."""

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
    player: Mapped[Player] = relationship(back_populates="events")

