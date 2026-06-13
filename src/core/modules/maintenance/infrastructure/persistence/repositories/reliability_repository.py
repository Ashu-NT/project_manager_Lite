from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenanceDowntimeEvent, MaintenanceFailureCode
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceDowntimeEventRepository,
    MaintenanceFailureCodeRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.mappers import (
    maintenance_downtime_event_from_orm,
    maintenance_downtime_event_to_orm,
    maintenance_failure_code_from_orm,
    maintenance_failure_code_to_orm,
)
from src.core.modules.maintenance.infrastructure.persistence.orm.models import (
    MaintenanceAssetORM,
    MaintenanceDowntimeEventORM,
    MaintenanceFailureCodeORM,
    MaintenanceSystemORM,
    MaintenanceWorkOrderORM,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories._tenant_scope import (
    MaintenanceParentScopedRepositorySupport,
    MaintenanceTenantScopedRepositorySupport,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyMaintenanceFailureCodeRepository(
    MaintenanceFailureCodeRepository, MaintenanceTenantScopedRepositorySupport
):
    _repository_label = "Maintenance failure code repository"

    def __init__(
        self,
        session: Session,
        *,
        tenant_context_service: TenantContextService | None = None,
    ):
        self.session = session
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label=type(self).__name__,
        )

    def add(self, failure_code: MaintenanceFailureCode) -> None:
        ctx = self._context(operation_label="add maintenance failure code")
        orm = maintenance_failure_code_to_orm(failure_code)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def update(self, failure_code: MaintenanceFailureCode) -> None:
        self._require_in_scope(
            MaintenanceFailureCodeORM,
            failure_code.id,
            operation_label="update maintenance failure code",
            not_found_message="Maintenance failure code not found.",
        )
        failure_code.version = update_with_version_check(
            self.session,
            MaintenanceFailureCodeORM,
            failure_code.id,
            getattr(failure_code, "version", 1),
            {
                "failure_code": failure_code.failure_code,
                "name": failure_code.name,
                "description": failure_code.description or None,
                "code_type": failure_code.code_type,
                "parent_code_id": failure_code.parent_code_id,
                "is_active": failure_code.is_active,
                "created_at": failure_code.created_at,
                "updated_at": failure_code.updated_at,
            },
            not_found_message="Maintenance failure code not found.",
            stale_message="Maintenance failure code was updated by another user.",
        )

    def get(self, failure_code_id: str) -> MaintenanceFailureCode | None:
        obj = self._get_in_scope(
            MaintenanceFailureCodeORM,
            failure_code_id,
            operation_label="get maintenance failure code",
        )
        return maintenance_failure_code_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        failure_code: str,
    ) -> MaintenanceFailureCode | None:
        ctx = self._context(operation_label="get maintenance failure code by code")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(MaintenanceFailureCodeORM).where(
            MaintenanceFailureCodeORM.organization_id == organization_id,
            MaintenanceFailureCodeORM.failure_code == failure_code,
        )
        stmt = self._apply_scope(stmt, MaintenanceFailureCodeORM, ctx)
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_failure_code_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        code_type: str | None = None,
        parent_code_id: str | None = None,
    ) -> list[MaintenanceFailureCode]:
        ctx = self._context(operation_label="list maintenance failure codes")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(MaintenanceFailureCodeORM).where(
            MaintenanceFailureCodeORM.organization_id == organization_id
        )
        stmt = self._apply_scope(stmt, MaintenanceFailureCodeORM, ctx)
        if active_only is not None:
            stmt = stmt.where(MaintenanceFailureCodeORM.is_active == bool(active_only))
        if code_type is not None:
            stmt = stmt.where(MaintenanceFailureCodeORM.code_type == code_type)
        if parent_code_id is not None:
            stmt = stmt.where(MaintenanceFailureCodeORM.parent_code_id == parent_code_id)
        rows = self.session.execute(
            stmt.order_by(MaintenanceFailureCodeORM.code_type.asc(), MaintenanceFailureCodeORM.failure_code.asc())
        ).scalars().all()
        return [maintenance_failure_code_from_orm(row) for row in rows]


