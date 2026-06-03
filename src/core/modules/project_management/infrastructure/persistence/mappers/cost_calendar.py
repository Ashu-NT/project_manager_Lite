from __future__ import annotations

from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import CalendarEventORM, CostItemORM


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
        cost_type=CostType(obj.cost_type) if obj.cost_type else CostType.OVERHEAD,
        incurred_date=obj.incurred_date,
        currency_code=obj.currency_code,
        version=getattr(obj, "version", 1),
    )


def event_to_orm(event: CalendarEvent) -> CalendarEventORM:
    return CalendarEventORM(
        id=event.id,
        title=event.title,
        start_date=event.start_date,
        end_date=event.end_date,
        project_id=event.project_id,
        task_id=event.task_id,
        all_day=event.all_day,
        description=event.description,
    )


def event_from_orm(obj: CalendarEventORM) -> CalendarEvent:
    return CalendarEvent(
        id=obj.id,
        title=obj.title,
        start_date=obj.start_date,
        end_date=obj.end_date,
        project_id=obj.project_id,
        task_id=obj.task_id,
        all_day=obj.all_day,
        description=obj.description,
    )

__all__ = [
    "cost_to_orm",
    "cost_from_orm",
    "event_to_orm",
    "event_from_orm",
]
