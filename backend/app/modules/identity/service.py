"""Transactional first-run and authentication services."""

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.identity.models import Membership, User
from app.modules.identity.schemas import BootstrapCommand, FootballJobTitle
from app.modules.identity.security import (
    InvalidCredentials,
    hash_password,
    verify_password,
    verify_unknown_user_password,
)
from app.modules.organizations.models import Organization
from app.modules.platform.models import SystemState, utc_now


class BootstrapAlreadyCompleted(RuntimeError):
    pass


class ResourceNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class BootstrapResult:
    organization: Organization
    user: User
    membership: Membership


@dataclass(frozen=True)
class Actor:
    user_id: int
    user_public_id: str
    membership_id: int
    organization_id: int
    organization_public_id: str
    display_name: str
    email: str
    role: str
    job_title: FootballJobTitle
    locale: str


def bootstrap_system(session: Session, command: BootstrapCommand) -> BootstrapResult:
    """Claim the singleton bootstrap marker and stage the first admin."""
    state = session.get(SystemState, 1)
    if state is None:
        session.add(SystemState(id=1, bootstrapped=False))
        session.flush()

    claim = session.execute(
        update(SystemState)
        .where(SystemState.id == 1, SystemState.bootstrapped.is_(False))
        .values(bootstrapped=True, updated_at=utc_now())
    )
    if claim.rowcount != 1:
        raise BootstrapAlreadyCompleted("Initial setup has already been completed")

    organization = Organization(
        name=command.organization_name,
        country_code=command.country_code,
        default_locale=command.default_locale,
        timezone=command.timezone,
    )
    user = User(
        email=str(command.email).lower(),
        display_name=command.admin_display_name,
        password_hash=hash_password(command.password),
        active=True,
        default_locale=command.default_locale,
        job_title=command.job_title,
    )
    session.add_all([organization, user])
    session.flush()
    membership = Membership(
        user_id=user.id,
        organization_id=organization.id,
        role="admin",
        active=True,
    )
    session.add(membership)
    session.flush()
    return BootstrapResult(organization=organization, user=user, membership=membership)


def actor_from_models(user: User, membership: Membership, organization: Organization) -> Actor:
    return Actor(
        user_id=user.id,
        user_public_id=user.public_id,
        membership_id=membership.id,
        organization_id=organization.id,
        organization_public_id=organization.public_id,
        display_name=user.display_name,
        email=user.email,
        role=membership.role,
        job_title=user.job_title,
        locale=user.default_locale,
    )


def load_actor(session: Session, user_id: int, membership_id: int) -> Actor:
    row = session.execute(
        select(User, Membership, Organization)
        .join(Membership, Membership.user_id == User.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            User.id == user_id,
            Membership.id == membership_id,
            User.active.is_(True),
            Membership.active.is_(True),
        )
    ).one_or_none()
    if row is None:
        raise InvalidCredentials("Invalid or expired session")
    return actor_from_models(*row)


def authenticate(session: Session, email: str, password: str) -> Actor:
    user = session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_unknown_user_password(password)
        raise InvalidCredentials("Invalid email or password")
    if not user.active or not verify_password(password, user.password_hash):
        raise InvalidCredentials("Invalid email or password")
    membership = session.scalar(
        select(Membership)
        .where(Membership.user_id == user.id, Membership.active.is_(True))
        .order_by(Membership.id)
    )
    if membership is None:
        raise InvalidCredentials("Invalid email or password")
    organization = session.get(Organization, membership.organization_id)
    if organization is None:
        raise InvalidCredentials("Invalid email or password")
    return actor_from_models(user, membership, organization)

