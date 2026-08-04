from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceFailureCodeType,
    MaintenanceLocation,
    MaintenancePriority,
    MaintenanceSystem,
    MaintenanceWorkRequest,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkRequestRepository,
)
from src.core.modules.maintenance.application.common.support import (
    normalize_maintenance_code,
    normalize_optional_text,
)
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.modules.maintenance.application.work_requests.validation import (
    MaintenanceWorkRequestValidationMixin,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.contracts import UserRepository
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization
from src.core.platform.domain.master_data.site import Site


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
        failure_code_repo: MaintenanceFailureCodeRepository | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session: Session = session
        self._work_request_repo: MaintenanceWorkRequestRepository = work_request_repo
        self._organization_repo: OrganizationRepository = organization_repo
        self._tenant_context_service: TenantContextService = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceWorkRequestService",
        )
        self._site_repo: SiteRepository = site_repo
        self._user_repo: UserRepository = user_repo
        self._asset_repo: MaintenanceAssetRepository = asset_repo
        self._component_repo: MaintenanceAssetComponentRepository = component_repo
        self._location_repo: MaintenanceLocationRepository = location_repo
        self._system_repo: MaintenanceSystemRepository = system_repo
        self._failure_code_repo: MaintenanceFailureCodeRepository | None = failure_code_repo
        self._user_session = user_session
        self._activity_service = activity_service

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
            scope_id_getter=self._scope_anchor_for,
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
        self._require_scope_read(self._scope_anchor_for(work_request), operation_label="view maintenance work request")
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
        source_id: str | None = None,
        source_plan_task_ids: tuple[str, ...] = (),
        request_type: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority | str | None = None,
        failure_symptom_code: str = "",
        safety_risk_level: str = "",
        production_impact_level: str = "",
        notes: str = "",
    ) -> MaintenanceWorkRequest:
        self._require_manage("create maintenance work request")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        asset_id, component_id, system_id, location_id = self._resolve_context_references(
            organization=organization,
            site=site,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
        )

        requested_by_user_id = self._current_user_id()
        requested_by_name_snapshot = ""
        if requested_by_user_id:
            user = self._user_repo.get(requested_by_user_id)
            if user:
                requested_by_user_id = user.id
                requested_by_name_snapshot = user.display_name or user.username or ""

        work_request = MaintenanceWorkRequest.create(
            organization_id=organization.id,
            site_id=site.id,
            work_request_code=work_request_code,
            source_type=source_type,
            source_id=source_id,
            source_plan_task_ids=source_plan_task_ids,
            request_type=request_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=title,
            description=description,
            priority=priority,
            requested_by_user_id=requested_by_user_id,
            requested_by_name_snapshot=requested_by_name_snapshot,
            failure_symptom_code=failure_symptom_code,
            safety_risk_level=safety_risk_level,
            production_impact_level=production_impact_level,
            notes=notes,
        )
        if self._work_request_repo.get_by_code(organization.id, work_request.work_request_code) is not None:
            raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS")
        if (
            work_request.source_type == MaintenanceWorkRequestSourceType.PREVENTIVE_PLAN
            and not work_request.source_id
        ):
            raise ValidationError(
                "Preventive maintenance work requests must retain their source plan id.",
                code="MAINTENANCE_WORK_REQUEST_SOURCE_REQUIRED",
            )
        work_request = replace(
            work_request,
            failure_symptom_code=self._normalize_failure_symptom_code(
                work_request.failure_symptom_code,
                organization=organization,
            ),
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
        priority: MaintenancePriority | str | None = None,
        status: str | None = None,
        failure_symptom_code: str | None = None,
        safety_risk_level: str | None = None,
        production_impact_level: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkRequest:
        self._require_manage("update maintenance work request")
        work_request = self.get_work_request(work_request_id)
        organization = self._active_organization()

        if expected_version is not None and work_request.version != expected_version:
            raise ConcurrencyError(
                "Maintenance work request changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        site = self._get_site(work_request.site_id, organization=organization)
        resolved_asset_id, resolved_component_id, resolved_system_id, resolved_location_id = self._resolve_context_references(
            organization=organization,
            site=site,
            asset_id=asset_id if asset_id is not None else work_request.asset_id,
            component_id=component_id if component_id is not None else work_request.component_id,
            system_id=system_id if system_id is not None else work_request.system_id,
            location_id=location_id if location_id is not None else work_request.location_id,
        )
        now = datetime.now(timezone.utc)
        updated = replace(
            work_request,
            work_request_code=work_request.work_request_code if work_request_code is None else work_request_code,
            request_type=work_request.request_type if request_type is None else request_type,
            asset_id=resolved_asset_id,
            component_id=resolved_component_id,
            system_id=resolved_system_id,
            location_id=resolved_location_id,
            title=work_request.title if title is None else title,
            description=work_request.description if description is None else description,
            priority=work_request.priority if priority is None else priority,
            status=work_request.status if status is None else status,
            failure_symptom_code=(
                work_request.failure_symptom_code
                if failure_symptom_code is None
                else failure_symptom_code
            ),
            safety_risk_level=(
                work_request.safety_risk_level
                if safety_risk_level is None
                else safety_risk_level
            ),
            production_impact_level=(
                work_request.production_impact_level
                if production_impact_level is None
                else production_impact_level
            ),
            notes=work_request.notes if notes is None else notes,
            updated_at=now,
        )
        if (
            updated.source_type == MaintenanceWorkRequestSourceType.PREVENTIVE_PLAN
            and not updated.source_id
        ):
            raise ValidationError(
                "Preventive maintenance work requests must retain their source plan id.",
                code="MAINTENANCE_WORK_REQUEST_SOURCE_REQUIRED",
            )
        if status is not None:
            self._validate_work_request_status_transition(work_request.status, updated.status)
            if updated.status == MaintenanceWorkRequestStatus.TRIAGED and work_request.triaged_at is None:
                current_user_id = self._current_user_id()
                updated = replace(
                    updated,
                    triaged_at=now,
                    triaged_by_user_id=current_user_id or updated.triaged_by_user_id,
                )
        updated = replace(
            updated,
            failure_symptom_code=self._normalize_failure_symptom_code(
                updated.failure_symptom_code,
                organization=organization,
            ),
        )
        if work_request_code is not None:
            existing = self._work_request_repo.get_by_code(updated.organization_id, updated.work_request_code)
            if existing is not None and existing.id != updated.id:
                raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS")

        try:
            self._work_request_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Work request code already exists in the active organization.", code="MAINTENANCE_WORK_REQUEST_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_request.update", updated)
        return updated

    def _get_asset(self, asset_id: str, *, organization: Organization) -> MaintenanceAsset:
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_component(self, component_id: str, *, organization: Organization) -> MaintenanceAssetComponent:
        component = self._component_repo.get(component_id)
        if component is None or component.organization_id != organization.id:
            raise NotFoundError("Maintenance asset component not found in the active organization.", code="MAINTENANCE_COMPONENT_NOT_FOUND")
        return component

    def _get_system(self, system_id: str, *, organization: Organization) -> MaintenanceSystem:
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _get_location(self, location_id: str, *, organization: Organization) -> MaintenanceLocation:
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance work requests"
        ).organization

    def _normalize_failure_symptom_code(
        self,
        value: str | None,
        *,
        organization: Organization,
    ) -> str:
        normalized = normalize_optional_text(value).upper()
        if not normalized or self._failure_code_repo is None:
            return normalized
        failure_code = self._failure_code_repo.get_by_code(organization.id, normalized)
        if failure_code is None:
            raise ValidationError(
                "Failure symptom code not found in the active organization.",
                code="MAINTENANCE_FAILURE_SYMPTOM_CODE_NOT_FOUND",
            )
        if failure_code.code_type != MaintenanceFailureCodeType.SYMPTOM:
            raise ValidationError(
                "Failure symptom code must use a SYMPTOM maintenance failure code.",
                code="MAINTENANCE_FAILURE_SYMPTOM_CODE_INVALID",
            )
        return normalized

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _record_change(self, action: str, work_request: MaintenanceWorkRequest) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_work_request",
            entity_id=work_request.id,
            module="maintenance",
            details={
                "organization_id": work_request.organization_id,
                "site_id": work_request.site_id,
                "work_request_code": work_request.work_request_code,
                "source_type": work_request.source_type.value,
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

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        return getattr(principal, "user_id", None) if principal is not None else None

    def _scope_anchor_for(self, work_request: MaintenanceWorkRequest) -> str:
        if work_request.asset_id:
            return work_request.asset_id
        if work_request.component_id:
            component = self._component_repo.get(work_request.component_id)
            if component is not None and component.asset_id:
                return component.asset_id
        if work_request.system_id:
            return work_request.system_id
        if work_request.location_id:
            return work_request.location_id
        return ""

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. The record is "
                    "not anchored to a maintenance scope grant."
                ),
            )

    def _resolve_context_references(
        self,
        *,
        organization: Organization,
        site: Site,
        asset_id: str | None,
        component_id: str | None,
        system_id: str | None,
        location_id: str | None,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        asset = self._get_asset(asset_id, organization=organization) if asset_id else None
        component = self._get_component(component_id, organization=organization) if component_id else None
        system = self._get_system(system_id, organization=organization) if system_id else None
        location = self._get_location(location_id, organization=organization) if location_id else None

        if asset is not None and asset.site_id != site.id:
            raise ValidationError(
                "Maintenance work request asset must belong to the selected site.",
                code="MAINTENANCE_WORK_REQUEST_SITE_MISMATCH",
            )
        if component is not None:
            component_asset = self._get_asset(component.asset_id, organization=organization)
            if component_asset.site_id != site.id:
                raise ValidationError(
                    "Maintenance work request component must belong to the selected site.",
                    code="MAINTENANCE_WORK_REQUEST_SITE_MISMATCH",
                )
            if asset is not None and component.asset_id != asset.id:
                raise ValidationError(
                    "Maintenance work request component must belong to the selected asset.",
                    code="MAINTENANCE_WORK_REQUEST_COMPONENT_ASSET_MISMATCH",
                )
            if asset is None:
                asset = component_asset
                asset_id = component_asset.id
        if system is not None and system.site_id != site.id:
            raise ValidationError(
                "Maintenance work request system must belong to the selected site.",
                code="MAINTENANCE_WORK_REQUEST_SITE_MISMATCH",
            )
        if location is not None and location.site_id != site.id:
            raise ValidationError(
                "Maintenance work request location must belong to the selected site.",
                code="MAINTENANCE_WORK_REQUEST_SITE_MISMATCH",
            )
        return asset_id, component_id, system_id, location_id


__all__ = ["MaintenanceWorkRequestService"]
