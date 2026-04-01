from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceWorkRequest
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkRequestRepository,
)
from core.modules.maintenance_management.support import (
    coerce_priority,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.modules.maintenance_management.services.work_request import MaintenanceWorkRequestValidationMixin
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository, UserRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization, Site


class MaintenanceWorkRequestService(MaintenanceWorkRequestValidationMixin):
    def __init__(
        self,
        session: Session,
        work_request_repo: MaintenanceWorkRequestRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        user_repo: UserRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        location_repo: MaintenanceLocationRepository,
        system_repo: MaintenanceSystemRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._work_request_repo = work_request_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._user_repo = user_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_work_requests(
        self,
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
        self._require_read("list maintenance work requests")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if component_id is not None:
            self._get_component(component_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        if location_id is not None:
            self._get_location(location_id, organization=organization)
        rows = self._work_request_repo.list_for_organization(
            organization.id,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            status=status,
            priority=priority,
            requested_by_user_id=requested_by_user_id,
            triaged_by_user_id=triaged_by_user_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_work_requests(
        self,
        *,
        search_text: str = "",
        site_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[MaintenanceWorkRequest]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_work_requests(
            site_id=site_id,
            status=status,
            priority=priority,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.work_request_code,
                        row.title,
                        row.description,
                        row.request_type,
                        row.status.value,
                        row.priority.value,
                        row.failure_symptom_code,
                        row.safety_risk_level,
                        row.production_impact_level,
                        row.requested_by_name_snapshot,
                    ],
                )
            ).lower()
        ]

    def get_work_request(self, work_request_id: str) -> MaintenanceWorkRequest:
        self._require_read("view maintenance work request")
        organization = self._active_organization()
        work_request = self._work_request_repo.get(work_request_id)
        if work_request is None or work_request.organization_id != organization.id:
            raise NotFoundError("Maintenance work request not found in the active organization.", code="MAINTENANCE_WORK_REQUEST_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "maintenance",
            work_request.id,
            "maintenance.read",
            operation_label="view maintenance work request",
        )
        return work_request

    def find_work_request_by_code(
        self,
        work_request_code: str,
    ) -> MaintenanceWorkRequest | None:
        self._require_read("resolve maintenance work request")
        organization = self._active_organization()
        work_request = self._work_request_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(work_request_code, label="Work request code"),
        )
        return work_request

    def create_work_request(
        self,
        *,
        site_id: str,
        work_request_code: str,
        source_type: str,
        request_type: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority=None,
        failure_symptom_code: str = "",
        safety_risk_level: str = "",
        production_impact_level: str = "",
        notes: str = "",
    ) -> MaintenanceWorkRequest:
        self._require_manage("create maintenance work request")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(work_request_code, label="Work request code")
        if self._work_request_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS")

        # Validate related entities
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if component_id is not None:
            self._get_component(component_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        if location_id is not None:
            self._get_location(location_id, organization=organization)

        # Get current user for requested_by
        requested_by_user_id = None
        requested_by_name_snapshot = ""
        if self._user_session and self._user_session.user_id:
            user = self._user_repo.get(self._user_session.user_id)
            if user:
                requested_by_user_id = user.id
                requested_by_name_snapshot = user.display_name or user.username or ""

        work_request = MaintenanceWorkRequest.create(
            organization_id=organization.id,
            site_id=site.id,
            work_request_code=normalized_code,
            source_type=source_type,
            request_type=request_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=normalize_optional_text(title),
            description=normalize_optional_text(description),
            priority=coerce_priority(priority),
            requested_by_user_id=requested_by_user_id,
            requested_by_name_snapshot=requested_by_name_snapshot,
            failure_symptom_code=normalize_optional_text(failure_symptom_code),
            safety_risk_level=normalize_optional_text(safety_risk_level),
            production_impact_level=normalize_optional_text(production_impact_level),
            notes=normalize_optional_text(notes),
        )
        try:
            self._work_request_repo.add(work_request)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_request.create", work_request)
        return work_request

    def update_work_request(
        self,
        work_request_id: str,
        *,
        work_request_code: str | None = None,
        request_type: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        priority=None,
        status=None,
        failure_symptom_code: str | None = None,
        safety_risk_level: str | None = None,
        production_impact_level: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkRequest:
        self._require_manage("update maintenance work request")
        work_request = self.get_work_request(work_request_id)

        if expected_version is not None and work_request.version != expected_version:
            raise ConcurrencyError(
                "Maintenance work request changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        # Validate status transition
        if status is not None:
            from core.modules.maintenance_management.domain import MaintenanceWorkRequestStatus
            new_status = MaintenanceWorkRequestStatus(status)
            self._validate_work_request_status_transition(work_request.status, new_status)
            work_request.status = new_status

            # Set triaged timestamp if moving to triaged
            if new_status == MaintenanceWorkRequestStatus.TRIAGED and work_request.triaged_at is None:
                work_request.triaged_at = datetime.now(timezone.utc)
                if self._user_session and self._user_session.user_id:
                    work_request.triaged_by_user_id = self._user_session.user_id

        if work_request_code is not None:
            normalized_code = normalize_maintenance_code(work_request_code, label="Work request code")
            existing = self._work_request_repo.get_by_code(work_request.organization_id, normalized_code)
            if existing is not None and existing.id != work_request.id:
                raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS")
            work_request.work_request_code = normalized_code

        if request_type is not None:
            work_request.request_type = request_type

        # Validate and update related entities
        if asset_id is not None:
            if asset_id:
                self._get_asset(asset_id, organization=self._active_organization())
            work_request.asset_id = asset_id
        if component_id is not None:
            if component_id:
                self._get_component(component_id, organization=self._active_organization())
            work_request.component_id = component_id
        if system_id is not None:
            if system_id:
                self._get_system(system_id, organization=self._active_organization())
            work_request.system_id = system_id
        if location_id is not None:
            if location_id:
                self._get_location(location_id, organization=self._active_organization())
            work_request.location_id = location_id

        if title is not None:
            work_request.title = normalize_optional_text(title)
        if description is not None:
            work_request.description = normalize_optional_text(description)
        if priority is not None:
            work_request.priority = coerce_priority(priority)
        if failure_symptom_code is not None:
            work_request.failure_symptom_code = normalize_optional_text(failure_symptom_code)
        if safety_risk_level is not None:
            work_request.safety_risk_level = normalize_optional_text(safety_risk_level)
        if production_impact_level is not None:
            work_request.production_impact_level = normalize_optional_text(production_impact_level)
        if notes is not None:
            work_request.notes = normalize_optional_text(notes)

        work_request.updated_at = datetime.now(timezone.utc)

        try:
            self._work_request_repo.update(work_request)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_request.update", work_request)
        return work_request

    def _get_asset(self, asset_id: str, *, organization: Organization) -> None:
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")

    def _get_component(self, component_id: str, *, organization: Organization) -> None:
        component = self._component_repo.get(component_id)
        if component is None or component.organization_id != organization.id:
            raise NotFoundError("Maintenance asset component not found in the active organization.", code="MAINTENANCE_COMPONENT_NOT_FOUND")

    def _get_system(self, system_id: str, *, organization: Organization) -> None:
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")

    def _get_location(self, location_id: str, *, organization: Organization) -> None:
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")

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

    def _record_change(self, action: str, work_request: MaintenanceWorkRequest) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_work_request",
            entity_id=work_request.id,
            details={
                "organization_id": work_request.organization_id,
                "site_id": work_request.site_id,
                "work_request_code": work_request.work_request_code,
                "source_type": work_request.source_type,
                "request_type": work_request.request_type,
                "status": work_request.status.value,
                "priority": work_request.priority.value,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_work_request",
                entity_id=work_request.id,
                source_event="maintenance_work_requests_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceWorkRequestService"]