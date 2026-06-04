from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskReservationDesktopDto:
    id: str
    reservation_number: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    issued_qty: float
    remaining_qty: float
    uom: str
    status: str
    status_label: str
    need_by_date: date | None
    notes: str


@dataclass(frozen=True)
class TaskMaterialDemandSummary:
    task_id: str
    total_reserved: int
    active_count: int
    fulfilled_count: int
    cancelled_count: int


__all__ = ["TaskMaterialDemandSummary", "TaskReservationDesktopDto"]
