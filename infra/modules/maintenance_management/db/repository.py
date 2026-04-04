from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceIntegrationSource,
    MaintenanceLocation,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceSensorException,
    MaintenanceSensor,
    MaintenanceSensorReading,
    MaintenanceSensorSourceMapping,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceSystem,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStep,
    MaintenanceWorkRequest,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetRepository,
    MaintenanceAssetComponentRepository,
    MaintenanceIntegrationSourceRepository,
    MaintenanceLocationRepository,
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceSensorExceptionRepository,
    MaintenanceSensorReadingRepository,
    MaintenanceSensorRepository,
    MaintenanceSensorSourceMappingRepository,
    MaintenanceSystemRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
    MaintenanceWorkOrderMaterialRequirementRepository,
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkOrderTaskStepRepository,
    MaintenanceWorkRequestRepository,
)
from infra.modules.maintenance_management.db.mapper import (
    maintenance_asset_from_orm,
    maintenance_asset_component_from_orm,
    maintenance_asset_component_to_orm,
    maintenance_asset_to_orm,
    maintenance_integration_source_from_orm,
    maintenance_integration_source_to_orm,
    maintenance_location_from_orm,
    maintenance_location_to_orm,
    maintenance_preventive_plan_from_orm,
    maintenance_preventive_plan_task_from_orm,
    maintenance_preventive_plan_task_to_orm,
    maintenance_preventive_plan_to_orm,
    maintenance_sensor_exception_from_orm,
    maintenance_sensor_exception_to_orm,
    maintenance_sensor_from_orm,
    maintenance_sensor_reading_from_orm,
    maintenance_sensor_reading_to_orm,
    maintenance_sensor_source_mapping_from_orm,
    maintenance_sensor_source_mapping_to_orm,
    maintenance_sensor_to_orm,
    maintenance_task_step_template_from_orm,
    maintenance_task_step_template_to_orm,
    maintenance_task_template_from_orm,
    maintenance_task_template_to_orm,
    maintenance_work_order_material_requirement_from_orm,
    maintenance_work_order_material_requirement_to_orm,
    maintenance_system_from_orm,
    maintenance_system_to_orm,
    maintenance_work_order_from_orm,
    maintenance_work_order_task_from_orm,
    maintenance_work_order_task_step_from_orm,
    maintenance_work_order_task_step_to_orm,
    maintenance_work_order_task_to_orm,
    maintenance_work_order_to_orm,
    maintenance_work_request_from_orm,
    maintenance_work_request_to_orm,
)
from infra.platform.db.maintenance_models import (
    MaintenanceAssetComponentORM,
    MaintenanceAssetORM,
    MaintenanceIntegrationSourceORM,
    MaintenanceLocationORM,
    MaintenancePreventivePlanORM,
    MaintenancePreventivePlanTaskORM,
    MaintenanceSensorExceptionORM,
    MaintenanceSensorORM,
    MaintenanceSensorReadingORM,
    MaintenanceSensorSourceMappingORM,
    MaintenanceSystemORM,
    MaintenanceTaskStepTemplateORM,
    MaintenanceTaskTemplateORM,
    MaintenanceWorkOrderMaterialRequirementORM,
    MaintenanceWorkOrderORM,
    MaintenanceWorkOrderTaskORM,
    MaintenanceWorkOrderTaskStepORM,
    MaintenanceWorkRequestORM,
)
from infra.platform.db.optimistic import update_with_version_check


