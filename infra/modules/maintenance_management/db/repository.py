from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceLocation, MaintenanceSystem
from core.modules.maintenance_management.interfaces import (
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from infra.modules.maintenance_management.db.mapper import (
    maintenance_location_from_orm,
    maintenance_location_to_orm,
    maintenance_system_from_orm,
    maintenance_system_to_orm,
)
from infra.platform.db.maintenance_models import MaintenanceLocationORM, MaintenanceSystemORM
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


__all__ = [
    "SqlAlchemyMaintenanceLocationRepository",
    "SqlAlchemyMaintenanceSystemRepository",
]
