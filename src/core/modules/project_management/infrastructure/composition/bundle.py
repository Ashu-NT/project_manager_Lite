"""Construct the Project Management service graph from supplied Platform capabilities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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

    def runtime_bindings(self) -> dict[str, Any]:
        """Export existing composed capabilities for application runtime assembly."""
        return {
            'time_entry_commands': self.time_entry_commands,
            'time_entry_queries': self.time_entry_queries,
            'collaboration_comment_commands': self.collaboration_comment_commands,
            'collaboration_comment_engagement': self.collaboration_comment_engagement,
            'collaboration_presence_commands': self.collaboration_presence_commands,
            'collaboration_comment_query': self.collaboration_comment_query,
            'collaboration_document_query': self.collaboration_document_query,
            'collaboration_inbox_query': self.collaboration_inbox_query,
            'collaboration_presence_query': self.collaboration_presence_query,
            'project_query': self.project_query,
            'project_create': self.project_create,
            'project_update': self.project_update,
            'project_status': self.project_status,
            'project_deletion': self.project_deletion,
            'task_hierarchy_query': self.task_hierarchy_query,
            'task_deletion_commands': self.task_deletion_commands,
            'task_progress_commands': self.task_progress_commands,
            'task_schedule_changes': self.task_schedule_changes,
            'task_hierarchy_commands': self.task_hierarchy_commands,
            'task_constraint_commands': self.task_constraint_commands,
            'task_leveling_commands': self.task_leveling_commands,
            'task_lifecycle_commands': self.task_lifecycle_commands,
            'task_dependency_commands': self.task_dependency_commands,
            'task_dependency_query': self.task_dependency_query,
            'task_uow_scope': self.task_uow_scope,
            'task_workspace_query': self.task_workspace_query,
            'task_detail_query': self.task_detail_query,
            'task_dependency_diagnostics': self.task_dependency_diagnostics,
            'task_lookup_query': self.task_lookup_query,
            'task_assignment_commands': self.task_assignment_commands,
            'task_time_entries': self.task_time_entries,
            'timesheet_workspace_query': self.timesheet_workspace_query,
            'timesheet_workspace_commands': self.timesheet_workspace_commands,
            'timesheet_review_query': self.timesheet_review_query,
            'timesheet_period_query': self.timesheet_period_query,
            'timesheet_period_transitions': self.timesheet_period_transitions,
            'resource_query': self.resource_query,
            'resource_master_commands': self.resource_master_commands,
            'resource_capability_commands': self.resource_capability_commands,
            'resource_capability_query': self.resource_capability_query,
            'resource_context_query': self.resource_context_query,
            'finance_governance_commands': self.finance_governance_commands,
            'financial_configuration_query': self.financial_configuration_query,
            'forecast_version_query': self.forecast_version_query,
            'financial_change_query': self.financial_change_query,
            'billing_profile_query': self.billing_profile_query,
            'billing_preparation_query': self.billing_preparation_query,
            'rate_card_query': self.rate_card_query,
            'rate_card_resolver': self.rate_card_resolver,
            'budget_query': self.budget_query,
            'cost_entry_query': self.cost_entry_query,
            'commitment_query': self.commitment_query,
            'planned_cost_query': self.planned_cost_query,
            'finance_workspace_query': self.finance_workspace_query,
            'finance_performance_query': self.finance_performance_query,
            'finance_snapshot_query': self.finance_snapshot_query,
            'work_calendar_engine': self.work_calendar_engine,
            'project_calendar_adapter': self.project_calendar_adapter,
            'scheduling_engine': self.scheduling_engine,
            'project_kpi_report': self.project_kpi_report,
            'earned_value_report': self.earned_value_report,
            'cost_breakdown_report': self.cost_breakdown_report,
            'baseline_compare_report': self.baseline_compare_report,
            'schedule_variance_report': self.schedule_variance_report,
            'profitability_report': self.profitability_report,
            'labor_report': self.labor_report,
            'baseline_query': self.baseline_query,
            'baseline_commands': self.baseline_commands,
            'schedule_change_impact_query': self.schedule_change_impact_query,
            'project_dashboard_query': self.project_dashboard_query,
            'portfolio_dashboard_query': self.portfolio_dashboard_query,
            'portfolio_intake_query': self.portfolio_intake_query,
            'portfolio_intake_commands': self.portfolio_intake_commands,
            'portfolio_template_query': self.portfolio_template_query,
            'portfolio_template_commands': self.portfolio_template_commands,
            'portfolio_scenario_query': self.portfolio_scenario_query,
            'portfolio_scenario_commands': self.portfolio_scenario_commands,
            'portfolio_dependency_query': self.portfolio_dependency_query,
            'portfolio_dependency_commands': self.portfolio_dependency_commands,
            'portfolio_executive_query': self.portfolio_executive_query,
            'register_query': self.register_query,
            'register_lifecycle_commands': self.register_lifecycle_commands,
            'project_resource_query': self.project_resource_query,
            'project_resource_commands': self.project_resource_commands,
            'data_import_service': self.data_import_service,
            'assignment_skill_validator': self.assignment_skill_validator,
            'resource_capacity_calculator': self.resource_capacity_calculator,
            'resource_workload_query': self.resource_workload_query,
            'resource_availability_service': self.enterprise_resource_availability,
            'portfolio_resource_pool_query': self.portfolio_resource_pool_query,
        }

