from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar, cast

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
    FinanceSnapshotQueryHandler,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCommitmentService,
    ProjectCostEntryService,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernedServicePort,
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
    ProfitabilityReportBuilder,
    ProjectKpiReportBuilder,
    ScheduleVarianceReportBuilder,
)
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolQueryHandler,
    ProjectResourceCommandHandler,
    ProjectResourceQueryHandler,
    ResourceCapabilityCommandHandler,
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
    ResourceWorkloadQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
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
from src.core.modules.project_management.application.scheduling import SchedulingEngine
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
    ResourceLevelingCommandHandler,
    TaskDeletionCommandHandler,
    TaskDependencyCommandHandler,
    TaskDependencyQueryHandler,
    TaskHierarchyCommandHandler,
    TaskHierarchyQueryHandler,
    TaskLifecycleCommandHandler,
    TaskProgressCommandHandler,
    TaskSchedulingConstraintHandler,
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
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
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

_T = TypeVar("_T")


def _resolve(services: Mapping[str, object], key: str, expected: type[_T]) -> _T | None:
    candidate = services.get(key)
    return candidate if isinstance(candidate, expected) else None


@dataclass(frozen=True)
class ProjectManagementDesktopRuntimeServices:
    project_query: ProjectQueryHandler | None
    project_create: ProjectCreateHandler | None
    project_update: ProjectUpdateHandler | None
    project_status: ProjectStatusHandler | None
    project_deletion: ProjectDeletionHandler | None
    portfolio_intake_query: PortfolioIntakeQueryHandler | None
    portfolio_intake_commands: PortfolioIntakeCommandHandler | None
    portfolio_template_query: PortfolioTemplateQueryHandler | None
    portfolio_template_commands: PortfolioTemplateCommandHandler | None
    portfolio_scenario_query: PortfolioScenarioQueryHandler | None
    portfolio_scenario_commands: PortfolioScenarioCommandHandler | None
    portfolio_dependency_query: PortfolioDependencyQueryHandler | None
    portfolio_dependency_commands: PortfolioDependencyCommandHandler | None
    portfolio_executive_query: PortfolioExecutiveQueryHandler | None
    collaboration_comment_commands: CollaborationCommentCommandHandler | None
    collaboration_comment_engagement: CollaborationCommentEngagementHandler | None
    collaboration_presence_commands: CollaborationPresenceCommandHandler | None
    collaboration_comment_query: CollaborationCommentQueryHandler | None
    collaboration_document_query: CollaborationDocumentQueryHandler | None
    collaboration_inbox_query: CollaborationInboxQueryHandler | None
    collaboration_presence_query: CollaborationPresenceQueryHandler | None
    register_query: RegisterQueryHandler | None
    register_lifecycle_commands: RegisterLifecycleHandler | None
    resource_query: ResourceQueryHandler | None
    resource_master_commands: ResourceMasterCommandHandler | None
    resource_capability_commands: ResourceCapabilityCommandHandler | None
    resource_capability_query: ResourceCapabilityQueryHandler | None
    resource_context_query: ResourceContextQueryHandler | None
    availability_service: ResourceAvailabilityQueryHandler | None
    resource_workload_query: ResourceWorkloadQueryHandler | None
    pool_service: PortfolioResourcePoolQueryHandler | None
    project_resource_query: ProjectResourceQueryHandler | None
    project_resource_commands: ProjectResourceCommandHandler | None
    timesheet_workspace_query: TimesheetWorkspaceQueryHandler | None
    timesheet_workspace_commands: TimesheetWorkspaceCommandHandler | None
    timesheet_review_query: TimesheetReviewQueryHandler | None
    time_entry_commands: TimeEntryCommandHandler | None
    time_entry_queries: TimeEntryQueryHandler | None
    timesheet_period_query: TimesheetPeriodQueryHandler | None
    timesheet_period_transitions: TimesheetPeriodTransitionHandler | None
    task_leveling_commands: ResourceLevelingCommandHandler | None
    task_hierarchy_query: TaskHierarchyQueryHandler | None
    task_deletion_commands: TaskDeletionCommandHandler | None
    task_progress_commands: TaskProgressCommandHandler | None
    task_hierarchy_commands: TaskHierarchyCommandHandler | None
    task_constraint_commands: TaskSchedulingConstraintHandler | None
    task_lifecycle_commands: TaskLifecycleCommandHandler | None
    task_dependency_commands: TaskDependencyCommandHandler | None
    task_dependency_query: TaskDependencyQueryHandler | None
    task_workspace_query: TaskWorkspacePageQueryHandler | None
    task_detail_query: TaskDetailPageQueryHandler | None
    task_dependency_diagnostics: TaskDependencyDiagnosticsQueryHandler | None
    task_lookup_query: TaskLookupQueryHandler | None
    task_assignment_commands: TaskAssignmentCommandHandler | None
    task_time_entries: TaskTimeEntryHandler | None
    assignment_skill_validator: AssignmentSkillValidator | None
    scheduling_engine: SchedulingEngine | None
    work_calendar_engine: CalendarProtocol | None
    project_dashboard_query: ProjectDashboardQueryHandler | None
    portfolio_dashboard_query: PortfolioDashboardQueryHandler | None
    finance_snapshot_query: FinanceSnapshotQueryHandler | None
    finance_workspace_query: ProjectFinanceWorkspaceQuery | None
    finance_performance_query: ProjectFinancePerformanceQuery | None
    finance_governance_commands: FinanceGovernanceCommandBoundary | None
    cost_entry_service: ProjectCostEntryService | FinanceGovernedServicePort | None
    commitment_service: ProjectCommitmentService | None
    billing_profile_service: ProjectBillingProfileService | None
    billing_preparation_service: ProjectBillingPreparationService | None
    baseline_query: BaselineQueryHandler | None
    baseline_commands: BaselineCommandHandler | None
    schedule_change_impact_query: ScheduleChangeImpactQueryHandler | None
    project_kpi_report: ProjectKpiReportBuilder | None
    earned_value_report: EarnedValueReportBuilder | None
    cost_breakdown_report: CostBreakdownReportBuilder | None
    baseline_compare_report: BaselineCompareReportBuilder | None
    schedule_variance_report: ScheduleVarianceReportBuilder | None
    profitability_report: ProfitabilityReportBuilder | None
    tenant_context_service: TenantContextService | None


