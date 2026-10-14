from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_portfolio_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
)
from src.core.modules.project_management.api.desktop_runtime.registry import (
    ProjectManagementDesktopRuntimeApis,
    ProjectManagementDesktopRuntimePlatformDependencies,
)
from src.core.modules.project_management.api.desktop_runtime.scheduling_helpers import (
    build_schedule_change_impact_service,
)
from src.core.modules.project_management.api.desktop_runtime.service_resolver import (
    resolve_project_management_desktop_runtime_services,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidator,
)
from src.core.modules.project_management.infrastructure.reporting.export_runtime import (
    ProjectReportSources,
)


def build_project_management_desktop_runtime_apis(
    services: Mapping[str, object],
    platform_dependencies: ProjectManagementDesktopRuntimePlatformDependencies,
) -> ProjectManagementDesktopRuntimeApis:
    resolved = resolve_project_management_desktop_runtime_services(services)
    register_desktop_api = build_project_management_register_desktop_api(
        project_service=resolved.project_service,
        register_query=resolved.register_query,
        register_lifecycle_commands=resolved.register_lifecycle_commands,
        module_catalog_service=platform_dependencies.module_catalog_service,
    )
    change_impact_service = build_schedule_change_impact_service(
        resolved.task_service,
        resolved.work_calendar_engine,
        resolved.baseline_service,
    )
    constraint_validator = (
        ConstraintValidator(resolved.work_calendar_engine)
        if resolved.work_calendar_engine is not None
        else None
    )
    return ProjectManagementDesktopRuntimeApis(
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=resolved.project_service,
            project_dashboard=resolved.project_dashboard_query,
            portfolio_dashboard=resolved.portfolio_dashboard_query,
            baseline_service=resolved.baseline_service,
            earned_value_report=resolved.earned_value_report,
            collaboration_inbox_query=resolved.collaboration_inbox_query,
            approval_service=platform_dependencies.approval_service,
            task_workspace_query=resolved.task_workspace_query,
            module_catalog_service=platform_dependencies.module_catalog_service,
        ),
        project_management_collaboration=build_project_management_collaboration_desktop_api(
            inbox_query=resolved.collaboration_inbox_query,
            comment_query=resolved.collaboration_comment_query,
            document_query=resolved.collaboration_document_query,
            presence_query=resolved.collaboration_presence_query,
            comment_commands=resolved.collaboration_comment_commands,
            comment_engagement=resolved.collaboration_comment_engagement,
            presence_commands=resolved.collaboration_presence_commands,
        ),
        project_management_financials=build_project_management_financials_desktop_api(
            finance_service=resolved.finance_service,
            finance_workspace_query=resolved.finance_workspace_query,
            finance_performance_query=resolved.finance_performance_query,
            finance_governance_commands=resolved.finance_governance_commands,
            cost_entry_service=resolved.cost_entry_service,
            commitment_service=resolved.commitment_service,
            billing_profile_service=resolved.billing_profile_service,
            billing_preparation_service=resolved.billing_preparation_service,
            report_sources=(
                ProjectReportSources(
                    kpi=resolved.project_kpi_report,
                    earned_value=resolved.earned_value_report,
                    schedule_variance=resolved.schedule_variance_report,
                    cost_breakdown=resolved.cost_breakdown_report,
                )
                if resolved.project_kpi_report is not None
                else None
            ),
            profitability_report=resolved.profitability_report,
        ),
        project_management_portfolio=build_project_management_portfolio_desktop_api(
            project_service=resolved.project_service,
            portfolio_intake_query=resolved.portfolio_intake_query,
            portfolio_intake_commands=resolved.portfolio_intake_commands,
            portfolio_template_query=resolved.portfolio_template_query,
            portfolio_template_commands=resolved.portfolio_template_commands,
            portfolio_scenario_query=resolved.portfolio_scenario_query,
            portfolio_scenario_commands=resolved.portfolio_scenario_commands,
            portfolio_dependency_query=resolved.portfolio_dependency_query,
            portfolio_dependency_commands=resolved.portfolio_dependency_commands,
            portfolio_executive_query=resolved.portfolio_executive_query,
            pool_service=resolved.pool_service,
        ),
        project_management_projects=build_project_management_projects_desktop_api(
            project_service=resolved.project_service,
            project_query=resolved.project_query,
            module_catalog_service=platform_dependencies.module_catalog_service,
            project_resource_service=resolved.project_resource_service,
            resource_query=resolved.resource_query,
            site_query=platform_dependencies.site_query,
            department_query=platform_dependencies.department_query,
        ),
        project_management_register=register_desktop_api,
        project_management_risk=register_desktop_api,
        project_management_resources=build_project_management_resources_desktop_api(
            resource_query=resolved.resource_query,
            resource_master_commands=resolved.resource_master_commands,
            resource_capability_commands=resolved.resource_capability_commands,
            resource_capability_query=resolved.resource_capability_query,
            resource_context_query=resolved.resource_context_query,
            module_catalog_service=platform_dependencies.module_catalog_service,
            employee_query=platform_dependencies.employee_query,
            workload_service=resolved.resource_workload_service,
            department_query=platform_dependencies.department_query,
            site_query=platform_dependencies.site_query,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            scheduling_engine=resolved.scheduling_engine,
            platform_calendar_api=platform_dependencies.platform_calendar_api,
            work_calendar_service=None,
            work_calendar_engine=resolved.work_calendar_engine,
            baseline_service=resolved.baseline_service,
            baseline_compare_report=resolved.baseline_compare_report,
            project_kpi_report=resolved.project_kpi_report,
            change_impact_service=change_impact_service,
            constraint_validator=constraint_validator,
            tenant_context_service=resolved.tenant_context_service,
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=resolved.project_service,
            task_service=resolved.task_service,
            task_workspace_query=resolved.task_workspace_query,
            task_detail_query=resolved.task_detail_query,
            task_dependency_diagnostics=resolved.task_dependency_diagnostics,
            task_assignment_commands=resolved.task_assignment_commands,
            task_time_entries=resolved.task_time_entries,
            module_catalog_service=platform_dependencies.module_catalog_service,
            project_resource_service=resolved.project_resource_service,
            resource_query=resolved.resource_query,
            reservation_service=platform_dependencies.reservation_service,
            assignment_skill_validator=resolved.assignment_skill_validator,
            schedule_change_impact_service=change_impact_service,
        ),
        project_management_timesheets=build_project_management_timesheets_desktop_api(
            project_service=resolved.project_service,
            task_lookup_query=resolved.task_lookup_query,
            task_assignment_commands=resolved.task_assignment_commands,
            module_catalog_service=platform_dependencies.module_catalog_service,
            resource_query=resolved.resource_query,
            timesheet_workspace_query=resolved.timesheet_workspace_query,
            timesheet_workspace_commands=resolved.timesheet_workspace_commands,
            timesheet_review_query=resolved.timesheet_review_query,
            time_entry_commands=resolved.time_entry_commands,
            time_entry_queries=resolved.time_entry_queries,
            timesheet_period_query=resolved.timesheet_period_query,
            timesheet_period_transitions=resolved.timesheet_period_transitions,
        ),
    )


__all__ = ["build_project_management_desktop_runtime_apis"]
