"""Organization-scoped player, registration, and consent services."""

from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.identity.service import ResourceNotFound
from app.modules.media.models import PlayerPhoto
from app.modules.matches.models import Event, TrackingPoint
from app.modules.organizations.models import Season, Team
from app.modules.platform.audit import write_audit
from app.modules.roster.models import Consent, Player, PlayerRegistration
from app.modules.roster.statistics_models import PlayerSeasonSnapshot
from app.modules.roster.schemas import RosterItem


class RosterConflict(RuntimeError):
    pass


class ConsentRequired(RuntimeError):
    pass


class PlayerDeleteBlocked(RuntimeError):
    pass


def _scoped(session: Session, model, public_id: str, organization_id: int):
    entity = session.scalar(
        select(model).where(model.public_id == public_id, model.organization_id == organization_id)
    )
    if entity is None:
        raise ResourceNotFound("Resource not found")
    return entity


def create_player(session: Session, organization_id: int, command) -> Player:
    player = Player(
        organization_id=organization_id,
        first_name=command.first_name,
        last_name=command.last_name,
        birth_date=command.birth_date,
        display_name=f"{command.first_name} {command.last_name}".strip(),
        primary_position=command.primary_position,
        name=f"{command.first_name} {command.last_name}".strip(),
        team_id=None,
        jersey_number=None,
        position=command.primary_position,
        preferred_foot=command.preferred_foot,
    )
    session.add(player)
    session.flush()
    write_audit(
        session,
        actor_id=None,
        organization_id=organization_id,
        action="player.created",
        entity_type="player",
        entity_public_id=player.public_id,
        after={"name": player.name},
    )
    return player


def update_player(
    session: Session,
    organization_id: int,
    player_public_id: str,
    command,
    *,
    actor_id: int | None,
) -> Player:
    player = _scoped(session, Player, player_public_id, organization_id)
    changed = command.model_dump(exclude_unset=True)
    audit_after = command.model_dump(exclude_unset=True, mode="json")
    before = {
        field: value.isoformat() if isinstance(value, (date, datetime)) else value
        for field in changed
        if (value := getattr(player, field)) is not None
    }
    moment = datetime.now(timezone.utc)
    overrides = dict(player.player_field_overrides or {})
    for field, value in changed.items():
        setattr(player, field, value)
        overrides[field] = {
            "source": "club",
            "actor_id": actor_id,
            "updated_at": moment.isoformat(),
        }
    if "primary_position" in changed:
        player.position = changed["primary_position"]
    if "first_name" in changed or "last_name" in changed:
        player.name = f"{player.first_name or ''} {player.last_name or ''}".strip()
    player.player_field_overrides = overrides
    player.local_override = True
    session.flush()
    write_audit(
        session,
        actor_id=actor_id,
        organization_id=organization_id,
        action="player.updated",
        entity_type="player",
        entity_public_id=player.public_id,
        before=before,
        after=audit_after,
    )
    return player


def deactivate_registration(
    session: Session,
    organization_id: int,
    registration_public_id: str,
    *,
    end_date: date,
    actor_id: int | None,
) -> PlayerRegistration:
    registration = session.scalar(
        select(PlayerRegistration)
        .join(Player, Player.id == PlayerRegistration.player_id)
        .where(
            PlayerRegistration.public_id == registration_public_id,
            Player.organization_id == organization_id,
        )
    )
    if registration is None:
        raise ResourceNotFound("Resource not found")
    before = {"status": registration.status, "end_date": registration.end_date}
    registration.status = "inactive"
    registration.end_date = end_date
    session.flush()
    write_audit(
        session,
        actor_id=actor_id,
        organization_id=organization_id,
        action="player_registration.deactivated",
        entity_type="player_registration",
        entity_public_id=registration.public_id,
        before=before,
        after={"status": "inactive", "end_date": end_date.isoformat()},
    )
    return registration


def safe_delete_player(
    session: Session,
    organization_id: int,
    player_public_id: str,
    *,
    actor_id: int | None,
) -> None:
    player = _scoped(session, Player, player_public_id, organization_id)
    dependencies = (
        (PlayerRegistration, PlayerRegistration.player_id),
        (Consent, Consent.player_id),
        (PlayerPhoto, PlayerPhoto.player_id),
        (Event, Event.player_id),
        (TrackingPoint, TrackingPoint.player_id),
        (PlayerSeasonSnapshot, PlayerSeasonSnapshot.player_id),
    )
    if any(
        session.scalar(select(func.count()).select_from(model).where(column == player.id))
        for model, column in dependencies
    ):
        raise PlayerDeleteBlocked(
            "Player has registrations or analytical history; deactivate the registration instead"
        )
    public_id = player.public_id
    before = {"name": player.name, "source": player.source}
    session.delete(player)
    session.flush()
    write_audit(
        session,
        actor_id=actor_id,
        organization_id=organization_id,
        action="player.deleted",
        entity_type="player",
        entity_public_id=public_id,
        before=before,
    )


def get_player(session: Session, organization_id: int, player_public_id: str) -> Player:
    return _scoped(session, Player, player_public_id, organization_id)


