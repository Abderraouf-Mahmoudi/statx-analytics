"""Release 1 end-to-end domain regression and legacy preservation."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.model_registry import Base
from app.modules.identity.schemas import BootstrapCommand
from app.modules.identity.service import ResourceNotFound, authenticate, bootstrap_system
from app.modules.organizations.schemas import SeasonCommand, TeamCommand
from app.modules.organizations.service import create_season, create_team
from app.modules.platform.models import AuditLog, SystemState
from app.modules.roster.schemas import ConsentCommand, PlayerCommand, RegistrationCommand
from app.modules.roster.service import create_player, record_consent, register_player, revoke_consent
from tests.factories import create_legacy_database
from tests.migrations.test_foundation_migration import upgrade_database


def test_release1_foundation_workflow_and_tenant_isolation(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'release1.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(SystemState(id=1, bootstrapped=False))
        session.commit()
        result = bootstrap_system(session, BootstrapCommand(
            organization_name="StatX Release Club", admin_display_name="Admin", email="admin@statx.local",
            password="A-secure-local-passphrase-2026", country_code="TN", default_locale="fr", timezone="Africa/Tunis",
            job_title="analyst",
        ))
        session.commit()
        actor = authenticate(session, "admin@statx.local", "A-secure-local-passphrase-2026")
        assert actor.organization_id == result.organization.id

        season = create_season(session, actor.organization_id, SeasonCommand(name="2026/27"))
        team = create_team(session, actor.organization_id, TeamCommand(name="U17", category="academy"))
        player = create_player(session, actor.organization_id, PlayerCommand(
            first_name="Amina", last_name="Ben Salah", birth_date=date(2010, 11, 20), primary_position="CM", preferred_foot="left",
        ))
        register_player(session, actor.organization_id, team.public_id, RegistrationCommand(
            player_id=player.public_id, season_id=season.public_id, shirt_number=8, position="CM", start_date=date(2026, 7, 1),
        ))
        consent = record_consent(session, actor.organization_id, player.public_id, ConsentCommand(
            consent_type="passport_publication", document_sha256="b" * 64,
            signed_at=datetime(2026, 10, 30, tzinfo=timezone.utc), guardian_name="Parent Ben Salah",
        ))
        revoke_consent(session, actor.organization_id, player.public_id, consent.public_id)
        session.commit()
        assert session.scalar(select(AuditLog).where(AuditLog.action == "consent.revoked")) is not None

        with pytest.raises(ResourceNotFound):
            register_player(session, actor.organization_id + 999, team.public_id, RegistrationCommand(
                player_id=player.public_id, season_id=season.public_id, shirt_number=9, position="CM",
            ))


def test_release1_upgrade_retains_legacy_identifiers(tmp_path: Path) -> None:
    database = tmp_path / "legacy-release1.db"
    create_legacy_database(database)
    upgrade_database(database)
    import sqlite3
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id FROM teams WHERE id=11").fetchone() == (11,)
        assert connection.execute("SELECT id FROM players WHERE id=21").fetchone() == (21,)
