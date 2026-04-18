from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceSystem
from core.modules.maintenance_management.interfaces import (
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from core.modules.maintenance_management.support import (
    coerce_criticality,
    coerce_lifecycle_status,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository, SiteRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization, Site


class MaintenanceSystemService:
    def __init__(
        self,
        session: Session,
        system_repo: MaintenanceSystemRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        location_repo: MaintenanceLocationRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._system_repo = system_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._location_repo = location_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_systems(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        parent_system_id: str | None = None,
    ) -> list[MaintenanceSystem]:
        self._require_read("list maintenance systems")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        if location_id is not None:
            self._get_location(location_id, organization=organization)
        rows = self._system_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
            location_id=location_id,
            parent_system_id=parent_system_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_systems(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
    ) -> list[MaintenanceSystem]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_systems(active_only=active_only, site_id=site_id, location_id=location_id)
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.system_code,
                        row.name,
                        row.description,
                        row.system_type,
                        row.status.value,
                        row.criticality.value,
                    ],
                )
            ).lower()
        ]

    def get_system(self, system_id: str) -> MaintenanceSystem:
        self._require_read("view maintenance system")
        organization = self._active_organization()
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "maintenance",
            system.id,
            "maintenance.read",
            operation_label="view maintenance system",
        )
        return system

    def find_system_by_code(
        self,
        system_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceSystem | None:
        self._require_read("resolve maintenance system")
        organization = self._active_organization()
        system = self._system_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(system_code, label="System code"),
        )
        if system is None:
            return None
        if active_only is not None and system.is_active != bool(active_only):
            return None
        return system

    def create_system(
        self,
        *,
        site_id: str,
        system_code: str,
        name: str,
        location_id: str | None = None,
        description: str = "",
        parent_system_id: str | None = None,
        system_type: str = "",
        criticality=None,
        status=None,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceSystem:
        self._require_manage("create maintenance system")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(system_code, label="System code")
        if self._system_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("System code already exists in the active organization.", code="MAINTENANCE_SYSTEM_CODE_EXISTS")
        location = self._resolve_location(location_id, site_id=site.id, organization=organization)
        parent = self._resolve_parent(parent_system_id, site_id=site.id, organization=organization, location_id=location.id if location else None)
        system = MaintenanceSystem.create(
            organization_id=organization.id,
            site_id=site.id,
            system_code=normalized_code,
            name=normalize_maintenance_name(name, label="System name"),
            location_id=location.id if location is not None else None,
            description=normalize_optional_text(description),
            parent_system_id=parent.id if parent is not None else None,
            system_type=normalize_optional_text(system_type),
            criticality=coerce_criticality(criticality),
            status=coerce_lifecycle_status(status, is_active=bool(is_active)),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
        try:
            self._system_repo.add(system)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("System code already exists in the active organization.", code="MAINTENANCE_SYSTEM_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_system.create", system)
        return system

    def update_system(
        self,
        system_id: str,
        *,
        site_id: str | None = None,
        system_code: str | None = None,
        name: str | None = None,
        location_id: str | None = None,
        description: str | None = None,
        parent_system_id: str | None = None,
        system_type: str | None = None,
        criticality=None,
        status=None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceSystem:
        self._require_manage("update maintenance system")
        organization = self._active_organization()
        system = self.get_system(system_id)
        if expected_version is not None and system.version != expected_version:
            raise ConcurrencyError(
                "Maintenance system changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_site_id = system.site_id
        if site_id is not None:
            target_site_id = self._get_site(site_id, organization=organization).id
        if system_code is not None:
            normalized_code = normalize_maintenance_code(system_code, label="System code")
            existing = self._system_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != system.id:
                raise ValidationError("System code already exists in the active organization.", code="MAINTENANCE_SYSTEM_CODE_EXISTS")
            system.system_code = normalized_code
        if name is not None:
            system.name = normalize_maintenance_name(name, label="System name")
        if description is not None:
            system.description = normalize_optional_text(description)
        if system_type is not None:
            system.system_type = normalize_optional_text(system_type)
        if criticality is not None:
            system.criticality = coerce_criticality(criticality)
        if is_active is not None:
            system.is_active = bool(is_active)
        if status is not None or is_active is not None:
            system.status = coerce_lifecycle_status(status, is_active=system.is_active)
        if notes is not None:
            system.notes = normalize_optional_text(notes)
        if target_site_id != system.site_id:
            system.site_id = target_site_id
        if location_id is not None:
            location = self._resolve_location(location_id, site_id=system.site_id, organization=organization)
            system.location_id = location.id if location is not None else None
        if parent_system_id is not None:
            parent = self._resolve_parent(
                parent_system_id,
                site_id=system.site_id,
                organization=organization,
                location_id=system.location_id,
                self_id=system.id,
            )
            system.parent_system_id = parent.id if parent is not None else None
        system.updated_at = datetime.now(timezone.utc)
        try:
            self._system_repo.update(system)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("System code already exists in the active organization.", code="MAINTENANCE_SYSTEM_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_system.update", system)
        return system

    def _resolve_location(
        self,
        location_id: str | None,
        *,
        site_id: str,
        organization: Organization,
    ):
        if location_id in (None, ""):
            return None
        location = self._get_location(location_id, organization=organization)
        if location.site_id != site_id:
            raise ValidationError("Maintenance system location must belong to the same site.", code="MAINTENANCE_SYSTEM_SITE_MISMATCH")
        return location

    def _resolve_parent(
        self,
        parent_system_id: str | None,
        *,
        site_id: str,
        organization: Organization,
        location_id: str | None,
        self_id: str | None = None,
    ) -> MaintenanceSystem | None:
        if parent_system_id in (None, ""):
            return None
        if self_id and parent_system_id == self_id:
            raise BusinessRuleError("A system cannot be its own parent.", code="MAINTENANCE_SYSTEM_PARENT_INVALID")
        parent = self._system_repo.get(parent_system_id)
        if parent is None or parent.organization_id != organization.id:
            raise NotFoundError("Parent maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_PARENT_NOT_FOUND")
        if parent.site_id != site_id:
            raise ValidationError("Parent maintenance system must belong to the same site.", code="MAINTENANCE_SYSTEM_SITE_MISMATCH")
        if location_id is not None and parent.location_id not in (None, location_id):
            raise ValidationError("Parent maintenance system must align to the same location.", code="MAINTENANCE_SYSTEM_LOCATION_MISMATCH")
        return parent

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _get_location(self, location_id: str, *, organization: Organization):
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _record_change(self, action: str, system: MaintenanceSystem) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_system",
            entity_id=system.id,
            details={
                "organization_id": system.organization_id,
                "site_id": system.site_id,
                "location_id": system.location_id or "",
                "system_code": system.system_code,
                "name": system.name,
                "status": system.status.value,
                "criticality": system.criticality.value,
                "is_active": str(system.is_active),
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_system",
                entity_id=system.id,
                source_event="maintenance_systems_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceSystemService"]
