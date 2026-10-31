"""Organization-scoped season and team endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.db.database import get_db
from app.modules.identity.dependencies import require_roles
from app.modules.identity.service import Actor
from app.modules.organizations.schemas import SeasonCommand, SeasonView, TeamCommand, TeamView
from app.modules.organizations.service import (
    OrganizationConflict,
    create_season,
    create_team,
    list_seasons,
    list_teams,
)


router = APIRouter(tags=["organization"])


@router.get("/seasons", response_model=list[SeasonView])
def seasons(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin", "analyst", "coach", "viewer"))):
    return list_seasons(db, actor.organization_id)


@router.post("/seasons", response_model=SeasonView, status_code=201)
def add_season(command: SeasonCommand, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    try:
        entity = create_season(db, actor.organization_id, command)
        db.commit()
        db.refresh(entity)
        return entity
    except OrganizationConflict as exc:
        db.rollback()
        raise ProblemException(409, "organization_conflict", str(exc)) from exc


@router.get("/teams", response_model=list[TeamView])
def teams(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin", "analyst", "coach", "viewer"))):
    return list_teams(db, actor.organization_id)


@router.post("/teams", response_model=TeamView, status_code=201)
def add_team(command: TeamCommand, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    try:
        entity = create_team(db, actor.organization_id, command)
        db.commit()
        db.refresh(entity)
        return entity
    except OrganizationConflict as exc:
        db.rollback()
        raise ProblemException(409, "organization_conflict", str(exc)) from exc

