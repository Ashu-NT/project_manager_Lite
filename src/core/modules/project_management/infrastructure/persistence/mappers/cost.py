from __future__ import annotations

from src.core.modules.project_management.domain.financials.cost import CommitmentStatus, CostItem
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.persistence.orm.cost import CostItemORM


def cost_to_orm(cost: CostItem) -> CostItemORM:
    return CostItemORM(
        id=cost.id,
        project_id=cost.project_id,
        task_id=cost.task_id,
        cost_code=getattr(cost, "code", "") or None,
        description=cost.description,
        planned_amount=cost.planned_amount,
        actual_amount=cost.actual_amount,
        committed_amount=cost.committed_amount,
        forecast_amount=cost.forecast_amount,
        commitment_status=(
            cost.commitment_status.value
            if hasattr(cost.commitment_status, "value")
            else cost.commitment_status
        ),
        vendor_reference=cost.vendor_reference,
        cost_type=(cost.cost_type.value if hasattr(cost.cost_type, "value") else cost.cost_type),
        incurred_date=cost.incurred_date,
        currency_code=cost.currency_code,
        version=getattr(cost, "version", 1),
    )


def cost_from_orm(obj: CostItemORM) -> CostItem:
    return CostItem(
        id=obj.id,
        project_id=obj.project_id,
        task_id=obj.task_id,
        code=getattr(obj, "cost_code", "") or "",
        description=obj.description,
        planned_amount=obj.planned_amount,
        committed_amount=obj.committed_amount,
        actual_amount=obj.actual_amount,
        forecast_amount=getattr(obj, "forecast_amount", None),
        commitment_status=CommitmentStatus(
            str(getattr(obj, "commitment_status", None) or CommitmentStatus.UNCOMMITTED.value).lower()
        ),
        vendor_reference=getattr(obj, "vendor_reference", None),
        cost_type=CostType(obj.cost_type) if obj.cost_type else CostType.OVERHEAD,
        incurred_date=obj.incurred_date,
        currency_code=obj.currency_code,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "cost_to_orm",
    "cost_from_orm",
]
