"""Build the Platform service graph for the application composition root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.access import (
    AccessControlService,
)
from src.core.platform.application.approval import (
    ApprovalCommandHandler,
    ApprovalParticipantRegistry,
    ApprovalQueryHandler,
)
from src.core.platform.application.data_operations.exporting import ExportRuntime
from src.core.platform.application.data_operations.importing import CsvImportRuntime
from src.core.platform.application.data_operations.runtime_tracking import (
    RuntimeExecutionCommandHandler,
    RuntimeExecutionQueryHandler,
)
from src.core.platform.application.finance import (
    FinancialPeriodCommandHandler,
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.history.audit import EnterpriseAuditService
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
    OrganizationProvisioningCommandHandler,
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
from src.core.platform.application.notifications import (
    NotificationCommandHandler,
    NotificationDeliveryHandler,
    NotificationQueryHandler,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeQueryHandler,
)
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceCommandHandler,
    TenantRoleCommandHandler,
    TenantRoleQueryHandler,
)
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.application.security.identity import (
    ApiKeyAuthenticationHandler,
    ServicePrincipalCommandHandler,
    ServicePrincipalQueryHandler,
)
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementCommandHandler,
)
from src.core.platform.application.tenant.tenancy import (
    TenantAdminQueryHandler,
    TenantContextService,
    TenantInvitationCommandHandler,
    TenantLifecycleCommandHandler,
    TenantMembershipLifecycleCommandHandler,
    TenantMembershipQueryHandler,
)
from src.core.platform.application.time_management.calendar.assignment.commands.calendar_assignment_commands import (
    CalendarAssignmentCommandHandler,
)
from src.core.platform.application.time_management.calendar.assignment.queries.calendar_assignment_queries import (
    CalendarAssignmentQueryHandler,
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
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.shift_pattern_commands import (
    ShiftPatternCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.shift_pattern_queries import (
    ShiftPatternQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.working_rule_queries import (
    WorkingRuleQueryHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
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
    platform_runtime_query: PlatformRuntimeQueryHandler
    organization_provisioning_commands: OrganizationProvisioningCommandHandler
    module_catalog_service: ModuleCatalogQueryHandler
    module_entitlement_commands: ModuleEntitlementCommandHandler
    auth: AuthComposition
    role_assignment_commands: RoleAssignmentHandler
    role_governance_commands: RoleGovernanceCommandHandler
    tenant_role_commands: TenantRoleCommandHandler
    tenant_role_queries: TenantRoleQueryHandler
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
    master_data_import_runtime: CsvImportRuntime
    master_data_export_runtime: ExportRuntime
    runtime_execution_commands: RuntimeExecutionCommandHandler
    runtime_execution_query: RuntimeExecutionQueryHandler
    access_service: AccessControlService
    activity_service: ActivityService
    enterprise_audit_service: EnterpriseAuditService
    financial_period_commands: FinancialPeriodCommandHandler
    financial_period_queries: FinancialPeriodQueryHandler
    notification_commands: NotificationCommandHandler
    notification_queries: NotificationQueryHandler
    notification_delivery: NotificationDeliveryHandler
    approval_commands: ApprovalCommandHandler
    approval_queries: ApprovalQueryHandler
    approval_participants: ApprovalParticipantRegistry
    platform_calendar_commands: PlatformCalendarCommandHandler
    platform_calendar_queries: PlatformCalendarQueryHandler
    working_rule_commands: WorkingRuleCommandHandler
    working_rule_queries: WorkingRuleQueryHandler
    calendar_exception_commands: CalendarExceptionCommandHandler
    calendar_exception_queries: CalendarExceptionQueryHandler
    recurring_event_commands: RecurringEventCommandHandler
    recurring_event_queries: RecurringEventQueryHandler
    shift_pattern_commands: ShiftPatternCommandHandler
    shift_pattern_queries: ShiftPatternQueryHandler
    calendar_assignment_commands: CalendarAssignmentCommandHandler
    calendar_assignment_queries: CalendarAssignmentQueryHandler
    platform_calendar_resolver: PlatformCalendarResolver
    working_time_calculator: WorkingTimeCalculator
    tenant_admin_queries: TenantAdminQueryHandler
    tenant_lifecycle_commands: TenantLifecycleCommandHandler
    tenant_invitation_commands: TenantInvitationCommandHandler
    tenant_membership_lifecycle_commands: TenantMembershipLifecycleCommandHandler
    tenant_membership_queries: TenantMembershipQueryHandler
    service_principal_commands: ServicePrincipalCommandHandler
    service_principal_query: ServicePrincipalQueryHandler
    api_key_authentication: ApiKeyAuthenticationHandler
    global_calendar_shim: GlobalCalendarShim
    runtime_security_configuration: RuntimeSecurityConfiguration

    def runtime_bindings(self) -> dict[str, Any]:
        """Export existing composed capabilities for application runtime assembly."""
        return {
            'user_session': self.user_session,
            'platform_runtime_query': self.platform_runtime_query,
            'organization_provisioning_commands': self.organization_provisioning_commands,
            'module_catalog_service': self.module_catalog_service,
            'module_entitlement_commands': self.module_entitlement_commands,
            'auth': self.auth,
            'auth_queries': self.auth.queries,
            'authentication': self.auth.authentication,
            'password_commands': self.auth.passwords,
            'mfa_commands': self.auth.mfa,
            'federated_identity_commands': self.auth.federated_identities,
            'user_registration': self.auth.registration,
            'user_administration_commands': self.auth.user_administration,
            'user_directory_query': self.auth.user_directory,
            'auth_session_commands': self.auth.session_commands,
            'auth_session_query': self.auth.session_queries,
            'context_switch_commands': self.auth.context_switch,
            'auth_bootstrap': self.auth.bootstrap,
            'platform_owner_provisioning': self.auth.platform_owner,
            'principal_builder': self.auth.principals,
            'auth_session_lifecycle': self.auth.session_lifecycle,
            'role_assignment_commands': self.role_assignment_commands,
            'role_governance_commands': self.role_governance_commands,
            'tenant_role_commands': self.tenant_role_commands,
            'tenant_role_queries': self.tenant_role_queries,
            'organization_commands': self.organization_commands,
            'organization_lifecycle': self.organization_lifecycle,
            'organization_query': self.organization_query,
            'tenant_context_service': self.tenant_context_service,
            'platform_view_invalidation_channel': self.platform_view_invalidation_channel,
            'tenant_admin_queries': self.tenant_admin_queries,
            'tenant_lifecycle_commands': self.tenant_lifecycle_commands,
            'tenant_invitation_commands': self.tenant_invitation_commands,
            'tenant_membership_lifecycle_commands': self.tenant_membership_lifecycle_commands,
            'tenant_membership_queries': self.tenant_membership_queries,
            'service_principal_commands': self.service_principal_commands,
            'service_principal_query': self.service_principal_query,
            'api_key_authentication': self.api_key_authentication,
            'document_access_policy': self.document_access_policy,
            'document_commands': self.document_commands,
            'document_structure_commands': self.document_structure_commands,
            'document_query': self.document_query,
            'document_attachment_commands': self.document_attachment_commands,
            'document_attachment_query': self.document_attachment_query,
            'party_commands': self.party_commands,
            'party_query': self.party_query,
            'department_commands': self.department_commands,
            'department_query': self.department_query,
            'site_commands': self.site_commands,
            'site_query': self.site_query,
            'employee_commands': self.employee_commands,
            'employee_query': self.employee_query,
            'employee_document_commands': self.employee_document_commands,
            'master_data_import_runtime': self.master_data_import_runtime,
            'master_data_export_runtime': self.master_data_export_runtime,
            'runtime_execution_commands': self.runtime_execution_commands,
            'runtime_execution_query': self.runtime_execution_query,
            'access_service': self.access_service,
            'activity_service': self.activity_service,
            'enterprise_audit_service': self.enterprise_audit_service,
            'financial_period_commands': self.financial_period_commands,
            'financial_period_queries': self.financial_period_queries,
            'notification_commands': self.notification_commands,
            'notification_queries': self.notification_queries,
            'notification_delivery': self.notification_delivery,
            'approval_commands': self.approval_commands,
            'approval_queries': self.approval_queries,
            'approval_participants': self.approval_participants,
            'platform_calendar_commands': self.platform_calendar_commands,
            'platform_calendar_queries': self.platform_calendar_queries,
            'working_rule_commands': self.working_rule_commands,
            'working_rule_queries': self.working_rule_queries,
            'calendar_exception_commands': self.calendar_exception_commands,
            'calendar_exception_queries': self.calendar_exception_queries,
            'recurring_event_commands': self.recurring_event_commands,
            'recurring_event_queries': self.recurring_event_queries,
            'shift_pattern_commands': self.shift_pattern_commands,
            'shift_pattern_queries': self.shift_pattern_queries,
            'calendar_assignment_commands': self.calendar_assignment_commands,
            'calendar_assignment_queries': self.calendar_assignment_queries,
            'platform_calendar_resolver': self.platform_calendar_resolver,
            'working_time_calculator': self.working_time_calculator,
        }

