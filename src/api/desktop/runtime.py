from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.api.desktop.platform import (
    PlatformAccessDesktopApi,
    PlatformApprovalDesktopApi,
    PlatformAuditDesktopApi,
    PlatformSupportDesktopApi,
)
from src.api.desktop.platform import (
    PlatformDocumentDesktopApi,
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformUserDesktopApi,
)
from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
    ProjectManagementProjectsDesktopApi,
    ProjectManagementResourcesDesktopApi,
    ProjectManagementSchedulingDesktopApi,
    ProjectManagementTasksDesktopApi,
    build_project_management_dashboard_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.application.runtime.platform_runtime import (
    PlatformRuntimeApplicationService,
    resolve_platform_runtime_application_service,
)
from src.core.modules.project_management.application.scheduling.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
    WorkCalendarEngine,
    WorkCalendarService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.platform.access import AccessControlService
from src.core.platform.approval import ApprovalService
from src.core.platform.audit import AuditService
from src.core.platform.auth.application import AuthService
from src.core.platform.documents import DocumentService
from src.core.platform.org import DepartmentService, EmployeeService, SiteService
from src.core.platform.party import PartyService


@dataclass(frozen=True)
class DesktopApiRegistry:
    platform_runtime: PlatformRuntimeDesktopApi
    platform_site: PlatformSiteDesktopApi
    platform_department: PlatformDepartmentDesktopApi
    platform_employee: PlatformEmployeeDesktopApi
    platform_access: PlatformAccessDesktopApi
    platform_approval: PlatformApprovalDesktopApi
    platform_audit: PlatformAuditDesktopApi
    platform_document: PlatformDocumentDesktopApi
    platform_party: PlatformPartyDesktopApi
    platform_support: PlatformSupportDesktopApi
    platform_user: PlatformUserDesktopApi
    project_management_dashboard: ProjectManagementDashboardDesktopApi
    project_management_projects: ProjectManagementProjectsDesktopApi
    project_management_resources: ProjectManagementResourcesDesktopApi
    project_management_scheduling: ProjectManagementSchedulingDesktopApi
    project_management_tasks: ProjectManagementTasksDesktopApi


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get("platform_runtime_application_service"),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
    )
    if not isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
        raise RuntimeError("Platform runtime application service is not configured.")
    site_service = services.get("site_service")
    if not isinstance(site_service, SiteService):
        raise RuntimeError("Platform site service is not configured.")
    department_service = services.get("department_service")
    if not isinstance(department_service, DepartmentService):
        raise RuntimeError("Platform department service is not configured.")
    employee_service = services.get("employee_service")
    if not isinstance(employee_service, EmployeeService):
        raise RuntimeError("Platform employee service is not configured.")
    access_service = services.get("access_service")
    if not isinstance(access_service, AccessControlService):
        raise RuntimeError("Platform access service is not configured.")
    approval_service = services.get("approval_service")
    if not isinstance(approval_service, ApprovalService):
        raise RuntimeError("Platform approval service is not configured.")
    audit_service = services.get("audit_service")
    if not isinstance(audit_service, AuditService):
        raise RuntimeError("Platform audit service is not configured.")
    document_service = services.get("document_service")
    if not isinstance(document_service, DocumentService):
        raise RuntimeError("Platform document service is not configured.")
    party_service = services.get("party_service")
    if not isinstance(party_service, PartyService):
        raise RuntimeError("Platform party service is not configured.")
    auth_service = services.get("auth_service")
    if not isinstance(auth_service, AuthService):
        raise RuntimeError("Platform auth service is not configured.")
    project_service = services.get("project_service")
    task_service = services.get("task_service")
    resource_service = services.get("resource_service")
    cost_service = services.get("cost_service")
    baseline_service = services.get("baseline_service")
    inventory_service = services.get("inventory_service")
    pm_project_service = (
        project_service if isinstance(project_service, ProjectService) else None
    )
    pm_resource_service = (
        resource_service if isinstance(resource_service, ResourceService) else None
    )
    pm_task_service = task_service if isinstance(task_service, TaskService) else None
    pm_scheduling_engine = services.get("scheduling_engine")
    if not isinstance(pm_scheduling_engine, SchedulingEngine):
        pm_scheduling_engine = None
    pm_work_calendar_service = services.get("work_calendar_service")
    if not isinstance(pm_work_calendar_service, WorkCalendarService):
        pm_work_calendar_service = None
    pm_work_calendar_engine = services.get("work_calendar_engine")
    if not isinstance(pm_work_calendar_engine, WorkCalendarEngine):
        pm_work_calendar_engine = None
    pm_dashboard_service = services.get("dashboard_service")
    if not isinstance(pm_dashboard_service, DashboardService):
        pm_dashboard_service = None
    pm_baseline_service = (
        baseline_service if isinstance(baseline_service, BaselineService) else None
    )
    pm_reporting_service = services.get("reporting_service")
    if not isinstance(pm_reporting_service, ReportingService):
        pm_reporting_service = None
    platform_site_api = PlatformSiteDesktopApi(site_service=site_service)
    access_scope_type_choices: list[tuple[str, str]] = []
    access_scope_option_loaders: dict[str, object] = {}
    access_scope_disabled_hints: dict[str, str] = {}
    if project_service is not None and hasattr(project_service, "list_projects"):
        access_scope_type_choices.append(("Project", "project"))
        access_scope_option_loaders["project"] = lambda: [
            (project.name, project.id)
            for project in project_service.list_projects()
        ]
    access_scope_type_choices.append(("Site", "site"))
    access_scope_option_loaders["site"] = lambda: _load_site_scope_options(platform_site_api)
    if inventory_service is not None and hasattr(inventory_service, "list_storerooms"):
        access_scope_type_choices.append(("Storeroom", "storeroom"))
        access_scope_option_loaders["storeroom"] = lambda: [
            (f"{storeroom.storeroom_code} - {storeroom.name}", storeroom.id)
            for storeroom in inventory_service.list_storerooms()
        ]
    return DesktopApiRegistry(
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service,
        ),
        platform_site=platform_site_api,
        platform_department=PlatformDepartmentDesktopApi(
            department_service=department_service,
        ),
        platform_employee=PlatformEmployeeDesktopApi(
            employee_service=employee_service,
        ),
        platform_access=PlatformAccessDesktopApi(
            access_service=access_service,
            scope_type_choices=tuple(access_scope_type_choices),
            scope_option_loaders=access_scope_option_loaders,
            scope_disabled_hints=access_scope_disabled_hints,
        ),
        platform_approval=PlatformApprovalDesktopApi(
            approval_service=approval_service,
        ),
        platform_audit=PlatformAuditDesktopApi(
            audit_service=audit_service,
            project_service=project_service,
            task_service=task_service,
            resource_service=resource_service,
            cost_service=cost_service,
            baseline_service=baseline_service,
        ),
        platform_document=PlatformDocumentDesktopApi(
            document_service=document_service,
        ),
        platform_party=PlatformPartyDesktopApi(
            party_service=party_service,
        ),
        platform_support=PlatformSupportDesktopApi(),
        platform_user=PlatformUserDesktopApi(
            auth_service=auth_service,
        ),
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=pm_project_service,
            dashboard_service=pm_dashboard_service,
            baseline_service=pm_baseline_service,
        ),
        project_management_projects=build_project_management_projects_desktop_api(
            project_service=pm_project_service,
        ),
        project_management_resources=build_project_management_resources_desktop_api(
            resource_service=pm_resource_service,
            employee_service=employee_service,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
            scheduling_engine=pm_scheduling_engine,
            work_calendar_service=pm_work_calendar_service,
            work_calendar_engine=pm_work_calendar_engine,
            baseline_service=pm_baseline_service,
            reporting_service=pm_reporting_service,
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
        ),
    )


def _load_site_scope_options(platform_site_desktop_api: PlatformSiteDesktopApi) -> list[tuple[str, str]]:
    result = platform_site_desktop_api.list_sites(active_only=None)
    if not result.ok or result.data is None:
        return []
    return [
        (f"{site.site_code} - {site.name}", site.id)
        for site in result.data
    ]


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]
