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
        project_service=resolved.project_query,
        register_query=resolved.register_query,
        register_lifecycle_commands=resolved.register_lifecycle_commands,
        module_catalog_service=platform_dependencies.module_catalog_service,
    )
    constraint_validator = (
        ConstraintValidator(resolved.work_calendar_engine)
        if resolved.work_calendar_engine is not None
        else None
    )
    return ProjectManagementDesktopRuntimeApis(
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=resolved.project_query,
            project_dashboard=resolved.project_dashboard_query,
            portfolio_dashboard=resolved.portfolio_dashboard_query,
            baseline_query=resolved.baseline_query,
            earned_value_report=resolved.earned_value_report,
            collaboration_inbox_query=resolved.collaboration_inbox_query,
            approval_queries=platform_dependencies.approval_queries,
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
            finance_snapshot_query=resolved.finance_snapshot_query,
            finance_workspace_query=resolved.finance_workspace_query,
            finance_performance_query=resolved.finance_performance_query,
            finance_governance_commands=resolved.finance_governance_commands,
            cost_entry_query=resolved.cost_entry_query,
            commitment_query=resolved.commitment_query,
            billing_profile_query=resolved.billing_profile_query,
            billing_preparation_query=resolved.billing_preparation_query,
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
            project_service=resolved.project_query,
            portfolio_intake_query=resolved.portfolio_intake_query,
            portfolio_intake_commands=resolved.portfolio_intake_commands,
            portfolio_template_query=resolved.portfolio_template_query,
            portfolio_template_commands=resolved.portfolio_template_commands,
            portfolio_scenario_query=resolved.portfolio_scenario_query,
            portfolio_scenario_commands=resolved.portfolio_scenario_commands,
            portfolio_dependency_query=resolved.portfolio_dependency_query,
            portfolio_dependency_commands=resolved.portfolio_dependency_commands,
            portfolio_executive_query=resolved.portfolio_executive_query,
        ),
        project_management_projects=build_project_management_projects_desktop_api(project_create=resolved.project_create, project_update=resolved.project_update, project_status=resolved.project_status, project_deletion=resolved.project_deletion, project_query=resolved.project_query, project_resource_query=resolved.project_resource_query, project_resource_commands=resolved.project_resource_commands, resource_query=resolved.resource_query),
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
            workload_service=resolved.resource_workload_query,
            department_query=platform_dependencies.department_query,
            site_query=platform_dependencies.site_query,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=resolved.project_query,
            task_lookup_query=resolved.task_lookup_query,
            task_detail_query=resolved.task_detail_query,
            task_hierarchy_query=resolved.task_hierarchy_query,
            task_dependency_query=resolved.task_dependency_query,
            task_dependency_commands=resolved.task_dependency_commands,
            task_leveling_commands=resolved.task_leveling_commands,
            scheduling_engine=resolved.scheduling_engine,
            platform_calendar_api=platform_dependencies.platform_calendar_api,
            work_calendar_service=None,
            work_calendar_engine=resolved.work_calendar_engine,
            project_calendar_adapter=resolved.project_calendar_adapter,
            baseline_query=resolved.baseline_query,
            baseline_compare_report=resolved.baseline_compare_report,
            baseline_commands=resolved.baseline_commands,
            project_kpi_report=resolved.project_kpi_report,
            change_impact_service=resolved.schedule_change_impact_query,
            constraint_validator=constraint_validator,
            tenant_context_service=resolved.tenant_context_service,
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=resolved.project_query,
            task_lookup_query=resolved.task_lookup_query,
            task_hierarchy_query=resolved.task_hierarchy_query,
            task_deletion_commands=resolved.task_deletion_commands,
            task_progress_commands=resolved.task_progress_commands,
            task_hierarchy_commands=resolved.task_hierarchy_commands,
            task_constraint_commands=resolved.task_constraint_commands,
            task_lifecycle_commands=resolved.task_lifecycle_commands,
            task_dependency_commands=resolved.task_dependency_commands,
            task_dependency_query=resolved.task_dependency_query,
            task_workspace_query=resolved.task_workspace_query,
            task_detail_query=resolved.task_detail_query,
            task_dependency_diagnostics=resolved.task_dependency_diagnostics,
            task_assignment_commands=resolved.task_assignment_commands,
            task_time_entries=resolved.task_time_entries,
            module_catalog_service=platform_dependencies.module_catalog_service,
            project_resource_query=resolved.project_resource_query,
            resource_query=resolved.resource_query,
            reservation_service=platform_dependencies.reservation_service,
            assignment_skill_validator=resolved.assignment_skill_validator,
            schedule_change_impact_query=resolved.schedule_change_impact_query,
        ),
        project_management_timesheets=build_project_management_timesheets_desktop_api(
            project_service=resolved.project_query,
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
