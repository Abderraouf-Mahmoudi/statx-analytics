"""FastAPI entry point and application lifecycle for StatX Analytics."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.video_routes import router as video_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configured StatX API instance."""
    resolved = settings or get_settings()
    export_root = resolved.data_root / "exports"
    export_root.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        """Prepare local storage; schema changes are owned by Alembic."""
        export_root.mkdir(parents=True, exist_ok=True)
        yield

    application = FastAPI(
        title="StatX Analytics API",
        description="API d'analyse tactique et de performance pour le football.",
        version="0.7.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    application.include_router(api_router)
    application.include_router(video_router)
    application.mount("/exports", StaticFiles(directory=export_root), name="exports")

    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "statx-analytics-api"}

    return application


app = create_app()

