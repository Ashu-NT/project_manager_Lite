from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import (
    FinancialChangeService,
    FinanceService,
    ForecastVersionService,
    ProjectCommitmentService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCostEntryService,
    ProjectFinanceWorkspaceQuery,
    ProjectFinancePerformanceQuery,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
)
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolService,
    ProjectResourceService,
    ResourceService,
    ResourceWorkloadService,
)
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


@dataclass(frozen=True)
class ProjectManagementDesktopRuntimeServices:
    project_service: ProjectService | None
    portfolio_service: PortfolioService | None
    collaboration_service: CollaborationService | None
    register_service: RegisterService | None
    resource_service: ResourceService | None
    availability_service: EnterpriseResourceAvailabilityService | None
    resource_workload_service: ResourceWorkloadService | None
    pool_service: PortfolioResourcePoolService | None
    project_resource_service: ProjectResourceService | None
    timesheet_service: TimesheetService | None
    task_service: TaskService | None
    assignment_skill_validator: AssignmentSkillValidator | None
    scheduling_engine: SchedulingEngine | None
    work_calendar_engine: CalendarProtocol | None
    dashboard_service: DashboardService | None
    finance_service: FinanceService | None
    finance_workspace_query: ProjectFinanceWorkspaceQuery | None
    finance_performance_query: ProjectFinancePerformanceQuery | None
    finance_governance_commands: FinanceGovernanceCommandBoundary | None
    cost_entry_service: ProjectCostEntryService | None
    commitment_service: ProjectCommitmentService | None
    forecast_version_service: ForecastVersionService | None
    financial_change_service: FinancialChangeService | None
    billing_profile_service: ProjectBillingProfileService | None
    billing_preparation_service: ProjectBillingPreparationService | None
    baseline_service: BaselineService | None
    reporting_service: ReportingService | None
    tenant_context_service: TenantContextService | None


def resolve_project_management_desktop_runtime_services(
    services: Mapping[str, object],
) -> ProjectManagementDesktopRuntimeServices:
    project_service = services.get("project_service")
    portfolio_service = services.get("portfolio_service")
    collaboration_service = services.get("collaboration_service")
    register_service = services.get("register_service")
    resource_service = services.get("resource_service")
    availability_service = services.get("resource_availability_service")
    resource_workload_service = services.get("resource_workload_service")
    pool_service = services.get("portfolio_resource_pool_service")
    project_resource_service = services.get("project_resource_service")
    timesheet_service = services.get("timesheet_service")
    task_service = services.get("task_service")
    assignment_skill_validator = services.get("assignment_skill_validator")
    scheduling_engine = services.get("scheduling_engine")
    work_calendar_engine = services.get("work_calendar_engine")
    dashboard_service = services.get("dashboard_service")
    finance_service = services.get("finance_service")
    finance_workspace_query = services.get("finance_workspace_query")
    finance_performance_query = services.get("finance_performance_query")
    finance_governance_commands = services.get("finance_governance_commands")
    cost_entry_service = services.get("cost_entry_service")
    commitment_service = services.get("commitment_service")
    forecast_version_service = services.get("forecast_version_service")
    financial_change_service = services.get("financial_change_service")
    billing_profile_service = services.get("billing_profile_service")
    billing_preparation_service = services.get("billing_preparation_service")
    baseline_service = services.get("baseline_service")
    reporting_service = services.get("reporting_service")
    tenant_context_service = services.get("tenant_context_service")

    if work_calendar_engine is not None and not hasattr(
        work_calendar_engine, "is_working_day"
    ):
        work_calendar_engine = None

    return ProjectManagementDesktopRuntimeServices(
        project_service=(
            project_service if isinstance(project_service, ProjectService) else None
        ),
        portfolio_service=(
            portfolio_service
            if isinstance(portfolio_service, PortfolioService)
            else None
        ),
        collaboration_service=(
            collaboration_service
            if isinstance(collaboration_service, CollaborationService)
            else None
        ),
        register_service=(
            register_service if isinstance(register_service, RegisterService) else None
        ),
        resource_service=(
            resource_service if isinstance(resource_service, ResourceService) else None
        ),
        availability_service=(
            availability_service
            if isinstance(availability_service, EnterpriseResourceAvailabilityService)
            else None
        ),
        pool_service=(
            pool_service
            if isinstance(pool_service, PortfolioResourcePoolService)
            else None
        ),
        project_resource_service=(
            project_resource_service
            if isinstance(project_resource_service, ProjectResourceService)
            else None
        ),
        timesheet_service=(
            timesheet_service
            if isinstance(timesheet_service, TimesheetService)
            else None
        ),
        task_service=task_service if isinstance(task_service, TaskService) else None,
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
        work_calendar_engine=work_calendar_engine,
        dashboard_service=(
            dashboard_service
            if isinstance(dashboard_service, DashboardService)
            else None
        ),
        finance_service=(
            finance_service if isinstance(finance_service, FinanceService) else None
        ),
        finance_workspace_query=(
            finance_workspace_query
            if isinstance(finance_workspace_query, ProjectFinanceWorkspaceQuery)
            else None
        ),
        cost_entry_service=(
            cost_entry_service
            if isinstance(cost_entry_service, ProjectCostEntryService)
            else None
        ),
        commitment_service=(
            commitment_service
            if isinstance(commitment_service, ProjectCommitmentService)
            else None
        ),
        forecast_version_service=(
            forecast_version_service
            if isinstance(forecast_version_service, ForecastVersionService)
            else None
        ),
        financial_change_service=(
            financial_change_service
            if isinstance(financial_change_service, FinancialChangeService)
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
        baseline_service=(
            baseline_service
            if isinstance(baseline_service, BaselineService)
            else None
        ),
        reporting_service=(
            reporting_service
            if isinstance(reporting_service, ReportingService)
            else None
        ),
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
        resource_workload_service=(
            resource_workload_service
            if isinstance(resource_workload_service, ResourceWorkloadService)
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
