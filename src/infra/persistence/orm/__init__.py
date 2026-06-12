"""ORM metadata and model packages."""

from src.infra.persistence.orm.base import Base
import src.core.platform.infrastructure.persistence.orm.tenant  # noqa: F401  — must precede org (FK dep)
import src.core.modules.maintenance.infrastructure.persistence.orm.models  # noqa: F401
import src.core.modules.maintenance.infrastructure.persistence.orm.preventive_runtime_models  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.org  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.employee  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.sites  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.departments  # noqa: F401
# src.core.platform.infrastructure.persistence.orm.calendar removed after Alembic migration
# working_calendars and holidays tables are dropped by migration o8p9q0r1s2t3
import src.core.platform.infrastructure.persistence.orm.enterprise_calendar  # noqa: F401
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
import src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.register  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.collaboration  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.portfolio  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.catalog  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.procurement  # noqa: F401

__all__ = ["Base"]
