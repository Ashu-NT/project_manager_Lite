from __future__ import annotations

from ui.modules.maintenance_management import MaintenanceDashboardTab, MaintenanceReliabilityTab
from ui.platform.shell.common import (
    MAINTENANCE_MANAGEMENT_MODULE_CODE,
    MAINTENANCE_MANAGEMENT_MODULE_LABEL,
    ShellWorkspaceContext,
    WorkspaceDefinition,
    has_permission,
)


def build_maintenance_management_workspace_definitions(
    context: ShellWorkspaceContext,
) -> list[WorkspaceDefinition]:
    if not context.maintenance_management_enabled:
        return []
    if not has_permission(context.user_session, "maintenance.read"):
        return []
    if not has_permission(context.user_session, "report.view"):
        return []

    services = context.services
    return [
        WorkspaceDefinition(
            module_code=MAINTENANCE_MANAGEMENT_MODULE_CODE,
            module_label=MAINTENANCE_MANAGEMENT_MODULE_LABEL,
            group_label="Overview",
            label="Maintenance Dashboard",
            widget=MaintenanceDashboardTab(
                reliability_service=services["maintenance_reliability_service"],
                site_service=services["site_service"],
                asset_service=services["maintenance_asset_service"],
                location_service=services["maintenance_location_service"],
                system_service=services["maintenance_system_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=MAINTENANCE_MANAGEMENT_MODULE_CODE,
            module_label=MAINTENANCE_MANAGEMENT_MODULE_LABEL,
            group_label="Analytics",
            label="Reliability",
            widget=MaintenanceReliabilityTab(
                reliability_service=services["maintenance_reliability_service"],
                reporting_service=services["maintenance_reporting_service"],
                failure_code_service=services["maintenance_failure_code_service"],
                site_service=services["site_service"],
                asset_service=services["maintenance_asset_service"],
                location_service=services["maintenance_location_service"],
                system_service=services["maintenance_system_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
    ]


__all__ = ["build_maintenance_management_workspace_definitions"]
