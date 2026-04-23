from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from src.api.desktop.platform import (
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
)
from src.application.runtime.platform_runtime import resolve_platform_runtime_application_service
from src.core.platform.auth import UserSessionContext
from src.core.platform.org import DepartmentService, EmployeeService, SiteService
from src.ui.platform.settings import MainWindowSettingsStore

PLATFORM_MODULE_CODE = "platform"
PLATFORM_MODULE_LABEL = "Platform"
INVENTORY_PROCUREMENT_MODULE_CODE = "inventory_procurement"
INVENTORY_PROCUREMENT_MODULE_LABEL = "Inventory & Procurement"
MAINTENANCE_MANAGEMENT_MODULE_CODE = "maintenance_management"
MAINTENANCE_MANAGEMENT_MODULE_LABEL = "Maintenance Management"
PROJECT_MANAGEMENT_MODULE_CODE = "project_management"
PROJECT_MANAGEMENT_MODULE_LABEL = "Project Management"

ScopeOptionsLoader = Callable[[], list[tuple[str, str]]]


@dataclass(frozen=True)
class WorkspaceDefinition:
    module_code: str
    module_label: str
    group_label: str
    label: str
    widget: QWidget


@dataclass(frozen=True)
class ShellWorkspaceContext:
    services: dict[str, object]
    settings_store: MainWindowSettingsStore
    user_session: UserSessionContext | None
    parent: QWidget | None
    platform_runtime_application_service: object | None
    platform_runtime_desktop_api: PlatformRuntimeDesktopApi | None
    platform_site_desktop_api: PlatformSiteDesktopApi | None
    platform_department_desktop_api: PlatformDepartmentDesktopApi | None
    platform_employee_desktop_api: PlatformEmployeeDesktopApi | None
    project_management_enabled: bool
    inventory_procurement_enabled: bool
    maintenance_management_enabled: bool
    access_scope_type_choices: tuple[tuple[str, str], ...]
    access_scope_option_loaders: dict[str, ScopeOptionsLoader]
    access_scope_disabled_hints: dict[str, str]


