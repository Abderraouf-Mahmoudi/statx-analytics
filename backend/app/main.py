"""FastAPI entry point and application lifecycle for StatX Analytics."""

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.video_routes import router as video_router
from app.core.video_processor import ensure_video_directories
from app.db.database import init_db


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = PROJECT_ROOT / "data" / "exports"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize persistent resources before accepting requests."""
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    init_db()
    ensure_video_directories()
    yield


app = FastAPI(
    title="StatX Analytics API",
    description="API d'analyse tactique et de performance pour le football.",
    version="0.5.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.include_router(api_router)
app.include_router(video_router)
app.mount("/exports", StaticFiles(directory=EXPORT_ROOT), name="exports")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "statx-analytics-api"}

