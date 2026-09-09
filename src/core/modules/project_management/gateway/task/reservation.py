"""PM-owned port for the task-material-reservation capability Inventory/
Procurement provides.

Mirrors the `ProcurementFinancialSourceProvider` pattern
(`gateway/procurement/financial_source.py`): PM defines the shape it needs, and
Inventory/Procurement's `ReservationService` already satisfies it structurally (same
method names, same keyword arguments) -- Python's `Protocol` typing is structural, not
nominal, so no import in either direction is required.

Reservation records themselves (`StockReservation`) remain Inventory-owned
and are deliberately not re-typed here -- PM's existing reservation
serializer reads them defensively via `getattr`, the correct way to consume
a record shape it does not own.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class TaskReservationGateway(Protocol):
    """What PM's desktop Tasks API needs from a stock-reservation service.

    Matches `inventory_procurement.application.inventory.reservation_service
    .ReservationService.list_reservations`/`.create_reservation` exactly --
    intentionally, since that class already implements this shape and needs
    no change."""

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