def build_shell_workspace_context(
    *,
    services: dict[str, object],
    settings_store: MainWindowSettingsStore,
    user_session: UserSessionContext | None,
    parent: QWidget | None = None,
) -> ShellWorkspaceContext:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get("platform_runtime_application_service"),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
    )
    configured_platform_runtime_api = services.get("desktop_platform_runtime_api")
    platform_runtime_desktop_api = (
        configured_platform_runtime_api
        if isinstance(configured_platform_runtime_api, PlatformRuntimeDesktopApi)
        else None
    )
    if platform_runtime_desktop_api is None and platform_runtime_application_service is not None:
        platform_runtime_desktop_api = PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service
        )
    configured_platform_site_api = services.get("desktop_platform_site_api")
    platform_site_desktop_api = (
        configured_platform_site_api
        if isinstance(configured_platform_site_api, PlatformSiteDesktopApi)
        else None
    )
    configured_platform_department_api = services.get("desktop_platform_department_api")
    platform_department_desktop_api = (
        configured_platform_department_api
        if isinstance(configured_platform_department_api, PlatformDepartmentDesktopApi)
        else None
    )
    configured_platform_employee_api = services.get("desktop_platform_employee_api")
    platform_employee_desktop_api = (
        configured_platform_employee_api
        if isinstance(configured_platform_employee_api, PlatformEmployeeDesktopApi)
        else None
    )
    site_service = services.get("site_service")
    department_service = services.get("department_service")
    employee_service = services.get("employee_service")
    if platform_site_desktop_api is None and isinstance(site_service, SiteService):
        platform_site_desktop_api = PlatformSiteDesktopApi(site_service=site_service)
    if platform_department_desktop_api is None and isinstance(department_service, DepartmentService):
        platform_department_desktop_api = PlatformDepartmentDesktopApi(
            department_service=department_service,
        )
    if platform_employee_desktop_api is None and isinstance(employee_service, EmployeeService):
        platform_employee_desktop_api = PlatformEmployeeDesktopApi(employee_service=employee_service)
    project_management_enabled = not bool(
        platform_runtime_application_service is not None
        and hasattr(platform_runtime_application_service, "is_enabled")
        and not platform_runtime_application_service.is_enabled(PROJECT_MANAGEMENT_MODULE_CODE)
    )
    inventory_procurement_enabled = not bool(
        platform_runtime_application_service is not None
        and hasattr(platform_runtime_application_service, "is_enabled")
        and not platform_runtime_application_service.is_enabled(INVENTORY_PROCUREMENT_MODULE_CODE)
    )
    maintenance_management_enabled = not bool(
        platform_runtime_application_service is not None
        and hasattr(platform_runtime_application_service, "is_enabled")
        and not platform_runtime_application_service.is_enabled(MAINTENANCE_MANAGEMENT_MODULE_CODE)
    )

    access_scope_type_choices: list[tuple[str, str]] = [("Project", "project")]
    access_scope_option_loaders: dict[str, ScopeOptionsLoader] = {}
    access_scope_disabled_hints: dict[str, str] = {}
    if platform_site_desktop_api is not None and has_any_permission(user_session, "site.read", "settings.manage"):
        access_scope_type_choices.append(("Site", "site"))
        access_scope_option_loaders["site"] = lambda: _load_site_scope_options(platform_site_desktop_api)
    inventory_service = services.get("inventory_service")
    if inventory_procurement_enabled and has_any_permission(user_session, "inventory.read", "inventory.manage"):
        if inventory_service is not None and hasattr(inventory_service, "list_storerooms"):
            access_scope_type_choices.append(("Storeroom", "storeroom"))
            access_scope_option_loaders["storeroom"] = lambda: [
                (f"{storeroom.storeroom_code} - {storeroom.name}", storeroom.id)
                for storeroom in inventory_service.list_storerooms()
            ]
            access_scope_disabled_hints["storeroom"] = (
                "Inventory & Procurement is disabled. Enable it in Modules before managing storeroom-scoped access."
            )

    return ShellWorkspaceContext(
        services=services,
        settings_store=settings_store,
        user_session=user_session,
        parent=parent,
        platform_runtime_application_service=platform_runtime_application_service,
        platform_runtime_desktop_api=platform_runtime_desktop_api,
        platform_site_desktop_api=platform_site_desktop_api,
        platform_department_desktop_api=platform_department_desktop_api,
        platform_employee_desktop_api=platform_employee_desktop_api,
        project_management_enabled=project_management_enabled,
        inventory_procurement_enabled=inventory_procurement_enabled,
        maintenance_management_enabled=maintenance_management_enabled,
        access_scope_type_choices=tuple(access_scope_type_choices),
        access_scope_option_loaders=access_scope_option_loaders,
        access_scope_disabled_hints=access_scope_disabled_hints,
    )


def has_permission(user_session: UserSessionContext | None, permission_code: str) -> bool:
    return bool(user_session is not None and user_session.has_permission(permission_code))


def has_any_permission(
    user_session: UserSessionContext | None,
    *permission_codes: str,
) -> bool:
    return any(has_permission(user_session, permission_code) for permission_code in permission_codes)


def _load_site_scope_options(platform_site_desktop_api: PlatformSiteDesktopApi) -> list[tuple[str, str]]:
    result = platform_site_desktop_api.list_sites(active_only=None)
    if not result.ok or result.data is None:
        return []
    return [
        (f"{site.site_code} - {site.name}", site.id)
        for site in result.data
    ]


__all__ = [
    "INVENTORY_PROCUREMENT_MODULE_CODE",
    "INVENTORY_PROCUREMENT_MODULE_LABEL",
    "MAINTENANCE_MANAGEMENT_MODULE_CODE",
    "MAINTENANCE_MANAGEMENT_MODULE_LABEL",
    "PLATFORM_MODULE_CODE",
    "PLATFORM_MODULE_LABEL",
    "PROJECT_MANAGEMENT_MODULE_CODE",
    "PROJECT_MANAGEMENT_MODULE_LABEL",
    "ShellWorkspaceContext",
    "WorkspaceDefinition",
    "build_shell_workspace_context",
    "has_any_permission",
    "has_permission",
]
