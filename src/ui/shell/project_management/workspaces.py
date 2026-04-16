from __future__ import annotations

from ui.modules.project_management.calendar.tab import CalendarTab
from ui.modules.project_management.collaboration.tab import CollaborationTab
from ui.modules.project_management.cost.tab import CostTab
from ui.modules.project_management.dashboard.tab import DashboardTab
from ui.modules.project_management.governance.tab import GovernanceTab
from ui.modules.project_management.portfolio.tab import PortfolioTab
from ui.modules.project_management.project.tab import ProjectTab
from ui.modules.project_management.register.tab import RegisterTab
from ui.modules.project_management.report.tab import ReportTab
from ui.modules.project_management.resource.tab import ResourceTab
from ui.modules.project_management.task.tab import TaskTab
from src.ui.shell.common import (
    PROJECT_MANAGEMENT_MODULE_CODE,
    PROJECT_MANAGEMENT_MODULE_LABEL,
    ShellWorkspaceContext,
    WorkspaceDefinition,
    has_any_permission,
    has_permission,
)


def build_project_management_workspace_definitions(
    context: ShellWorkspaceContext,
) -> list[WorkspaceDefinition]:
    if not context.project_management_enabled:
        return []

    services = context.services
    definitions: list[WorkspaceDefinition] = []

    if has_permission(context.user_session, "project.read") or has_permission(context.user_session, "report.view"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Overview",
                label="Dashboard",
                widget=DashboardTab(
                    dashboard_service=services["dashboard_service"],
                    project_service=services["project_service"],
                    baseline_service=services["baseline_service"],
                    settings_store=context.settings_store,
                    user_session=context.user_session,
                ),
            )
        )

    if has_permission(context.user_session, "task.read"):
        definitions.extend(
            [
                WorkspaceDefinition(
                    module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                    module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                    group_label="Execution",
                    label="Projects",
                    widget=ProjectTab(
                        project_service=services["project_service"],
                        task_service=services["task_service"],
                        reporting_service=services["reporting_service"],
                        project_resource_service=services["project_resource_service"],
                        resource_service=services["resource_service"],
                        data_import_service=services["data_import_service"],
                        user_session=context.user_session,
                    ),
                ),
                WorkspaceDefinition(
                    module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                    module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                    group_label="Execution",
                    label="Tasks",
                    widget=TaskTab(
                        project_service=services["project_service"],
                        task_service=services["task_service"],
                        resource_service=services["resource_service"],
                        project_resource_service=services["project_resource_service"],
                        timesheet_service=services.get("timesheet_service"),
                        collaboration_service=services.get("collaboration_service"),
                        settings_store=context.settings_store,
                        user_session=context.user_session,
                    ),
                ),
                WorkspaceDefinition(
                    module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                    module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                    group_label="Execution",
                    label="Calendar",
                    widget=CalendarTab(
                        work_calendar_service=services["work_calendar_service"],
                        work_calendar_engine=services["work_calendar_engine"],
                        scheduling_engine=services["scheduling_engine"],
                        project_service=services["project_service"],
                        task_service=services["task_service"],
                        user_session=context.user_session,
                    ),
                ),
            ]
        )

    if has_permission(context.user_session, "collaboration.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Execution",
                label="Collaboration",
                widget=CollaborationTab(
                    collaboration_service=services["collaboration_service"],
                    parent=context.parent,
                ),
            )
        )

    if has_permission(context.user_session, "resource.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Operations",
                label="Resources",
                widget=ResourceTab(
                    resource_service=services["resource_service"],
                    employee_service=services.get("employee_service"),
                    user_session=context.user_session,
                ),
            )
        )

    if has_permission(context.user_session, "cost.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Operations",
                label="Costs",
                widget=CostTab(
                    project_service=services["project_service"],
                    task_service=services["task_service"],
                    cost_service=services["cost_service"],
                    reporting_service=services["reporting_service"],
                    resource_service=services["resource_service"],
                    user_session=context.user_session,
                ),
            )
        )

    if has_permission(context.user_session, "register.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Control",
                label="Register",
                widget=RegisterTab(
                    register_service=services["register_service"],
                    project_service=services["project_service"],
                    user_session=context.user_session,
                ),
            )
        )

    if has_permission(context.user_session, "report.view"):
        definitions.extend(
            [
                WorkspaceDefinition(
                    module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                    module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                    group_label="Overview",
                    label="Reports",
                    widget=ReportTab(
                        project_service=services["project_service"],
                        reporting_service=services["reporting_service"],
                        task_service=services["task_service"],
                        finance_service=services.get("finance_service"),
                        user_session=context.user_session,
                    ),
                ),
            ]
        )

    if has_permission(context.user_session, "portfolio.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Overview",
                label="Portfolio",
                widget=PortfolioTab(
                    portfolio_service=services["portfolio_service"],
                    project_service=services["project_service"],
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_any_permission(
        context.user_session,
        "settings.manage",
        "timesheet.approve",
    ):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Control",
                label="Governance",
                widget=GovernanceTab(
                    approval_service=services["approval_service"],
                    project_service=services["project_service"],
                    task_service=services["task_service"],
                    cost_service=services["cost_service"],
                    timesheet_service=services.get("timesheet_service"),
                    user_session=context.user_session,
                ),
            )
        )

    return definitions


__all__ = ["build_project_management_workspace_definitions"]