class SqlAlchemyMaintenanceDowntimeEventRepository(
    MaintenanceDowntimeEventRepository, MaintenanceParentScopedRepositorySupport
):
    _repository_label = "Maintenance downtime event repository"

    def __init__(
        self,
        session: Session,
        *,
        tenant_context_service: TenantContextService | None = None,
    ):
        self.session = session
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label=type(self).__name__,
        )

    def _downtime_references_in_scope(
        self,
        downtime_event: MaintenanceDowntimeEvent | MaintenanceDowntimeEventORM,
        *,
        operation_label: str,
    ) -> bool:
        if downtime_event.work_order_id and self._get_in_scope(
            MaintenanceWorkOrderORM,
            downtime_event.work_order_id,
            operation_label=f"{operation_label} work order",
        ) is None:
            return False
        if downtime_event.asset_id and self._get_in_scope(
            MaintenanceAssetORM,
            downtime_event.asset_id,
            operation_label=f"{operation_label} asset",
        ) is None:
            return False
        if downtime_event.system_id and self._get_in_scope(
            MaintenanceSystemORM,
            downtime_event.system_id,
            operation_label=f"{operation_label} system",
        ) is None:
            return False
        return True

    def _require_downtime_references_in_scope(
        self,
        downtime_event: MaintenanceDowntimeEvent | MaintenanceDowntimeEventORM,
        *,
        operation_label: str,
    ) -> None:
        if downtime_event.work_order_id:
            self._require_in_scope(
                MaintenanceWorkOrderORM,
                downtime_event.work_order_id,
                operation_label=f"{operation_label} work order",
                not_found_message="Maintenance work order not found.",
            )
        if downtime_event.asset_id:
            self._require_in_scope(
                MaintenanceAssetORM,
                downtime_event.asset_id,
                operation_label=f"{operation_label} asset",
                not_found_message="Maintenance asset not found.",
            )
        if downtime_event.system_id:
            self._require_in_scope(
                MaintenanceSystemORM,
                downtime_event.system_id,
                operation_label=f"{operation_label} system",
                not_found_message="Maintenance system not found.",
            )

    def _get_downtime_event_in_scope(
        self,
        downtime_event_id: str,
        *,
        operation_label: str,
    ):
        ctx = self._context(operation_label=operation_label)
        stmt = select(MaintenanceDowntimeEventORM).where(
            MaintenanceDowntimeEventORM.id == downtime_event_id,
            MaintenanceDowntimeEventORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        if obj is None or not self._downtime_references_in_scope(
            obj,
            operation_label=operation_label,
        ):
            return None
        return obj

    def add(self, downtime_event: MaintenanceDowntimeEvent) -> None:
        self._context(operation_label="add maintenance downtime event")
        self._require_downtime_references_in_scope(
            downtime_event,
            operation_label="add maintenance downtime event",
        )
        self.session.add(maintenance_downtime_event_to_orm(downtime_event))

    def update(self, downtime_event: MaintenanceDowntimeEvent) -> None:
        if self._get_downtime_event_in_scope(
            downtime_event.id,
            operation_label="update maintenance downtime event",
        ) is None:
            raise NotFoundError("Maintenance downtime event not found.")
        self._require_downtime_references_in_scope(
            downtime_event,
            operation_label="update maintenance downtime event",
        )
        downtime_event.version = update_with_version_check(
            self.session,
            MaintenanceDowntimeEventORM,
            downtime_event.id,
            getattr(downtime_event, "version", 1),
            {
                "asset_id": downtime_event.asset_id,
                "system_id": downtime_event.system_id,
                "work_order_id": downtime_event.work_order_id,
                "started_at": downtime_event.started_at,
                "ended_at": downtime_event.ended_at,
                "duration_minutes": downtime_event.duration_minutes,
                "downtime_type": downtime_event.downtime_type,
                "reason_code": downtime_event.reason_code,
                "impact_notes": downtime_event.impact_notes,
                "created_at": downtime_event.created_at,
                "updated_at": downtime_event.updated_at,
            },
            not_found_message="Maintenance downtime event not found.",
            stale_message="Maintenance downtime event was updated by another user.",
        )

    def get(self, downtime_event_id: str) -> MaintenanceDowntimeEvent | None:
        obj = self._get_downtime_event_in_scope(
            downtime_event_id,
            operation_label="get maintenance downtime event",
        )
        return maintenance_downtime_event_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
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
        ctx = self._context(operation_label="list maintenance downtime events")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(MaintenanceDowntimeEventORM).where(
            MaintenanceDowntimeEventORM.organization_id == organization_id
        )
        if work_order_id is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.work_order_id == work_order_id)
        if asset_id is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.asset_id == asset_id)
        if system_id is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.system_id == system_id)
        if downtime_type is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.downtime_type == downtime_type)
        if reason_code is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.reason_code == reason_code)
        if open_only is True:
            stmt = stmt.where(MaintenanceDowntimeEventORM.ended_at.is_(None))
        elif open_only is False:
            stmt = stmt.where(MaintenanceDowntimeEventORM.ended_at.is_not(None))
        if started_from is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.started_at >= started_from)
        if started_to is not None:
            stmt = stmt.where(MaintenanceDowntimeEventORM.started_at <= started_to)
        rows = self.session.execute(
            stmt.order_by(
                MaintenanceDowntimeEventORM.started_at.desc(),
                MaintenanceDowntimeEventORM.created_at.desc(),
            )
        ).scalars().all()
        return [
            maintenance_downtime_event_from_orm(row)
            for row in rows
            if self._downtime_references_in_scope(
                row,
                operation_label="list maintenance downtime events",
            )
        ]


__all__ = [
    "SqlAlchemyMaintenanceDowntimeEventRepository",
    "SqlAlchemyMaintenanceFailureCodeRepository",
]

