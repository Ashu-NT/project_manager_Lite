"""Construct the Project Management service graph from supplied Platform capabilities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
    ApprovedTimeLaborCostConsumer,
    BudgetService,
    FinanceService,
    FinancialChangeService,
    FinancialConfigurationService,
    ForecastGenerationService,
    ForecastVersionService,
    PlannedCostService,
    ProcurementFinancialConsumer,
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
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
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
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
)
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)


@dataclass(frozen=True)
class ProjectManagementServiceBundle:
    time_entry_commands: TimeEntryCommandHandler
    time_entry_queries: TimeEntryQueryHandler
    timesheet_period_transitions: TimesheetPeriodTransitionHandler
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
    finance_worker_uow_factory: SqlAlchemyFinanceGovernanceUnitOfWorkFactory
    approved_time_consumer_factory: Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal],
        ApprovedTimeLaborCostConsumer,
    ]
    procurement_consumer_factory: Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal],
        ProcurementFinancialConsumer,
    ]
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
    project_calendar_adapter: ProjectCalendarAdapter
    enterprise_resource_availability: EnterpriseResourceAvailabilityService
    resource_capacity_calculator: ResourceCapacityCalculator
    resource_workload_service: ResourceWorkloadService
    portfolio_resource_pool_service: PortfolioResourcePoolService

