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
from src.core.modules.project_management.gateway.task.reservation import (
    TaskReservationGateway,
)
from src.core.platform.application.master_data.department import (
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.employee import EmployeeQueryHandler
from src.core.platform.application.master_data.site import SiteQueryHandler
from src.core.platform.contract.port.approval.capabilities import ApprovalQueries
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


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
    employee_query: EmployeeQueryHandler
    site_query: SiteQueryHandler
    department_query: DepartmentQueryHandler | None
    approval_queries: ApprovalQueries
    module_catalog_service: SupportsModuleEntitlements | None = None
    reservation_service: TaskReservationGateway | None = None
    platform_calendar_api: object | None = None


__all__ = [
    "ProjectManagementDesktopRuntimeApis",
    "ProjectManagementDesktopRuntimePlatformDependencies",
]
