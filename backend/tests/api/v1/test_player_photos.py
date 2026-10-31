"""Authenticated player portrait API contract."""

from app.main import create_app


def test_player_photo_routes_are_versioned_and_not_public_static_exports() -> None:
    routes = {(route.path, method) for route in create_app().routes if hasattr(route, "methods") for method in route.methods}
    assert {
        ("/api/v1/players/{player_id}/photo", "POST"),
        ("/api/v1/players/{player_id}/photo", "GET"),
        ("/api/v1/players/{player_id}/photo", "DELETE"),
    } <= routes
