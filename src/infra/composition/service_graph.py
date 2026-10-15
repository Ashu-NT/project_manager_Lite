from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.core.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.global_overview.application.action_center_service import (
    ActionCenterService,
)
from src.core.global_overview.application.global_overview_service import (
    GlobalOverviewService,
)
from src.core.modules.project_management.application.collaboration.commands import (
    CollaborationCommentCommandHandler,
    CollaborationCommentEngagementHandler,
    CollaborationPresenceCommandHandler,
)
from src.core.modules.project_management.application.collaboration.queries import (
    CollaborationCommentQueryHandler,
    CollaborationDocumentQueryHandler,
    CollaborationInboxQueryHandler,
    CollaborationPresenceQueryHandler,
)
from src.core.modules.project_management.application.dashboard import (
    PortfolioDashboardQueryHandler,
    ProjectDashboardQueryHandler,
)
from src.core.modules.project_management.application.financials import (
    BudgetQueries,
    FinanceSnapshotQueryHandler,
    FinancialChangeQueryHandler,
    FinancialConfigurationQueryHandler,
    ForecastVersionQueries,
    PlannedCostQueryHandler,
    ProjectBillingPreparationQueryHandler,
    ProjectBillingProfileQueryHandler,
    ProjectCommitmentQueryHandler,
    ProjectCostEntryQueryHandler,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
    ProjectRateCardQueryHandler,
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.governance.command_boundary import (
    FinanceGovernanceCommandBoundary,
)
from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioDependencyCommandHandler,
    PortfolioIntakeCommandHandler,
    PortfolioScenarioCommandHandler,
    PortfolioTemplateCommandHandler,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioDependencyQueryHandler,
    PortfolioExecutiveQueryHandler,
    PortfolioIntakeQueryHandler,
    PortfolioScenarioQueryHandler,
    PortfolioTemplateQueryHandler,
)
from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.deletion import (
    ProjectDeletionHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.reporting import (
    BaselineCompareReportBuilder,
    CostBreakdownReportBuilder,
    EarnedValueReportBuilder,
    LaborReportBuilder,
    ProfitabilityReportBuilder,
    ProjectKpiReportBuilder,
    ScheduleVarianceReportBuilder,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceCommandHandler,
    ProjectResourceQueryHandler,
    ResourceCapabilityCommandHandler,
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.queries.workload import (
    ResourceWorkloadQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.resource_capacity_calculator import (
    ResourceCapacityCalculator,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.portfolio.queries.resource_pool import (
    PortfolioResourcePoolQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.baselines.commands.lifecycle import (
    BaselineCommandHandler,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)
from src.core.modules.project_management.application.scheduling.forecasting.queries.change_impact import (
    ScheduleChangeImpactQueryHandler,
)
from src.core.modules.project_management.application.tasks import (
    ApprovedScheduleChangeHandler,
    ResourceLevelingCommandHandler,
    TaskDeletionCommandHandler,
    TaskDependencyCommandHandler,
    TaskDependencyQueryHandler,
    TaskHierarchyCommandHandler,
    TaskHierarchyQueryHandler,
    TaskLifecycleCommandHandler,
    TaskProgressCommandHandler,
    TaskSchedulingConstraintHandler,
    TaskUowScope,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
)
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.platform.access import AccessControlService
from src.core.platform.api.desktop.notifications.notification import (
    PlatformNotificationDesktopApi,
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
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.integration.accounting.commands import (
    AccountingConnectorConfigurationCommandHandler,
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
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
)
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    AuthComposition,
)
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.integration.approved_time_dispatcher import (
    ApprovedTimeFinancialDispatcher,
)
from src.infra.integration.procurement_financial_dispatcher import (
    ProcurementFinancialDispatcher,
)


@dataclass(frozen=True)
class ServiceGraph:
    session: Session
    user_session: UserSessionContext
    platform_runtime_query: PlatformRuntimeQueryHandler
    organization_provisioning_commands: OrganizationProvisioningCommandHandler
    module_catalog_service: ModuleCatalogQueryHandler
    module_entitlement_commands: ModuleEntitlementCommandHandler
    module_registry: ModuleRegistry
    integration_resolver: IntegrationResolver
    time_financial_outbox_service: IntegrationOutboxService
    procurement_financial_outbox_service: IntegrationOutboxService
    approved_time_financial_dispatcher: ApprovedTimeFinancialDispatcher
    procurement_financial_dispatcher: ProcurementFinancialDispatcher
    time_entry_commands: TimeEntryCommandHandler
    time_entry_queries: TimeEntryQueryHandler
    auth: AuthComposition
    role_assignment_commands: RoleAssignmentHandler
    role_governance_commands: RoleGovernanceCommandHandler
    tenant_role_commands: TenantRoleCommandHandler
    tenant_role_queries: TenantRoleQueryHandler
    organization_commands: OrganizationCommandHandler
    organization_lifecycle: OrganizationLifecycleCommandHandler
    organization_query: OrganizationQueryHandler
    tenant_context_service: TenantContextService
    platform_view_invalidation_channel: ViewInvalidationChannel
    tenant_admin_queries: TenantAdminQueryHandler
    tenant_lifecycle_commands: TenantLifecycleCommandHandler
    tenant_invitation_commands: TenantInvitationCommandHandler
    tenant_membership_lifecycle_commands: TenantMembershipLifecycleCommandHandler
    tenant_membership_queries: TenantMembershipQueryHandler
    service_principal_commands: ServicePrincipalCommandHandler
    service_principal_query: ServicePrincipalQueryHandler
    api_key_authentication: ApiKeyAuthenticationHandler
    document_access_policy: DocumentAccessPolicy
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
    accounting_connector_commands: AccountingConnectorConfigurationCommandHandler
    notification_commands: NotificationCommandHandler
    notification_queries: NotificationQueryHandler
    notification_delivery: NotificationDeliveryHandler
    approval_commands: ApprovalCommandHandler
    approval_queries: ApprovalQueryHandler
    approval_participants: ApprovalParticipantRegistry
    collaboration_comment_commands: CollaborationCommentCommandHandler
    collaboration_comment_engagement: CollaborationCommentEngagementHandler
    collaboration_presence_commands: CollaborationPresenceCommandHandler
    collaboration_comment_query: CollaborationCommentQueryHandler
    collaboration_document_query: CollaborationDocumentQueryHandler
    collaboration_inbox_query: CollaborationInboxQueryHandler
    collaboration_presence_query: CollaborationPresenceQueryHandler
    project_query: ProjectQueryHandler
    project_create: ProjectCreateHandler
    project_update: ProjectUpdateHandler
    project_status: ProjectStatusHandler
    project_deletion: ProjectDeletionHandler
    task_hierarchy_query: TaskHierarchyQueryHandler
    task_deletion_commands: TaskDeletionCommandHandler
    task_progress_commands: TaskProgressCommandHandler
    task_schedule_changes: ApprovedScheduleChangeHandler
    task_hierarchy_commands: TaskHierarchyCommandHandler
    task_constraint_commands: TaskSchedulingConstraintHandler
    task_leveling_commands: ResourceLevelingCommandHandler
    task_lifecycle_commands: TaskLifecycleCommandHandler
    task_dependency_commands: TaskDependencyCommandHandler
    task_dependency_query: TaskDependencyQueryHandler
    task_uow_scope: TaskUowScope
    task_workspace_query: TaskWorkspacePageQueryHandler
    task_detail_query: TaskDetailPageQueryHandler
    task_dependency_diagnostics: TaskDependencyDiagnosticsQueryHandler
    task_lookup_query: TaskLookupQueryHandler
    task_assignment_commands: TaskAssignmentCommandHandler
    task_time_entries: TaskTimeEntryHandler
    timesheet_workspace_query: TimesheetWorkspaceQueryHandler
    timesheet_workspace_commands: TimesheetWorkspaceCommandHandler
    timesheet_review_query: TimesheetReviewQueryHandler
    timesheet_period_query: TimesheetPeriodQueryHandler
    timesheet_period_transitions: TimesheetPeriodTransitionHandler
    resource_query: ResourceQueryHandler
    resource_master_commands: ResourceMasterCommandHandler
    resource_capability_commands: ResourceCapabilityCommandHandler
    resource_capability_query: ResourceCapabilityQueryHandler
    resource_context_query: ResourceContextQueryHandler
    finance_governance_commands: FinanceGovernanceCommandBoundary
    financial_configuration_query: FinancialConfigurationQueryHandler
    forecast_version_query: ForecastVersionQueries
    financial_change_query: FinancialChangeQueryHandler
    billing_profile_query: ProjectBillingProfileQueryHandler
    billing_preparation_query: ProjectBillingPreparationQueryHandler
    rate_card_query: ProjectRateCardQueryHandler
    rate_card_resolver: RateCardResolver
    budget_query: BudgetQueries
    cost_entry_query: ProjectCostEntryQueryHandler
    commitment_query: ProjectCommitmentQueryHandler
    planned_cost_query: PlannedCostQueryHandler
    finance_workspace_query: ProjectFinanceWorkspaceQuery
    finance_performance_query: ProjectFinancePerformanceQuery
    finance_snapshot_query: FinanceSnapshotQueryHandler
    work_calendar_engine: CalendarProtocol  # GlobalCalendarShim - enterprise-backed
    scheduling_engine: SchedulingEngine
    project_kpi_report: ProjectKpiReportBuilder
    earned_value_report: EarnedValueReportBuilder
    cost_breakdown_report: CostBreakdownReportBuilder
    baseline_compare_report: BaselineCompareReportBuilder
    schedule_variance_report: ScheduleVarianceReportBuilder
    profitability_report: ProfitabilityReportBuilder
    labor_report: LaborReportBuilder
    baseline_query: BaselineQueryHandler
    baseline_commands: BaselineCommandHandler
    schedule_change_impact_query: ScheduleChangeImpactQueryHandler
    project_dashboard_query: ProjectDashboardQueryHandler
    portfolio_dashboard_query: PortfolioDashboardQueryHandler
    portfolio_intake_query: PortfolioIntakeQueryHandler
    portfolio_intake_commands: PortfolioIntakeCommandHandler
    portfolio_template_query: PortfolioTemplateQueryHandler
    portfolio_template_commands: PortfolioTemplateCommandHandler
    portfolio_scenario_query: PortfolioScenarioQueryHandler
    portfolio_scenario_commands: PortfolioScenarioCommandHandler
    portfolio_dependency_query: PortfolioDependencyQueryHandler
    portfolio_dependency_commands: PortfolioDependencyCommandHandler
    portfolio_executive_query: PortfolioExecutiveQueryHandler
    register_query: RegisterQueryHandler
    register_lifecycle_commands: RegisterLifecycleHandler
    project_resource_query: ProjectResourceQueryHandler
    project_resource_commands: ProjectResourceCommandHandler
    data_import_service: DataImportService
    assignment_skill_validator: AssignmentSkillValidator
    platform_calendar_commands: PlatformCalendarCommandHandler | None
    platform_calendar_queries: PlatformCalendarQueryHandler | None
    working_rule_commands: WorkingRuleCommandHandler | None
    working_rule_queries: WorkingRuleQueryHandler | None
    calendar_exception_commands: CalendarExceptionCommandHandler | None
    calendar_exception_queries: CalendarExceptionQueryHandler | None
    recurring_event_commands: RecurringEventCommandHandler | None
    recurring_event_queries: RecurringEventQueryHandler | None
    shift_pattern_commands: ShiftPatternCommandHandler | None
    shift_pattern_queries: ShiftPatternQueryHandler | None
    calendar_assignment_commands: CalendarAssignmentCommandHandler | None
    calendar_assignment_queries: CalendarAssignmentQueryHandler | None
    platform_calendar_resolver: PlatformCalendarResolver | None
    working_time_calculator: WorkingTimeCalculator | None
    resource_capacity_calculator: ResourceCapacityCalculator | None
    resource_workload_query: ResourceWorkloadQueryHandler | None
    enterprise_resource_availability: ResourceAvailabilityQueryHandler | None
    portfolio_resource_pool_query: PortfolioResourcePoolQueryHandler | None
    action_center_service: ActionCenterService
    global_overview_service: GlobalOverviewService
    global_overview_desktop_api: GlobalOverviewDesktopApi
    platform_notification_desktop_api: PlatformNotificationDesktopApi

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "platform_runtime_query": self.platform_runtime_query,
            "organization_provisioning_commands": self.organization_provisioning_commands,
            "module_catalog_service": self.module_catalog_service,
            "module_entitlement_commands": self.module_entitlement_commands,
            "module_registry": self.module_registry,
            "integration_resolver": self.integration_resolver,
            "time_financial_outbox_service": self.time_financial_outbox_service,
            "procurement_financial_outbox_service": self.procurement_financial_outbox_service,
            "approved_time_financial_dispatcher": self.approved_time_financial_dispatcher,
            "procurement_financial_dispatcher": self.procurement_financial_dispatcher,
            "time_entry_commands": self.time_entry_commands,
            "time_entry_queries": self.time_entry_queries,
            "auth": self.auth,
            "auth_queries": self.auth.queries,
            "authentication": self.auth.authentication,
            "password_commands": self.auth.passwords,
            "mfa_commands": self.auth.mfa,
            "federated_identity_commands": self.auth.federated_identities,
            "user_registration": self.auth.registration,
            "user_administration_commands": self.auth.user_administration,
            "user_directory_query": self.auth.user_directory,
            "auth_session_commands": self.auth.session_commands,
            "auth_session_query": self.auth.session_queries,
            "context_switch_commands": self.auth.context_switch,
            "auth_bootstrap": self.auth.bootstrap,
            "platform_owner_provisioning": self.auth.platform_owner,
            "principal_builder": self.auth.principals,
            "auth_session_lifecycle": self.auth.session_lifecycle,
            "role_assignment_commands": self.role_assignment_commands,
            "role_governance_commands": self.role_governance_commands,
            "tenant_role_commands": self.tenant_role_commands,
            "tenant_role_queries": self.tenant_role_queries,
            "organization_commands": self.organization_commands,
            "organization_lifecycle": self.organization_lifecycle,
            "organization_query": self.organization_query,
            "tenant_context_service": self.tenant_context_service,
            "platform_view_invalidation_channel": self.platform_view_invalidation_channel,
            "tenant_admin_queries": self.tenant_admin_queries,
            "tenant_lifecycle_commands": self.tenant_lifecycle_commands,
            "tenant_invitation_commands": self.tenant_invitation_commands,
            "tenant_membership_lifecycle_commands": self.tenant_membership_lifecycle_commands,
            "tenant_membership_queries": self.tenant_membership_queries,
            "service_principal_commands": self.service_principal_commands,
            "service_principal_query": self.service_principal_query,
            "api_key_authentication": self.api_key_authentication,
            "document_access_policy": self.document_access_policy,
            "document_commands": self.document_commands,
            "document_structure_commands": self.document_structure_commands,
            "document_query": self.document_query,
            "document_attachment_commands": self.document_attachment_commands,
            "document_attachment_query": self.document_attachment_query,
            "party_commands": self.party_commands,
            "party_query": self.party_query,
            "department_commands": self.department_commands,
            "department_query": self.department_query,
            "site_commands": self.site_commands,
            "site_query": self.site_query,
            "employee_commands": self.employee_commands,
            "employee_query": self.employee_query,
            "employee_document_commands": self.employee_document_commands,
            "master_data_import_runtime": self.master_data_import_runtime,
            "master_data_export_runtime": self.master_data_export_runtime,
            "runtime_execution_commands": self.runtime_execution_commands,
            "runtime_execution_query": self.runtime_execution_query,
            "access_service": self.access_service,
            "activity_service": self.activity_service,
            "enterprise_audit_service": self.enterprise_audit_service,
            "financial_period_commands": self.financial_period_commands,
            "financial_period_queries": self.financial_period_queries,
            "accounting_connector_commands": self.accounting_connector_commands,
            "notification_commands": self.notification_commands,
            "notification_queries": self.notification_queries,
            "notification_delivery": self.notification_delivery,
            "approval_commands": self.approval_commands,
            "approval_queries": self.approval_queries,
            "approval_participants": self.approval_participants,
            "collaboration_comment_commands": self.collaboration_comment_commands,
            "collaboration_comment_engagement": self.collaboration_comment_engagement,
            "collaboration_presence_commands": self.collaboration_presence_commands,
            "collaboration_comment_query": self.collaboration_comment_query,
            "collaboration_document_query": self.collaboration_document_query,
            "collaboration_inbox_query": self.collaboration_inbox_query,
            "collaboration_presence_query": self.collaboration_presence_query,
            "project_query": self.project_query,
            "project_create": self.project_create,
            "project_update": self.project_update,
            "project_status": self.project_status,
            "project_deletion": self.project_deletion,
            "task_hierarchy_query": self.task_hierarchy_query,
            "task_deletion_commands": self.task_deletion_commands,
            "task_progress_commands": self.task_progress_commands,
            "task_schedule_changes": self.task_schedule_changes,
            "task_hierarchy_commands": self.task_hierarchy_commands,
            "task_constraint_commands": self.task_constraint_commands,
            "task_leveling_commands": self.task_leveling_commands,
            "task_lifecycle_commands": self.task_lifecycle_commands,
            "task_dependency_commands": self.task_dependency_commands,
            "task_dependency_query": self.task_dependency_query,
            "task_uow_scope": self.task_uow_scope,
            "task_workspace_query": self.task_workspace_query,
            "task_detail_query": self.task_detail_query,
            "task_dependency_diagnostics": self.task_dependency_diagnostics,
            "task_lookup_query": self.task_lookup_query,
            "task_assignment_commands": self.task_assignment_commands,
            "task_time_entries": self.task_time_entries,
            "timesheet_workspace_query": self.timesheet_workspace_query,
            "timesheet_workspace_commands": self.timesheet_workspace_commands,
            "timesheet_review_query": self.timesheet_review_query,
            "timesheet_period_query": self.timesheet_period_query,
            "timesheet_period_transitions": self.timesheet_period_transitions,
            "resource_query": self.resource_query,
            "resource_master_commands": self.resource_master_commands,
            "resource_capability_commands": self.resource_capability_commands,
            "resource_capability_query": self.resource_capability_query,
            "resource_context_query": self.resource_context_query,
            "finance_governance_commands": self.finance_governance_commands,
            "financial_configuration_query": self.financial_configuration_query,
            "forecast_version_query": self.forecast_version_query,
            "financial_change_query": self.financial_change_query,
            "billing_profile_query": self.billing_profile_query,
            "billing_preparation_query": self.billing_preparation_query,
            "rate_card_query": self.rate_card_query,
            "rate_card_resolver": self.rate_card_resolver,
            "budget_query": self.budget_query,
            "cost_entry_query": self.cost_entry_query,
            "commitment_query": self.commitment_query,
            "planned_cost_query": self.planned_cost_query,
            "finance_workspace_query": self.finance_workspace_query,
            "finance_performance_query": self.finance_performance_query,
            "finance_snapshot_query": self.finance_snapshot_query,
            "work_calendar_engine": self.work_calendar_engine,
            "scheduling_engine": self.scheduling_engine,
            "project_kpi_report": self.project_kpi_report,
            "earned_value_report": self.earned_value_report,
            "cost_breakdown_report": self.cost_breakdown_report,
            "baseline_compare_report": self.baseline_compare_report,
            "schedule_variance_report": self.schedule_variance_report,
            "profitability_report": self.profitability_report,
            "labor_report": self.labor_report,
            "baseline_query": self.baseline_query,
            "baseline_commands": self.baseline_commands,
            "schedule_change_impact_query": self.schedule_change_impact_query,
            "project_dashboard_query": self.project_dashboard_query,
            "portfolio_dashboard_query": self.portfolio_dashboard_query,
            "portfolio_intake_query": self.portfolio_intake_query,
            "portfolio_intake_commands": self.portfolio_intake_commands,
            "portfolio_template_query": self.portfolio_template_query,
            "portfolio_template_commands": self.portfolio_template_commands,
            "portfolio_scenario_query": self.portfolio_scenario_query,
            "portfolio_scenario_commands": self.portfolio_scenario_commands,
            "portfolio_dependency_query": self.portfolio_dependency_query,
            "portfolio_dependency_commands": self.portfolio_dependency_commands,
            "portfolio_executive_query": self.portfolio_executive_query,
            "register_query": self.register_query,
            "register_lifecycle_commands": self.register_lifecycle_commands,
            "project_resource_query": self.project_resource_query,
            "project_resource_commands": self.project_resource_commands,
            "data_import_service": self.data_import_service,
            "assignment_skill_validator": self.assignment_skill_validator,
            "platform_calendar_commands": self.platform_calendar_commands,
            "platform_calendar_queries": self.platform_calendar_queries,
            "working_rule_commands": self.working_rule_commands,
            "working_rule_queries": self.working_rule_queries,
            "calendar_exception_commands": self.calendar_exception_commands,
            "calendar_exception_queries": self.calendar_exception_queries,
            "recurring_event_commands": self.recurring_event_commands,
            "recurring_event_queries": self.recurring_event_queries,
            "shift_pattern_commands": self.shift_pattern_commands,
            "shift_pattern_queries": self.shift_pattern_queries,
            "calendar_assignment_commands": self.calendar_assignment_commands,
            "calendar_assignment_queries": self.calendar_assignment_queries,
            "platform_calendar_resolver": self.platform_calendar_resolver,
            "working_time_calculator": self.working_time_calculator,
            "resource_capacity_calculator": self.resource_capacity_calculator,
            "resource_workload_query": self.resource_workload_query,
            # The calendar-based capacity authority for Task Assignment
            # availability/overallocation. Resource Detail Availability also
            # uses this instance through the bounded Resource workload query.
            "resource_availability_service": self.enterprise_resource_availability,
            "portfolio_resource_pool_query": self.portfolio_resource_pool_query,
            "action_center_service": self.action_center_service,
            "global_overview_service": self.global_overview_service,
            "global_overview_desktop_api": self.global_overview_desktop_api,
            "platform_notification_desktop_api": self.platform_notification_desktop_api,
        }

