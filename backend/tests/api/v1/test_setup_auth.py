"""First-run bootstrap and local session security contracts."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.db.model_registry import Base
from app.modules.identity.models import Membership, User
from app.modules.identity.schemas import BootstrapCommand
from app.modules.identity.security import (
    clear_auth_cookies,
    create_session_token,
    hash_password,
    read_session_token,
    set_auth_cookies,
    verify_password,
)
from app.modules.identity.service import (
    BootstrapAlreadyCompleted,
    InvalidCredentials,
    authenticate,
    bootstrap_system,
)
from app.modules.integrations.models import ProviderSyncRun, ProviderSyncStage
from app.modules.integrations.api_football import ProviderEnvelope
from app.modules.integrations.schemas import ClubSelectionCommand
from app.modules.integrations.service import ClubSyncService, InvalidProviderPayload
from app.modules.identity.router import session_view
from app.modules.organizations.models import Organization
from app.modules.platform.models import SystemState


def database_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{(tmp_path / 'auth.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(SystemState(id=1, bootstrapped=False))
    session.commit()
    return session


def bootstrap_command() -> BootstrapCommand:
    return BootstrapCommand(
        organization_name="Espérance StatX",
        admin_display_name="Admin StatX",
        email="ADMIN@STATX.LOCAL",
        password="A-secure-local-passphrase-2026",
        country_code="TN",
        default_locale="fr",
        timezone="Africa/Tunis",
        job_title="coach",
    )


def test_bootstrap_keeps_owner_admin_role_and_records_job_title(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    try:
        result = bootstrap_system(session, bootstrap_command())
        session.commit()

        actor = authenticate(session, "admin@statx.local", bootstrap_command().password)
        view = session_view(actor)

        assert result.membership.role == "admin"
        assert result.user.job_title == "coach"
        assert actor.role == "admin"
        assert actor.job_title == "coach"
        assert view.role == "admin"
        assert view.job_title == "coach"
    finally:
        session.close()


@pytest.mark.parametrize("job_title", ["president", "goalkeeper", "root", ""])
def test_bootstrap_rejects_unsupported_football_functions(job_title: str) -> None:
    payload = bootstrap_command().model_dump()
    payload["job_title"] = job_title

    with pytest.raises(ValueError):
        BootstrapCommand.model_validate(payload)


def test_bootstrap_atomically_queues_selected_provider_club(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    selected = ClubSelectionCommand(
        team_provider_id="1001",
        team_name="Espérance ST",
        logo_url="https://media.api-sports.io/football/teams/1001.png",
        league_provider_id="202",
        league_name="Ligue 1",
        season=2026,
    )
    try:
        result = bootstrap_system(
            session,
            bootstrap_command().model_copy(update={"selected_club": selected}),
        )
        session.commit()

        run = session.scalar(select(ProviderSyncRun))
        assert result.user.job_title == "coach"
        assert run.organization_id == result.organization.id
        assert run.status == "queued"
        assert run.request_json["team_provider_id"] == "1001"
        assert {stage.name for stage in session.scalars(select(ProviderSyncStage))} == {
            "squad",
            "profiles",
            "fixtures",
            "standings",
            "portraits",
        }
    finally:
        session.close()


def test_manual_bootstrap_creates_no_provider_run(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    try:
        bootstrap_system(session, bootstrap_command())
        session.commit()
        assert session.query(User).count() == 1
        assert session.query(ProviderSyncRun).count() == 0
    finally:
        session.close()


def test_provider_failure_after_bootstrap_does_not_remove_creator_account(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    selected = ClubSelectionCommand(
        team_provider_id="1001",
        team_name="Espérance ST",
        league_provider_id="202",
        league_name="Ligue 1",
        season=2026,
    )
    try:
        bootstrap_system(
            session,
            bootstrap_command().model_copy(update={"selected_club": selected}),
        )
        session.commit()
        run = session.scalar(select(ProviderSyncRun))

        class InvalidSquadRepository:
            def cached_request(self, endpoint, params, ttl):
                duplicate = {"id": 501, "name": "Aymen Ben Ali"}
                payload = [{"team": {"id": 1001}, "players": [duplicate, duplicate]}]
                return ProviderEnvelope(payload, 1, 1, 1)

        with pytest.raises(InvalidProviderPayload):
            ClubSyncService(session, InvalidSquadRepository()).execute_run(run.public_id)
        session.rollback()

        assert session.query(User).count() == 1
        assert session.query(Membership).count() == 1
        assert session.query(Organization).count() == 1
    finally:
        session.close()


def test_bootstrap_is_atomic_hashes_password_and_can_run_only_once(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    competitor = Session(session.get_bind())
    try:
        result = bootstrap_system(session, bootstrap_command())
        session.commit()

        assert result.organization.name == "Espérance StatX"
        assert result.user.email == "admin@statx.local"
        assert result.membership.role == "admin"
        assert result.user.password_hash != bootstrap_command().password
        assert verify_password(bootstrap_command().password, result.user.password_hash)
        assert session.scalar(select(SystemState).where(SystemState.id == 1)).bootstrapped
        assert session.query(Organization).count() == 1
        assert session.query(User).count() == 1
        assert session.query(Membership).count() == 1

        with pytest.raises(BootstrapAlreadyCompleted):
            bootstrap_system(competitor, bootstrap_command())
        competitor.rollback()
        assert session.query(Organization).count() == 1
    finally:
        competitor.close()
        session.close()


def test_authentication_failure_is_generic_and_sessions_are_signed(tmp_path: Path) -> None:
    session = database_session(tmp_path)
    try:
        bootstrap_system(session, bootstrap_command())
        session.commit()

        actor = authenticate(session, "admin@statx.local", bootstrap_command().password)
        token = create_session_token(actor.user_id, actor.membership_id, "test-secret-123456789")
        payload = read_session_token(token, "test-secret-123456789", max_age=60)
        assert payload == {"user_id": actor.user_id, "membership_id": actor.membership_id}

        for email, password in (
            ("missing@statx.local", "wrong-password"),
            ("admin@statx.local", "wrong-password"),
        ):
            with pytest.raises(InvalidCredentials, match="Invalid email or password"):
                authenticate(session, email, password)

        with pytest.raises(InvalidCredentials):
            read_session_token(token, "another-secret-123456", max_age=60)
        with pytest.raises(InvalidCredentials):
            read_session_token(token, "test-secret-123456789", max_age=-1)
    finally:
        session.close()


def test_cookie_contract_is_http_only_samesite_and_clearable() -> None:
    response = Response()
    set_auth_cookies(response, "signed-session", "csrf-value", ttl_seconds=28_800)
    cookies = response.headers.getlist("set-cookie")
    assert any("statx_session=signed-session" in value and "HttpOnly" in value for value in cookies)
    assert any("statx_csrf=csrf-value" in value and "HttpOnly" not in value for value in cookies)
    assert all("SameSite=lax" in value for value in cookies)

    logout = Response()
    clear_auth_cookies(logout)
    assert all("Max-Age=0" in value for value in logout.headers.getlist("set-cookie"))


def test_password_hash_uses_argon2id() -> None:
    encoded = hash_password("another-secure-passphrase")
    assert encoded.startswith("$argon2id$")
    assert verify_password("another-secure-passphrase", encoded)

