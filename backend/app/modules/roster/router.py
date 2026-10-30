"""Organization-scoped player, registration, roster, and consent endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.db.database import get_db
from app.modules.identity.dependencies import require_roles
from app.modules.identity.service import Actor
from app.modules.organizations.models import Season, Team
from app.modules.roster.schemas import (
    ConsentCommand,
    ConsentView,
    PlayerCommand,
    PlayerView,
    RegistrationCommand,
    RegistrationView,
    RosterItem,
)
from app.modules.roster.service import (
    ConsentRequired,
    RosterConflict,
    create_player,
    list_roster,
    record_consent,
    register_player,
    revoke_consent,
)


router = APIRouter(tags=["roster"])
editor = require_roles("admin", "analyst")


@router.post("/players", response_model=PlayerView, status_code=201)
def add_player(command: PlayerCommand, db: Session = Depends(get_db), actor: Actor = Depends(editor)):
    player = create_player(db, actor.organization_id, command)
    db.commit()
    db.refresh(player)
    return player


@router.post("/teams/{team_id}/registrations", response_model=RegistrationView, status_code=201)
def add_registration(team_id: str, command: RegistrationCommand, db: Session = Depends(get_db), actor: Actor = Depends(editor)):
    try:
        registration = register_player(db, actor.organization_id, team_id, command)
        team = db.get(Team, registration.team_id)
        season = db.get(Season, registration.season_id)
        player_public_id = command.player_id
        db.commit()
        return RegistrationView(
            public_id=registration.public_id,
            player_id=player_public_id,
            team_id=team.public_id,
            season_id=season.public_id,
            shirt_number=registration.shirt_number,
            position=registration.position,
            status=registration.status,
        )
    except RosterConflict as exc:
        db.rollback()
        raise ProblemException(409, "roster_conflict", str(exc)) from exc


@router.get("/teams/{team_id}/roster", response_model=list[RosterItem])
def roster(
    team_id: str,
    season_id: str = Query(...),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "analyst", "coach", "viewer")),
):
    return list_roster(db, actor.organization_id, team_id, season_id)


@router.post("/players/{player_id}/consents", response_model=ConsentView, status_code=201)
def add_consent(player_id: str, command: ConsentCommand, db: Session = Depends(get_db), actor: Actor = Depends(editor)):
    try:
        consent = record_consent(db, actor.organization_id, player_id, command)
        db.commit()
        db.refresh(consent)
        return consent
    except ConsentRequired as exc:
        db.rollback()
        raise ProblemException(422, "guardian_consent_required", str(exc)) from exc


@router.delete("/players/{player_id}/consents/{consent_id}", response_model=ConsentView)
def remove_consent(player_id: str, consent_id: str, db: Session = Depends(get_db), actor: Actor = Depends(editor)):
    consent = revoke_consent(db, actor.organization_id, player_id, consent_id)
    db.commit()
    db.refresh(consent)
    return consent

