from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.maintenance.api.desktop import (
    build_maintenance_assets_desktop_api,
    build_maintenance_dashboard_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_preventive_desktop_api,
    build_maintenance_reliability_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
    build_maintenance_workspace_desktop_api,
)
from src.core.modules.maintenance.api.desktop_runtime.registry import (
    MaintenanceDesktopRuntimeApis,
    MaintenanceDesktopRuntimePlatformDependencies,
)
from src.core.modules.maintenance.api.desktop_runtime.service_resolver import (
    resolve_maintenance_desktop_runtime_services,
)


def build_maintenance_desktop_runtime_apis(
    services: Mapping[str, object],
    platform_dependencies: MaintenanceDesktopRuntimePlatformDependencies,
) -> MaintenanceDesktopRuntimeApis:
    resolved = resolve_maintenance_desktop_runtime_services(services)
    return MaintenanceDesktopRuntimeApis(
        maintenance_workspaces=build_maintenance_workspace_desktop_api(),
        maintenance_assets=build_maintenance_assets_desktop_api(
            location_service=resolved.location_service,
            system_service=resolved.system_service,
            asset_service=resolved.asset_service,
            component_service=resolved.component_service,
            site_service=platform_dependencies.site_service,
            party_service=platform_dependencies.party_service,
        ),
        maintenance_dashboard=build_maintenance_dashboard_desktop_api(
            reliability_service=resolved.reliability_service,
            site_service=platform_dependencies.site_service,
            asset_service=resolved.asset_service,
            location_service=resolved.location_service,
            system_service=resolved.system_service,
        ),
        maintenance_planner=build_maintenance_planner_desktop_api(
            site_service=platform_dependencies.site_service,
            asset_service=resolved.asset_service,
            system_service=resolved.system_service,
            work_request_service=resolved.work_request_service,
            work_order_service=resolved.work_order_service,
            material_requirement_service=resolved.material_requirement_service,
            preventive_plan_service=resolved.preventive_plan_service,
            preventive_generation_service=resolved.preventive_generation_service,
            reliability_service=resolved.reliability_service,
            sensor_exception_service=resolved.sensor_exception_service,
        ),
        maintenance_preventive=build_maintenance_preventive_desktop_api(
            site_service=platform_dependencies.site_service,
            asset_service=resolved.asset_service,
            component_service=resolved.component_service,
            system_service=resolved.system_service,
            sensor_service=resolved.sensor_service,
            task_template_service=resolved.task_template_service,
            task_step_template_service=resolved.task_step_template_service,
            preventive_plan_service=resolved.preventive_plan_service,
            preventive_plan_task_service=resolved.preventive_plan_task_service,
            preventive_generation_service=resolved.preventive_generation_service,
        ),
        maintenance_reliability=build_maintenance_reliability_desktop_api(
            reliability_service=resolved.reliability_service,
            failure_code_service=resolved.failure_code_service,
            site_service=platform_dependencies.site_service,
            asset_service=resolved.asset_service,
            location_service=resolved.location_service,
            system_service=resolved.system_service,
        ),
        maintenance_work_requests=build_maintenance_work_requests_desktop_api(
            work_request_service=resolved.work_request_service,
            site_service=platform_dependencies.site_service,
            location_service=resolved.location_service,
            system_service=resolved.system_service,
            asset_service=resolved.asset_service,
            component_service=resolved.component_service,
        ),
        maintenance_work_orders=build_maintenance_work_orders_desktop_api(
            work_order_service=resolved.work_order_service,
            work_request_service=resolved.work_request_service,
            site_service=platform_dependencies.site_service,
            employee_service=platform_dependencies.employee_service,
            party_service=platform_dependencies.party_service,
            location_service=resolved.location_service,
            system_service=resolved.system_service,
            asset_service=resolved.asset_service,
            component_service=resolved.component_service,
        ),
    )


__all__ = ["build_maintenance_desktop_runtime_apis"]
