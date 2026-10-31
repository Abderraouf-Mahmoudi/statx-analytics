"""FastAPI session, role, tenant, and CSRF boundaries."""

import hmac
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.modules.identity.security import CSRF_COOKIE, SESSION_COOKIE, read_session_token
from app.modules.identity.service import Actor, ResourceNotFound, load_actor


class AuthenticationRequired(RuntimeError):
    pass


class AuthorizationDenied(RuntimeError):
    pass


class CsrfRejected(RuntimeError):
    pass


def require_actor_role(actor: Actor, allowed_roles: set[str]) -> None:
    if actor.role not in allowed_roles:
        raise AuthorizationDenied("Insufficient permissions")


def ensure_actor_organization(actor: Actor, organization_public_id: str) -> None:
    if not hmac.compare_digest(actor.organization_public_id, organization_public_id):
        raise ResourceNotFound("Resource not found")


def validate_csrf_values(
    method: str,
    path: str,
    session_token: str | None,
    csrf_cookie: str | None,
    csrf_header: str | None,
) -> None:
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return
    if path in {"/api/v1/setup", "/api/v1/auth/login"} and not session_token:
        return
    if not session_token:
        return
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise CsrfRejected("CSRF token mismatch")


def enforce_csrf(request: Request) -> None:
    validate_csrf_values(
        request.method,
        request.url.path,
        request.cookies.get(SESSION_COOKIE),
        request.cookies.get(CSRF_COOKIE),
        request.headers.get("X-CSRF-Token"),
    )


def current_actor(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Actor:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthenticationRequired("Authentication required")
    payload = read_session_token(token, settings.session_secret, max_age=settings.session_ttl_seconds)
    return load_actor(db, payload["user_id"], payload["membership_id"])


def require_roles(*roles: str) -> Callable[[Actor], Actor]:
    allowed = set(roles)

    def dependency(actor: Actor = Depends(current_actor)) -> Actor:
        require_actor_role(actor, allowed)
        return actor

    return dependency

