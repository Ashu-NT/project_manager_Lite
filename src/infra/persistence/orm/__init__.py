"""ORM metadata and model packages."""

from src.infra.persistence.orm.base import Base
import src.infra.persistence.orm.inventory_procurement.models  # noqa: F401
import src.infra.persistence.orm.maintenance.models  # noqa: F401
import src.infra.persistence.orm.maintenance.preventive_runtime_models  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.models  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.models  # noqa: F401

__all__ = ["Base"]
