from __future__ import annotations

from dataclasses import dataclass

from core.platform.access import ScopedRolePolicy
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceAssetComponentService,
    MaintenanceDowntimeEventService,
    MaintenanceFailureCodeService,
    MaintenanceIntegrationSourceService,
    MaintenanceLocationService,
    MaintenanceReliabilityService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceRuntimeContractCatalogService,
    MaintenanceSensorExceptionService,
    MaintenanceSensorReadingService,
    MaintenanceSensorService,
    MaintenanceSensorSourceMappingService,
    MaintenanceSystemService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.access import (
    MAINTENANCE_SCOPE_ROLE_CHOICES,
    normalize_maintenance_scope_role,
    resolve_maintenance_scope_permissions,
)
from infra.modules.maintenance_management.db import (
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceAssetComponentRepository,
    SqlAlchemyMaintenanceDowntimeEventRepository,
    SqlAlchemyMaintenanceFailureCodeRepository,
    SqlAlchemyMaintenanceIntegrationSourceRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenanceSensorExceptionRepository,
    SqlAlchemyMaintenanceSensorReadingRepository,
    SqlAlchemyMaintenanceSensorRepository,
    SqlAlchemyMaintenanceSensorSourceMappingRepository,
    SqlAlchemyMaintenanceSystemRepository,
    SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
    SqlAlchemyMaintenanceWorkOrderRepository,
    SqlAlchemyMaintenanceWorkOrderTaskRepository,
    SqlAlchemyMaintenanceWorkOrderTaskStepRepository,
    SqlAlchemyMaintenanceWorkRequestRepository,
)
from infra.platform.db.auth.repository import SqlAlchemyUserRepository
from infra.platform.service_registration.inventory_procurement_bundle import InventoryProcurementServiceBundle
from infra.platform.service_registration.platform_bundle import PlatformServiceBundle


@dataclass(frozen=True)
class MaintenanceManagementServiceBundle:
    maintenance_runtime_contract_catalog_service: MaintenanceRuntimeContractCatalogService
    maintenance_asset_service: MaintenanceAssetService
    maintenance_asset_component_service: MaintenanceAssetComponentService
    maintenance_downtime_event_service: MaintenanceDowntimeEventService
    maintenance_failure_code_service: MaintenanceFailureCodeService
    maintenance_integration_source_service: MaintenanceIntegrationSourceService
    maintenance_location_service: MaintenanceLocationService
    maintenance_reliability_service: MaintenanceReliabilityService
    maintenance_sensor_exception_service: MaintenanceSensorExceptionService
    maintenance_sensor_service: MaintenanceSensorService
    maintenance_sensor_reading_service: MaintenanceSensorReadingService
    maintenance_sensor_source_mapping_service: MaintenanceSensorSourceMappingService
    maintenance_system_service: MaintenanceSystemService
    maintenance_work_request_service: MaintenanceWorkRequestService
    maintenance_work_order_service: MaintenanceWorkOrderService
    maintenance_work_order_material_requirement_service: MaintenanceWorkOrderMaterialRequirementService
    maintenance_work_order_task_service: MaintenanceWorkOrderTaskService
    maintenance_work_order_task_step_service: MaintenanceWorkOrderTaskStepService


