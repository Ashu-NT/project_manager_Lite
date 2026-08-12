"""PM-owned port for the task-material-reservation capability Inventory/
Procurement provides.

This mirrors the existing `ProcurementFinancialSourceProvider` pattern
(`gateway/procurement/financial_source.py`): PM defines the shape it needs; the
Inventory/Procurement module's `ReservationService` already satisfies it
structurally (same method names, same keyword arguments) and requires no
change and no import of this module to do so -- Python's `Protocol` typing
is structural, not nominal. This closes the boundary gap where PM's desktop
runtime previously received that service typed as plain `object` purely to
avoid a static cross-module import (see TODO §5A).

Reservation records themselves (`StockReservation`) remain Inventory-owned
and are deliberately not re-typed here -- PM's existing reservation
serializer already reads them defensively via `getattr`, which is the
correct way for PM to consume a record shape it does not own.
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
