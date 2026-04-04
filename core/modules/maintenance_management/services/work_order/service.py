from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceFailureCodeType, MaintenanceWorkOrder
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
    MaintenanceWorkRequestRepository,
)
from core.modules.maintenance_management.support import (
    coerce_priority,
    coerce_work_order_status,
    coerce_work_order_type,
    normalize_maintenance_code,
    normalize_optional_text,
)
from core.modules.maintenance_management.services.work_order.validation import MaintenanceWorkOrderValidationMixin
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository, UserRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization, Site


class MaintenanceWorkOrderService(MaintenanceWorkOrderValidationMixin):
    def __init__(
        self,
        session: Session,
        work_order_repo: MaintenanceWorkOrderRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        user_repo: UserRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        location_repo: MaintenanceLocationRepository,
        system_repo: MaintenanceSystemRepository,
        work_request_repo: MaintenanceWorkRequestRepository,
        failure_code_repo: MaintenanceFailureCodeRepository | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._work_order_repo = work_order_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._user_repo = user_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._work_request_repo = work_request_repo
        self._failure_code_repo = failure_code_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_work_orders(
        self,
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
        self._require_read("list maintenance work orders")
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
        rows = self._work_order_repo.list_for_organization(
            organization.id,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            status=status,
            priority=priority,
            assigned_employee_id=assigned_employee_id,
            assigned_team_id=assigned_team_id,
            planner_user_id=planner_user_id,
            supervisor_user_id=supervisor_user_id,
            work_order_type=work_order_type,
            is_preventive=is_preventive,
            is_emergency=is_emergency,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def search_work_orders(
        self,
        *,
        search_text: str = "",
        site_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        work_order_type: str | None = None,
    ) -> list[MaintenanceWorkOrder]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_work_orders(
            site_id=site_id,
            status=status,
            priority=priority,
            work_order_type=work_order_type,
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
                        row.work_order_code,
                        row.title,
                        row.description,
                        row.work_order_type.value,
                        row.status.value,
                        row.priority.value,
                        row.failure_code,
                        row.root_cause_code,
                    ],
                )
            ).lower()
        ]

    def get_work_order(self, work_order_id: str) -> MaintenanceWorkOrder:
        self._require_read("view maintenance work order")
        organization = self._active_organization()
        work_order = self._work_order_repo.get(work_order_id)
        if work_order is None or work_order.organization_id != organization.id:
            raise NotFoundError("Maintenance work order not found in the active organization.", code="MAINTENANCE_WORK_ORDER_NOT_FOUND")
        self._require_scope_read(self._scope_anchor_for(work_order), operation_label="view maintenance work order")
        return work_order

    def find_work_order_by_code(
        self,
        work_order_code: str,
    ) -> MaintenanceWorkOrder | None:
        self._require_read("resolve maintenance work order")
        organization = self._active_organization()
        work_order = self._work_order_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(work_order_code, label="Work order code"),
        )
        return work_order

    def create_work_order(
        self,
        *,
        site_id: str,
        work_order_code: str,
        work_order_type: str,
        source_type: str,
        source_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority=None,
        assigned_team_id: str | None = None,
        requires_shutdown: bool = False,
        permit_required: bool = False,
        approval_required: bool = False,
        vendor_party_id: str | None = None,
        is_preventive: bool = False,
        is_emergency: bool = False,
        notes: str = "",
    ) -> MaintenanceWorkOrder:
        self._require_manage("create maintenance work order")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(work_order_code, label="Work order code")
        normalized_work_order_type = coerce_work_order_type(work_order_type)
        normalized_source_type = normalize_maintenance_code(source_type, label="Source type")
        if self._work_order_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Work order code already exists in the active organization.", code="MAINTENANCE_WORK_ORDER_CODE_EXISTS")

        if normalized_source_type == "WORK_REQUEST":
            if not source_id:
                raise ValidationError(
                    "Source id is required when creating a work order from a work request.",
                    code="MAINTENANCE_WORK_ORDER_SOURCE_REQUIRED",
                )
            source_request = self._get_work_request(source_id, organization=organization)
            if source_request.site_id != site.id:
                raise ValidationError(
                    "Maintenance work order source must belong to the selected site.",
                    code="MAINTENANCE_WORK_ORDER_SITE_MISMATCH",
                )
            asset_id = asset_id if asset_id is not None else source_request.asset_id
            component_id = component_id if component_id is not None else source_request.component_id
            system_id = system_id if system_id is not None else source_request.system_id
            location_id = location_id if location_id is not None else source_request.location_id
            if not title:
                title = source_request.title
            if not description:
                description = source_request.description
            if priority is None:
                priority = source_request.priority

        asset_id, component_id, system_id, location_id = self._resolve_context_references(
            organization=organization,
            site=site,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
        )

        requested_by_user_id = self._current_user_id()

        work_order = MaintenanceWorkOrder.create(
            organization_id=organization.id,
            site_id=site.id,
            work_order_code=normalized_code,
            work_order_type=normalized_work_order_type,
            source_type=normalized_source_type,
            source_id=source_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=normalize_optional_text(title),
            description=normalize_optional_text(description),
            priority=coerce_priority(priority),
            requested_by_user_id=requested_by_user_id,
            assigned_team_id=assigned_team_id,
            requires_shutdown=bool(requires_shutdown),
            permit_required=bool(permit_required),
            approval_required=bool(approval_required),
            vendor_party_id=vendor_party_id,
            is_preventive=bool(is_preventive),
            is_emergency=bool(is_emergency),
            notes=normalize_optional_text(notes),
        )
        try:
            self._work_order_repo.add(work_order)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Work order code already exists in the active organization.", code="MAINTENANCE_WORK_ORDER_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order.create", work_order)
        return work_order

    def update_work_order(
        self,
        work_order_id: str,
        *,
        work_order_code: str | None = None,
        work_order_type: str | None = None,
        source_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        priority=None,
        status=None,
        planner_user_id: str | None = None,
        supervisor_user_id: str | None = None,
        assigned_team_id: str | None = None,
        assigned_employee_id: str | None = None,
        planned_start=None,
        planned_end=None,
        requires_shutdown: bool | None = None,
        permit_required: bool | None = None,
        approval_required: bool | None = None,
        failure_code: str | None = None,
        root_cause_code: str | None = None,
        downtime_minutes: int | None = None,
        parts_cost=None,
        labor_cost=None,
        vendor_party_id: str | None = None,
        is_preventive: bool | None = None,
        is_emergency: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceWorkOrder:
        self._require_manage("update maintenance work order")
        work_order = self.get_work_order(work_order_id)

        if expected_version is not None and work_order.version != expected_version:
            raise ConcurrencyError(
                "Maintenance work order changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        # Validate status transition
        if status is not None:
            from core.modules.maintenance_management.domain import MaintenanceWorkOrderStatus
            new_status = coerce_work_order_status(status)
            self._validate_work_order_status_transition(work_order.status, new_status)
            work_order.status = new_status

            # Set timestamps based on status changes
            now = datetime.now(timezone.utc)
            if new_status == MaintenanceWorkOrderStatus.IN_PROGRESS and work_order.actual_start is None:
                work_order.actual_start = now
            elif new_status in (MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.CANCELLED) and work_order.actual_end is None:
                work_order.actual_end = now
            elif new_status == MaintenanceWorkOrderStatus.CLOSED and work_order.closed_at is None:
                work_order.closed_at = now
                current_user_id = self._current_user_id()
                if current_user_id:
                    work_order.closed_by_user_id = current_user_id

        if work_order_code is not None:
            normalized_code = normalize_maintenance_code(work_order_code, label="Work order code")
            existing = self._work_order_repo.get_by_code(work_order.organization_id, normalized_code)
            if existing is not None and existing.id != work_order.id:
                raise ValidationError("Work order code already exists in the active organization.", code="MAINTENANCE_WORK_ORDER_CODE_EXISTS")
            work_order.work_order_code = normalized_code

        if work_order_type is not None:
            work_order.work_order_type = coerce_work_order_type(work_order_type)
        if source_id is not None:
            if work_order.source_type == "WORK_REQUEST":
                self._get_work_request(source_id, organization=self._active_organization())
            work_order.source_id = source_id

        organization = self._active_organization()
        site = self._get_site(work_order.site_id, organization=organization)
        resolved_asset_id, resolved_component_id, resolved_system_id, resolved_location_id = self._resolve_context_references(
            organization=organization,
            site=site,
            asset_id=asset_id if asset_id is not None else work_order.asset_id,
            component_id=component_id if component_id is not None else work_order.component_id,
            system_id=system_id if system_id is not None else work_order.system_id,
            location_id=location_id if location_id is not None else work_order.location_id,
        )
        work_order.asset_id = resolved_asset_id
        work_order.component_id = resolved_component_id
        work_order.system_id = resolved_system_id
        work_order.location_id = resolved_location_id

        if title is not None:
            work_order.title = normalize_optional_text(title)
        if description is not None:
            work_order.description = normalize_optional_text(description)
        if priority is not None:
            work_order.priority = coerce_priority(priority)
        if planner_user_id is not None:
            work_order.planner_user_id = planner_user_id
        if supervisor_user_id is not None:
            work_order.supervisor_user_id = supervisor_user_id
        if assigned_team_id is not None:
            work_order.assigned_team_id = assigned_team_id
        if assigned_employee_id is not None:
            work_order.assigned_employee_id = assigned_employee_id
        if planned_start is not None:
            work_order.planned_start = planned_start
        if planned_end is not None:
            work_order.planned_end = planned_end
        if requires_shutdown is not None:
            work_order.requires_shutdown = bool(requires_shutdown)
        if permit_required is not None:
            work_order.permit_required = bool(permit_required)
        if approval_required is not None:
            work_order.approval_required = bool(approval_required)
        if failure_code is not None:
            work_order.failure_code = self._normalize_failure_code(
                failure_code,
                organization=organization,
                expected_type=MaintenanceFailureCodeType.SYMPTOM,
                label="Failure code",
                not_found_code="MAINTENANCE_FAILURE_CODE_NOT_FOUND",
                invalid_code="MAINTENANCE_FAILURE_CODE_INVALID",
            )
        if root_cause_code is not None:
            work_order.root_cause_code = self._normalize_failure_code(
                root_cause_code,
                organization=organization,
                expected_type=MaintenanceFailureCodeType.CAUSE,
                label="Root cause code",
                not_found_code="MAINTENANCE_ROOT_CAUSE_CODE_NOT_FOUND",
                invalid_code="MAINTENANCE_ROOT_CAUSE_CODE_INVALID",
            )
        if downtime_minutes is not None:
            work_order.downtime_minutes = downtime_minutes
        if parts_cost is not None:
            work_order.parts_cost = parts_cost
        if labor_cost is not None:
            work_order.labor_cost = labor_cost
        if vendor_party_id is not None:
            work_order.vendor_party_id = vendor_party_id
        if is_preventive is not None:
            work_order.is_preventive = bool(is_preventive)
        if is_emergency is not None:
            work_order.is_emergency = bool(is_emergency)
        if notes is not None:
            work_order.notes = normalize_optional_text(notes)

        work_order.updated_at = datetime.now(timezone.utc)

        try:
            self._work_order_repo.update(work_order)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Work order code already exists in the active organization.", code="MAINTENANCE_WORK_ORDER_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_work_order.update", work_order)
        return work_order

    def _get_asset(self, asset_id: str, *, organization: Organization):
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_component(self, component_id: str, *, organization: Organization):
        component = self._component_repo.get(component_id)
        if component is None or component.organization_id != organization.id:
            raise NotFoundError("Maintenance asset component not found in the active organization.", code="MAINTENANCE_COMPONENT_NOT_FOUND")
        return component

    def _get_system(self, system_id: str, *, organization: Organization):
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _get_location(self, location_id: str, *, organization: Organization):
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _get_work_request(self, work_request_id: str, *, organization: Organization):
        work_request = self._work_request_repo.get(work_request_id)
        if work_request is None or work_request.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work request not found in the active organization.",
                code="MAINTENANCE_WORK_REQUEST_NOT_FOUND",
            )
        return work_request

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _normalize_failure_code(
        self,
        value: str | None,
        *,
        organization: Organization,
        expected_type: MaintenanceFailureCodeType,
        label: str,
        not_found_code: str,
        invalid_code: str,
    ) -> str:
        normalized = normalize_optional_text(value).upper()
        if not normalized or self._failure_code_repo is None:
            return normalized
        failure_code = self._failure_code_repo.get_by_code(organization.id, normalized)
        if failure_code is None:
            raise ValidationError(f"{label} not found in the active organization.", code=not_found_code)
        if failure_code.code_type != expected_type:
            raise ValidationError(
                f"{label} must use a {expected_type.value} maintenance failure code.",
                code=invalid_code,
            )
        return normalized

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _record_change(self, action: str, work_order: MaintenanceWorkOrder) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_work_order",
            entity_id=work_order.id,
            details={
                "organization_id": work_order.organization_id,
                "site_id": work_order.site_id,
                "work_order_code": work_order.work_order_code,
                "work_order_type": work_order.work_order_type.value,
                "source_type": work_order.source_type,
                "status": work_order.status.value,
                "priority": work_order.priority.value,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_work_order",
                entity_id=work_order.id,
                source_event="maintenance_work_orders_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        return getattr(principal, "user_id", None) if principal is not None else None

    def _scope_anchor_for(self, work_order: MaintenanceWorkOrder) -> str:
        if work_order.asset_id:
            return work_order.asset_id
        if work_order.component_id:
            component = self._component_repo.get(work_order.component_id)
            if component is not None and component.asset_id:
                return component.asset_id
        if work_order.system_id:
            return work_order.system_id
        if work_order.location_id:
            return work_order.location_id
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
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
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
                "Maintenance work order asset must belong to the selected site.",
                code="MAINTENANCE_WORK_ORDER_SITE_MISMATCH",
            )
        if component is not None:
            component_asset = self._get_asset(component.asset_id, organization=organization)
            if component_asset.site_id != site.id:
                raise ValidationError(
                    "Maintenance work order component must belong to the selected site.",
                    code="MAINTENANCE_WORK_ORDER_SITE_MISMATCH",
                )
            if asset is not None and component.asset_id != asset.id:
                raise ValidationError(
                    "Maintenance work order component must belong to the selected asset.",
                    code="MAINTENANCE_WORK_ORDER_COMPONENT_ASSET_MISMATCH",
                )
            if asset is None:
                asset = component_asset
                asset_id = component_asset.id
        if system is not None and system.site_id != site.id:
            raise ValidationError(
                "Maintenance work order system must belong to the selected site.",
                code="MAINTENANCE_WORK_ORDER_SITE_MISMATCH",
            )
        if location is not None and location.site_id != site.id:
            raise ValidationError(
                "Maintenance work order location must belong to the selected site.",
                code="MAINTENANCE_WORK_ORDER_SITE_MISMATCH",
            )
        return asset_id, component_id, system_id, location_id


__all__ = ["MaintenanceWorkOrderService"]
