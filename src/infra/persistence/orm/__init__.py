"""ORM metadata and model packages."""

from src.infra.persistence.orm.base import Base
import src.infra.persistence.orm.inventory_procurement.models  # noqa: F401
import src.infra.persistence.orm.maintenance.models  # noqa: F401
import src.infra.persistence.orm.maintenance.preventive_runtime_models  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.org  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.documents  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.party  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.modules  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.time  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.auth  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.access  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.audit  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.approval  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.runtime_tracking  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.project  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.resource  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.task  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.baseline  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.register  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.collaboration  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.portfolio  # noqa: F401

__all__ = ["Base"]