class SqlAlchemyMaintenanceLocationRepository(MaintenanceLocationRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, location: MaintenanceLocation) -> None:
        self.session.add(maintenance_location_to_orm(location))

    def update(self, location: MaintenanceLocation) -> None:
        location.version = update_with_version_check(
            self.session,
            MaintenanceLocationORM,
            location.id,
            getattr(location, "version", 1),
            {
                "site_id": location.site_id,
                "location_code": location.location_code,
                "name": location.name,
                "description": location.description or None,
                "parent_location_id": location.parent_location_id,
                "location_type": location.location_type or None,
                "criticality": location.criticality,
                "status": location.status,
                "is_active": location.is_active,
                "created_at": location.created_at,
                "updated_at": location.updated_at,
                "notes": location.notes or None,
            },
            not_found_message="Maintenance location not found.",
            stale_message="Maintenance location was updated by another user.",
        )

    def get(self, location_id: str) -> MaintenanceLocation | None:
        obj = self.session.get(MaintenanceLocationORM, location_id)
        return maintenance_location_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        location_code: str,
    ) -> MaintenanceLocation | None:
        stmt = select(MaintenanceLocationORM).where(
            MaintenanceLocationORM.organization_id == organization_id,
            MaintenanceLocationORM.location_code == location_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_location_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        parent_location_id: str | None = None,
    ) -> list[MaintenanceLocation]:
        stmt = select(MaintenanceLocationORM).where(MaintenanceLocationORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceLocationORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(MaintenanceLocationORM.site_id == site_id)
        if parent_location_id is not None:
            stmt = stmt.where(MaintenanceLocationORM.parent_location_id == parent_location_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceLocationORM.name.asc(), MaintenanceLocationORM.location_code.asc())
        ).scalars().all()
        return [maintenance_location_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceSystemRepository(MaintenanceSystemRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, system: MaintenanceSystem) -> None:
        self.session.add(maintenance_system_to_orm(system))

    def update(self, system: MaintenanceSystem) -> None:
        system.version = update_with_version_check(
            self.session,
            MaintenanceSystemORM,
            system.id,
            getattr(system, "version", 1),
            {
                "site_id": system.site_id,
                "system_code": system.system_code,
                "name": system.name,
                "location_id": system.location_id,
                "description": system.description or None,
                "parent_system_id": system.parent_system_id,
                "system_type": system.system_type or None,
                "criticality": system.criticality,
                "status": system.status,
                "is_active": system.is_active,
                "created_at": system.created_at,
                "updated_at": system.updated_at,
                "notes": system.notes or None,
            },
            not_found_message="Maintenance system not found.",
            stale_message="Maintenance system was updated by another user.",
        )

    def get(self, system_id: str) -> MaintenanceSystem | None:
        obj = self.session.get(MaintenanceSystemORM, system_id)
        return maintenance_system_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        system_code: str,
    ) -> MaintenanceSystem | None:
        stmt = select(MaintenanceSystemORM).where(
            MaintenanceSystemORM.organization_id == organization_id,
            MaintenanceSystemORM.system_code == system_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_system_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        parent_system_id: str | None = None,
    ) -> list[MaintenanceSystem]:
        stmt = select(MaintenanceSystemORM).where(MaintenanceSystemORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceSystemORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(MaintenanceSystemORM.site_id == site_id)
        if location_id is not None:
            stmt = stmt.where(MaintenanceSystemORM.location_id == location_id)
        if parent_system_id is not None:
            stmt = stmt.where(MaintenanceSystemORM.parent_system_id == parent_system_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceSystemORM.name.asc(), MaintenanceSystemORM.system_code.asc())
        ).scalars().all()
        return [maintenance_system_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceAssetRepository(MaintenanceAssetRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, asset: MaintenanceAsset) -> None:
        self.session.add(maintenance_asset_to_orm(asset))

    def update(self, asset: MaintenanceAsset) -> None:
        asset.version = update_with_version_check(
            self.session,
            MaintenanceAssetORM,
            asset.id,
            getattr(asset, "version", 1),
            {
                "site_id": asset.site_id,
                "location_id": asset.location_id,
                "asset_code": asset.asset_code,
                "name": asset.name,
                "system_id": asset.system_id,
                "description": asset.description or None,
                "parent_asset_id": asset.parent_asset_id,
                "asset_type": asset.asset_type or None,
                "asset_category": asset.asset_category or None,
                "status": asset.status,
                "criticality": asset.criticality,
                "manufacturer_party_id": asset.manufacturer_party_id,
                "supplier_party_id": asset.supplier_party_id,
                "model_number": asset.model_number or None,
                "serial_number": asset.serial_number or None,
                "barcode": asset.barcode or None,
                "install_date": asset.install_date,
                "commission_date": asset.commission_date,
                "warranty_start": asset.warranty_start,
                "warranty_end": asset.warranty_end,
                "expected_life_years": asset.expected_life_years,
                "replacement_cost": asset.replacement_cost,
                "maintenance_strategy": asset.maintenance_strategy or None,
                "service_level": asset.service_level or None,
                "requires_shutdown_for_major_work": asset.requires_shutdown_for_major_work,
                "is_active": asset.is_active,
                "created_at": asset.created_at,
                "updated_at": asset.updated_at,
                "notes": asset.notes or None,
            },
            not_found_message="Maintenance asset not found.",
            stale_message="Maintenance asset was updated by another user.",
        )

    def get(self, asset_id: str) -> MaintenanceAsset | None:
        obj = self.session.get(MaintenanceAssetORM, asset_id)
        return maintenance_asset_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        asset_code: str,
    ) -> MaintenanceAsset | None:
        stmt = select(MaintenanceAssetORM).where(
            MaintenanceAssetORM.organization_id == organization_id,
            MaintenanceAssetORM.asset_code == asset_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_asset_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
        parent_asset_id: str | None = None,
        asset_category: str | None = None,
    ) -> list[MaintenanceAsset]:
        stmt = select(MaintenanceAssetORM).where(MaintenanceAssetORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceAssetORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(MaintenanceAssetORM.site_id == site_id)
        if location_id is not None:
            stmt = stmt.where(MaintenanceAssetORM.location_id == location_id)
        if system_id is not None:
            stmt = stmt.where(MaintenanceAssetORM.system_id == system_id)
        if parent_asset_id is not None:
            stmt = stmt.where(MaintenanceAssetORM.parent_asset_id == parent_asset_id)
        if asset_category is not None:
            stmt = stmt.where(MaintenanceAssetORM.asset_category == asset_category)
        rows = self.session.execute(
            stmt.order_by(MaintenanceAssetORM.name.asc(), MaintenanceAssetORM.asset_code.asc())
        ).scalars().all()
        return [maintenance_asset_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceAssetComponentRepository(MaintenanceAssetComponentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, component: MaintenanceAssetComponent) -> None:
        self.session.add(maintenance_asset_component_to_orm(component))

    def update(self, component: MaintenanceAssetComponent) -> None:
        component.version = update_with_version_check(
            self.session,
            MaintenanceAssetComponentORM,
            component.id,
            getattr(component, "version", 1),
            {
                "asset_id": component.asset_id,
                "component_code": component.component_code,
                "name": component.name,
                "description": component.description or None,
                "parent_component_id": component.parent_component_id,
                "component_type": component.component_type or None,
                "status": component.status,
                "manufacturer_party_id": component.manufacturer_party_id,
                "supplier_party_id": component.supplier_party_id,
                "manufacturer_part_number": component.manufacturer_part_number or None,
                "supplier_part_number": component.supplier_part_number or None,
                "model_number": component.model_number or None,
                "serial_number": component.serial_number or None,
                "install_date": component.install_date,
                "warranty_end": component.warranty_end,
                "expected_life_hours": component.expected_life_hours,
                "expected_life_cycles": component.expected_life_cycles,
                "is_critical_component": component.is_critical_component,
                "is_active": component.is_active,
                "created_at": component.created_at,
                "updated_at": component.updated_at,
                "notes": component.notes or None,
            },
            not_found_message="Maintenance asset component not found.",
            stale_message="Maintenance asset component was updated by another user.",
        )

    def get(self, component_id: str) -> MaintenanceAssetComponent | None:
        obj = self.session.get(MaintenanceAssetComponentORM, component_id)
        return maintenance_asset_component_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        component_code: str,
    ) -> MaintenanceAssetComponent | None:
        stmt = select(MaintenanceAssetComponentORM).where(
            MaintenanceAssetComponentORM.organization_id == organization_id,
            MaintenanceAssetComponentORM.component_code == component_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_asset_component_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
    ) -> list[MaintenanceAssetComponent]:
        stmt = select(MaintenanceAssetComponentORM).where(
            MaintenanceAssetComponentORM.organization_id == organization_id
        )
        if active_only is not None:
            stmt = stmt.where(MaintenanceAssetComponentORM.is_active == bool(active_only))
        if asset_id is not None:
            stmt = stmt.where(MaintenanceAssetComponentORM.asset_id == asset_id)
        if parent_component_id is not None:
            stmt = stmt.where(MaintenanceAssetComponentORM.parent_component_id == parent_component_id)
        if component_type is not None:
            stmt = stmt.where(MaintenanceAssetComponentORM.component_type == component_type)
        rows = self.session.execute(
            stmt.order_by(MaintenanceAssetComponentORM.name.asc(), MaintenanceAssetComponentORM.component_code.asc())
        ).scalars().all()
        return [maintenance_asset_component_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceSensorRepository(MaintenanceSensorRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, sensor: MaintenanceSensor) -> None:
        self.session.add(maintenance_sensor_to_orm(sensor))

    def update(self, sensor: MaintenanceSensor) -> None:
        sensor.version = update_with_version_check(
            self.session,
            MaintenanceSensorORM,
            sensor.id,
            getattr(sensor, "version", 1),
            {
                "site_id": sensor.site_id,
                "sensor_code": sensor.sensor_code,
                "sensor_name": sensor.sensor_name,
                "sensor_tag": sensor.sensor_tag or None,
                "sensor_type": sensor.sensor_type or None,
                "asset_id": sensor.asset_id,
                "component_id": sensor.component_id,
                "system_id": sensor.system_id,
                "source_type": sensor.source_type or None,
                "source_name": sensor.source_name or None,
                "source_key": sensor.source_key or None,
                "unit": sensor.unit or None,
                "current_value": sensor.current_value,
                "last_read_at": sensor.last_read_at,
                "last_quality_state": sensor.last_quality_state,
                "is_active": sensor.is_active,
                "notes": sensor.notes or None,
                "created_at": sensor.created_at,
                "updated_at": sensor.updated_at,
            },
            not_found_message="Maintenance sensor not found.",
            stale_message="Maintenance sensor was updated by another user.",
        )

    def get(self, sensor_id: str) -> MaintenanceSensor | None:
        obj = self.session.get(MaintenanceSensorORM, sensor_id)
        return maintenance_sensor_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        sensor_code: str,
    ) -> MaintenanceSensor | None:
        stmt = select(MaintenanceSensorORM).where(
            MaintenanceSensorORM.organization_id == organization_id,
            MaintenanceSensorORM.sensor_code == sensor_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_sensor_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        sensor_type: str | None = None,
        source_type: str | None = None,
    ) -> list[MaintenanceSensor]:
        stmt = select(MaintenanceSensorORM).where(MaintenanceSensorORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceSensorORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(MaintenanceSensorORM.site_id == site_id)
        if asset_id is not None:
            stmt = stmt.where(MaintenanceSensorORM.asset_id == asset_id)
        if component_id is not None:
            stmt = stmt.where(MaintenanceSensorORM.component_id == component_id)
        if system_id is not None:
            stmt = stmt.where(MaintenanceSensorORM.system_id == system_id)
        if sensor_type is not None:
            stmt = stmt.where(MaintenanceSensorORM.sensor_type == sensor_type)
        if source_type is not None:
            stmt = stmt.where(MaintenanceSensorORM.source_type == source_type)
        rows = self.session.execute(
            stmt.order_by(MaintenanceSensorORM.sensor_name.asc(), MaintenanceSensorORM.sensor_code.asc())
        ).scalars().all()
        return [maintenance_sensor_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceSensorReadingRepository(MaintenanceSensorReadingRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, sensor_reading: MaintenanceSensorReading) -> None:
        self.session.add(maintenance_sensor_reading_to_orm(sensor_reading))

    def get(self, sensor_reading_id: str) -> MaintenanceSensorReading | None:
        obj = self.session.get(MaintenanceSensorReadingORM, sensor_reading_id)
        return maintenance_sensor_reading_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id: str | None = None,
        quality_state: str | None = None,
        source_batch_id: str | None = None,
        reading_from=None,
        reading_to=None,
    ) -> list[MaintenanceSensorReading]:
        stmt = select(MaintenanceSensorReadingORM).where(
            MaintenanceSensorReadingORM.organization_id == organization_id
        )
        if sensor_id is not None:
            stmt = stmt.where(MaintenanceSensorReadingORM.sensor_id == sensor_id)
        if quality_state is not None:
            stmt = stmt.where(MaintenanceSensorReadingORM.quality_state == quality_state)
        if source_batch_id is not None:
            stmt = stmt.where(MaintenanceSensorReadingORM.source_batch_id == source_batch_id)
        if reading_from is not None:
            stmt = stmt.where(MaintenanceSensorReadingORM.reading_timestamp >= reading_from)
        if reading_to is not None:
            stmt = stmt.where(MaintenanceSensorReadingORM.reading_timestamp <= reading_to)
        rows = self.session.execute(
            stmt.order_by(MaintenanceSensorReadingORM.reading_timestamp.desc())
        ).scalars().all()
        return [maintenance_sensor_reading_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceIntegrationSourceRepository(MaintenanceIntegrationSourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, integration_source: MaintenanceIntegrationSource) -> None:
        self.session.add(maintenance_integration_source_to_orm(integration_source))

    def update(self, integration_source: MaintenanceIntegrationSource) -> None:
        integration_source.version = update_with_version_check(
            self.session,
            MaintenanceIntegrationSourceORM,
            integration_source.id,
            getattr(integration_source, "version", 1),
            {
                "integration_code": integration_source.integration_code,
                "name": integration_source.name,
                "integration_type": integration_source.integration_type,
                "endpoint_or_path": integration_source.endpoint_or_path or None,
                "authentication_mode": integration_source.authentication_mode or None,
                "schedule_expression": integration_source.schedule_expression or None,
                "last_successful_sync_at": integration_source.last_successful_sync_at,
                "last_failed_sync_at": integration_source.last_failed_sync_at,
                "last_error_message": integration_source.last_error_message or None,
                "is_active": integration_source.is_active,
                "notes": integration_source.notes or None,
                "created_at": integration_source.created_at,
                "updated_at": integration_source.updated_at,
            },
            not_found_message="Maintenance integration source not found.",
            stale_message="Maintenance integration source was updated by another user.",
        )

    def get(self, integration_source_id: str) -> MaintenanceIntegrationSource | None:
        obj = self.session.get(MaintenanceIntegrationSourceORM, integration_source_id)
        return maintenance_integration_source_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        integration_code: str,
    ) -> MaintenanceIntegrationSource | None:
        stmt = select(MaintenanceIntegrationSourceORM).where(
            MaintenanceIntegrationSourceORM.organization_id == organization_id,
            MaintenanceIntegrationSourceORM.integration_code == integration_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_integration_source_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        integration_type: str | None = None,
    ) -> list[MaintenanceIntegrationSource]:
        stmt = select(MaintenanceIntegrationSourceORM).where(
            MaintenanceIntegrationSourceORM.organization_id == organization_id
        )
        if active_only is not None:
            stmt = stmt.where(MaintenanceIntegrationSourceORM.is_active == bool(active_only))
        if integration_type is not None:
            stmt = stmt.where(MaintenanceIntegrationSourceORM.integration_type == integration_type)
        rows = self.session.execute(
            stmt.order_by(
                MaintenanceIntegrationSourceORM.name.asc(),
                MaintenanceIntegrationSourceORM.integration_code.asc(),
            )
        ).scalars().all()
        return [maintenance_integration_source_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceSensorSourceMappingRepository(MaintenanceSensorSourceMappingRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None:
        self.session.add(maintenance_sensor_source_mapping_to_orm(sensor_source_mapping))

    def update(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None:
        sensor_source_mapping.version = update_with_version_check(
            self.session,
            MaintenanceSensorSourceMappingORM,
            sensor_source_mapping.id,
            getattr(sensor_source_mapping, "version", 1),
            {
                "integration_source_id": sensor_source_mapping.integration_source_id,
                "sensor_id": sensor_source_mapping.sensor_id,
                "external_equipment_key": sensor_source_mapping.external_equipment_key or None,
                "external_measurement_key": sensor_source_mapping.external_measurement_key,
                "transform_rule": sensor_source_mapping.transform_rule or None,
                "unit_conversion_rule": sensor_source_mapping.unit_conversion_rule or None,
                "is_active": sensor_source_mapping.is_active,
                "notes": sensor_source_mapping.notes or None,
                "created_at": sensor_source_mapping.created_at,
                "updated_at": sensor_source_mapping.updated_at,
            },
            not_found_message="Maintenance sensor source mapping not found.",
            stale_message="Maintenance sensor source mapping was updated by another user.",
        )

    def get(self, sensor_source_mapping_id: str) -> MaintenanceSensorSourceMapping | None:
        obj = self.session.get(MaintenanceSensorSourceMappingORM, sensor_source_mapping_id)
        return maintenance_sensor_source_mapping_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        integration_source_id: str | None = None,
        sensor_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceSensorSourceMapping]:
        stmt = select(MaintenanceSensorSourceMappingORM).where(
            MaintenanceSensorSourceMappingORM.organization_id == organization_id
        )
        if integration_source_id is not None:
            stmt = stmt.where(MaintenanceSensorSourceMappingORM.integration_source_id == integration_source_id)
        if sensor_id is not None:
            stmt = stmt.where(MaintenanceSensorSourceMappingORM.sensor_id == sensor_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceSensorSourceMappingORM.is_active == bool(active_only))
        rows = self.session.execute(
            stmt.order_by(
                MaintenanceSensorSourceMappingORM.integration_source_id.asc(),
                MaintenanceSensorSourceMappingORM.external_measurement_key.asc(),
            )
        ).scalars().all()
        return [maintenance_sensor_source_mapping_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceSensorExceptionRepository(MaintenanceSensorExceptionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, sensor_exception: MaintenanceSensorException) -> None:
        self.session.add(maintenance_sensor_exception_to_orm(sensor_exception))

    def update(self, sensor_exception: MaintenanceSensorException) -> None:
        sensor_exception.version = update_with_version_check(
            self.session,
            MaintenanceSensorExceptionORM,
            sensor_exception.id,
            getattr(sensor_exception, "version", 1),
            {
                "sensor_id": sensor_exception.sensor_id,
                "integration_source_id": sensor_exception.integration_source_id,
                "source_mapping_id": sensor_exception.source_mapping_id,
                "exception_type": sensor_exception.exception_type,
                "status": sensor_exception.status,
                "message": sensor_exception.message,
                "source_batch_id": sensor_exception.source_batch_id or None,
                "raw_payload_ref": sensor_exception.raw_payload_ref or None,
                "detected_at": sensor_exception.detected_at,
                "acknowledged_at": sensor_exception.acknowledged_at,
                "acknowledged_by_user_id": sensor_exception.acknowledged_by_user_id,
                "resolved_at": sensor_exception.resolved_at,
                "resolved_by_user_id": sensor_exception.resolved_by_user_id,
                "notes": sensor_exception.notes or None,
                "created_at": sensor_exception.created_at,
                "updated_at": sensor_exception.updated_at,
            },
            not_found_message="Maintenance sensor exception not found.",
            stale_message="Maintenance sensor exception was updated by another user.",
        )

    def get(self, sensor_exception_id: str) -> MaintenanceSensorException | None:
        obj = self.session.get(MaintenanceSensorExceptionORM, sensor_exception_id)
        return maintenance_sensor_exception_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: str | None = None,
        status: str | None = None,
        source_batch_id: str | None = None,
    ) -> list[MaintenanceSensorException]:
        stmt = select(MaintenanceSensorExceptionORM).where(
            MaintenanceSensorExceptionORM.organization_id == organization_id
        )
        if sensor_id is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.sensor_id == sensor_id)
        if integration_source_id is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.integration_source_id == integration_source_id)
        if source_mapping_id is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.source_mapping_id == source_mapping_id)
        if exception_type is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.exception_type == exception_type)
        if status is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.status == status)
        if source_batch_id is not None:
            stmt = stmt.where(MaintenanceSensorExceptionORM.source_batch_id == source_batch_id)
        rows = self.session.execute(
            stmt.order_by(
                MaintenanceSensorExceptionORM.detected_at.desc(),
                MaintenanceSensorExceptionORM.created_at.desc(),
            )
        ).scalars().all()
        return [maintenance_sensor_exception_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceWorkRequestRepository(MaintenanceWorkRequestRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, work_request: MaintenanceWorkRequest) -> None:
        self.session.add(maintenance_work_request_to_orm(work_request))

    def update(self, work_request: MaintenanceWorkRequest) -> None:
        work_request.version = update_with_version_check(
            self.session,
            MaintenanceWorkRequestORM,
            work_request.id,
            getattr(work_request, "version", 1),
            {
                "site_id": work_request.site_id,
                "work_request_code": work_request.work_request_code,
                "source_type": work_request.source_type,
                "request_type": work_request.request_type,
                "asset_id": work_request.asset_id,
                "component_id": work_request.component_id,
                "system_id": work_request.system_id,
                "location_id": work_request.location_id,
                "title": work_request.title,
                "description": work_request.description,
                "priority": work_request.priority,
                "status": work_request.status,
                "requested_at": work_request.requested_at,
                "requested_by_user_id": work_request.requested_by_user_id,
                "requested_by_name_snapshot": work_request.requested_by_name_snapshot,
                "triaged_at": work_request.triaged_at,
                "triaged_by_user_id": work_request.triaged_by_user_id,
                "failure_symptom_code": work_request.failure_symptom_code,
                "safety_risk_level": work_request.safety_risk_level,
                "production_impact_level": work_request.production_impact_level,
                "notes": work_request.notes,
                "created_at": work_request.created_at,
                "updated_at": work_request.updated_at,
            },
            not_found_message="Maintenance work request not found.",
            stale_message="Maintenance work request was updated by another user.",
        )

    def get(self, work_request_id: str) -> MaintenanceWorkRequest | None:
        obj = self.session.get(MaintenanceWorkRequestORM, work_request_id)
        return maintenance_work_request_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        work_request_code: str,
    ) -> MaintenanceWorkRequest | None:
        stmt = select(MaintenanceWorkRequestORM).where(
            MaintenanceWorkRequestORM.organization_id == organization_id,
            MaintenanceWorkRequestORM.work_request_code == work_request_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_work_request_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        requested_by_user_id: str | None = None,
        triaged_by_user_id: str | None = None,
    ) -> list[MaintenanceWorkRequest]:
        stmt = select(MaintenanceWorkRequestORM).where(MaintenanceWorkRequestORM.organization_id == organization_id)
        if site_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.site_id == site_id)
        if asset_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.asset_id == asset_id)
        if component_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.component_id == component_id)
        if system_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.system_id == system_id)
        if location_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.location_id == location_id)
        if status is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.status == status)
        if priority is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.priority == priority)
        if requested_by_user_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.requested_by_user_id == requested_by_user_id)
        if triaged_by_user_id is not None:
            stmt = stmt.where(MaintenanceWorkRequestORM.triaged_by_user_id == triaged_by_user_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceWorkRequestORM.created_at.desc())
        ).scalars().all()
        return [maintenance_work_request_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceWorkOrderRepository(MaintenanceWorkOrderRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, work_order: MaintenanceWorkOrder) -> None:
        self.session.add(maintenance_work_order_to_orm(work_order))

    def update(self, work_order: MaintenanceWorkOrder) -> None:
        work_order.version = update_with_version_check(
            self.session,
            MaintenanceWorkOrderORM,
            work_order.id,
            getattr(work_order, "version", 1),
            {
                "site_id": work_order.site_id,
                "work_order_code": work_order.work_order_code,
                "work_order_type": work_order.work_order_type,
                "source_type": work_order.source_type,
                "source_id": work_order.source_id,
                "asset_id": work_order.asset_id,
                "component_id": work_order.component_id,
                "system_id": work_order.system_id,
                "location_id": work_order.location_id,
                "title": work_order.title,
                "description": work_order.description,
                "priority": work_order.priority,
                "status": work_order.status,
                "requested_by_user_id": work_order.requested_by_user_id,
                "planner_user_id": work_order.planner_user_id,
                "supervisor_user_id": work_order.supervisor_user_id,
                "assigned_team_id": work_order.assigned_team_id,
                "assigned_employee_id": work_order.assigned_employee_id,
                "planned_start": work_order.planned_start,
                "planned_end": work_order.planned_end,
                "actual_start": work_order.actual_start,
                "actual_end": work_order.actual_end,
                "requires_shutdown": work_order.requires_shutdown,
                "permit_required": work_order.permit_required,
                "approval_required": work_order.approval_required,
                "failure_code": work_order.failure_code,
                "root_cause_code": work_order.root_cause_code,
                "downtime_minutes": work_order.downtime_minutes,
                "parts_cost": work_order.parts_cost,
                "labor_cost": work_order.labor_cost,
                "vendor_party_id": work_order.vendor_party_id,
                "is_preventive": work_order.is_preventive,
                "is_emergency": work_order.is_emergency,
                "closed_at": work_order.closed_at,
                "closed_by_user_id": work_order.closed_by_user_id,
                "notes": work_order.notes,
                "created_at": work_order.created_at,
                "updated_at": work_order.updated_at,
            },
            not_found_message="Maintenance work order not found.",
            stale_message="Maintenance work order was updated by another user.",
        )

    def get(self, work_order_id: str) -> MaintenanceWorkOrder | None:
        obj = self.session.get(MaintenanceWorkOrderORM, work_order_id)
        return maintenance_work_order_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        work_order_code: str,
    ) -> MaintenanceWorkOrder | None:
        stmt = select(MaintenanceWorkOrderORM).where(
            MaintenanceWorkOrderORM.organization_id == organization_id,
            MaintenanceWorkOrderORM.work_order_code == work_order_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_work_order_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        planner_user_id: str | None = None,
        supervisor_user_id: str | None = None,
        work_order_type: str | None = None,
        is_preventive: bool | None = None,
        is_emergency: bool | None = None,
    ) -> list[MaintenanceWorkOrder]:
        stmt = select(MaintenanceWorkOrderORM).where(MaintenanceWorkOrderORM.organization_id == organization_id)
        if site_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.site_id == site_id)
        if asset_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.asset_id == asset_id)
        if component_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.component_id == component_id)
        if system_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.system_id == system_id)
        if location_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.location_id == location_id)
        if status is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.status == status)
        if priority is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.priority == priority)
        if assigned_employee_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.assigned_employee_id == assigned_employee_id)
        if assigned_team_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.assigned_team_id == assigned_team_id)
        if planner_user_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.planner_user_id == planner_user_id)
        if supervisor_user_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.supervisor_user_id == supervisor_user_id)
        if work_order_type is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.work_order_type == work_order_type)
        if is_preventive is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.is_preventive == bool(is_preventive))
        if is_emergency is not None:
            stmt = stmt.where(MaintenanceWorkOrderORM.is_emergency == bool(is_emergency))
        rows = self.session.execute(
            stmt.order_by(MaintenanceWorkOrderORM.created_at.desc())
        ).scalars().all()
        return [maintenance_work_order_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceWorkOrderTaskRepository(MaintenanceWorkOrderTaskRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, work_order_task: MaintenanceWorkOrderTask) -> None:
        self.session.add(maintenance_work_order_task_to_orm(work_order_task))

    def update(self, work_order_task: MaintenanceWorkOrderTask) -> None:
        work_order_task.version = update_with_version_check(
            self.session,
            MaintenanceWorkOrderTaskORM,
            work_order_task.id,
            getattr(work_order_task, "version", 1),
            {
                "work_order_id": work_order_task.work_order_id,
                "task_template_id": work_order_task.task_template_id,
                "task_name": work_order_task.task_name,
                "description": work_order_task.description,
                "assigned_employee_id": work_order_task.assigned_employee_id,
                "assigned_team_id": work_order_task.assigned_team_id,
                "estimated_minutes": work_order_task.estimated_minutes,
                "actual_minutes": work_order_task.actual_minutes,
                "required_skill": work_order_task.required_skill,
                "status": work_order_task.status,
                "started_at": work_order_task.started_at,
                "completed_at": work_order_task.completed_at,
                "sequence_no": work_order_task.sequence_no,
                "is_mandatory": work_order_task.is_mandatory,
                "completion_rule": work_order_task.completion_rule,
                "notes": work_order_task.notes,
                "created_at": work_order_task.created_at,
                "updated_at": work_order_task.updated_at,
            },
            not_found_message="Maintenance work order task not found.",
            stale_message="Maintenance work order task was updated by another user.",
        )

    def get(self, work_order_task_id: str) -> MaintenanceWorkOrderTask | None:
        obj = self.session.get(MaintenanceWorkOrderTaskORM, work_order_task_id)
        return maintenance_work_order_task_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        status: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
    ) -> list[MaintenanceWorkOrderTask]:
        stmt = select(MaintenanceWorkOrderTaskORM).where(MaintenanceWorkOrderTaskORM.organization_id == organization_id)
        if work_order_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskORM.work_order_id == work_order_id)
        if status is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskORM.status == status)
        if assigned_employee_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskORM.assigned_employee_id == assigned_employee_id)
        if assigned_team_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskORM.assigned_team_id == assigned_team_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceWorkOrderTaskORM.sequence_no.asc(), MaintenanceWorkOrderTaskORM.created_at.asc())
        ).scalars().all()
        return [maintenance_work_order_task_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceWorkOrderTaskStepRepository(MaintenanceWorkOrderTaskStepRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None:
        self.session.add(maintenance_work_order_task_step_to_orm(work_order_task_step))

    def update(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None:
        work_order_task_step.version = update_with_version_check(
            self.session,
            MaintenanceWorkOrderTaskStepORM,
            work_order_task_step.id,
            getattr(work_order_task_step, "version", 1),
            {
                "work_order_task_id": work_order_task_step.work_order_task_id,
                "source_step_template_id": work_order_task_step.source_step_template_id,
                "step_number": work_order_task_step.step_number,
                "instruction": work_order_task_step.instruction,
                "expected_result": work_order_task_step.expected_result,
                "hint_level": work_order_task_step.hint_level,
                "hint_text": work_order_task_step.hint_text,
                "status": work_order_task_step.status,
                "requires_confirmation": work_order_task_step.requires_confirmation,
                "requires_measurement": work_order_task_step.requires_measurement,
                "requires_photo": work_order_task_step.requires_photo,
                "measurement_value": work_order_task_step.measurement_value,
                "measurement_unit": work_order_task_step.measurement_unit,
                "completed_by_user_id": work_order_task_step.completed_by_user_id,
                "completed_at": work_order_task_step.completed_at,
                "confirmed_by_user_id": work_order_task_step.confirmed_by_user_id,
                "confirmed_at": work_order_task_step.confirmed_at,
                "notes": work_order_task_step.notes,
                "created_at": work_order_task_step.created_at,
                "updated_at": work_order_task_step.updated_at,
            },
            not_found_message="Maintenance work order task step not found.",
            stale_message="Maintenance work order task step was updated by another user.",
        )

    def get(self, work_order_task_step_id: str) -> MaintenanceWorkOrderTaskStep | None:
        obj = self.session.get(MaintenanceWorkOrderTaskStepORM, work_order_task_step_id)
        return maintenance_work_order_task_step_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_task_id: str | None = None,
        status: str | None = None,
    ) -> list[MaintenanceWorkOrderTaskStep]:
        stmt = select(MaintenanceWorkOrderTaskStepORM).where(MaintenanceWorkOrderTaskStepORM.organization_id == organization_id)
        if work_order_task_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskStepORM.work_order_task_id == work_order_task_id)
        if status is not None:
            stmt = stmt.where(MaintenanceWorkOrderTaskStepORM.status == status)
        rows = self.session.execute(
            stmt.order_by(MaintenanceWorkOrderTaskStepORM.step_number.asc(), MaintenanceWorkOrderTaskStepORM.created_at.asc())
        ).scalars().all()
        return [maintenance_work_order_task_step_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository(
    MaintenanceWorkOrderMaterialRequirementRepository
):
    def __init__(self, session: Session):
        self.session = session

    def add(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None:
        self.session.add(maintenance_work_order_material_requirement_to_orm(material_requirement))

    def update(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None:
        material_requirement.version = update_with_version_check(
            self.session,
            MaintenanceWorkOrderMaterialRequirementORM,
            material_requirement.id,
            getattr(material_requirement, "version", 1),
            {
                "work_order_id": material_requirement.work_order_id,
                "stock_item_id": material_requirement.stock_item_id,
                "description": material_requirement.description,
                "required_qty": material_requirement.required_qty,
                "issued_qty": material_requirement.issued_qty,
                "required_uom": material_requirement.required_uom,
                "is_stock_item": material_requirement.is_stock_item,
                "preferred_storeroom_id": material_requirement.preferred_storeroom_id,
                "procurement_status": material_requirement.procurement_status,
                "last_availability_status": material_requirement.last_availability_status,
                "last_missing_qty": material_requirement.last_missing_qty,
                "linked_requisition_id": material_requirement.linked_requisition_id,
                "notes": material_requirement.notes,
                "created_at": material_requirement.created_at,
                "updated_at": material_requirement.updated_at,
            },
            not_found_message="Maintenance material requirement not found.",
            stale_message="Maintenance material requirement was updated by another user.",
        )

    def get(self, material_requirement_id: str) -> MaintenanceWorkOrderMaterialRequirement | None:
        obj = self.session.get(MaintenanceWorkOrderMaterialRequirementORM, material_requirement_id)
        return maintenance_work_order_material_requirement_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        procurement_status: str | None = None,
        preferred_storeroom_id: str | None = None,
        stock_item_id: str | None = None,
    ) -> list[MaintenanceWorkOrderMaterialRequirement]:
        stmt = select(MaintenanceWorkOrderMaterialRequirementORM).where(
            MaintenanceWorkOrderMaterialRequirementORM.organization_id == organization_id
        )
        if work_order_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderMaterialRequirementORM.work_order_id == work_order_id)
        if procurement_status is not None:
            stmt = stmt.where(MaintenanceWorkOrderMaterialRequirementORM.procurement_status == procurement_status)
        if preferred_storeroom_id is not None:
            stmt = stmt.where(
                MaintenanceWorkOrderMaterialRequirementORM.preferred_storeroom_id == preferred_storeroom_id
            )
        if stock_item_id is not None:
            stmt = stmt.where(MaintenanceWorkOrderMaterialRequirementORM.stock_item_id == stock_item_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceWorkOrderMaterialRequirementORM.created_at.asc())
        ).scalars().all()
        return [maintenance_work_order_material_requirement_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceTaskTemplateRepository(MaintenanceTaskTemplateRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, task_template: MaintenanceTaskTemplate) -> None:
        self.session.add(maintenance_task_template_to_orm(task_template))

    def update(self, task_template: MaintenanceTaskTemplate) -> None:
        task_template.version = update_with_version_check(
            self.session,
            MaintenanceTaskTemplateORM,
            task_template.id,
            getattr(task_template, "version", 1),
            {
                "task_template_code": task_template.task_template_code,
                "name": task_template.name,
                "description": task_template.description or None,
                "maintenance_type": task_template.maintenance_type or None,
                "revision_no": task_template.revision_no,
                "template_status": task_template.template_status,
                "estimated_minutes": task_template.estimated_minutes,
                "required_skill": task_template.required_skill,
                "requires_shutdown": task_template.requires_shutdown,
                "requires_permit": task_template.requires_permit,
                "is_active": task_template.is_active,
                "notes": task_template.notes,
                "created_at": task_template.created_at,
                "updated_at": task_template.updated_at,
            },
            not_found_message="Maintenance task template not found.",
            stale_message="Maintenance task template was updated by another user.",
        )

    def get(self, task_template_id: str) -> MaintenanceTaskTemplate | None:
        obj = self.session.get(MaintenanceTaskTemplateORM, task_template_id)
        return maintenance_task_template_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, task_template_code: str) -> MaintenanceTaskTemplate | None:
        stmt = select(MaintenanceTaskTemplateORM).where(
            MaintenanceTaskTemplateORM.organization_id == organization_id,
            MaintenanceTaskTemplateORM.task_template_code == task_template_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_task_template_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
    ) -> list[MaintenanceTaskTemplate]:
        stmt = select(MaintenanceTaskTemplateORM).where(MaintenanceTaskTemplateORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceTaskTemplateORM.is_active == bool(active_only))
        if maintenance_type is not None:
            stmt = stmt.where(MaintenanceTaskTemplateORM.maintenance_type == maintenance_type)
        if template_status is not None:
            stmt = stmt.where(MaintenanceTaskTemplateORM.template_status == template_status)
        rows = self.session.execute(
            stmt.order_by(MaintenanceTaskTemplateORM.name.asc(), MaintenanceTaskTemplateORM.task_template_code.asc())
        ).scalars().all()
        return [maintenance_task_template_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceTaskStepTemplateRepository(MaintenanceTaskStepTemplateRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, task_step_template: MaintenanceTaskStepTemplate) -> None:
        self.session.add(maintenance_task_step_template_to_orm(task_step_template))

    def update(self, task_step_template: MaintenanceTaskStepTemplate) -> None:
        task_step_template.version = update_with_version_check(
            self.session,
            MaintenanceTaskStepTemplateORM,
            task_step_template.id,
            getattr(task_step_template, "version", 1),
            {
                "task_template_id": task_step_template.task_template_id,
                "step_number": task_step_template.step_number,
                "instruction": task_step_template.instruction,
                "expected_result": task_step_template.expected_result,
                "hint_level": task_step_template.hint_level,
                "hint_text": task_step_template.hint_text,
                "requires_confirmation": task_step_template.requires_confirmation,
                "requires_measurement": task_step_template.requires_measurement,
                "requires_photo": task_step_template.requires_photo,
                "measurement_unit": task_step_template.measurement_unit,
                "sort_order": task_step_template.sort_order,
                "is_active": task_step_template.is_active,
                "notes": task_step_template.notes,
                "created_at": task_step_template.created_at,
                "updated_at": task_step_template.updated_at,
            },
            not_found_message="Maintenance task step template not found.",
            stale_message="Maintenance task step template was updated by another user.",
        )

    def get(self, task_step_template_id: str) -> MaintenanceTaskStepTemplate | None:
        obj = self.session.get(MaintenanceTaskStepTemplateORM, task_step_template_id)
        return maintenance_task_step_template_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        task_template_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceTaskStepTemplate]:
        stmt = select(MaintenanceTaskStepTemplateORM).where(
            MaintenanceTaskStepTemplateORM.organization_id == organization_id
        )
        if task_template_id is not None:
            stmt = stmt.where(MaintenanceTaskStepTemplateORM.task_template_id == task_template_id)
        if active_only is not None:
            stmt = stmt.where(MaintenanceTaskStepTemplateORM.is_active == bool(active_only))
        rows = self.session.execute(
            stmt.order_by(
                MaintenanceTaskStepTemplateORM.sort_order.asc(),
                MaintenanceTaskStepTemplateORM.step_number.asc(),
                MaintenanceTaskStepTemplateORM.created_at.asc(),
            )
        ).scalars().all()
        return [maintenance_task_step_template_from_orm(row) for row in rows]


class SqlAlchemyMaintenancePreventivePlanRepository(MaintenancePreventivePlanRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, preventive_plan: MaintenancePreventivePlan) -> None:
        self.session.add(maintenance_preventive_plan_to_orm(preventive_plan))

    def update(self, preventive_plan: MaintenancePreventivePlan) -> None:
        preventive_plan.version = update_with_version_check(
            self.session,
            MaintenancePreventivePlanORM,
            preventive_plan.id,
            getattr(preventive_plan, "version", 1),
            {
                "site_id": preventive_plan.site_id,
                "plan_code": preventive_plan.plan_code,
                "name": preventive_plan.name,
                "asset_id": preventive_plan.asset_id,
                "component_id": preventive_plan.component_id,
                "system_id": preventive_plan.system_id,
                "description": preventive_plan.description,
                "status": preventive_plan.status,
                "plan_type": preventive_plan.plan_type,
                "priority": preventive_plan.priority,
                "trigger_mode": preventive_plan.trigger_mode,
                "calendar_frequency_unit": preventive_plan.calendar_frequency_unit,
                "calendar_frequency_value": preventive_plan.calendar_frequency_value,
                "sensor_id": preventive_plan.sensor_id,
                "sensor_threshold": preventive_plan.sensor_threshold,
                "sensor_direction": preventive_plan.sensor_direction,
                "sensor_reset_rule": preventive_plan.sensor_reset_rule,
                "last_generated_at": preventive_plan.last_generated_at,
                "last_completed_at": preventive_plan.last_completed_at,
                "next_due_at": preventive_plan.next_due_at,
                "next_due_counter": preventive_plan.next_due_counter,
                "requires_shutdown": preventive_plan.requires_shutdown,
                "approval_required": preventive_plan.approval_required,
                "auto_generate_work_order": preventive_plan.auto_generate_work_order,
                "is_active": preventive_plan.is_active,
                "notes": preventive_plan.notes,
                "created_at": preventive_plan.created_at,
                "updated_at": preventive_plan.updated_at,
            },
            not_found_message="Maintenance preventive plan not found.",
            stale_message="Maintenance preventive plan was updated by another user.",
        )

    def get(self, preventive_plan_id: str) -> MaintenancePreventivePlan | None:
        obj = self.session.get(MaintenancePreventivePlanORM, preventive_plan_id)
        return maintenance_preventive_plan_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, plan_code: str) -> MaintenancePreventivePlan | None:
        stmt = select(MaintenancePreventivePlanORM).where(
            MaintenancePreventivePlanORM.organization_id == organization_id,
            MaintenancePreventivePlanORM.plan_code == plan_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_preventive_plan_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        status: str | None = None,
        plan_type: str | None = None,
        trigger_mode: str | None = None,
        sensor_id: str | None = None,
    ) -> list[MaintenancePreventivePlan]:
        stmt = select(MaintenancePreventivePlanORM).where(
            MaintenancePreventivePlanORM.organization_id == organization_id
        )
        if active_only is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.site_id == site_id)
        if asset_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.asset_id == asset_id)
        if component_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.component_id == component_id)
        if system_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.system_id == system_id)
        if status is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.status == status)
        if plan_type is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.plan_type == plan_type)
        if trigger_mode is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.trigger_mode == trigger_mode)
        if sensor_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanORM.sensor_id == sensor_id)
        rows = self.session.execute(
            stmt.order_by(MaintenancePreventivePlanORM.name.asc(), MaintenancePreventivePlanORM.plan_code.asc())
        ).scalars().all()
        return [maintenance_preventive_plan_from_orm(row) for row in rows]


