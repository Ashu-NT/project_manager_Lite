from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceLocation,
    MaintenanceSystem,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetRepository,
    MaintenanceAssetComponentRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from infra.modules.maintenance_management.db.mapper import (
    maintenance_asset_from_orm,
    maintenance_asset_component_from_orm,
    maintenance_asset_component_to_orm,
    maintenance_asset_to_orm,
    maintenance_location_from_orm,
    maintenance_location_to_orm,
    maintenance_system_from_orm,
    maintenance_system_to_orm,
)
from infra.platform.db.maintenance_models import (
    MaintenanceAssetComponentORM,
    MaintenanceAssetORM,
    MaintenanceLocationORM,
    MaintenanceSystemORM,
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


__all__ = [
    "SqlAlchemyMaintenanceAssetRepository",
    "SqlAlchemyMaintenanceAssetComponentRepository",
    "SqlAlchemyMaintenanceLocationRepository",
    "SqlAlchemyMaintenanceSystemRepository",
]
