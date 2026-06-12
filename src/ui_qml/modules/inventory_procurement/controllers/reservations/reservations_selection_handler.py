from __future__ import annotations


def select_reservation(ctrl, reservation_id: str) -> None:
    normalized = (reservation_id or "").strip()
    if normalized == ctrl._selected_reservation_id:
        return
    ctrl._set_selected_reservation_id(normalized)
    ctrl.refresh()


def set_reservation_page(ctrl, page: int) -> None:
    ctrl._reservation_page = max(1, int(page))
    ctrl.reservationPageChanged.emit()


def set_reservation_page_size(ctrl, size: int) -> None:
    ctrl._reservation_page_size = max(10, min(200, int(size)))
    ctrl._reservation_page = 1
    ctrl.reservationPageSizeChanged.emit()
    ctrl.reservationPageChanged.emit()
