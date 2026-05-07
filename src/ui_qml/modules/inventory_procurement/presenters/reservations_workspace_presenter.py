from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementReservationsDesktopApi,
    InventoryReservationCreateCommand,
    InventoryReservationIssueCommand,
    build_inventory_procurement_reservations_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.reservations import (
    InventoryReservationsWorkspaceViewModel,
)


class InventoryReservationsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementReservationsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_reservations_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        item_filter: str = "all",
        storeroom_filter: str = "all",
        selected_reservation_id: str | None = None,
    ) -> InventoryReservationsWorkspaceViewModel:
        all_reservations = self._desktop_api.list_reservations(limit=500)
        status_options = (
            InventorySelectorOptionViewModel(value="all", label="All statuses"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_statuses()
            ),
        )
        item_options = (
            InventorySelectorOptionViewModel(value="all", label="All items"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_item_options(active_only=None)
            ),
        )
        storeroom_options = (
            InventorySelectorOptionViewModel(value="all", label="All storerooms"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_storeroom_options(active_only=None)
            ),
        )

        normalized_search = (search_text or "").strip()
        normalized_status_filter = self._normalize_filter(status_filter, status_options)
        normalized_item_filter = self._normalize_filter(item_filter, item_options)
        normalized_storeroom_filter = self._normalize_filter(
            storeroom_filter,
            storeroom_options,
        )

        filtered_rows = self._desktop_api.list_reservations(
            stock_item_id=None if normalized_item_filter == "all" else normalized_item_filter,
            storeroom_id=None
            if normalized_storeroom_filter == "all"
            else normalized_storeroom_filter,
            status=None if normalized_status_filter == "all" else normalized_status_filter,
            limit=500,
        )
        if normalized_search:
            filtered_rows = tuple(
                row
                for row in filtered_rows
                if self._matches_search(
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

        resolved_selected_reservation_id = self._resolve_selected_id(
            selected_reservation_id,
            filtered_rows,
        )
        selected_reservation = next(
            (
                row
                for row in filtered_rows
                if row.id == resolved_selected_reservation_id
            ),
            None,
        )

        return InventoryReservationsWorkspaceViewModel(
            overview=self._build_overview(
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
            reservations=tuple(
                self._to_record_view_model(row) for row in filtered_rows
            ),
            selected_reservation_id=resolved_selected_reservation_id,
            selected_reservation_detail=self._build_detail(selected_reservation),
            empty_state=self._build_empty_state(
                all_reservations=all_reservations,
                filtered_reservations=filtered_rows,
                search_text=normalized_search,
                status_filter=normalized_status_filter,
                item_filter=normalized_item_filter,
                storeroom_filter=normalized_storeroom_filter,
            ),
        )

    def create_reservation(self, payload: dict[str, Any]) -> None:
        command = InventoryReservationCreateCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before saving.",
            ),
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Choose a storeroom before saving.",
            ),
            reserved_qty=self._require_positive_float(
                payload,
                "reservedQty",
                "Reserved quantity must be greater than zero.",
            ),
            need_by_date=self._optional_date(payload, "needByDate"),
            source_reference_type=self._optional_text(payload, "sourceReferenceType") or "",
            source_reference_id=self._optional_text(payload, "sourceReferenceId") or "",
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_reservation(command)

    def issue_reservation(self, payload: dict[str, Any]) -> None:
        command = InventoryReservationIssueCommand(
            reservation_id=self._require_text(
                payload,
                "reservationId",
                "Reservation ID is required before issuing stock.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Issue quantity must be greater than zero.",
            ),
            note=self._optional_text(payload, "note") or "",
        )
        self._desktop_api.issue_reserved_stock(command)

    def release_reservation(self, reservation_id: str, note: str = "") -> None:
        normalized_id = (reservation_id or "").strip()
        if not normalized_id:
            raise ValueError("Reservation ID is required before releasing stock.")
        self._desktop_api.release_reservation(normalized_id, note=note)

    def cancel_reservation(self, reservation_id: str, note: str = "") -> None:
        normalized_id = (reservation_id or "").strip()
        if not normalized_id:
            raise ValueError("Reservation ID is required before cancelling stock.")
        self._desktop_api.cancel_reservation(normalized_id, note=note)

    @staticmethod
    def _build_overview(
        *,
        all_reservations,
        filtered_reservations,
    ) -> InventoryCatalogOverviewViewModel:
        active_count = sum(
            1
            for row in all_reservations
            if row.status in {"ACTIVE", "PARTIALLY_ISSUED"}
            and float(row.remaining_qty or 0.0) > 0
        )
        issued_count = sum(
            1
            for row in all_reservations
            if row.status in {"PARTIALLY_ISSUED", "FULLY_ISSUED"}
        )
        closed_count = sum(
            1 for row in all_reservations if row.status in {"RELEASED", "CANCELLED"}
        )
        return InventoryCatalogOverviewViewModel(
            title="Reservations",
            subtitle="Stock demand holds, issue execution, and release or cancellation flows through the module-local reservations desktop API.",
            metrics=(
                InventoryCatalogMetricViewModel(
                    label="Reservations",
                    value=str(len(all_reservations)),
                    supporting_text=f"Showing {len(filtered_reservations)} reservations with the current filters.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Active",
                    value=str(active_count),
                    supporting_text="Open demand holds still consuming available stock.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Issued",
                    value=str(issued_count),
                    supporting_text="Reservations with at least some stock already issued.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Closed",
                    value=str(closed_count),
                    supporting_text="Reservations already released or cancelled.",
                ),
            ),
        )

    def _to_record_view_model(self, row) -> InventoryRecordViewModel:
        can_operate = self._can_operate(row)
        return InventoryRecordViewModel(
            id=row.id,
            title=row.reservation_number,
            status_label=row.status_label,
            subtitle=row.stock_item_label,
            supporting_text=(
                f"{row.storeroom_label} | Reserved {row.reserved_qty_label} | Remaining {row.remaining_qty_label}"
            ),
            meta_text=self._build_source_meta(row),
            can_primary_action=can_operate,
            can_secondary_action=can_operate,
            can_tertiary_action=can_operate,
            state=self._build_state(row),
        )

    def _build_detail(self, row) -> InventoryDetailViewModel:
        if row is None:
            return InventoryDetailViewModel(
                title="No reservation selected",
                empty_state="Select a reservation to inspect source context, remaining quantity, or launch issue, release, and cancel actions.",
            )
        return InventoryDetailViewModel(
            id=row.id,
            title=row.reservation_number,
            status_label=row.status_label,
            subtitle=f"Requester: {row.requested_by_username or '-'}",
            description=self._build_source_meta(row),
            fields=(
                InventoryDetailFieldViewModel(
                    label="Item",
                    value=row.stock_item_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Storeroom",
                    value=row.storeroom_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Quantities",
                    value=f"Reserved {row.reserved_qty_label} | Issued {row.issued_qty_label} | Remaining {row.remaining_qty_label}",
                ),
                InventoryDetailFieldViewModel(
                    label="Need by",
                    value=row.need_by_date_label or "-",
                ),
                InventoryDetailFieldViewModel(
                    label="Created / Released / Cancelled",
                    value=f"{row.created_at_label or '-'} / {row.released_at_label or '-'} / {row.cancelled_at_label or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                InventoryDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state=self._build_state(row),
        )

    @staticmethod
    def _build_state(row) -> dict[str, object]:
        can_operate = InventoryReservationsWorkspacePresenter._can_operate(row)
        return {
            "reservationId": row.id,
            "reservationNumber": row.reservation_number,
            "stockItemId": row.stock_item_id,
            "storeroomId": row.storeroom_id,
            "remainingQty": row.remaining_qty,
            "remainingQtyLabel": row.remaining_qty_label,
            "status": row.status,
            "version": row.version,
            "canIssue": can_operate,
            "canRelease": can_operate,
            "canCancel": can_operate,
            "sourceReferenceType": row.source_reference_type,
            "sourceReferenceId": row.source_reference_id,
        }

    @staticmethod
    def _build_source_meta(row) -> str:
        source = f"{row.source_reference_type or '-'}: {row.source_reference_id or '-'}"
        requester = row.requested_by_username or "-"
        need_by = row.need_by_date_label or "-"
        return f"Source {source} | Requester {requester} | Need by {need_by}"

    @staticmethod
    def _can_operate(row) -> bool:
        return bool(
            row.status in {"ACTIVE", "PARTIALLY_ISSUED"}
            and float(row.remaining_qty or 0.0) > 0
        )

    @staticmethod
    def _matches_search(search_text: str, *values: str) -> bool:
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"

    @staticmethod
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

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be a valid number.") from exc

    @staticmethod
    def _require_positive_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = InventoryReservationsWorkspacePresenter._optional_float(payload, key)
        if value is None or value <= 0:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{key} must use YYYY-MM-DD format.") from exc


__all__ = ["InventoryReservationsWorkspacePresenter"]