def resolve_project_management_desktop_runtime_services(
    services: Mapping[str, object],
) -> ProjectManagementDesktopRuntimeServices:
    project_query = services.get("project_query")
    register_query = services.get("register_query")
    register_lifecycle_commands = services.get("register_lifecycle_commands")
    resource_query = services.get("resource_query")
    resource_capability_query = services.get("resource_capability_query")
    resource_context_query = services.get("resource_context_query")
    availability_service = services.get("resource_availability_service")
    resource_workload_query = services.get("resource_workload_query")
    pool_service = services.get("portfolio_resource_pool_query")
    project_resource_query = services.get("project_resource_query")
    project_resource_commands = services.get("project_resource_commands")
    timesheet_workspace_query = services.get("timesheet_workspace_query")
    timesheet_workspace_commands = services.get("timesheet_workspace_commands")
    timesheet_review_query = services.get("timesheet_review_query")
    time_entry_commands = services.get("time_entry_commands")
    time_entry_queries = services.get("time_entry_queries")
    timesheet_period_query = services.get("timesheet_period_query")
    timesheet_period_transitions = services.get("timesheet_period_transitions")
    task_workspace_query = services.get("task_workspace_query")
    task_detail_query = services.get("task_detail_query")
    task_dependency_diagnostics = services.get("task_dependency_diagnostics")
    task_lookup_query = services.get("task_lookup_query")
    task_assignment_commands = services.get("task_assignment_commands")
    task_time_entries = services.get("task_time_entries")
    assignment_skill_validator = services.get("assignment_skill_validator")
    scheduling_engine = services.get("scheduling_engine")
    work_calendar_engine = services.get("work_calendar_engine")
    finance_snapshot_query = services.get("finance_snapshot_query")
    finance_workspace_query = services.get("finance_workspace_query")
    finance_performance_query = services.get("finance_performance_query")
    finance_governance_commands = services.get("finance_governance_commands")
    cost_entry_service = services.get("cost_entry_service")
    commitment_service = services.get("commitment_service")
    billing_profile_service = services.get("billing_profile_service")
    billing_preparation_service = services.get("billing_preparation_service")
    baseline_query = services.get("baseline_query")
    schedule_change_impact_query = services.get("schedule_change_impact_query")
    tenant_context_service = services.get("tenant_context_service")

    if work_calendar_engine is not None and not hasattr(
        work_calendar_engine, "is_working_day"
    ):
        work_calendar_engine = None

    return ProjectManagementDesktopRuntimeServices(
        baseline_commands=_resolve(services, "baseline_commands", BaselineCommandHandler),
        task_leveling_commands=_resolve(services, "task_leveling_commands", ResourceLevelingCommandHandler),
        task_hierarchy_query=_resolve(services, "task_hierarchy_query", TaskHierarchyQueryHandler),
        task_deletion_commands=_resolve(services, "task_deletion_commands", TaskDeletionCommandHandler),
        task_progress_commands=_resolve(services, "task_progress_commands", TaskProgressCommandHandler),
        task_hierarchy_commands=_resolve(services, "task_hierarchy_commands", TaskHierarchyCommandHandler),
        task_constraint_commands=_resolve(services, "task_constraint_commands", TaskSchedulingConstraintHandler),
        task_lifecycle_commands=_resolve(services, "task_lifecycle_commands", TaskLifecycleCommandHandler),
        task_dependency_commands=_resolve(services, "task_dependency_commands", TaskDependencyCommandHandler),
        task_dependency_query=_resolve(services, "task_dependency_query", TaskDependencyQueryHandler),
        project_create=_resolve(services, "project_create", ProjectCreateHandler),
        project_update=_resolve(services, "project_update", ProjectUpdateHandler),
        project_status=_resolve(services, "project_status", ProjectStatusHandler),
        project_deletion=_resolve(services, "project_deletion", ProjectDeletionHandler),
        project_query=(
            project_query if isinstance(project_query, ProjectQueryHandler) else None
        ),
        portfolio_intake_query=_resolve(services, "portfolio_intake_query", PortfolioIntakeQueryHandler),
        portfolio_intake_commands=_resolve(services, "portfolio_intake_commands", PortfolioIntakeCommandHandler),
        portfolio_template_query=_resolve(services, "portfolio_template_query", PortfolioTemplateQueryHandler),
        portfolio_template_commands=_resolve(services, "portfolio_template_commands", PortfolioTemplateCommandHandler),
        portfolio_scenario_query=_resolve(services, "portfolio_scenario_query", PortfolioScenarioQueryHandler),
        portfolio_scenario_commands=_resolve(services, "portfolio_scenario_commands", PortfolioScenarioCommandHandler),
        portfolio_dependency_query=_resolve(services, "portfolio_dependency_query", PortfolioDependencyQueryHandler),
        portfolio_dependency_commands=_resolve(services, "portfolio_dependency_commands", PortfolioDependencyCommandHandler),
        portfolio_executive_query=_resolve(services, "portfolio_executive_query", PortfolioExecutiveQueryHandler),
        collaboration_comment_commands=_resolve(services, "collaboration_comment_commands", CollaborationCommentCommandHandler),
        collaboration_comment_engagement=_resolve(services, "collaboration_comment_engagement", CollaborationCommentEngagementHandler),
        collaboration_presence_commands=_resolve(services, "collaboration_presence_commands", CollaborationPresenceCommandHandler),
        collaboration_comment_query=_resolve(services, "collaboration_comment_query", CollaborationCommentQueryHandler),
        collaboration_document_query=_resolve(services, "collaboration_document_query", CollaborationDocumentQueryHandler),
        collaboration_inbox_query=_resolve(services, "collaboration_inbox_query", CollaborationInboxQueryHandler),
        collaboration_presence_query=_resolve(services, "collaboration_presence_query", CollaborationPresenceQueryHandler),
        register_query=(
            register_query if isinstance(register_query, RegisterQueryHandler) else None
        ),
        register_lifecycle_commands=(
            register_lifecycle_commands
            if isinstance(register_lifecycle_commands, RegisterLifecycleHandler)
            else None
        ),
        resource_query=(
            resource_query if isinstance(resource_query, ResourceQueryHandler) else None
        ),
        resource_master_commands=_resolve(services, "resource_master_commands", ResourceMasterCommandHandler),
        resource_capability_commands=_resolve(
            services, "resource_capability_commands", ResourceCapabilityCommandHandler
        ),
        resource_capability_query=(
            resource_capability_query
            if isinstance(resource_capability_query, ResourceCapabilityQueryHandler)
            else None
        ),
        resource_context_query=(
            resource_context_query
            if isinstance(resource_context_query, ResourceContextQueryHandler)
            else None
        ),
        availability_service=(
            availability_service
            if isinstance(availability_service, ResourceAvailabilityQueryHandler)
            else None
        ),
        pool_service=(
            pool_service
            if isinstance(pool_service, PortfolioResourcePoolQueryHandler)
            else None
        ),
        project_resource_query=(
            project_resource_query
            if isinstance(project_resource_query, ProjectResourceQueryHandler)
            else None
        ),
        project_resource_commands=(
            project_resource_commands
            if isinstance(project_resource_commands, ProjectResourceCommandHandler)
            else None
        ),
        timesheet_workspace_query=timesheet_workspace_query if isinstance(timesheet_workspace_query, TimesheetWorkspaceQueryHandler) else None,
        timesheet_workspace_commands=timesheet_workspace_commands if isinstance(timesheet_workspace_commands, TimesheetWorkspaceCommandHandler) else None,
        timesheet_review_query=timesheet_review_query if isinstance(timesheet_review_query, TimesheetReviewQueryHandler) else None,
        time_entry_commands=time_entry_commands if isinstance(time_entry_commands, TimeEntryCommandHandler) else None,
        time_entry_queries=time_entry_queries if isinstance(time_entry_queries, TimeEntryQueryHandler) else None,
        timesheet_period_query=timesheet_period_query if isinstance(timesheet_period_query, TimesheetPeriodQueryHandler) else None,
        timesheet_period_transitions=timesheet_period_transitions if isinstance(timesheet_period_transitions, TimesheetPeriodTransitionHandler) else None,
        task_workspace_query=(
            task_workspace_query
            if isinstance(task_workspace_query, TaskWorkspacePageQueryHandler)
            else None
        ),
        task_detail_query=(
            task_detail_query if isinstance(task_detail_query, TaskDetailPageQueryHandler) else None
        ),
        task_dependency_diagnostics=(
            task_dependency_diagnostics
            if isinstance(task_dependency_diagnostics, TaskDependencyDiagnosticsQueryHandler)
            else None
        ),
        task_lookup_query=(
            task_lookup_query if isinstance(task_lookup_query, TaskLookupQueryHandler) else None
        ),
        task_assignment_commands=(
            task_assignment_commands
            if isinstance(task_assignment_commands, TaskAssignmentCommandHandler)
            else None
        ),
        task_time_entries=(
            task_time_entries if isinstance(task_time_entries, TaskTimeEntryHandler) else None
        ),
        assignment_skill_validator=(
            assignment_skill_validator
            if isinstance(assignment_skill_validator, AssignmentSkillValidator)
            else None
        ),
        scheduling_engine=(
            scheduling_engine
            if isinstance(scheduling_engine, SchedulingEngine)
            else None
        ),
        work_calendar_engine=cast(CalendarProtocol | None, work_calendar_engine),
        project_dashboard_query=_resolve(services, "project_dashboard_query", ProjectDashboardQueryHandler),
        portfolio_dashboard_query=_resolve(
            services, "portfolio_dashboard_query", PortfolioDashboardQueryHandler
        ),
        finance_snapshot_query=(
            finance_snapshot_query if isinstance(finance_snapshot_query, FinanceSnapshotQueryHandler) else None
        ),
        finance_workspace_query=(
            finance_workspace_query
            if isinstance(finance_workspace_query, ProjectFinanceWorkspaceQuery)
            else None
        ),
        cost_entry_service=(
            cost_entry_service
            if isinstance(
                cost_entry_service,
                (ProjectCostEntryService, FinanceGovernedServicePort),
            )
            else None
        ),
        commitment_service=(
            commitment_service
            if isinstance(commitment_service, ProjectCommitmentService)
            else None
        ),
        billing_profile_service=(
            billing_profile_service
            if isinstance(billing_profile_service, ProjectBillingProfileService)
            else None
        ),
        billing_preparation_service=(
            billing_preparation_service
            if isinstance(billing_preparation_service, ProjectBillingPreparationService)
            else None
        ),
        baseline_query=(
            baseline_query
            if isinstance(baseline_query, BaselineQueryHandler)
            else None
        ),
        schedule_change_impact_query=(
            schedule_change_impact_query
            if isinstance(schedule_change_impact_query, ScheduleChangeImpactQueryHandler)
            else None
        ),
        project_kpi_report=_resolve(services, "project_kpi_report", ProjectKpiReportBuilder),
        earned_value_report=_resolve(services, "earned_value_report", EarnedValueReportBuilder),
        cost_breakdown_report=_resolve(services, "cost_breakdown_report", CostBreakdownReportBuilder),
        baseline_compare_report=_resolve(services, "baseline_compare_report", BaselineCompareReportBuilder),
        schedule_variance_report=_resolve(services, "schedule_variance_report", ScheduleVarianceReportBuilder),
        profitability_report=_resolve(services, "profitability_report", ProfitabilityReportBuilder),
        finance_performance_query=(
            finance_performance_query
            if isinstance(finance_performance_query, ProjectFinancePerformanceQuery)
            else None
        ),
        finance_governance_commands=(
            finance_governance_commands
            if isinstance(finance_governance_commands, FinanceGovernanceCommandBoundary)
            else None
        ),
        resource_workload_query=(
            resource_workload_query
            if isinstance(resource_workload_query, ResourceWorkloadQueryHandler)
            else None
        ),
        tenant_context_service=(
            tenant_context_service
            if isinstance(tenant_context_service, TenantContextService)
            else None
        ),
    )


__all__ = [
    "ProjectManagementDesktopRuntimeServices",
    "resolve_project_management_desktop_runtime_services",
]