def list_consents(session: Session, organization_id: int, player_public_id: str) -> list[Consent]:
    player = _scoped(session, Player, player_public_id, organization_id)
    return list(session.scalars(select(Consent).where(Consent.player_id == player.id).order_by(Consent.created_at.desc())))


def register_player(
    session: Session, organization_id: int, team_public_id: str, command
) -> PlayerRegistration:
    team = _scoped(session, Team, team_public_id, organization_id)
    player = _scoped(session, Player, command.player_id, organization_id)
    season = _scoped(session, Season, command.season_id, organization_id)
    overlaps = session.scalar(
        select(PlayerRegistration.id).where(
            PlayerRegistration.player_id == player.id,
            PlayerRegistration.season_id == season.id,
            PlayerRegistration.status == "active",
            or_(PlayerRegistration.end_date.is_(None), PlayerRegistration.end_date >= command.start_date)
            if command.start_date
            else PlayerRegistration.id.is_not(None),
        )
    )
    if overlaps:
        raise RosterConflict("Player already has an overlapping active registration")
    if command.shirt_number is not None and session.scalar(
        select(PlayerRegistration.id).where(
            PlayerRegistration.team_id == team.id,
            PlayerRegistration.season_id == season.id,
            PlayerRegistration.shirt_number == command.shirt_number,
            PlayerRegistration.status == "active",
        )
    ):
        raise RosterConflict("Shirt number is already assigned for this team and season")
    registration = PlayerRegistration(
        player_id=player.id,
        team_id=team.id,
        season_id=season.id,
        shirt_number=command.shirt_number,
        position=command.position or player.position,
        preferred_foot=player.preferred_foot,
        start_date=command.start_date,
        end_date=command.end_date,
        status="active",
    )
    session.add(registration)
    player.team_id = team.id
    player.jersey_number = command.shirt_number
    player.position = registration.position or player.position
    session.flush()
    return registration


def _age_on(birth_date: date, moment: datetime) -> int:
    day = moment.date()
    return day.year - birth_date.year - ((day.month, day.day) < (birth_date.month, birth_date.day))


def record_consent(session: Session, organization_id: int, player_public_id: str, command) -> Consent:
    player = _scoped(session, Player, player_public_id, organization_id)
    is_minor = bool(player.birth_date and _age_on(player.birth_date, command.signed_at) < 18)
    if is_minor and not command.guardian_name:
        raise ConsentRequired("Guardian evidence is required for a minor")
    consent = Consent(
        player_id=player.id,
        consent_type=command.consent_type,
        status="active",
        document_sha256=command.document_sha256.lower(),
        subject_is_minor=is_minor,
        guardian_name=command.guardian_name,
        signed_at=command.signed_at,
        granted_at=command.signed_at,
    )
    session.add(consent)
    session.flush()
    write_audit(
        session,
        actor_id=None,
        organization_id=organization_id,
        action="consent.recorded",
        entity_type="consent",
        entity_public_id=consent.public_id,
        after={"status": "active", "document_sha256": consent.document_sha256},
    )
    return consent


def revoke_consent(
    session: Session, organization_id: int, player_public_id: str, consent_public_id: str
) -> Consent:
    player = _scoped(session, Player, player_public_id, organization_id)
    consent = session.scalar(
        select(Consent).where(Consent.public_id == consent_public_id, Consent.player_id == player.id)
    )
    if consent is None:
        raise ResourceNotFound("Resource not found")
    before = {"status": consent.status}
    consent.status = "revoked"
    consent.revoked_at = datetime.now(timezone.utc)
    session.flush()
    write_audit(
        session,
        actor_id=None,
        organization_id=organization_id,
        action="consent.revoked",
        entity_type="consent",
        entity_public_id=consent.public_id,
        before=before,
        after={"status": "revoked"},
    )
    return consent


def list_roster(
    session: Session, organization_id: int, team_public_id: str, season_public_id: str
) -> list[RosterItem]:
    team = _scoped(session, Team, team_public_id, organization_id)
    season = _scoped(session, Season, season_public_id, organization_id)
    rows = session.execute(
        select(PlayerRegistration, Player)
        .join(Player, Player.id == PlayerRegistration.player_id)
        .where(
            PlayerRegistration.team_id == team.id,
            PlayerRegistration.season_id == season.id,
            PlayerRegistration.status == "active",
        )
        .order_by(PlayerRegistration.shirt_number, Player.last_name)
    ).all()
    result: list[RosterItem] = []
    for registration, player in rows:
        active_consent = session.scalar(
            select(Consent.id).where(Consent.player_id == player.id, Consent.status == "active")
        )
        photo = session.scalar(
            select(PlayerPhoto)
            .where(PlayerPhoto.player_id == player.id)
            .order_by(
                (PlayerPhoto.source.in_(["camera", "gallery"])).desc(),
                PlayerPhoto.created_at.desc(),
            )
        )
        result.append(
            RosterItem(
                player_id=player.public_id,
                first_name=player.first_name or "",
                last_name=player.last_name or "",
                shirt_number=registration.shirt_number,
                position=registration.position,
                publishable=active_consent is not None,
                preferred_foot=registration.preferred_foot or player.preferred_foot,
                source=player.source,
                provider_absent=player.provider_absent,
                photo_status=photo.processing_status if photo else None,
                photo_rights_status=photo.rights_status if photo else None,
            )
        )
    return result

