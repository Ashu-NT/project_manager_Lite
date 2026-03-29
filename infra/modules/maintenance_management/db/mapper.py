from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceLocation, MaintenanceSystem
from infra.platform.db.maintenance_models import MaintenanceLocationORM, MaintenanceSystemORM


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


__all__ = [
    "maintenance_location_from_orm",
    "maintenance_location_to_orm",
    "maintenance_system_from_orm",
    "maintenance_system_to_orm",
]
