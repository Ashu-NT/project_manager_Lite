from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.reservations import (
    InventoryReservationsWorkspaceViewModel,
)

from .detail_builder import build_detail
from .filtering import matches_search, normalize_filter
from .overview_builder import build_overview
from .reservation_mapper import to_record_view_model
from .selection import resolve_selected_id


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    status_filter: str = "all",
    item_filter: str = "all",
    storeroom_filter: str = "all",
    selected_reservation_id: str | None = None,
) -> InventoryReservationsWorkspaceViewModel:
    all_reservations = desktop_api.list_reservations(limit=500)
    status_options = (
        InventorySelectorOptionViewModel(value="all", label="All statuses"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_statuses()
        ),
    )
    item_options = (
        InventorySelectorOptionViewModel(value="all", label="All items"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_item_options(active_only=None)
        ),
    )
    storeroom_options = (
        InventorySelectorOptionViewModel(value="all", label="All storerooms"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_storeroom_options(active_only=None)
        ),
    )

    normalized_search = (search_text or "").strip()
    normalized_status_filter = normalize_filter(status_filter, status_options)
    normalized_item_filter = normalize_filter(item_filter, item_options)
    normalized_storeroom_filter = normalize_filter(storeroom_filter, storeroom_options)

    filtered_rows = desktop_api.list_reservations(
        stock_item_id=None if normalized_item_filter == "all" else normalized_item_filter,
        storeroom_id=None if normalized_storeroom_filter == "all" else normalized_storeroom_filter,
        status=None if normalized_status_filter == "all" else normalized_status_filter,
        limit=500,
    )
    if normalized_search:
        filtered_rows = tuple(
            row
            for row in filtered_rows
            if matches_search(
                normalized_search,
                row.reservation_number,
                row.source_reference_type,
                row.source_reference_id,
                row.requested_by_username,
                row.status,
                row.status_label,
                row.stock_item_label,
                row.storeroom_label,
                row.notes,
            )
        )

    resolved_selected_reservation_id = resolve_selected_id(
        selected_reservation_id, filtered_rows
    )
    selected_reservation = next(
        (row for row in filtered_rows if row.id == resolved_selected_reservation_id),
        None,
    )

    return InventoryReservationsWorkspaceViewModel(
        overview=build_overview(
            all_reservations=all_reservations,
            filtered_reservations=filtered_rows,
        ),
        status_options=status_options,
        item_options=item_options,
        storeroom_options=storeroom_options,
        selected_status_filter=normalized_status_filter,
        selected_item_filter=normalized_item_filter,
        selected_storeroom_filter=normalized_storeroom_filter,
        search_text=normalized_search,
        reservations=tuple(to_record_view_model(row) for row in filtered_rows),
        selected_reservation_id=resolved_selected_reservation_id,
        selected_reservation_detail=build_detail(selected_reservation),
        empty_state=_build_empty_state(
            all_reservations=all_reservations,
            filtered_reservations=filtered_rows,
            search_text=normalized_search,
            status_filter=normalized_status_filter,
            item_filter=normalized_item_filter,
            storeroom_filter=normalized_storeroom_filter,
        ),
    )


def _build_empty_state(
    *,
    all_reservations,
    filtered_reservations,
    search_text: str,
    status_filter: str,
    item_filter: str,
    storeroom_filter: str,
) -> str:
    if filtered_reservations:
        return ""
    if not all_reservations:
        return "No reservations are available yet. Create a reservation to hold stock against a real upstream demand reference."
    if (
        search_text
        or status_filter != "all"
        or item_filter != "all"
        or storeroom_filter != "all"
    ):
        return "No reservations match the current filters."
    return "No reservations are available yet."