class SqlAlchemyMaintenancePreventivePlanTaskRepository(MaintenancePreventivePlanTaskRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None:
        self.session.add(maintenance_preventive_plan_task_to_orm(preventive_plan_task))

    def update(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None:
        preventive_plan_task.version = update_with_version_check(
            self.session,
            MaintenancePreventivePlanTaskORM,
            preventive_plan_task.id,
            getattr(preventive_plan_task, "version", 1),
            {
                "plan_id": preventive_plan_task.plan_id,
                "task_template_id": preventive_plan_task.task_template_id,
                "trigger_scope": preventive_plan_task.trigger_scope,
                "trigger_mode_override": preventive_plan_task.trigger_mode_override,
                "calendar_frequency_unit_override": preventive_plan_task.calendar_frequency_unit_override,
                "calendar_frequency_value_override": preventive_plan_task.calendar_frequency_value_override,
                "sensor_id_override": preventive_plan_task.sensor_id_override,
                "sensor_threshold_override": preventive_plan_task.sensor_threshold_override,
                "sensor_direction_override": preventive_plan_task.sensor_direction_override,
                "sequence_no": preventive_plan_task.sequence_no,
                "is_mandatory": preventive_plan_task.is_mandatory,
                "default_assigned_employee_id": preventive_plan_task.default_assigned_employee_id,
                "default_assigned_team_id": preventive_plan_task.default_assigned_team_id,
                "estimated_minutes_override": preventive_plan_task.estimated_minutes_override,
                "notes": preventive_plan_task.notes,
                "created_at": preventive_plan_task.created_at,
                "updated_at": preventive_plan_task.updated_at,
            },
            not_found_message="Maintenance preventive plan task not found.",
            stale_message="Maintenance preventive plan task was updated by another user.",
        )

    def get(self, preventive_plan_task_id: str) -> MaintenancePreventivePlanTask | None:
        obj = self.session.get(MaintenancePreventivePlanTaskORM, preventive_plan_task_id)
        return maintenance_preventive_plan_task_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        task_template_id: str | None = None,
    ) -> list[MaintenancePreventivePlanTask]:
        stmt = select(MaintenancePreventivePlanTaskORM).where(
            MaintenancePreventivePlanTaskORM.organization_id == organization_id
        )
        if plan_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanTaskORM.plan_id == plan_id)
        if task_template_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanTaskORM.task_template_id == task_template_id)
        rows = self.session.execute(
            stmt.order_by(
                MaintenancePreventivePlanTaskORM.sequence_no.asc(),
                MaintenancePreventivePlanTaskORM.created_at.asc(),
            )
        ).scalars().all()
        return [maintenance_preventive_plan_task_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyMaintenanceAssetRepository",
    "SqlAlchemyMaintenanceAssetComponentRepository",
    "SqlAlchemyMaintenanceLocationRepository",
    "SqlAlchemyMaintenancePreventivePlanRepository",
    "SqlAlchemyMaintenancePreventivePlanTaskRepository",
    "SqlAlchemyMaintenanceSystemRepository",
    "SqlAlchemyMaintenanceTaskStepTemplateRepository",
    "SqlAlchemyMaintenanceTaskTemplateRepository",
    "SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository",
    "SqlAlchemyMaintenanceWorkOrderRepository",
    "SqlAlchemyMaintenanceWorkOrderTaskRepository",
    "SqlAlchemyMaintenanceWorkOrderTaskStepRepository",
    "SqlAlchemyMaintenanceWorkRequestRepository",
]
