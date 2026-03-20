"""Reservation UI workspaces and dialogs."""

from ui.modules.inventory_procurement.reservation.reservation_dialogs import (
    ReservationCreateDialog,
    ReservationIssueDialog,
)
from ui.modules.inventory_procurement.reservation.reservations_tab import ReservationsTab

__all__ = [
    "ReservationCreateDialog",
    "ReservationIssueDialog",
    "ReservationsTab",
]
