from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from core.services.auth import UserSessionContext
from ui.access.tab import AccessTab
from ui.admin.audit_tab import AuditLogTab
from ui.admin.users_tab import UserAdminTab
from ui.calendar.tab import CalendarTab
from ui.collaboration.tab import CollaborationTab
from ui.cost.tab import CostTab
from ui.dashboard.tab import DashboardTab
from ui.governance.tab import GovernanceTab
from ui.portfolio.tab import PortfolioTab
from ui.project.tab import ProjectTab
from ui.register.tab import RegisterTab
from ui.report.tab import ReportTab
from ui.resource.tab import ResourceTab
from ui.settings import MainWindowSettingsStore
from ui.support.tab import SupportTab
from ui.task.tab import TaskTab


@dataclass(frozen=True)
class WorkspaceDefinition:
    section: str
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

    if _has_permission(user_session, "project.read") or _has_permission(user_session, "report.view"):
        definitions.append(
            WorkspaceDefinition(
                section="Home",
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
                section="Delivery",
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

    if _has_permission(user_session, "resource.read"):
        definitions.append(
            WorkspaceDefinition(
                section="Delivery",
                label="Resources",
                widget=ResourceTab(
                    resource_service=services["resource_service"],
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "project.read"):
        definitions.append(
            WorkspaceDefinition(
                section="Delivery",
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
                section="Delivery",
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

    if _has_permission(user_session, "cost.read"):
        definitions.append(
            WorkspaceDefinition(
                section="Delivery",
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

    if _has_permission(user_session, "collaboration.read"):
        definitions.append(
            WorkspaceDefinition(
                section="Team",
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
                section="Control",
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
                section="Control",
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
                section="Control",
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
                section="Control",
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

    if _has_permission(user_session, "auth.manage"):
        definitions.append(
            WorkspaceDefinition(
                section="Admin",
                label="Users",
                widget=UserAdminTab(
                    auth_service=services["auth_service"],
                    user_session=user_session,
                ),
            )
        )

    if _has_permission(user_session, "access.manage"):
        definitions.append(
            WorkspaceDefinition(
                section="Admin",
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
                section="Admin",
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
                section="Admin",
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
