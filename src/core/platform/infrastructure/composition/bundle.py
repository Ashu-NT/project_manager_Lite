"""Build the Platform service graph for the application composition root."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.access import (
    AccessControlService,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.data_operations.runtime_tracking import (
    RuntimeExecutionService,
)
from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.data_exchange import (
    MasterDataExchangeService,
)
from src.core.platform.application.master_data.department.department_service import (
    DepartmentService,
)
from src.core.platform.application.master_data.documents import (
    DocumentIntegrationService,
    DocumentService,
)
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.notifications.notification_service import (
    NotificationService,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.tenant.tenancy import (
    TenantAdminService,
    TenantContextService,
    TenantMembershipService,
)
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import (
    GlobalCalendarShim,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    PlatformCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import (
    WorkingTimeCalculator,
)
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import (
    RecurringEventService,
)
from src.core.platform.application.time_management.calendar.definitions.shift_pattern_service import (
    ShiftPatternService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import (
    WorkingRuleService,
)
from src.core.platform.application.time_management.calendar.platform_calendar_service import (
    PlatformCalendarService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    build_platform_repositories as build_platform_repositories,
)
from src.core.shared.events.view_invalidation import (
    ViewInvalidationChannel,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.platform.security_config import (
    RuntimeSecurityConfiguration,
)


@dataclass(frozen=True)
class PlatformServiceBundle:
    session: Session
    user_session: UserSessionContext
    organization_repo: OrganizationRepository
    site_repo: SiteRepository
    party_repo: PartyRepository
    tenant_context_service: TenantContextService
    platform_view_invalidation_channel: ViewInvalidationChannel
   
    platform_transactional_dispatcher: InProcessTransactionalEventDispatcher
    platform_post_commit_bus: InProcessPostCommitEventBus
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_catalog_service: ModuleCatalogService
    auth_service: AuthService
    role_governance_service: RoleGovernanceService
    tenant_role_administration_service: TenantRoleAdministrationService
    organization_service: OrganizationService
    document_service: DocumentService
    document_integration_service: DocumentIntegrationService
    party_service: PartyService
    department_service: DepartmentService
    site_service: SiteService
    employee_service: EmployeeService
    master_data_exchange_service: MasterDataExchangeService
    runtime_execution_service: RuntimeExecutionService
    access_service: AccessControlService
    activity_service: ActivityService
    enterprise_audit_service: EnterpriseAuditService
    financial_period_service: FinancialPeriodService
    notification_service: NotificationService
    approval_service: ApprovalService
    platform_calendar_service: PlatformCalendarService
    working_rule_service: WorkingRuleService
    calendar_exception_service: CalendarExceptionService
    recurring_event_service: RecurringEventService
    shift_pattern_service: ShiftPatternService
    calendar_assignment_service: CalendarAssignmentService
    platform_calendar_resolver: PlatformCalendarResolver
    working_time_calculator: WorkingTimeCalculator
    tenant_admin_service: TenantAdminService
    tenant_membership_service: TenantMembershipService
    service_principal_service: ServicePrincipalService
    global_calendar_shim: GlobalCalendarShim
    runtime_security_configuration: RuntimeSecurityConfiguration

