"""ORM metadata and model packages."""

from src.infra.persistence.orm.base import Base
import src.infra.persistence.orm.inventory_procurement.models  # noqa: F401
import src.infra.persistence.orm.maintenance.models  # noqa: F401
import src.infra.persistence.orm.maintenance.preventive_runtime_models  # noqa: F401
import src.infra.persistence.orm.platform.models  # noqa: F401
import src.infra.persistence.orm.project_management.models  # noqa: F401

__all__ = ["Base"]
