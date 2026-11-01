"""Persistent provider cache, quota, lease, sync, and standings records."""

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def uuid_string() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderCacheEntry(Base):
    __tablename__ = "provider_cache_entries"
    __table_args__ = (
        UniqueConstraint("provider", "cache_key", name="uq_provider_cache_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    cache_key: Mapped[str] = mapped_column(String(64))
    endpoint: Mapped[str] = mapped_column(String(160))
    parameters_json: Mapped[dict] = mapped_column(JSON)
    response_json: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProviderQuotaDay(Base):
    __tablename__ = "provider_quota_days"
    __table_args__ = (UniqueConstraint("provider", "quota_date", name="uq_provider_quota_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    quota_date: Mapped[date] = mapped_column(Date)
    calls_used: Mapped[int] = mapped_column(Integer, default=0)
    remaining_reported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProviderSyncLease(Base):
    __tablename__ = "provider_sync_leases"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_provider_sync_lease"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    owner_token: Mapped[str] = mapped_column(String(64))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProviderSyncRun(Base):
    __tablename__ = "provider_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=uuid_string)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    remaining_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stages: Mapped[list["ProviderSyncStage"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ProviderSyncStage.id",
    )


class ProviderSyncStage(Base):
    __tablename__ = "provider_sync_stages"
    __table_args__ = (
        UniqueConstraint("sync_run_id", "name", name="uq_provider_sync_stage"),
        CheckConstraint(
            "status IN ('pending','running','completed','skipped','failed')",
            name="ck_provider_sync_stage_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("provider_sync_runs.id"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run: Mapped["ProviderSyncRun"] = relationship(back_populates="stages")


class ProviderRequestLease(Base):
    __tablename__ = "provider_request_leases"
    __table_args__ = (
        UniqueConstraint("provider", "scope_key", name="uq_provider_request_lease"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40))
    scope_key: Mapped[str] = mapped_column(String(160))
    owner_token: Mapped[str] = mapped_column(String(64))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProviderStandingSnapshot(Base):
    __tablename__ = "provider_standing_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "team_id", "season_id", "provider", name="uq_provider_standing"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
