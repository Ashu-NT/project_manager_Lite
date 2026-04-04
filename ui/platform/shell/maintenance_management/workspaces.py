from __future__ import annotations

from ui.modules.maintenance_management import (
    MaintenanceAssetsTab,
    MaintenanceDashboardTab,
    MaintenanceReliabilityTab,
    MaintenanceRequestsTab,
    MaintenanceWorkOrdersTab,
)
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

    services = context.services
    definitions: list[WorkspaceDefinition] = []
    if has_permission(context.user_session, "report.view"):
        definitions.append(
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
            )
        )
    definitions.append(
        WorkspaceDefinition(
            module_code=MAINTENANCE_MANAGEMENT_MODULE_CODE,
            module_label=MAINTENANCE_MANAGEMENT_MODULE_LABEL,
            group_label="Records",
            label="Assets",
            widget=MaintenanceAssetsTab(
                asset_service=services["maintenance_asset_service"],
                component_service=services["maintenance_asset_component_service"],
                site_service=services["site_service"],
                location_service=services["maintenance_location_service"],
                system_service=services["maintenance_system_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        )
    )
    definitions.append(
        WorkspaceDefinition(
            module_code=MAINTENANCE_MANAGEMENT_MODULE_CODE,
            module_label=MAINTENANCE_MANAGEMENT_MODULE_LABEL,
            group_label="Records",
            label="Requests",
            widget=MaintenanceRequestsTab(
                work_request_service=services["maintenance_work_request_service"],
                work_order_service=services["maintenance_work_order_service"],
                site_service=services["site_service"],
                asset_service=services["maintenance_asset_service"],
                location_service=services["maintenance_location_service"],
                system_service=services["maintenance_system_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        )
    )
    definitions.append(
        WorkspaceDefinition(
            module_code=MAINTENANCE_MANAGEMENT_MODULE_CODE,
            module_label=MAINTENANCE_MANAGEMENT_MODULE_LABEL,
            group_label="Records",
            label="Work Orders",
            widget=MaintenanceWorkOrdersTab(
                work_order_service=services["maintenance_work_order_service"],
                work_order_task_service=services["maintenance_work_order_task_service"],
                work_order_task_step_service=services["maintenance_work_order_task_step_service"],
                material_requirement_service=services["maintenance_work_order_material_requirement_service"],
                work_request_service=services["maintenance_work_request_service"],
                site_service=services["site_service"],
                asset_service=services["maintenance_asset_service"],
                location_service=services["maintenance_location_service"],
                system_service=services["maintenance_system_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        )
    )
    if has_permission(context.user_session, "report.view"):
        definitions.append(
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
            )
        )
    return definitions


__all__ = ["build_maintenance_management_workspace_definitions"]
