from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceFailureCodeService,
    MaintenanceLocationService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceReliabilityService,
    MaintenanceSensorService,
    MaintenanceSensorExceptionService,
    MaintenanceSystemService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)


@dataclass(frozen=True)
class MaintenanceDesktopRuntimeServices:
    location_service: MaintenanceLocationService | None
    system_service: MaintenanceSystemService | None
    asset_service: MaintenanceAssetService | None
    component_service: MaintenanceAssetComponentService | None
    work_request_service: MaintenanceWorkRequestService | None
    work_order_service: MaintenanceWorkOrderService | None
    material_requirement_service: MaintenanceWorkOrderMaterialRequirementService | None
    preventive_plan_service: MaintenancePreventivePlanService | None
    preventive_generation_service: MaintenancePreventiveGenerationService | None
    preventive_plan_task_service: MaintenancePreventivePlanTaskService | None
    task_template_service: MaintenanceTaskTemplateService | None
    task_step_template_service: MaintenanceTaskStepTemplateService | None
    reliability_service: MaintenanceReliabilityService | None
    sensor_service: MaintenanceSensorService | None
    sensor_exception_service: MaintenanceSensorExceptionService | None
    failure_code_service: MaintenanceFailureCodeService | None


def resolve_maintenance_desktop_runtime_services(
    services: Mapping[str, object],
) -> MaintenanceDesktopRuntimeServices:
    location_service = services.get("maintenance_location_service")
    system_service = services.get("maintenance_system_service")
    asset_service = services.get("maintenance_asset_service")
    component_service = services.get("maintenance_asset_component_service")
    work_request_service = services.get("maintenance_work_request_service")
    work_order_service = services.get("maintenance_work_order_service")
    material_requirement_service = services.get(
        "maintenance_work_order_material_requirement_service"
    )
    preventive_plan_service = services.get("maintenance_preventive_plan_service")
    preventive_generation_service = services.get(
        "maintenance_preventive_generation_service"
    )
    preventive_plan_task_service = services.get(
        "maintenance_preventive_plan_task_service"
    )
    task_template_service = services.get("maintenance_task_template_service")
    task_step_template_service = services.get(
        "maintenance_task_step_template_service"
    )
    reliability_service = services.get("maintenance_reliability_service")
    sensor_service = services.get("maintenance_sensor_service")
    sensor_exception_service = services.get("maintenance_sensor_exception_service")
    failure_code_service = services.get("maintenance_failure_code_service")
    return MaintenanceDesktopRuntimeServices(
        location_service=(
            location_service
            if isinstance(location_service, MaintenanceLocationService)
            else None
        ),
        system_service=(
            system_service if isinstance(system_service, MaintenanceSystemService) else None
        ),
        asset_service=(
            asset_service if isinstance(asset_service, MaintenanceAssetService) else None
        ),
        component_service=(
            component_service
            if isinstance(component_service, MaintenanceAssetComponentService)
            else None
        ),
        work_request_service=(
            work_request_service
            if isinstance(work_request_service, MaintenanceWorkRequestService)
            else None
        ),
        work_order_service=(
            work_order_service
            if isinstance(work_order_service, MaintenanceWorkOrderService)
            else None
        ),
        material_requirement_service=(
            material_requirement_service
            if isinstance(
                material_requirement_service,
                MaintenanceWorkOrderMaterialRequirementService,
            )
            else None
        ),
        preventive_plan_service=(
            preventive_plan_service
            if isinstance(preventive_plan_service, MaintenancePreventivePlanService)
            else None
        ),
        preventive_generation_service=(
            preventive_generation_service
            if isinstance(
                preventive_generation_service,
                MaintenancePreventiveGenerationService,
            )
            else None
        ),
        preventive_plan_task_service=(
            preventive_plan_task_service
            if isinstance(
                preventive_plan_task_service,
                MaintenancePreventivePlanTaskService,
            )
            else None
        ),
        task_template_service=(
            task_template_service
            if isinstance(task_template_service, MaintenanceTaskTemplateService)
            else None
        ),
        task_step_template_service=(
            task_step_template_service
            if isinstance(
                task_step_template_service,
                MaintenanceTaskStepTemplateService,
            )
            else None
        ),
        reliability_service=(
            reliability_service
            if isinstance(reliability_service, MaintenanceReliabilityService)
            else None
        ),
        sensor_service=(
            sensor_service if isinstance(sensor_service, MaintenanceSensorService) else None
        ),
        sensor_exception_service=(
            sensor_exception_service
            if isinstance(
                sensor_exception_service,
                MaintenanceSensorExceptionService,
            )
            else None
        ),
        failure_code_service=(
            failure_code_service
            if isinstance(failure_code_service, MaintenanceFailureCodeService)
            else None
        ),
    )


__all__ = [
    "MaintenanceDesktopRuntimeServices",
    "resolve_maintenance_desktop_runtime_services",
]
