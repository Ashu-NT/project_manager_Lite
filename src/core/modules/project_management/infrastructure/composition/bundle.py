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
    BudgetQueries,
    FinanceSnapshotQueryHandler,
    FinancialChangeQueryHandler,
    FinancialConfigurationQueryHandler,
    ForecastVersionQueries,
    PlannedCostQueryHandler,
    ProcurementFinancialConsumer,
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
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
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
    finance_worker_uow_factory: SqlAlchemyFinanceGovernanceUnitOfWorkFactory
    approved_time_consumer_factory: Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal],
        ApprovedTimeLaborCostConsumer,
    ]
    procurement_consumer_factory: Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal],
        ProcurementFinancialConsumer,
    ]
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
    project_calendar_adapter: ProjectCalendarAdapter
    enterprise_resource_availability: ResourceAvailabilityQueryHandler
    resource_capacity_calculator: ResourceCapacityCalculator
    resource_workload_query: ResourceWorkloadQueryHandler
    portfolio_resource_pool_query: PortfolioResourcePoolQueryHandler

