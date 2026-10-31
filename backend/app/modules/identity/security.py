"""Argon2id passwords, signed sessions, and cookie primitives."""

import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pwdlib import PasswordHash
from starlette.responses import Response


SESSION_COOKIE = "statx_session"
CSRF_COOKIE = "statx_csrf"
SESSION_SALT = "statx-local-session-v1"
_password_hash = PasswordHash.recommended()
_dummy_hash = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "bF11FNRZFiFs5jAdbAc5rA$+aJqbYlk9QdfWqm4pV4LchCjjtR5Gs8YvdT4dUv1KrA"
)


class InvalidCredentials(RuntimeError):
    """A generic authentication failure that does not reveal its cause."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _password_hash.verify(password, encoded)
    except (ValueError, TypeError):
        return False


def create_session_token(user_id: int, membership_id: int, secret: str) -> str:
    serializer = URLSafeTimedSerializer(secret_key=secret, salt=SESSION_SALT)
    return serializer.dumps({"user_id": user_id, "membership_id": membership_id})


def read_session_token(token: str, secret: str, *, max_age: int) -> dict[str, int]:
    serializer = URLSafeTimedSerializer(secret_key=secret, salt=SESSION_SALT)
    try:
        payload = serializer.loads(token, max_age=max_age)
        user_id = int(payload["user_id"])
        membership_id = int(payload["membership_id"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError) as exc:
        raise InvalidCredentials("Invalid or expired session") from exc
    return {"user_id": user_id, "membership_id": membership_id}


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    session_token: str,
    csrf_token: str,
    *,
    ttl_seconds: int,
) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=ttl_seconds,
        httponly=False,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", httponly=False, samesite="lax")


def verify_unknown_user_password(password: str) -> None:
    """Spend one normal password verification for unknown accounts."""
    verify_password(password, _dummy_hash)

