"""Composition root for the supported version 1 API."""

from fastapi import APIRouter, Depends

from app.modules.identity.dependencies import enforce_csrf
from app.modules.identity.router import router as identity_router
from app.modules.integrations.router import router as integration_router
from app.modules.organizations.router import router as organization_router
from app.modules.roster.router import router as roster_router


router = APIRouter(prefix="/api/v1", dependencies=[Depends(enforce_csrf)])
router.include_router(identity_router)
router.include_router(integration_router)
router.include_router(organization_router)
router.include_router(roster_router)

