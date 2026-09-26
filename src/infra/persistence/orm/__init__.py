"""ORM metadata and model packages."""

import src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff
import src.core.modules.project_management.infrastructure.persistence.orm.baseline
import src.core.modules.project_management.infrastructure.persistence.orm.billing
import src.core.modules.project_management.infrastructure.persistence.orm.budget
import src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment
import src.core.modules.project_management.infrastructure.persistence.orm.collaboration
import src.core.modules.project_management.infrastructure.persistence.orm.commitment
import src.core.modules.project_management.infrastructure.persistence.orm.cost_entry
import src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox
import src.core.modules.project_management.infrastructure.persistence.orm.financial_change
import src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration
import src.core.modules.project_management.infrastructure.persistence.orm.forecast
import src.core.modules.project_management.infrastructure.persistence.orm.labor_posting
import src.core.modules.project_management.infrastructure.persistence.orm.planned_cost
import src.core.modules.project_management.infrastructure.persistence.orm.portfolio
import src.core.modules.project_management.infrastructure.persistence.orm.project
import src.core.modules.project_management.infrastructure.persistence.orm.rate_cards
import src.core.modules.project_management.infrastructure.persistence.orm.register
import src.core.modules.project_management.infrastructure.persistence.orm.resource
import src.core.modules.project_management.infrastructure.persistence.orm.skills
import src.core.modules.project_management.infrastructure.persistence.orm.task
import src.core.platform.infrastructure.persistence.orm.approval.approval
import src.core.platform.infrastructure.persistence.orm.data_operations.runtime_tracking.runtime_tracking
import src.core.platform.infrastructure.persistence.orm.events.notifications.notification
import src.core.platform.infrastructure.persistence.orm.events.platform_events.platform_events
import src.core.platform.infrastructure.persistence.orm.finance.financial_period
import src.core.platform.infrastructure.persistence.orm.history.activity.activity
import src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry
import src.core.platform.infrastructure.persistence.orm.integration.accounting_connector
import src.core.platform.infrastructure.persistence.orm.integration.procurement_financial_outbox
import src.core.platform.infrastructure.persistence.orm.master_data.department.departments
import src.core.platform.infrastructure.persistence.orm.master_data.documents.documents
import src.core.platform.infrastructure.persistence.orm.master_data.employee.employee
import src.core.platform.infrastructure.persistence.orm.master_data.org.org
import src.core.platform.infrastructure.persistence.orm.master_data.party.party
import src.core.platform.infrastructure.persistence.orm.master_data.site.sites
import src.core.platform.infrastructure.persistence.orm.security.auth.auth
import src.core.platform.infrastructure.persistence.orm.security.identity.identity
import src.core.platform.infrastructure.persistence.orm.tenant.modules.modules
import src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant
import src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant

# src.core.platform.infrastructure.persistence.orm.calendar removed after Alembic migration
# working_calendars and holidays tables are dropped by migration o8p9q0r1s2t3
import src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar
import src.core.platform.infrastructure.persistence.orm.time_management.time.time
import src.core.platform.infrastructure.persistence.orm.time_management.time_financial_outbox  # noqa: F401
from src.infra.persistence.orm.base import Base

__all__ = ["Base"]
