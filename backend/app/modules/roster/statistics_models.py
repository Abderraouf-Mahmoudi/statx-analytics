"""Versioned provider snapshots for one player's season performance."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlayerSeasonSnapshot(Base):
    __tablename__ = "player_season_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "player_id",
            "team_id",
            "season_id",
            "provider",
            name="uq_player_season_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    statistics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

