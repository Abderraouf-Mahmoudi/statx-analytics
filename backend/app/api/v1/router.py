"""Composition root for the supported version 1 API."""

from fastapi import APIRouter, Depends

from app.modules.identity.dependencies import enforce_csrf
from app.modules.identity.router import router as identity_router


router = APIRouter(prefix="/api/v1", dependencies=[Depends(enforce_csrf)])
router.include_router(identity_router)

