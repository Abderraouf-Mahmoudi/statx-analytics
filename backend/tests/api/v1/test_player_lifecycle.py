"""Player lifecycle route and authorization surface."""

import pytest

from app.main import create_app
from app.modules.identity.dependencies import AuthorizationDenied, require_actor_role
from app.modules.identity.service import Actor


def actor(role: str) -> Actor:
    return Actor(
        user_id=1,
        user_public_id="user-1",
        membership_id=1,
        organization_id=1,
        organization_public_id="org-1",
        display_name="Test",
        email="test@statx.local",
        role=role,
        job_title="coach",
        locale="fr",
    )


def test_player_lifecycle_routes_are_versioned() -> None:
    routes = {
        (route.path, method)
        for route in create_app().routes
        if hasattr(route, "methods")
        for method in route.methods
    }
    assert ("/api/v1/players/{player_id}", "PATCH") in routes
    assert ("/api/v1/players/{player_id}", "DELETE") in routes
    assert ("/api/v1/registrations/{registration_id}/deactivate", "POST") in routes


def test_admin_and_coach_can_edit_but_viewer_cannot() -> None:
    for role in ("admin", "coach"):
        require_actor_role(actor(role), {"admin", "coach"})
    with pytest.raises(AuthorizationDenied):
        require_actor_role(actor("viewer"), {"admin", "coach"})
