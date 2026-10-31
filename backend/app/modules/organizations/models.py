"""Organization, season, and team persistence models."""

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def uuid_string() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(160), index=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    default_locale: Mapped[str] = mapped_column(String(10), default="fr")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    primary_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_season_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    competition_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    season_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Team(Base):
    """A club team; legacy fields remain available during the transition."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_teams_org_name"),
        UniqueConstraint(
            "organization_id", "provider", "provider_id", name="uq_teams_org_provider_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source: Mapped[str] = mapped_column(String(24), default="manual")
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    logo_source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    players: Mapped[list["Player"]] = relationship(back_populates="team")


class TeamSeason(Base):
    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint("team_id", "season_id", name="uq_team_season"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