def build_maintenance_management_service_bundle(
    platform_services: PlatformServiceBundle,
    inventory_services: InventoryProcurementServiceBundle,
) -> MaintenanceManagementServiceBundle:
    location_repo = SqlAlchemyMaintenanceLocationRepository(platform_services.session)
    system_repo = SqlAlchemyMaintenanceSystemRepository(platform_services.session)
    asset_repo = SqlAlchemyMaintenanceAssetRepository(platform_services.session)
    component_repo = SqlAlchemyMaintenanceAssetComponentRepository(platform_services.session)
    downtime_event_repo = SqlAlchemyMaintenanceDowntimeEventRepository(platform_services.session)
    failure_code_repo = SqlAlchemyMaintenanceFailureCodeRepository(platform_services.session)
    integration_source_repo = SqlAlchemyMaintenanceIntegrationSourceRepository(platform_services.session)
    sensor_source_mapping_repo = SqlAlchemyMaintenanceSensorSourceMappingRepository(platform_services.session)
    sensor_exception_repo = SqlAlchemyMaintenanceSensorExceptionRepository(platform_services.session)
    sensor_repo = SqlAlchemyMaintenanceSensorRepository(platform_services.session)
    sensor_reading_repo = SqlAlchemyMaintenanceSensorReadingRepository(platform_services.session)
    work_request_repo = SqlAlchemyMaintenanceWorkRequestRepository(platform_services.session)
    work_order_repo = SqlAlchemyMaintenanceWorkOrderRepository(platform_services.session)
    work_order_material_requirement_repo = SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository(platform_services.session)
    work_order_task_repo = SqlAlchemyMaintenanceWorkOrderTaskRepository(platform_services.session)
    work_order_task_step_repo = SqlAlchemyMaintenanceWorkOrderTaskStepRepository(platform_services.session)
    user_repo = SqlAlchemyUserRepository(platform_services.session)
    
    platform_services.department_service.register_location_reference_repository(location_repo)
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="maintenance",
            role_choices=MAINTENANCE_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_maintenance_scope_role,
            resolve_permissions=resolve_maintenance_scope_permissions,
        )
    )
    platform_services.access_service.register_scope_exists_resolver(
        "maintenance",
        lambda entity_id: (
            location_repo.get(entity_id) is not None
            or system_repo.get(entity_id) is not None
            or asset_repo.get(entity_id) is not None
        ),
    )
    maintenance_runtime_contract_catalog_service = MaintenanceRuntimeContractCatalogService()
    maintenance_asset_service = MaintenanceAssetService(
        platform_services.session,
        asset_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        location_repo=location_repo,
        system_repo=system_repo,
        party_repo=platform_services.party_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_asset_component_service = MaintenanceAssetComponentService(
        platform_services.session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=platform_services.organization_repo,
        party_repo=platform_services.party_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_downtime_event_service = MaintenanceDowntimeEventService(
        platform_services.session,
        downtime_event_repo,
        organization_repo=platform_services.organization_repo,
        work_order_repo=work_order_repo,
        asset_repo=asset_repo,
        component_repo=component_repo,
        system_repo=system_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_failure_code_service = MaintenanceFailureCodeService(
        platform_services.session,
        failure_code_repo,
        organization_repo=platform_services.organization_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_location_service = MaintenanceLocationService(
        platform_services.session,
        location_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_reliability_service = MaintenanceReliabilityService(
        platform_services.session,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        asset_repo=asset_repo,
        component_repo=component_repo,
        location_repo=location_repo,
        system_repo=system_repo,
        work_order_repo=work_order_repo,
        failure_code_repo=failure_code_repo,
        downtime_event_repo=downtime_event_repo,
        user_session=platform_services.user_session,
    )
    maintenance_sensor_exception_service = MaintenanceSensorExceptionService(
        platform_services.session,
        sensor_exception_repo,
        organization_repo=platform_services.organization_repo,
        sensor_repo=sensor_repo,
        integration_source_repo=integration_source_repo,
        sensor_source_mapping_repo=sensor_source_mapping_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_integration_source_service = MaintenanceIntegrationSourceService(
        platform_services.session,
        integration_source_repo,
        organization_repo=platform_services.organization_repo,
        sensor_exception_service=maintenance_sensor_exception_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_sensor_service = MaintenanceSensorService(
        platform_services.session,
        sensor_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        asset_repo=asset_repo,
        component_repo=component_repo,
        system_repo=system_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_sensor_source_mapping_service = MaintenanceSensorSourceMappingService(
        platform_services.session,
        sensor_source_mapping_repo,
        organization_repo=platform_services.organization_repo,
        integration_source_repo=integration_source_repo,
        sensor_repo=sensor_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_sensor_reading_service = MaintenanceSensorReadingService(
        platform_services.session,
        sensor_reading_repo,
        organization_repo=platform_services.organization_repo,
        sensor_repo=sensor_repo,
        component_repo=component_repo,
        sensor_exception_service=maintenance_sensor_exception_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_system_service = MaintenanceSystemService(
        platform_services.session,
        system_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        location_repo=location_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_work_request_service = MaintenanceWorkRequestService(
        platform_services.session,
        work_request_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        user_repo=user_repo,
        asset_repo=asset_repo,
        component_repo=component_repo,
        location_repo=location_repo,
        system_repo=system_repo,
        failure_code_repo=failure_code_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_work_order_service = MaintenanceWorkOrderService(
        platform_services.session,
        work_order_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        user_repo=user_repo,
        asset_repo=asset_repo,
        component_repo=component_repo,
        location_repo=location_repo,
        system_repo=system_repo,
        work_request_repo=work_request_repo,
        failure_code_repo=failure_code_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_work_order_material_requirement_service = MaintenanceWorkOrderMaterialRequirementService(
        platform_services.session,
        work_order_material_requirement_repo,
        organization_repo=platform_services.organization_repo,
        work_order_repo=work_order_repo,
        item_service=inventory_services.inventory_item_service,
        inventory_service=inventory_services.inventory_service,
        maintenance_material_service=inventory_services.inventory_maintenance_material_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_work_order_task_service = MaintenanceWorkOrderTaskService(
        platform_services.session,
        work_order_task_repo,
        organization_repo=platform_services.organization_repo,
        work_order_repo=work_order_repo,
        work_order_task_step_repo=work_order_task_step_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_work_order_task_step_service = MaintenanceWorkOrderTaskStepService(
        platform_services.session,
        work_order_task_step_repo,
        organization_repo=platform_services.organization_repo,
        work_order_repo=work_order_repo,
        work_order_task_repo=work_order_task_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    return MaintenanceManagementServiceBundle(
        maintenance_runtime_contract_catalog_service=maintenance_runtime_contract_catalog_service,
        maintenance_asset_service=maintenance_asset_service,
        maintenance_asset_component_service=maintenance_asset_component_service,
        maintenance_downtime_event_service=maintenance_downtime_event_service,
        maintenance_failure_code_service=maintenance_failure_code_service,
        maintenance_integration_source_service=maintenance_integration_source_service,
        maintenance_location_service=maintenance_location_service,
        maintenance_reliability_service=maintenance_reliability_service,
        maintenance_sensor_exception_service=maintenance_sensor_exception_service,
        maintenance_sensor_service=maintenance_sensor_service,
        maintenance_sensor_reading_service=maintenance_sensor_reading_service,
        maintenance_sensor_source_mapping_service=maintenance_sensor_source_mapping_service,
        maintenance_system_service=maintenance_system_service,
        maintenance_work_request_service=maintenance_work_request_service,
        maintenance_work_order_service=maintenance_work_order_service,
        maintenance_work_order_material_requirement_service=maintenance_work_order_material_requirement_service,
        maintenance_work_order_task_service=maintenance_work_order_task_service,
        maintenance_work_order_task_step_service=maintenance_work_order_task_step_service,
    )


__all__ = [
    "MaintenanceManagementServiceBundle",
    "build_maintenance_management_service_bundle",
]
