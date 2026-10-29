"""FastAPI entry point and application lifecycle for StatX Analytics."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.db.database import init_db


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = PROJECT_ROOT / "data" / "exports"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize persistent resources before accepting requests."""
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="StatX Analytics API",
    description="API d'analyse tactique et de performance pour le football.",
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(api_router)
app.mount("/exports", StaticFiles(directory=EXPORT_ROOT), name="exports")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "statx-analytics-api"}

