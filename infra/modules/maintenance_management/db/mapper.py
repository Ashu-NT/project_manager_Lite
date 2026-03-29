from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceAsset, MaintenanceLocation, MaintenanceSystem
from infra.platform.db.maintenance_models import MaintenanceAssetORM, MaintenanceLocationORM, MaintenanceSystemORM


def maintenance_location_to_orm(location: MaintenanceLocation) -> MaintenanceLocationORM:
    return MaintenanceLocationORM(
        id=location.id,
        organization_id=location.organization_id,
        site_id=location.site_id,
        location_code=location.location_code,
        name=location.name,
        description=location.description or None,
        parent_location_id=location.parent_location_id,
        location_type=location.location_type or None,
        criticality=location.criticality,
        status=location.status,
        is_active=location.is_active,
        created_at=location.created_at,
        updated_at=location.updated_at,
        notes=location.notes or None,
        version=getattr(location, "version", 1),
    )


def maintenance_location_from_orm(obj: MaintenanceLocationORM) -> MaintenanceLocation:
    return MaintenanceLocation(
        id=obj.id,
        organization_id=obj.organization_id,
        site_id=obj.site_id,
        location_code=obj.location_code,
        name=obj.name,
        description=obj.description or "",
        parent_location_id=obj.parent_location_id,
        location_type=obj.location_type or "",
        criticality=obj.criticality,
        status=obj.status,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


def maintenance_system_to_orm(system: MaintenanceSystem) -> MaintenanceSystemORM:
    return MaintenanceSystemORM(
        id=system.id,
        organization_id=system.organization_id,
        site_id=system.site_id,
        system_code=system.system_code,
        name=system.name,
        location_id=system.location_id,
        description=system.description or None,
        parent_system_id=system.parent_system_id,
        system_type=system.system_type or None,
        criticality=system.criticality,
        status=system.status,
        is_active=system.is_active,
        created_at=system.created_at,
        updated_at=system.updated_at,
        notes=system.notes or None,
        version=getattr(system, "version", 1),
    )


def maintenance_system_from_orm(obj: MaintenanceSystemORM) -> MaintenanceSystem:
    return MaintenanceSystem(
        id=obj.id,
        organization_id=obj.organization_id,
        site_id=obj.site_id,
        system_code=obj.system_code,
        name=obj.name,
        location_id=obj.location_id,
        description=obj.description or "",
        parent_system_id=obj.parent_system_id,
        system_type=obj.system_type or "",
        criticality=obj.criticality,
        status=obj.status,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


def maintenance_asset_to_orm(asset: MaintenanceAsset) -> MaintenanceAssetORM:
    return MaintenanceAssetORM(
        id=asset.id,
        organization_id=asset.organization_id,
        site_id=asset.site_id,
        location_id=asset.location_id,
        asset_code=asset.asset_code,
        name=asset.name,
        system_id=asset.system_id,
        description=asset.description or None,
        parent_asset_id=asset.parent_asset_id,
        asset_type=asset.asset_type or None,
        asset_category=asset.asset_category or None,
        status=asset.status,
        criticality=asset.criticality,
        manufacturer_party_id=asset.manufacturer_party_id,
        supplier_party_id=asset.supplier_party_id,
        model_number=asset.model_number or None,
        serial_number=asset.serial_number or None,
        barcode=asset.barcode or None,
        install_date=asset.install_date,
        commission_date=asset.commission_date,
        warranty_start=asset.warranty_start,
        warranty_end=asset.warranty_end,
        expected_life_years=asset.expected_life_years,
        replacement_cost=asset.replacement_cost,
        maintenance_strategy=asset.maintenance_strategy or None,
        service_level=asset.service_level or None,
        requires_shutdown_for_major_work=asset.requires_shutdown_for_major_work,
        is_active=asset.is_active,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        notes=asset.notes or None,
        version=getattr(asset, "version", 1),
    )


def maintenance_asset_from_orm(obj: MaintenanceAssetORM) -> MaintenanceAsset:
    return MaintenanceAsset(
        id=obj.id,
        organization_id=obj.organization_id,
        site_id=obj.site_id,
        location_id=obj.location_id,
        asset_code=obj.asset_code,
        name=obj.name,
        system_id=obj.system_id,
        description=obj.description or "",
        parent_asset_id=obj.parent_asset_id,
        asset_type=obj.asset_type or "",
        asset_category=obj.asset_category or "",
        status=obj.status,
        criticality=obj.criticality,
        manufacturer_party_id=obj.manufacturer_party_id,
        supplier_party_id=obj.supplier_party_id,
        model_number=obj.model_number or "",
        serial_number=obj.serial_number or "",
        barcode=obj.barcode or "",
        install_date=obj.install_date,
        commission_date=obj.commission_date,
        warranty_start=obj.warranty_start,
        warranty_end=obj.warranty_end,
        expected_life_years=obj.expected_life_years,
        replacement_cost=obj.replacement_cost,
        maintenance_strategy=obj.maintenance_strategy or "",
        service_level=obj.service_level or "",
        requires_shutdown_for_major_work=obj.requires_shutdown_for_major_work,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "maintenance_asset_from_orm",
    "maintenance_asset_to_orm",
    "maintenance_location_from_orm",
    "maintenance_location_to_orm",
    "maintenance_system_from_orm",
    "maintenance_system_to_orm",
]
