"""Organization-scoped season and team services."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Season, Team


class OrganizationConflict(RuntimeError):
    pass


def create_season(session: Session, organization_id: int, command) -> Season:
    if session.scalar(select(Season).where(Season.organization_id == organization_id, Season.name == command.name)):
        raise OrganizationConflict("Season name already exists")
    season = Season(organization_id=organization_id, **command.model_dump())
    session.add(season)
    session.flush()
    return season


def create_team(session: Session, organization_id: int, command) -> Team:
    if session.scalar(select(Team).where(Team.organization_id == organization_id, Team.name == command.name)):
        raise OrganizationConflict("Team name already exists")
    team = Team(organization_id=organization_id, **command.model_dump())
    session.add(team)
    session.flush()
    return team


def list_seasons(session: Session, organization_id: int) -> list[Season]:
    return list(session.scalars(select(Season).where(Season.organization_id == organization_id).order_by(Season.name)))


def list_teams(session: Session, organization_id: int) -> list[Team]:
    return list(session.scalars(select(Team).where(Team.organization_id == organization_id).order_by(Team.name)))

