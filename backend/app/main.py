"""FastAPI entry point for StatX Analytics."""

from fastapi import FastAPI


app = FastAPI(
    title="StatX Analytics API",
    description="API d'analyse tactique et de performance pour le football.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "statx-analytics-api"}

