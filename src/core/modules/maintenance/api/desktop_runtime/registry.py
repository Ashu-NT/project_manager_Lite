from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetsDesktopApi,
    MaintenanceDashboardDesktopApi,
    MaintenancePlannerDesktopApi,
    MaintenancePreventiveDesktopApi,
    MaintenanceReliabilityDesktopApi,
    MaintenanceWorkOrdersDesktopApi,
    MaintenanceWorkRequestsDesktopApi,
    MaintenanceWorkspaceDesktopApi,
)
from src.core.platform.employee import EmployeeService
from src.core.platform.party import PartyService
from src.core.platform.site import SiteService


@dataclass(frozen=True)
class MaintenanceDesktopRuntimeApis:
    maintenance_workspaces: MaintenanceWorkspaceDesktopApi
    maintenance_assets: MaintenanceAssetsDesktopApi
    maintenance_dashboard: MaintenanceDashboardDesktopApi
    maintenance_planner: MaintenancePlannerDesktopApi
    maintenance_preventive: MaintenancePreventiveDesktopApi
    maintenance_reliability: MaintenanceReliabilityDesktopApi
    maintenance_work_requests: MaintenanceWorkRequestsDesktopApi
    maintenance_work_orders: MaintenanceWorkOrdersDesktopApi


@dataclass(frozen=True)
class MaintenanceDesktopRuntimePlatformDependencies:
    site_service: SiteService
    party_service: PartyService
    employee_service: EmployeeService


__all__ = [
    "MaintenanceDesktopRuntimeApis",
    "MaintenanceDesktopRuntimePlatformDependencies",
]
