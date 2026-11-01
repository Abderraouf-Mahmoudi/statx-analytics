"""Public, secret-safe integration routes used only during first setup."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.config import Settings, get_settings
from app.db.database import get_db
from app.modules.integrations.api_football import (
    ApiFootballClient,
    IntegrationDisabled,
    ProviderUnavailable,
)
from app.modules.integrations.catalog import (
    CatalogRefreshInProgress,
    TunisianClubCatalogService,
)
from app.modules.integrations.repository import ProviderRepository, QuotaReserved
from app.modules.integrations.schemas import ClubCatalog
from app.modules.platform.models import SystemState


router = APIRouter(prefix="/setup", tags=["setup"])


def _repository(db: Session, settings: Settings) -> ProviderRepository:
    return ProviderRepository(
        db,
        ApiFootballClient(settings),
        daily_ceiling=settings.api_football_daily_ceiling,
    )


@router.get("/provider-catalog", response_model=ClubCatalog)
def provider_catalog(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ClubCatalog:
    state = db.get(SystemState, 1)
    if state is not None and state.bootstrapped:
        raise ProblemException(409, "setup_complete", "Initial setup is already complete")
    repository = _repository(db, settings)
    try:
        catalog = TunisianClubCatalogService(repository).current_catalog()
        db.commit()
        return catalog
    except CatalogRefreshInProgress as exc:
        db.rollback()
        raise ProblemException(409, "catalog_refresh_in_progress", str(exc)) from exc
    except IntegrationDisabled as exc:
        db.rollback()
        raise ProblemException(503, "integration_disabled", str(exc)) from exc
    except QuotaReserved as exc:
        db.rollback()
        raise ProblemException(429, "provider_quota_reserved", str(exc)) from exc
    except ProviderUnavailable as exc:
        db.rollback()
        raise ProblemException(503, "provider_unavailable", str(exc)) from exc
    finally:
        repository.client.close()
