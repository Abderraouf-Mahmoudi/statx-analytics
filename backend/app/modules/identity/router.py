"""First-run setup and local authentication endpoints."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.config import Settings, get_settings
from app.db.database import get_db
from app.modules.identity.dependencies import current_actor
from app.modules.identity.schemas import BootstrapCommand, LoginCommand, SessionView
from app.modules.identity.security import (
    InvalidCredentials,
    clear_auth_cookies,
    create_session_token,
    new_csrf_token,
    set_auth_cookies,
)
from app.modules.identity.service import (
    Actor,
    BootstrapAlreadyCompleted,
    actor_from_models,
    authenticate,
    bootstrap_system,
)
from app.modules.platform.models import SystemState


router = APIRouter(tags=["identity"])


def session_view(actor: Actor) -> SessionView:
    return SessionView(
        user_id=actor.user_public_id,
        organization_id=actor.organization_public_id,
        display_name=actor.display_name,
        email=actor.email,
        role=actor.role,
        locale=actor.locale,
    )


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)) -> dict[str, bool]:
    state = db.get(SystemState, 1)
    return {"required": state is None or not state.bootstrapped}


@router.post("/setup", response_model=SessionView, status_code=201)
def setup(
    command: BootstrapCommand,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionView:
    try:
        result = bootstrap_system(db, command)
        actor = actor_from_models(result.user, result.membership, result.organization)
        db.commit()
    except BootstrapAlreadyCompleted as exc:
        db.rollback()
        raise ProblemException(409, "setup_already_completed", str(exc)) from exc
    token = create_session_token(actor.user_id, actor.membership_id, settings.session_secret)
    set_auth_cookies(
        response,
        token,
        new_csrf_token(),
        ttl_seconds=settings.session_ttl_seconds,
    )
    return session_view(actor)


@router.post("/auth/login", response_model=SessionView)
def login(
    command: LoginCommand,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionView:
    try:
        actor = authenticate(db, command.email, command.password)
    except InvalidCredentials as exc:
        raise ProblemException(401, "invalid_credentials", "Invalid email or password") from exc
    token = create_session_token(actor.user_id, actor.membership_id, settings.session_secret)
    set_auth_cookies(
        response,
        token,
        new_csrf_token(),
        ttl_seconds=settings.session_ttl_seconds,
    )
    return session_view(actor)


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> Response:
    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.get("/session", response_model=SessionView)
def read_session(actor: Actor = Depends(current_actor)) -> SessionView:
    return session_view(actor)

