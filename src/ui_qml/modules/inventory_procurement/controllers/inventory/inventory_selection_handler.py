from __future__ import annotations


def select_storeroom(ctrl, storeroom_id: str) -> None:
    normalized = (storeroom_id or "").strip()
    if normalized == ctrl._selected_storeroom_id:
        return
    ctrl._set_selected_storeroom_id(normalized)
    ctrl.refresh()


def select_balance(ctrl, balance_id: str) -> None:
    normalized = (balance_id or "").strip()
    if normalized == ctrl._selected_balance_id:
        return
    ctrl._set_selected_balance_id(normalized)
    ctrl.refresh()


def select_location(ctrl, location_id: str) -> None:
    normalized = (location_id or "").strip()
    if normalized == ctrl._selected_location_id:
        return
    ctrl._selected_location_id = normalized
    ctrl.selectedLocationIdChanged.emit()


def set_active_view(ctrl, view: str) -> None:
    normalized = view if view in ("balances", "storerooms") else "balances"
    if normalized == ctrl._active_view:
        return
    ctrl._active_view = normalized
    ctrl.activeViewChanged.emit()


def set_balance_page(ctrl, page: int) -> None:
    ctrl._balance_page = max(1, int(page))
    ctrl.balancePageChanged.emit()


def set_balance_page_size(ctrl, size: int) -> None:
    ctrl._balance_page_size = max(10, min(200, int(size)))
    ctrl._balance_page = 1
    ctrl.balancePageSizeChanged.emit()
    ctrl.balancePageChanged.emit()


def set_storeroom_page(ctrl, page: int) -> None:
    ctrl._storeroom_page = max(1, int(page))
    ctrl.storeroomPageChanged.emit()


def set_storeroom_page_size(ctrl, size: int) -> None:
    ctrl._storeroom_page_size = max(10, min(200, int(size)))
    ctrl._storeroom_page = 1
    ctrl.storeroomPageSizeChanged.emit()
    ctrl.storeroomPageChanged.emit()


def set_movement_page(ctrl, page: int) -> None:
    ctrl._movement_page = max(1, int(page))
    ctrl.movementPageChanged.emit()


def set_movement_page_size(ctrl, size: int) -> None:
    ctrl._movement_page_size = max(10, min(200, int(size)))
    ctrl._movement_page = 1
    ctrl.movementPageSizeChanged.emit()
    ctrl.movementPageChanged.emit()


def set_location_page(ctrl, page: int) -> None:
    ctrl._location_page = max(1, int(page))
    ctrl.locationPageChanged.emit()


def set_location_page_size(ctrl, size: int) -> None:
    ctrl._location_page_size = max(10, min(200, int(size)))
    ctrl._location_page = 1
    ctrl.locationPageSizeChanged.emit()
    ctrl.locationPageChanged.emit()
