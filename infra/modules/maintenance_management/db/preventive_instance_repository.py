from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenancePreventivePlanInstance
from core.modules.maintenance_management.interfaces import MaintenancePreventivePlanInstanceRepository
from infra.modules.maintenance_management.db.mapper import (
    maintenance_preventive_plan_instance_from_orm,
    maintenance_preventive_plan_instance_to_orm,
)
from src.infra.persistence.orm.maintenance.preventive_runtime_models import MaintenancePreventivePlanInstanceORM
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyMaintenancePreventivePlanInstanceRepository(MaintenancePreventivePlanInstanceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, preventive_instance: MaintenancePreventivePlanInstance) -> None:
        self.session.add(maintenance_preventive_plan_instance_to_orm(preventive_instance))

    def update(self, preventive_instance: MaintenancePreventivePlanInstance) -> None:
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
        obj = self.session.get(MaintenancePreventivePlanInstanceORM, preventive_instance_id)
        if obj is not None:
            self.session.delete(obj)

    def get(self, preventive_instance_id: str) -> MaintenancePreventivePlanInstance | None:
        obj = self.session.get(MaintenancePreventivePlanInstanceORM, preventive_instance_id)
        return maintenance_preventive_plan_instance_from_orm(obj) if obj else None

    def get_by_generated_work_order_id(
        self,
        organization_id: str,
        work_order_id: str,
    ) -> MaintenancePreventivePlanInstance | None:
        stmt = select(MaintenancePreventivePlanInstanceORM).where(
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
        stmt = select(MaintenancePreventivePlanInstanceORM).where(
            MaintenancePreventivePlanInstanceORM.organization_id == organization_id
        )
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
