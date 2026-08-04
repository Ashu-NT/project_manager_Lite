from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain._validation import normalize_maintenance_code
from src.core.modules.maintenance.domain import MaintenanceLocation
from src.core.modules.maintenance.contracts.repositories import MaintenanceLocationRepository
from src.core.modules.maintenance.application.common.support import (
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site


class MaintenanceLocationService:
    def __init__(
        self,
        session: Session,
        location_repo: MaintenanceLocationRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._location_repo = location_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceLocationService",
        )
        self._site_repo = site_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def list_locations(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        parent_location_id: str | None = None,
    ) -> list[MaintenanceLocation]:
        self._require_read("list maintenance locations")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        rows = self._location_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
            parent_location_id=parent_location_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_locations(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> list[MaintenanceLocation]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_locations(active_only=active_only, site_id=site_id)
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.location_code,
                        row.name,
                        row.description,
                        row.location_type,
                        row.status.value,
                        row.criticality.value,
                    ],
                )
            ).lower()
        ]

    def get_location(self, location_id: str) -> MaintenanceLocation:
        self._require_read("view maintenance location")
        organization = self._active_organization()
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "maintenance",
            location.id,
            "maintenance.read",
            operation_label="view maintenance location",
        )
        return location

    def find_location_by_code(
        self,
        location_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceLocation | None:
        self._require_read("resolve maintenance location")
        organization = self._active_organization()
        location = self._location_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(location_code, label="Location code"),
        )
        if location is None:
            return None
        if active_only is not None and location.is_active != bool(active_only):
            return None
        return location

    def create_location(
        self,
        *,
        site_id: str,
        location_code: str,
        name: str,
        description: str = "",
        parent_location_id: str | None = None,
        location_type: str = "",
        criticality=None,
        status=None,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceLocation:
        self._require_manage("create maintenance location")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(location_code, label="Location code")
        if self._location_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Location code already exists in the active organization.", code="MAINTENANCE_LOCATION_CODE_EXISTS")
        parent = self._resolve_parent(parent_location_id, site_id=site.id, organization=organization)
        location = MaintenanceLocation.create(
            organization_id=organization.id,
            site_id=site.id,
            location_code=location_code,
            name=name,
            description=description,
            parent_location_id=parent.id if parent is not None else None,
            location_type=location_type,
            criticality=criticality,
            status=status,
            is_active=is_active,
            notes=notes,
        )
        if self._location_repo.get_by_code(organization.id, location.location_code) is not None:
            raise ValidationError("Location code already exists in the active organization.", code="MAINTENANCE_LOCATION_CODE_EXISTS")
        try:
            self._location_repo.add(location)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Location code already exists in the active organization.", code="MAINTENANCE_LOCATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_location.create", location)
        return location

    def update_location(
        self,
        location_id: str,
        *,
        site_id: str | None = None,
        location_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        parent_location_id: str | None = None,
        location_type: str | None = None,
        criticality=None,
        status=None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceLocation:
        self._require_manage("update maintenance location")
        organization = self._active_organization()
        location = self.get_location(location_id)
        if expected_version is not None and location.version != expected_version:
            raise ConcurrencyError(
                "Maintenance location changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_site_id = location.site_id
        if site_id is not None:
            target_site_id = self._get_site(site_id, organization=organization).id
        requested_parent_id = (
            location.parent_location_id
            if parent_location_id is None
            else normalize_optional_text(parent_location_id) or None
        )
        parent = self._resolve_parent(
            requested_parent_id,
            site_id=target_site_id,
            organization=organization,
            self_id=location.id,
        )
        updated = replace(
            location,
            site_id=target_site_id,
            location_code=location.location_code if location_code is None else location_code,
            name=location.name if name is None else name,
            description=location.description if description is None else description,
            parent_location_id=parent.id if parent is not None else None,
            location_type=location.location_type if location_type is None else location_type,
            criticality=location.criticality if criticality is None else criticality,
            status=location.status if status is None and is_active is None else status,
            is_active=location.is_active if is_active is None else is_active,
            notes=location.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        if location_code is not None:
            existing = self._location_repo.get_by_code(organization.id, updated.location_code)
            if existing is not None and existing.id != location.id:
                raise ValidationError("Location code already exists in the active organization.", code="MAINTENANCE_LOCATION_CODE_EXISTS")
        try:
            self._location_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Location code already exists in the active organization.", code="MAINTENANCE_LOCATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_location.update", updated)
        return updated

    def _resolve_parent(
        self,
        parent_location_id: str | None,
        *,
        site_id: str,
        organization: Organization,
        self_id: str | None = None,
    ) -> MaintenanceLocation | None:
        if parent_location_id in (None, ""):
            return None
        if self_id and parent_location_id == self_id:
            raise BusinessRuleError("A location cannot be its own parent.", code="MAINTENANCE_LOCATION_PARENT_INVALID")
        parent = self._location_repo.get(parent_location_id)
        if parent is None or parent.organization_id != organization.id:
            raise NotFoundError("Parent maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_PARENT_NOT_FOUND")
        if parent.site_id != site_id:
            raise ValidationError("Parent maintenance location must belong to the same site.", code="MAINTENANCE_LOCATION_SITE_MISMATCH")
        return parent

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance locations"
        ).organization

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _record_change(self, action: str, location: MaintenanceLocation) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_location",
            entity_id=location.id,
            module="maintenance",
            details={
                "organization_id": location.organization_id,
                "site_id": location.site_id,
                "location_code": location.location_code,
                "name": location.name,
                "status": location.status.value,
                "criticality": location.criticality.value,
                "is_active": str(location.is_active),
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_location",
                entity_id=location.id,
                source_event="maintenance_locations_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceLocationService"]
