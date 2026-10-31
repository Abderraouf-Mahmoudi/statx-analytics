"""Restart-recoverable provider synchronization worker backed by SQLite leases."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.database import SessionLocal
from app.modules.integrations.api_football import ApiFootballClient
from app.modules.integrations.models import ProviderSyncLease, ProviderSyncRun
from app.modules.integrations.repository import ProviderRepository
from app.modules.integrations.service import ClubSyncService


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def claim_sync_run(
    session: Session,
    owner_token: str,
    *,
    now: datetime | None = None,
    lease_seconds: int = 300,
) -> ProviderSyncRun | None:
    moment = _utc(now or datetime.now(timezone.utc))
    stale_started = moment - timedelta(seconds=lease_seconds)
    candidates = list(
        session.scalars(
            select(ProviderSyncRun)
            .where(
                or_(
                    ProviderSyncRun.status == "queued",
                    (ProviderSyncRun.status == "processing")
                    & (ProviderSyncRun.started_at < stale_started),
                )
            )
            .order_by(ProviderSyncRun.created_at)
        )
    )
    for run in candidates:
        lease = session.scalar(
            select(ProviderSyncLease).where(
                ProviderSyncLease.organization_id == run.organization_id,
                ProviderSyncLease.provider == run.provider,
            )
        )
        if lease is not None and _utc(lease.expires_at) > moment:
            continue
        if lease is None:
            lease = ProviderSyncLease(
                organization_id=run.organization_id,
                provider=run.provider,
                owner_token=owner_token,
                acquired_at=moment,
                expires_at=moment + timedelta(seconds=lease_seconds),
            )
            session.add(lease)
        else:
            lease.owner_token = owner_token
            lease.acquired_at = moment
            lease.expires_at = moment + timedelta(seconds=lease_seconds)
        run.status = "processing"
        run.started_at = moment
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return None
        return run
    return None


def _release_lease(session: Session, run: ProviderSyncRun, owner_token: str) -> None:
    lease = session.scalar(
        select(ProviderSyncLease).where(
            ProviderSyncLease.organization_id == run.organization_id,
            ProviderSyncLease.provider == run.provider,
            ProviderSyncLease.owner_token == owner_token,
        )
    )
    if lease is not None:
        session.delete(lease)


def run_pending_syncs_once(
    settings: Settings,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    owner = uuid4().hex
    with session_factory() as session:
        run = claim_sync_run(session, owner)
        if run is None:
            session.rollback()
            return 0
        run_id = run.public_id
        session.commit()
    client = ApiFootballClient(settings)
    try:
        with session_factory() as session:
            repository = ProviderRepository(
                session, client, daily_ceiling=settings.api_football_daily_ceiling
            )
            try:
                run = session.scalar(
                    select(ProviderSyncRun).where(ProviderSyncRun.public_id == run_id)
                )
                ClubSyncService(session, repository).execute_run(run_id)
                _release_lease(session, run, owner)
                session.commit()
                return 1
            except Exception as exc:
                session.rollback()
                run = session.scalar(
                    select(ProviderSyncRun).where(ProviderSyncRun.public_id == run_id)
                )
                if run is not None:
                    run.status = "failed"
                    run.error_summary = type(exc).__name__
                    run.completed_at = datetime.now(timezone.utc)
                    _release_lease(session, run, owner)
                    session.commit()
                return 0
    finally:
        client.close()


async def provider_worker_loop(stop: asyncio.Event, settings: Settings) -> None:
    while not stop.is_set():
        await asyncio.to_thread(run_pending_syncs_once, settings)
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.provider_worker_poll_seconds)
        except TimeoutError:
            pass
