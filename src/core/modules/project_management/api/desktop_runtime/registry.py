from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    ProjectManagementDashboardDesktopApi,
    ProjectManagementFinancialsDesktopApi,
    ProjectManagementPortfolioDesktopApi,
    ProjectManagementProjectsDesktopApi,
    ProjectManagementRegisterDesktopApi,
    ProjectManagementResourcesDesktopApi,
    ProjectManagementSchedulingDesktopApi,
    ProjectManagementTasksDesktopApi,
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.platform.approval import ApprovalService
from src.core.platform.employee import EmployeeService
from src.core.platform.site import SiteService


@dataclass(frozen=True)
class ProjectManagementDesktopRuntimeApis:
    project_management_dashboard: ProjectManagementDashboardDesktopApi
    project_management_collaboration: ProjectManagementCollaborationDesktopApi
    project_management_financials: ProjectManagementFinancialsDesktopApi
    project_management_portfolio: ProjectManagementPortfolioDesktopApi
    project_management_projects: ProjectManagementProjectsDesktopApi
    project_management_register: ProjectManagementRegisterDesktopApi
    project_management_risk: ProjectManagementRegisterDesktopApi
    project_management_resources: ProjectManagementResourcesDesktopApi
    project_management_scheduling: ProjectManagementSchedulingDesktopApi
    project_management_tasks: ProjectManagementTasksDesktopApi
    project_management_timesheets: ProjectManagementTimesheetsDesktopApi


@dataclass(frozen=True)
class ProjectManagementDesktopRuntimePlatformDependencies:
    employee_service: EmployeeService
    site_service: SiteService
    approval_service: ApprovalService
    procurement_service: object | None
    reservation_service: object | None


__all__ = [
    "ProjectManagementDesktopRuntimeApis",
    "ProjectManagementDesktopRuntimePlatformDependencies",
]
