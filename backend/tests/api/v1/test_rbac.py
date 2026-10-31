"""Role, CSRF, and tenant-isolation security contracts."""

import pytest

from app.main import create_app
from app.modules.identity.dependencies import (
    AuthorizationDenied,
    CsrfRejected,
    ensure_actor_organization,
    require_actor_role,
    validate_csrf_values,
)
from app.modules.identity.service import Actor, ResourceNotFound


def actor(role: str = "admin") -> Actor:
    return Actor(
        user_id=1,
        user_public_id="11111111-1111-4111-8111-111111111111",
        membership_id=2,
        organization_id=3,
        organization_public_id="33333333-3333-4333-8333-333333333333",
        display_name="Analyste",
        email="analyst@statx.local",
        role=role,
        locale="fr",
    )


def test_admin_only_policy_rejects_every_non_admin_role() -> None:
    require_actor_role(actor("admin"), {"admin"})
    for role in ("analyst", "coach", "viewer"):
        with pytest.raises(AuthorizationDenied):
            require_actor_role(actor(role), {"admin"})


def test_cross_organization_lookup_is_hidden_as_not_found() -> None:
    ensure_actor_organization(actor(), "33333333-3333-4333-8333-333333333333")
    with pytest.raises(ResourceNotFound):
        ensure_actor_organization(actor(), "44444444-4444-4444-8444-444444444444")


def test_csrf_requires_double_submit_on_authenticated_mutations() -> None:
    validate_csrf_values("GET", "/api/v1/session", "session", None, None)
    validate_csrf_values("POST", "/api/v1/auth/login", None, None, None)
    validate_csrf_values("POST", "/api/v1/teams", "session", "same", "same")
    for cookie, header in ((None, None), ("token", None), ("token", "other")):
        with pytest.raises(CsrfRejected):
            validate_csrf_values("POST", "/api/v1/teams", "session", cookie, header)


def test_v1_setup_auth_and_session_routes_are_composed() -> None:
    paths = {route.path for route in create_app().routes}
    assert {
        "/api/v1/setup/status",
        "/api/v1/setup",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/session",
    }.issubset(paths)
