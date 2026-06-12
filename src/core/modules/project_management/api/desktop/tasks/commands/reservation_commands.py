from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskReservationCreateCommand:
    task_id: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    uom: str | None = None
    need_by_date: date | None = None
    notes: str = ""


__all__ = ["TaskReservationCreateCommand"]
