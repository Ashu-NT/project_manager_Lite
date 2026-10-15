"""PM-owned boundary for a future Inventory reservation capability.

Inventory will own reservation operations and records. PM declares only the
capability shape consumed by its Tasks adapter; no operational Inventory or
Procurement implementation is introduced by this gateway.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class TaskReservationGateway(Protocol):
    """Optional reservation capability supplied to PM by composition."""

    def list_reservations(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Any]: ...

    def create_reservation(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        reserved_qty: float,
        uom: str | None = None,
        need_by_date: date | None = None,
        source_reference_type: str,
        source_reference_id: str,
        source_module: str = "",
        source_entity_type: str = "",
        source_code_snapshot: str = "",
        source_title_snapshot: str = "",
        source_status_snapshot: str = "",
        notes: str = "",
    ) -> Any: ...


__all__ = ["TaskReservationGateway"]
