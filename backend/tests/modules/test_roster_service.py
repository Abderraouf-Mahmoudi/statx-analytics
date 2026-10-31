"""Seasonal registration and consent invariants."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.model_registry import Base
from app.modules.organizations.models import Organization, Season, Team
from app.modules.roster.schemas import ConsentCommand, PlayerCommand, RegistrationCommand
from app.modules.roster.service import (
    ConsentRequired,
    RosterConflict,
    create_player,
    list_roster,
    record_consent,
    register_player,
    revoke_consent,
)


def roster_context(tmp_path: Path) -> tuple[Session, Organization, Season, Team]:
    engine = create_engine(f"sqlite:///{(tmp_path / 'roster.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    organization = Organization(name="StatX Club")
    session.add(organization)
    session.flush()
    season = Season(organization_id=organization.id, name="2026/27")
    team = Team(organization_id=organization.id, name="U17")
    session.add_all([season, team])
    session.flush()
    return session, organization, season, team


def test_registration_rejects_overlap_and_duplicate_active_shirt(tmp_path: Path) -> None:
    session, organization, season, team = roster_context(tmp_path)
    try:
        first = create_player(
            session,
            organization.id,
            PlayerCommand(first_name="Amina", last_name="Ben Salah", birth_date=date(2009, 5, 4), primary_position="CM", preferred_foot="left"),
        )
        second = create_player(
            session,
            organization.id,
            PlayerCommand(first_name="Lina", last_name="Trabelsi", birth_date=date(2008, 8, 8), primary_position="RW", preferred_foot="right"),
        )
        command = RegistrationCommand(
            player_id=first.public_id,
            season_id=season.public_id,
            shirt_number=8,
            position="CM",
            start_date=date(2026, 7, 1),
        )
        register_player(session, organization.id, team.public_id, command)
        with pytest.raises(RosterConflict):
            register_player(session, organization.id, team.public_id, command)
        with pytest.raises(RosterConflict):
            register_player(
                session,
                organization.id,
                team.public_id,
                command.model_copy(update={"player_id": second.public_id}),
            )
    finally:
        session.close()


def test_minor_consent_guardian_revocation_and_publishability(tmp_path: Path) -> None:
    session, organization, season, team = roster_context(tmp_path)
    try:
        player = create_player(
            session,
            organization.id,
            PlayerCommand(first_name="Amina", last_name="Ben Salah", birth_date=date(2010, 11, 20), primary_position="CM", preferred_foot="left"),
        )
        register_player(
            session,
            organization.id,
            team.public_id,
            RegistrationCommand(player_id=player.public_id, season_id=season.public_id, shirt_number=8, position="CM", start_date=date(2026, 7, 1)),
        )
        assert list_roster(session, organization.id, team.public_id, season.public_id)[0].publishable is False

        unsigned = ConsentCommand(
            consent_type="passport_publication",
            document_sha256="a" * 64,
            signed_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            guardian_name=None,
        )
        with pytest.raises(ConsentRequired):
            record_consent(session, organization.id, player.public_id, unsigned)

        consent = record_consent(
            session,
            organization.id,
            player.public_id,
            unsigned.model_copy(update={"guardian_name": "Parent Ben Salah"}),
        )
        assert consent.subject_is_minor is True
        assert consent.document_sha256 == "a" * 64
        assert list_roster(session, organization.id, team.public_id, season.public_id)[0].publishable is True

        revoked = revoke_consent(session, organization.id, player.public_id, consent.public_id)
        assert revoked.status == "revoked"
        assert revoked.revoked_at is not None
        assert revoked.document_sha256 == "a" * 64
        assert list_roster(session, organization.id, team.public_id, season.public_id)[0].publishable is False
    finally:
        session.close()

