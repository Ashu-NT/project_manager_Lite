from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceDowntimeEvent, MaintenanceWorkOrder
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceDowntimeEventRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
)
from core.modules.maintenance_management.support import (
    calculate_downtime_minutes,
    coerce_optional_datetime,
    normalize_maintenance_name,
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization


class MaintenanceDowntimeEventService:
    def __init__(
        self,
        session: Session,
        downtime_event_repo: MaintenanceDowntimeEventRepository,
        *,
        organization_repo: OrganizationRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        system_repo: MaintenanceSystemRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._downtime_event_repo = downtime_event_repo
        self._organization_repo = organization_repo
        self._work_order_repo = work_order_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._system_repo = system_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_downtime_events(
        self,
        *,
        work_order_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        downtime_type: str | None = None,
        reason_code: str | None = None,
        open_only: bool | None = None,
        started_from=None,
        started_to=None,
    ) -> list[MaintenanceDowntimeEvent]:
        self._require_read("list maintenance downtime events")
        organization = self._active_organization()
        if work_order_id is not None:
            work_order = self._get_work_order(work_order_id, organization=organization)
            self._require_scope_read(
                self._scope_anchor_for_work_order(work_order),
                operation_label="list maintenance downtime events",
            )
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        rows = self._downtime_event_repo.list_for_organization(
            organization.id,
            work_order_id=normalize_optional_text(work_order_id) or None,
            asset_id=normalize_optional_text(asset_id) or None,
            system_id=normalize_optional_text(system_id) or None,
            downtime_type=normalize_optional_text(downtime_type).upper() or None,
            reason_code=normalize_optional_text(reason_code).upper() or None,
            open_only=open_only,
            started_from=coerce_optional_datetime(started_from, label="Start from"),
            started_to=coerce_optional_datetime(started_to, label="Start to"),
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def search_downtime_events(
        self,
        *,
        search_text: str = "",
        work_order_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        open_only: bool | None = None,
    ) -> list[MaintenanceDowntimeEvent]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_downtime_events(
            work_order_id=work_order_id,
            asset_id=asset_id,
            system_id=system_id,
            open_only=open_only,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(None, [row.downtime_type, row.reason_code, row.impact_notes])
            ).lower()
        ]

    def get_downtime_event(self, downtime_event_id: str) -> MaintenanceDowntimeEvent:
        self._require_read("view maintenance downtime event")
        row = self._get_downtime_event(downtime_event_id, organization=self._active_organization())
        self._require_scope_read(
            self._scope_anchor_for(row),
            operation_label="view maintenance downtime event",
        )
        return row

    def create_downtime_event(
        self,
        *,
        started_at,
        downtime_type: str,
        work_order_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        ended_at=None,
        reason_code: str = "",
        impact_notes: str = "",
    ) -> MaintenanceDowntimeEvent:
        self._require_manage("create maintenance downtime event")
        organization = self._active_organization()
        context = self._resolve_context(
            organization=organization,
            work_order_id=work_order_id,
            asset_id=asset_id,
            system_id=system_id,
            operation_label="create maintenance downtime event",
        )
        resolved_started_at = coerce_optional_datetime(started_at, label="Downtime start")
        if resolved_started_at is None:
            raise ValidationError(
                "Downtime start is required.",
                code="MAINTENANCE_DOWNTIME_START_REQUIRED",
            )
        resolved_ended_at = coerce_optional_datetime(ended_at, label="Downtime end")
        row = MaintenanceDowntimeEvent.create(
            organization_id=organization.id,
            work_order_id=context.work_order.id if context.work_order is not None else None,
            asset_id=context.asset_id,
            system_id=context.system_id,
            started_at=resolved_started_at,
            ended_at=resolved_ended_at,
            duration_minutes=calculate_downtime_minutes(resolved_started_at, resolved_ended_at),
            downtime_type=normalize_maintenance_name(downtime_type, label="Downtime type").upper(),
            reason_code=normalize_optional_text(reason_code).upper(),
            impact_notes=normalize_optional_text(impact_notes),
        )
        try:
            self._downtime_event_repo.add(row)
            self._sync_work_order_downtime_minutes(context.work_order)
            self._session.commit()
            self._session.expire_all()
        except IntegrityError:
            self._session.rollback()
            raise
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_downtime_event.create", row)
        return row

    def update_downtime_event(
        self,
        downtime_event_id: str,
        *,
        work_order_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        started_at=None,
        ended_at=None,
        downtime_type: str | None = None,
        reason_code: str | None = None,
        impact_notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceDowntimeEvent:
        self._require_manage("update maintenance downtime event")
        organization = self._active_organization()
        row = self.get_downtime_event(downtime_event_id)
        if expected_version is not None and row.version != expected_version:
            raise ConcurrencyError(
                "Maintenance downtime event changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        previous_work_order = self._get_work_order(row.work_order_id, organization=organization) if row.work_order_id else None
        context = self._resolve_context(
            organization=organization,
            work_order_id=row.work_order_id if work_order_id is None else work_order_id,
            asset_id=row.asset_id if asset_id is None else asset_id,
            system_id=row.system_id if system_id is None else system_id,
            operation_label="update maintenance downtime event",
        )
        row.work_order_id = context.work_order.id if context.work_order is not None else None
        row.asset_id = context.asset_id
        row.system_id = context.system_id
        if started_at is not None:
            resolved_started_at = coerce_optional_datetime(started_at, label="Downtime start")
            if resolved_started_at is None:
                raise ValidationError(
                    "Downtime start is required.",
                    code="MAINTENANCE_DOWNTIME_START_REQUIRED",
                )
            row.started_at = resolved_started_at
        if ended_at is not None:
            row.ended_at = coerce_optional_datetime(ended_at, label="Downtime end")
        if row.started_at is None:
            raise ValidationError(
                "Downtime start is required.",
                code="MAINTENANCE_DOWNTIME_START_REQUIRED",
            )
        row.duration_minutes = calculate_downtime_minutes(row.started_at, row.ended_at)
        if downtime_type is not None:
            row.downtime_type = normalize_maintenance_name(downtime_type, label="Downtime type").upper()
        if reason_code is not None:
            row.reason_code = normalize_optional_text(reason_code).upper()
        if impact_notes is not None:
            row.impact_notes = normalize_optional_text(impact_notes)
        row.updated_at = datetime.now(timezone.utc)
        try:
            self._downtime_event_repo.update(row)
            affected_work_orders: list[MaintenanceWorkOrder] = []
            if previous_work_order is not None:
                affected_work_orders.append(previous_work_order)
            if context.work_order is not None and all(
                existing.id != context.work_order.id for existing in affected_work_orders
            ):
                affected_work_orders.append(context.work_order)
            for work_order in affected_work_orders:
                self._sync_work_order_downtime_minutes(work_order)
            self._session.commit()
            self._session.expire_all()
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_downtime_event.update", row)
        return row

    def _resolve_context(
        self,
        *,
        organization: Organization,
        work_order_id: str | None,
        asset_id: str | None,
        system_id: str | None,
        operation_label: str,
    ) -> _DowntimeContext:
        work_order = self._get_work_order(work_order_id, organization=organization) if normalize_optional_text(work_order_id) else None
        asset = self._get_asset(asset_id, organization=organization) if normalize_optional_text(asset_id) else None
        system = self._get_system(system_id, organization=organization) if normalize_optional_text(system_id) else None
        if work_order is not None:
            if asset is None and work_order.asset_id:
                asset = self._get_asset(work_order.asset_id, organization=organization)
            if system is None and work_order.system_id:
                system = self._get_system(work_order.system_id, organization=organization)
            if asset is not None and work_order.asset_id and work_order.asset_id != asset.id:
                raise ValidationError(
                    "Downtime event asset must match the selected work order asset.",
                    code="MAINTENANCE_DOWNTIME_WORK_ORDER_ASSET_MISMATCH",
                )
            if system is not None and work_order.system_id and work_order.system_id != system.id:
                raise ValidationError(
                    "Downtime event system must match the selected work order system.",
                    code="MAINTENANCE_DOWNTIME_WORK_ORDER_SYSTEM_MISMATCH",
                )
        if asset is None and system is None and work_order is None:
            raise ValidationError(
                "Downtime event must be linked to a work order, asset, or system.",
                code="MAINTENANCE_DOWNTIME_CONTEXT_REQUIRED",
            )
        if asset is not None and system is not None and asset.system_id and asset.system_id != system.id:
            raise ValidationError(
                "Downtime event asset is already anchored to a different maintenance system.",
                code="MAINTENANCE_DOWNTIME_SYSTEM_MISMATCH",
            )
        scope_id = ""
        if asset is not None:
            scope_id = asset.id
        elif system is not None:
            scope_id = system.id
        elif work_order is not None:
            scope_id = self._scope_anchor_for_work_order(work_order)
        self._require_scope_manage(scope_id, operation_label=operation_label)
        return _DowntimeContext(
            work_order=work_order,
            asset_id=asset.id if asset is not None else None,
            system_id=system.id if system is not None else None,
        )

    def _scope_anchor_for(self, row: MaintenanceDowntimeEvent) -> str:
        if row.asset_id:
            return row.asset_id
        if row.system_id:
            return row.system_id
        if row.work_order_id:
            work_order = self._work_order_repo.get(row.work_order_id)
            if work_order is not None:
                return self._scope_anchor_for_work_order(work_order)
        return ""

    def _scope_anchor_for_work_order(self, work_order: MaintenanceWorkOrder) -> str:
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

    def _sync_work_order_downtime_minutes(self, work_order: MaintenanceWorkOrder | None) -> None:
        if work_order is None:
            return
        self._session.flush()
        rows = self._downtime_event_repo.list_for_organization(
            work_order.organization_id,
            work_order_id=work_order.id,
        )
        work_order.downtime_minutes = sum(row.duration_minutes or 0 for row in rows) or None
        work_order.updated_at = datetime.now(timezone.utc)
        self._work_order_repo.update(work_order)

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_work_order(self, work_order_id: str, *, organization: Organization) -> MaintenanceWorkOrder:
        work_order = self._work_order_repo.get(work_order_id)
        if work_order is None or work_order.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance work order not found in the active organization.",
                code="MAINTENANCE_WORK_ORDER_NOT_FOUND",
            )
        return work_order

    def _get_asset(self, asset_id: str, *, organization: Organization):
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_system(self, system_id: str, *, organization: Organization):
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _get_downtime_event(
        self,
        downtime_event_id: str,
        *,
        organization: Organization,
    ) -> MaintenanceDowntimeEvent:
        row = self._downtime_event_repo.get(downtime_event_id)
        if row is None or row.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance downtime event not found in the active organization.",
                code="MAINTENANCE_DOWNTIME_EVENT_NOT_FOUND",
            )
        return row

    def _record_change(self, action: str, row: MaintenanceDowntimeEvent) -> None:
        record_audit(
            self,
            action=action,
            entity_type="maintenance_downtime_event",
            entity_id=row.id,
            details={
                "organization_id": row.organization_id,
                "work_order_id": row.work_order_id,
                "asset_id": row.asset_id,
                "system_id": row.system_id,
                "started_at": row.started_at.isoformat() if row.started_at is not None else None,
                "ended_at": row.ended_at.isoformat() if row.ended_at is not None else None,
                "duration_minutes": row.duration_minutes,
                "downtime_type": row.downtime_type,
                "reason_code": row.reason_code,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_downtime_event",
                entity_id=row.id,
                source_event="maintenance_downtime_events_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)

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

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.manage",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )


class _DowntimeContext:
    def __init__(
        self,
        *,
        work_order: MaintenanceWorkOrder | None,
        asset_id: str | None,
        system_id: str | None,
    ) -> None:
        self.work_order = work_order
        self.asset_id = asset_id
        self.system_id = system_id


__all__ = ["MaintenanceDowntimeEventService"]
