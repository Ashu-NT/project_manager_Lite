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
from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
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
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.reporting import (
    ReportingService,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
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
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
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
from src.core.platform.application.master_data.department.department_service import (
    DepartmentService,
)
from src.core.platform.application.master_data.documents.document_service import (
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
from src.core.platform.application.time_management.time import TimeService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
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
    module_catalog_service: ModuleCatalogService
    module_registry: ModuleRegistry
    integration_resolver: IntegrationResolver
    time_financial_outbox_service: IntegrationOutboxService
    procurement_financial_outbox_service: IntegrationOutboxService
    approved_time_financial_dispatcher: ApprovedTimeFinancialDispatcher
    procurement_financial_dispatcher: ProcurementFinancialDispatcher
    time_service: TimeService
    auth_service: AuthService
    role_governance_service: RoleGovernanceService
    tenant_role_administration_service: TenantRoleAdministrationService
    organization_service: OrganizationService
    tenant_context_service: TenantContextService
    platform_view_invalidation_channel: ViewInvalidationChannel
    tenant_admin_service: TenantAdminService
    tenant_membership_service: TenantMembershipService
    service_principal_service: ServicePrincipalService
    document_service: DocumentService
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
    accounting_connector_commands: AccountingConnectorConfigurationCommands
    notification_service: NotificationService
    approval_service: ApprovalService
    collaboration_service: CollaborationService
    project_service: ProjectService
    task_service: TaskService
    timesheet_service: TimesheetService
    resource_service: ResourceService
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
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
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
            "module_registry": self.module_registry,
            "integration_resolver": self.integration_resolver,
            "time_financial_outbox_service": self.time_financial_outbox_service,
            "procurement_financial_outbox_service": self.procurement_financial_outbox_service,
            "approved_time_financial_dispatcher": self.approved_time_financial_dispatcher,
            "procurement_financial_dispatcher": self.procurement_financial_dispatcher,
            "time_service": self.time_service,
            "auth_service": self.auth_service,
            "role_governance_service": self.role_governance_service,
            "tenant_role_administration_service": (
                self.tenant_role_administration_service
            ),
            "organization_service": self.organization_service,
            "tenant_context_service": self.tenant_context_service,
            "platform_view_invalidation_channel": self.platform_view_invalidation_channel,
            "tenant_admin_service": self.tenant_admin_service,
            "tenant_membership_service": self.tenant_membership_service,
            "service_principal_service": self.service_principal_service,
            "document_service": self.document_service,
            "party_service": self.party_service,
            "department_service": self.department_service,
            "site_service": self.site_service,
            "employee_service": self.employee_service,
            "master_data_exchange_service": self.master_data_exchange_service,
            "runtime_execution_service": self.runtime_execution_service,
            "access_service": self.access_service,
            "activity_service": self.activity_service,
            "enterprise_audit_service": self.enterprise_audit_service,
            "financial_period_service": self.financial_period_service,
            "accounting_connector_commands": self.accounting_connector_commands,
            "notification_service": self.notification_service,
            "approval_service": self.approval_service,
            "collaboration_service": self.collaboration_service,
            "project_service": self.project_service,
            "task_service": self.task_service,
            "timesheet_service": self.timesheet_service,
            "resource_service": self.resource_service,
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
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "portfolio_service": self.portfolio_service,
            "register_service": self.register_service,
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

