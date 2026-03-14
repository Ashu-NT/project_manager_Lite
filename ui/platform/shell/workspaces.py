from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from core.platform.auth import UserSessionContext
from ui.platform.admin.access.tab import AccessTab
from ui.platform.admin.audit_tab import AuditLogTab
from ui.platform.admin.employees_tab import EmployeeAdminTab
from ui.platform.admin.users_tab import UserAdminTab
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
from ui.platform.settings import MainWindowSettingsStore
from ui.platform.admin.support.tab import SupportTab
from ui.platform.shell.home import PlatformHomeTab
from ui.modules.project_management.task.tab import TaskTab

PLATFORM_MODULE_CODE = "platform"
PLATFORM_MODULE_LABEL = "Platform"
PROJECT_MANAGEMENT_MODULE_CODE = "project_management"
PROJECT_MANAGEMENT_MODULE_LABEL = "Project Management"


@dataclass(frozen=True)
class WorkspaceDefinition:
    module_code: str
    module_label: str
    group_label: str
    label: str
    widget: QWidget


def build_workspace_definitions(
    *,
    services: dict[str, object],
    settings_store: MainWindowSettingsStore,
    user_session: UserSessionContext | None,
    parent: QWidget | None = None,
) -> list[WorkspaceDefinition]:
    definitions: list[WorkspaceDefinition] = []
    module_catalog_service = services.get("module_catalog_service")

    if bool(user_session is not None and user_session.is_authenticated()):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Shared Services",
                label="Home",
                widget=PlatformHomeTab(
                    module_catalog_service=module_catalog_service,  # type: ignore[arg-type]
                    user_session=user_session,
                    parent=parent,
                ),
            )
        )

    if _has_permission(user_session, "project.read") or _has_permission(user_session, "report.view"):
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
                    settings_store=settings_store,
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "task.read"):
        definitions.append(
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
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "task.read"):
        definitions.append(
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
                    collaboration_store=services["task_collaboration_store"],
                    collaboration_service=services.get("collaboration_service"),
                    settings_store=settings_store,
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "resource.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Operations",
                label="Resources",
                widget=ResourceTab(
                    resource_service=services["resource_service"],
                    employee_service=services.get("employee_service"),
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "cost.read"):
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
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "task.read"):
        definitions.append(
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
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "collaboration.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Execution",
                label="Collaboration",
                widget=CollaborationTab(
                    collaboration_service=services["collaboration_service"],
                    parent=parent,
                ),
            )
        )

    if _has_permission(user_session, "register.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Control",
                label="Register",
                widget=RegisterTab(
                    register_service=services["register_service"],
                    project_service=services["project_service"],
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "report.view"):
        definitions.append(
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
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "portfolio.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PROJECT_MANAGEMENT_MODULE_CODE,
                module_label=PROJECT_MANAGEMENT_MODULE_LABEL,
                group_label="Overview",
                label="Portfolio",
                widget=PortfolioTab(
                    portfolio_service=services["portfolio_service"],
                    project_service=services["project_service"],
                    user_session=user_session,
                    parent=parent,
                ),
            )
        )

    if _has_permission(user_session, "approval.request") or _has_permission(
        user_session, "approval.decide"
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
                    user_session=user_session,
                ),
            )
        )

    if _has_any_permission(user_session, "auth.read", "auth.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Users",
                widget=UserAdminTab(
                    auth_service=services["auth_service"],
                    user_session=user_session,
                ),
            )
        )

    if _has_any_permission(user_session, "employee.read", "employee.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Employees",
                widget=EmployeeAdminTab(
                    employee_service=services["employee_service"],
                    user_session=user_session,
                    parent=parent,
                ),
            )
        )

    if _has_any_permission(user_session, "access.manage", "security.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Access",
                widget=AccessTab(
                    access_service=services["access_service"],
                    auth_service=services["auth_service"],
                    project_service=services["project_service"],
                    user_session=user_session,
                    parent=parent,
                ),
            )
        )

    if _has_permission(user_session, "audit.read"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Control",
                label="Audit",
                widget=AuditLogTab(
                    audit_service=services["audit_service"],
                    project_service=services["project_service"],
                    task_service=services["task_service"],
                    resource_service=services["resource_service"],
                    cost_service=services["cost_service"],
                    baseline_service=services["baseline_service"],
                ),
            )
        )

    if _has_permission(user_session, "support.manage"):
        definitions.append(
            WorkspaceDefinition(
                module_code=PLATFORM_MODULE_CODE,
                module_label=PLATFORM_MODULE_LABEL,
                group_label="Administration",
                label="Support",
                widget=SupportTab(
                    settings_store=settings_store,
                    user_session=user_session,
                ),
            )
        )

    return definitions


def _has_permission(user_session: UserSessionContext | None, permission_code: str) -> bool:
    return bool(user_session is not None and user_session.has_permission(permission_code))


def _has_any_permission(
    user_session: UserSessionContext | None,
    *permission_codes: str,
) -> bool:
    return any(_has_permission(user_session, permission_code) for permission_code in permission_codes)
