"""RFC 7807-style application errors with trace identifiers."""

from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class ProblemException(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def problem_response(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": f"urn:statx:problem:{code}",
            "title": code.replace("_", " ").title(),
            "status": status_code,
            "code": code,
            "detail": detail,
            "trace_id": str(uuid4()),
        },
    )


async def problem_exception_handler(_: Request, exc: ProblemException) -> JSONResponse:
    return problem_response(exc.status_code, exc.code, exc.detail)


async def authentication_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return problem_response(401, "authentication_required", str(exc))


async def authorization_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return problem_response(403, "authorization_denied", str(exc))


async def csrf_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return problem_response(403, "csrf_rejected", str(exc))


async def not_found_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return problem_response(404, "resource_not_found", "Resource not found")


async def invalid_credentials_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return problem_response(401, "invalid_credentials", "Invalid email or password")

