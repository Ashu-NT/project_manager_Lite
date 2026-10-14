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
    BudgetService,
    FinanceService,
    FinancialChangeService,
    FinancialConfigurationService,
    ForecastGenerationService,
    ForecastVersionService,
    PlannedCostService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCommitmentService,
    ProjectCostEntryService,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
    ProjectRateCardService,
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.governance import (
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
from src.core.modules.project_management.application.projects import ProjectService
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
    ProjectResourceService,
    ResourceCapabilityCommandHandler,
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.capacity.resource_capacity_calculator import (
    ResourceCapacityCalculator,
)
from src.core.modules.project_management.application.resources.capacity.resource_workload_service import (
    ResourceWorkloadService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.portfolio.resource_pool_service import (
    PortfolioResourcePoolService,
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
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
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
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.data_operations.runtime_tracking import (
    RuntimeExecutionService,
)
from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.integration.accounting.commands import (
    AccountingConnectorConfigurationCommands,
)
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
    platform_runtime_application_service: PlatformRuntimeApplicationService
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
    role_governance_service: RoleGovernanceService
    tenant_role_administration_service: TenantRoleAdministrationService
    organization_commands: OrganizationCommandHandler
    organization_lifecycle: OrganizationLifecycleCommandHandler
    organization_query: OrganizationQueryHandler
    tenant_context_service: TenantContextService
    platform_view_invalidation_channel: ViewInvalidationChannel
    tenant_admin_service: TenantAdminService
    tenant_membership_service: TenantMembershipService
    service_principal_service: ServicePrincipalService
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
    master_data_exchange_service: MasterDataExchangeService
    runtime_execution_service: RuntimeExecutionService
    access_service: AccessControlService
    activity_service: ActivityService
    enterprise_audit_service: EnterpriseAuditService
    financial_period_service: FinancialPeriodService
    accounting_connector_commands: AccountingConnectorConfigurationCommands
    notification_service: NotificationService
    approval_service: ApprovalService
    collaboration_comment_commands: CollaborationCommentCommandHandler
    collaboration_comment_engagement: CollaborationCommentEngagementHandler
    collaboration_presence_commands: CollaborationPresenceCommandHandler
    collaboration_comment_query: CollaborationCommentQueryHandler
    collaboration_document_query: CollaborationDocumentQueryHandler
    collaboration_inbox_query: CollaborationInboxQueryHandler
    collaboration_presence_query: CollaborationPresenceQueryHandler
    project_service: ProjectService
    project_query: ProjectQueryHandler
    task_service: TaskService
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
    financial_configuration_service: FinancialConfigurationService
    forecast_generation_service: ForecastGenerationService
    forecast_version_service: ForecastVersionService
    financial_change_service: FinancialChangeService
    billing_profile_service: ProjectBillingProfileService
    billing_preparation_service: ProjectBillingPreparationService
    rate_card_service: ProjectRateCardService
    rate_card_resolver: RateCardResolver
    budget_service: BudgetService
    cost_entry_service: ProjectCostEntryService
    commitment_service: ProjectCommitmentService
    planned_cost_service: PlannedCostService
    finance_workspace_query: ProjectFinanceWorkspaceQuery
    finance_performance_query: ProjectFinancePerformanceQuery
    finance_service: FinanceService
    work_calendar_engine: CalendarProtocol  # GlobalCalendarShim - enterprise-backed
    scheduling_engine: SchedulingEngine
    project_kpi_report: ProjectKpiReportBuilder
    earned_value_report: EarnedValueReportBuilder
    cost_breakdown_report: CostBreakdownReportBuilder
    baseline_compare_report: BaselineCompareReportBuilder
    schedule_variance_report: ScheduleVarianceReportBuilder
    profitability_report: ProfitabilityReportBuilder
    labor_report: LaborReportBuilder
    baseline_service: BaselineService
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
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    assignment_skill_validator: AssignmentSkillValidator
    platform_calendar_service: PlatformCalendarService | None
    working_rule_service: WorkingRuleService | None
    calendar_exception_service: CalendarExceptionService | None
    recurring_event_service: RecurringEventService | None
    shift_pattern_service: ShiftPatternService | None
    calendar_assignment_service: CalendarAssignmentService | None
    platform_calendar_resolver: PlatformCalendarResolver | None
    working_time_calculator: WorkingTimeCalculator | None
    resource_capacity_calculator: ResourceCapacityCalculator | None
    resource_workload_service: ResourceWorkloadService | None
    enterprise_resource_availability: EnterpriseResourceAvailabilityService | None
    portfolio_resource_pool_service: PortfolioResourcePoolService | None
    action_center_service: ActionCenterService
    global_overview_service: GlobalOverviewService
    global_overview_desktop_api: GlobalOverviewDesktopApi
    platform_notification_desktop_api: PlatformNotificationDesktopApi

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "platform_runtime_application_service": self.platform_runtime_application_service,
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
            "role_governance_service": self.role_governance_service,
            "tenant_role_administration_service": (
                self.tenant_role_administration_service
            ),
            "organization_commands": self.organization_commands,
            "organization_lifecycle": self.organization_lifecycle,
            "organization_query": self.organization_query,
            "tenant_context_service": self.tenant_context_service,
            "platform_view_invalidation_channel": self.platform_view_invalidation_channel,
            "tenant_admin_service": self.tenant_admin_service,
            "tenant_membership_service": self.tenant_membership_service,
            "service_principal_service": self.service_principal_service,
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
            "master_data_exchange_service": self.master_data_exchange_service,
            "runtime_execution_service": self.runtime_execution_service,
            "access_service": self.access_service,
            "activity_service": self.activity_service,
            "enterprise_audit_service": self.enterprise_audit_service,
            "financial_period_service": self.financial_period_service,
            "accounting_connector_commands": self.accounting_connector_commands,
            "notification_service": self.notification_service,
            "approval_service": self.approval_service,
            "collaboration_comment_commands": self.collaboration_comment_commands,
            "collaboration_comment_engagement": self.collaboration_comment_engagement,
            "collaboration_presence_commands": self.collaboration_presence_commands,
            "collaboration_comment_query": self.collaboration_comment_query,
            "collaboration_document_query": self.collaboration_document_query,
            "collaboration_inbox_query": self.collaboration_inbox_query,
            "collaboration_presence_query": self.collaboration_presence_query,
            "project_service": self.project_service,
            "project_query": self.project_query,
            "task_service": self.task_service,
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
            "financial_configuration_service": self.financial_configuration_service,
            "forecast_generation_service": self.forecast_generation_service,
            "forecast_version_service": self.forecast_version_service,
            "financial_change_service": self.financial_change_service,
            "billing_profile_service": self.billing_profile_service,
            "billing_preparation_service": self.billing_preparation_service,
            "rate_card_service": self.rate_card_service,
            "rate_card_resolver": self.rate_card_resolver,
            "budget_service": self.budget_service,
            "cost_entry_service": self.cost_entry_service,
            "commitment_service": self.commitment_service,
            "planned_cost_service": self.planned_cost_service,
            "finance_workspace_query": self.finance_workspace_query,
            "finance_performance_query": self.finance_performance_query,
            "finance_service": self.finance_service,
            "work_calendar_engine": self.work_calendar_engine,
            "scheduling_engine": self.scheduling_engine,
            "project_kpi_report": self.project_kpi_report,
            "earned_value_report": self.earned_value_report,
            "cost_breakdown_report": self.cost_breakdown_report,
            "baseline_compare_report": self.baseline_compare_report,
            "schedule_variance_report": self.schedule_variance_report,
            "profitability_report": self.profitability_report,
            "labor_report": self.labor_report,
            "baseline_service": self.baseline_service,
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
            "project_resource_service": self.project_resource_service,
            "data_import_service": self.data_import_service,
            "assignment_skill_validator": self.assignment_skill_validator,
            "platform_calendar_service": self.platform_calendar_service,
            "working_rule_service": self.working_rule_service,
            "calendar_exception_service": self.calendar_exception_service,
            "recurring_event_service": self.recurring_event_service,
            "shift_pattern_service": self.shift_pattern_service,
            "calendar_assignment_service": self.calendar_assignment_service,
            "platform_calendar_resolver": self.platform_calendar_resolver,
            "working_time_calculator": self.working_time_calculator,
            "resource_capacity_calculator": self.resource_capacity_calculator,
            "resource_workload_service": self.resource_workload_service,
            # The calendar-based capacity authority for Task Assignment
            # availability/overallocation. Resource Detail Availability also
            # uses this instance through the bounded Resource workload query.
            "resource_availability_service": self.enterprise_resource_availability,
            "portfolio_resource_pool_service": self.portfolio_resource_pool_service,
            "action_center_service": self.action_center_service,
            "global_overview_service": self.global_overview_service,
            "global_overview_desktop_api": self.global_overview_desktop_api,
            "platform_notification_desktop_api": self.platform_notification_desktop_api,
        }

