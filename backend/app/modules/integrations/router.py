"""Authenticated API-Football status, selection, refresh, and run routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.config import Settings, get_settings
from app.db.database import get_db
from app.modules.identity.dependencies import require_roles
from app.modules.identity.service import Actor, ResourceNotFound
from app.modules.integrations.api_football import (
    ApiFootballClient,
    IntegrationDisabled,
    ProviderUnavailable,
)
from app.modules.integrations.models import ProviderQuotaDay, ProviderSyncRun
from app.modules.integrations.repository import ProviderRepository, QuotaReserved
from app.modules.integrations.schemas import (
    ClubCatalog,
    ClubSelectionCommand,
    IntegrationStatus,
    SelectedTeamView,
    SyncRunView,
)
from app.modules.integrations.service import ClubSyncService
from app.modules.organizations.models import Organization, Season, Team


router = APIRouter(prefix="/integrations/api-football", tags=["api-football"])
admin = require_roles("admin")
reader = require_roles("admin", "analyst", "coach", "viewer")


def _repository(db: Session, settings: Settings) -> ProviderRepository:
    return ProviderRepository(
        db,
        ApiFootballClient(settings),
        daily_ceiling=settings.api_football_daily_ceiling,
    )


def _selected_team(db: Session, organization: Organization) -> SelectedTeamView | None:
    if organization.primary_team_id is None:
        return None
    team = db.get(Team, organization.primary_team_id)
    if team is None:
        return None
    return SelectedTeamView(public_id=team.public_id, name=team.name, logo_url=team.logo_url or team.logo_source_url)


@router.get("/status", response_model=IntegrationStatus)
def integration_status(
    db: Session = Depends(get_db),
    actor: Actor = Depends(reader),
    settings: Settings = Depends(get_settings),
) -> IntegrationStatus:
    organization = db.get(Organization, actor.organization_id)
    if organization is None:
        raise ResourceNotFound("Resource not found")
    quota = db.scalar(
        select(ProviderQuotaDay)
        .where(ProviderQuotaDay.provider == "api_football")
        .order_by(ProviderQuotaDay.quota_date.desc())
    )
    last_run = db.scalar(
        select(ProviderSyncRun)
        .where(ProviderSyncRun.organization_id == actor.organization_id)
        .order_by(ProviderSyncRun.created_at.desc())
    )
    calls_used = quota.calls_used if quota else 0
    remaining = quota.remaining_reported if quota and quota.remaining_reported is not None else max(0, settings.api_football_daily_ceiling - calls_used)
    return IntegrationStatus(
        configured=settings.api_football_key is not None,
        calls_used=calls_used,
        remaining=remaining,
        selected_team=_selected_team(db, organization),
        last_run=SyncRunView.model_validate(last_run) if last_run else None,
    )


@router.get("/tunisia/clubs", response_model=ClubCatalog)
def tunisian_clubs(
    db: Session = Depends(get_db),
    _: Actor = Depends(reader),
    settings: Settings = Depends(get_settings),
) -> ClubCatalog:
    repository = _repository(db, settings)
    try:
        clubs = ClubSyncService(db, repository).list_tunisian_clubs()
        db.commit()
        return ClubCatalog(clubs=clubs)
    except IntegrationDisabled as exc:
        db.rollback()
        raise ProblemException(503, "integration_disabled", str(exc)) from exc
    except QuotaReserved as exc:
        db.rollback()
        raise ProblemException(429, "provider_quota_reserved", str(exc)) from exc
    except ProviderUnavailable as exc:
        db.rollback()
        raise ProblemException(503, "provider_unavailable", str(exc)) from exc
    finally:
        repository.client.close()


@router.post("/select-club", response_model=SyncRunView, status_code=status.HTTP_202_ACCEPTED)
def select_club(
    command: ClubSelectionCommand,
    db: Session = Depends(get_db),
    actor: Actor = Depends(admin),
    settings: Settings = Depends(get_settings),
) -> ProviderSyncRun:
    repository = _repository(db, settings)
    try:
        run = ClubSyncService(db, repository).queue_initial_sync(actor.organization_id, command)
        db.commit()
        db.refresh(run)
        return run
    finally:
        repository.client.close()


@router.post("/sync", response_model=SyncRunView, status_code=status.HTTP_202_ACCEPTED)
def refresh_selected_club(
    db: Session = Depends(get_db),
    actor: Actor = Depends(admin),
    settings: Settings = Depends(get_settings),
) -> ProviderSyncRun:
    organization = db.get(Organization, actor.organization_id)
    team = db.get(Team, organization.primary_team_id) if organization and organization.primary_team_id else None
    season = db.scalar(
        select(Season)
        .where(Season.organization_id == actor.organization_id, Season.provider == "api_football")
        .order_by(Season.season_year.desc())
    )
    if team is None or season is None or not team.provider_id or not season.competition_provider_id or not season.season_year:
        raise ProblemException(409, "club_not_selected", "Select a provider club before refreshing")
    command = ClubSelectionCommand(
        team_provider_id=team.provider_id,
        team_name=team.name,
        logo_url=team.logo_source_url,
        league_provider_id=season.competition_provider_id,
        league_name=season.name.rsplit(" ", 1)[0],
        season=season.season_year,
    )
    repository = _repository(db, settings)
    try:
        run = ClubSyncService(db, repository).queue_initial_sync(actor.organization_id, command)
        db.commit()
        db.refresh(run)
        return run
    finally:
        repository.client.close()


@router.get("/sync-runs/{run_id}", response_model=SyncRunView)
def sync_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(reader),
) -> ProviderSyncRun:
    run = db.scalar(
        select(ProviderSyncRun).where(
            ProviderSyncRun.public_id == run_id,
            ProviderSyncRun.organization_id == actor.organization_id,
        )
    )
    if run is None:
        raise ResourceNotFound("Resource not found")
    return run
