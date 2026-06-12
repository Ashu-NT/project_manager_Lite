from __future__ import annotations


def set_overview(ctrl, v: dict[str, object]) -> None:
    if v == ctrl._overview:
        return
    ctrl._overview = v
    ctrl.overviewChanged.emit()


def set_status_options(ctrl, v: list[dict[str, str]]) -> None:
    if v == ctrl._status_options:
        return
    ctrl._status_options = v
    ctrl.statusOptionsChanged.emit()


def set_item_options(ctrl, v: list[dict[str, str]]) -> None:
    if v == ctrl._item_options:
        return
    ctrl._item_options = v
    ctrl.itemOptionsChanged.emit()


def set_storeroom_options(ctrl, v: list[dict[str, str]]) -> None:
    if v == ctrl._storeroom_options:
        return
    ctrl._storeroom_options = v
    ctrl.storeroomOptionsChanged.emit()


def set_selected_status_filter(ctrl, v: str) -> None:
    if v == ctrl._selected_status_filter:
        return
    ctrl._selected_status_filter = v
    ctrl.selectedStatusFilterChanged.emit()


def set_selected_item_filter(ctrl, v: str) -> None:
    if v == ctrl._selected_item_filter:
        return
    ctrl._selected_item_filter = v
    ctrl.selectedItemFilterChanged.emit()


def set_selected_storeroom_filter(ctrl, v: str) -> None:
    if v == ctrl._selected_storeroom_filter:
        return
    ctrl._selected_storeroom_filter = v
    ctrl.selectedStoreroomFilterChanged.emit()


def set_search_text(ctrl, v: str) -> None:
    if v == ctrl._search_text:
        return
    ctrl._search_text = v
    ctrl.searchTextChanged.emit()


def set_reservations(ctrl, v: dict[str, object]) -> None:
    if v == ctrl._reservations:
        return
    ctrl._reservations = v
    ctrl._reservations_table_model.set_rows(v.get("items", []))
    ctrl.reservationsChanged.emit()


def set_selected_reservation(ctrl, v: dict[str, object]) -> None:
    if v == ctrl._selected_reservation:
        return
    ctrl._selected_reservation = v
    ctrl.selectedReservationChanged.emit()


def set_selected_reservation_id(ctrl, v: str) -> None:
    if v == ctrl._selected_reservation_id:
        return
    ctrl._selected_reservation_id = v
    ctrl.selectedReservationIdChanged.emit()


def set_selected_reservation_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_reservation_ids:
        return
    ctrl._selected_reservation_ids = ids
    ctrl.selectedReservationIdsChanged.emit()


def set_detail_activity_items(ctrl, v: list[dict[str, object]]) -> None:
    if v == ctrl._detail_activity_items:
        return
    ctrl._detail_activity_items = v
    ctrl.detailActivityItemsChanged.emit()
