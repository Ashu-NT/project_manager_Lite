from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenancePreventivePlanInstance
from src.core.modules.maintenance.contracts.repositories import MaintenancePreventivePlanInstanceRepository
from src.core.modules.maintenance.infrastructure.persistence.mappers import (
    maintenance_preventive_plan_instance_from_orm,
    maintenance_preventive_plan_instance_to_orm,
)
from src.core.modules.maintenance.infrastructure.persistence.orm.models import (
    MaintenancePreventivePlanORM,
    MaintenanceWorkOrderORM,
    MaintenanceWorkRequestORM,
)
from src.core.modules.maintenance.infrastructure.persistence.orm.preventive_runtime_models import MaintenancePreventivePlanInstanceORM
from src.core.modules.maintenance.infrastructure.persistence.repositories._tenant_scope import (
    MaintenanceParentScopedRepositorySupport,
)
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyMaintenancePreventivePlanInstanceRepository(
    MaintenancePreventivePlanInstanceRepository, MaintenanceParentScopedRepositorySupport
):
    _repository_label = "Maintenance preventive plan instance repository"
    _scope_joins = (
        (MaintenancePreventivePlanORM, MaintenancePreventivePlanInstanceORM.plan_id == MaintenancePreventivePlanORM.id),
    )

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

    def add(self, preventive_instance: MaintenancePreventivePlanInstance) -> None:
        self._require_in_scope(
            MaintenancePreventivePlanORM,
            preventive_instance.plan_id,
            operation_label="add maintenance preventive plan instance",
            not_found_message="Maintenance preventive plan not found.",
        )
        if preventive_instance.generated_work_request_id:
            self._require_in_scope(
                MaintenanceWorkRequestORM,
                preventive_instance.generated_work_request_id,
                operation_label="add maintenance preventive plan instance work request",
                not_found_message="Maintenance work request not found.",
            )
        if preventive_instance.generated_work_order_id:
            self._require_in_scope(
                MaintenanceWorkOrderORM,
                preventive_instance.generated_work_order_id,
                operation_label="add maintenance preventive plan instance work order",
                not_found_message="Maintenance work order not found.",
            )
        self.session.add(maintenance_preventive_plan_instance_to_orm(preventive_instance))

    def update(self, preventive_instance: MaintenancePreventivePlanInstance) -> None:
        self._require_via_anchor_in_scope(
            MaintenancePreventivePlanInstanceORM,
            MaintenancePreventivePlanORM,
            joins=self._scope_joins,
            record_id=preventive_instance.id,
            operation_label="update maintenance preventive plan instance",
            not_found_message="Maintenance preventive plan instance not found.",
        )
        self._require_in_scope(
            MaintenancePreventivePlanORM,
            preventive_instance.plan_id,
            operation_label="update maintenance preventive plan instance plan",
            not_found_message="Maintenance preventive plan not found.",
        )
        if preventive_instance.generated_work_request_id:
            self._require_in_scope(
                MaintenanceWorkRequestORM,
                preventive_instance.generated_work_request_id,
                operation_label="update maintenance preventive plan instance work request",
                not_found_message="Maintenance work request not found.",
            )
        if preventive_instance.generated_work_order_id:
            self._require_in_scope(
                MaintenanceWorkOrderORM,
                preventive_instance.generated_work_order_id,
                operation_label="update maintenance preventive plan instance work order",
                not_found_message="Maintenance work order not found.",
            )
        preventive_instance.version = update_with_version_check(
            self.session,
            MaintenancePreventivePlanInstanceORM,
            preventive_instance.id,
            getattr(preventive_instance, "version", 1),
            {
                "plan_id": preventive_instance.plan_id,
                "due_at": preventive_instance.due_at,
                "due_counter": preventive_instance.due_counter,
                "status": preventive_instance.status,
                "generated_at": preventive_instance.generated_at,
                "generated_work_request_id": preventive_instance.generated_work_request_id,
                "generated_work_order_id": preventive_instance.generated_work_order_id,
                "completed_at": preventive_instance.completed_at,
                "notes": preventive_instance.notes,
                "created_at": preventive_instance.created_at,
                "updated_at": preventive_instance.updated_at,
            },
            not_found_message="Maintenance preventive plan instance not found.",
            stale_message="Maintenance preventive plan instance was updated by another user.",
        )

    def delete(self, preventive_instance_id: str) -> None:
        obj = self._get_via_anchor_in_scope(
            MaintenancePreventivePlanInstanceORM,
            MaintenancePreventivePlanORM,
            joins=self._scope_joins,
            record_id=preventive_instance_id,
            operation_label="delete maintenance preventive plan instance",
        )
        if obj is not None:
            self.session.delete(obj)

    def get(self, preventive_instance_id: str) -> MaintenancePreventivePlanInstance | None:
        obj = self._get_via_anchor_in_scope(
            MaintenancePreventivePlanInstanceORM,
            MaintenancePreventivePlanORM,
            joins=self._scope_joins,
            record_id=preventive_instance_id,
            operation_label="get maintenance preventive plan instance",
        )
        return maintenance_preventive_plan_instance_from_orm(obj) if obj else None

    def get_by_generated_work_order_id(
        self,
        organization_id: str,
        work_order_id: str,
    ) -> MaintenancePreventivePlanInstance | None:
        ctx = self._context(operation_label="get maintenance preventive plan instance by work order")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = self._scoped_stmt_for_anchor(
            MaintenancePreventivePlanInstanceORM,
            MaintenancePreventivePlanORM,
            joins=self._scope_joins,
            operation_label="get maintenance preventive plan instance by work order",
        ).where(
            MaintenancePreventivePlanInstanceORM.organization_id == organization_id,
            MaintenancePreventivePlanInstanceORM.generated_work_order_id == work_order_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return maintenance_preventive_plan_instance_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        status: str | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]:
        ctx = self._context(operation_label="list maintenance preventive plan instances")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = self._scoped_stmt_for_anchor(
            MaintenancePreventivePlanInstanceORM,
            MaintenancePreventivePlanORM,
            joins=self._scope_joins,
            operation_label="list maintenance preventive plan instances",
        ).where(MaintenancePreventivePlanInstanceORM.organization_id == organization_id)
        if plan_id is not None:
            stmt = stmt.where(MaintenancePreventivePlanInstanceORM.plan_id == plan_id)
        if status is not None:
            stmt = stmt.where(MaintenancePreventivePlanInstanceORM.status == status)
        if generated_work_request_id is not None:
            stmt = stmt.where(
                MaintenancePreventivePlanInstanceORM.generated_work_request_id == generated_work_request_id
            )
        if generated_work_order_id is not None:
            stmt = stmt.where(
                MaintenancePreventivePlanInstanceORM.generated_work_order_id == generated_work_order_id
            )
        rows = self.session.execute(
            stmt.order_by(
                MaintenancePreventivePlanInstanceORM.due_at.asc(),
                MaintenancePreventivePlanInstanceORM.created_at.asc(),
            )
        ).scalars().all()
        return [maintenance_preventive_plan_instance_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyMaintenancePreventivePlanInstanceRepository"]

