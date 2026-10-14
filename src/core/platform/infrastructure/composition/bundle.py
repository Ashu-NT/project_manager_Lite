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
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.documents import (
    DocumentAttachmentCommandHandler,
    DocumentAttachmentQueryHandler,
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
    PermissionDocumentAccessPolicy,
)
from src.core.platform.application.master_data.employee import (
    EmployeeCommandHandler,
    EmployeeDocumentCommandHandler,
    EmployeeQueryHandler,
)
from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationQueryHandler,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.notifications.notification_service import (
    NotificationService,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementCommandHandler,
)
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
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    AuthComposition,
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
    module_catalog_service: ModuleCatalogQueryHandler
    module_entitlement_commands: ModuleEntitlementCommandHandler
    auth: AuthComposition
    role_assignment_commands: RoleAssignmentHandler
    role_governance_service: RoleGovernanceService
    tenant_role_administration_service: TenantRoleAdministrationService
    organization_commands: OrganizationCommandHandler
    organization_lifecycle: OrganizationLifecycleCommandHandler
    organization_query: OrganizationQueryHandler
    document_access_policy: PermissionDocumentAccessPolicy
    document_commands: DocumentCommandHandler
    document_structure_commands: DocumentStructureCommandHandler
    document_query: DocumentQueryHandler
    document_attachment_commands: DocumentAttachmentCommandHandler
    document_attachment_query: DocumentAttachmentQueryHandler
    party_commands: PartyCommandHandler
    party_query: PartyQueryHandler
    department_commands: DepartmentCommandHandler
    department_query: DepartmentQueryHandler
    site_commands: SiteCommandHandler
    site_query: SiteQueryHandler
    employee_commands: EmployeeCommandHandler
    employee_query: EmployeeQueryHandler
    employee_document_commands: EmployeeDocumentCommandHandler
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

