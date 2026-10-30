"""Import every ORM module so Alembic sees complete metadata."""

from app.db.database import Base
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.matches import models as match_models  # noqa: F401
from app.modules.organizations import models as organization_models  # noqa: F401
from app.modules.platform import models as platform_models  # noqa: F401
from app.modules.roster import models as roster_models  # noqa: F401

__all__ = ["Base"]

