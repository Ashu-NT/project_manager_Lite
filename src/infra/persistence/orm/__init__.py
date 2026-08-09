"""ORM metadata and model packages."""

from src.infra.persistence.orm.base import Base
import src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant  # noqa: F401  — must precede org (FK dep)
import src.core.modules.maintenance.infrastructure.persistence.orm.models  # noqa: F401
import src.core.modules.maintenance.infrastructure.persistence.orm.preventive_runtime_models  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.org.org  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.employee.employee  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.site.sites  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.department.departments  # noqa: F401
# src.core.platform.infrastructure.persistence.orm.calendar removed after Alembic migration
# working_calendars and holidays tables are dropped by migration o8p9q0r1s2t3
import src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.documents.documents  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.master_data.party.party  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.tenant.modules.modules  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.time_management.time.time  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.time_management.time_financial_outbox  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.finance.financial_period  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.security.auth.auth  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.security.identity.identity  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.history.activity.activity  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.events.platform_events.platform_events  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.events.notifications.notification  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.approval.approval  # noqa: F401
import src.core.platform.infrastructure.persistence.orm.data_operations.runtime_tracking.runtime_tracking  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.project  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.resource  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.task  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.cost  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.cost_entry  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.commitment  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.baseline  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.register  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.collaboration  # noqa: F401
import src.core.modules.project_management.infrastructure.persistence.orm.portfolio  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.catalog  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.procurement  # noqa: F401
import src.core.modules.inventory_procurement.infrastructure.persistence.orm.integration_outbox  # noqa: F401

__all__ = ["Base"]
