from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    run_mutation,
    serialize_audit_entries_for_activity,
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryProcurementWorkspacePresenter,
    InventoryReservationsWorkspacePresenter,
)

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementReservationsWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    statusOptionsChanged = Signal()
    itemOptionsChanged = Signal()
    storeroomOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedItemFilterChanged = Signal()
    selectedStoreroomFilterChanged = Signal()
    searchTextChanged = Signal()
    reservationsChanged = Signal()
    selectedReservationChanged = Signal()
    selectedReservationIdChanged = Signal()
    # pagination + bulk
    reservationPageChanged = Signal()
    reservationPageSizeChanged = Signal()
    selectedReservationIdsChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        reservations_workspace_presenter: InventoryReservationsWorkspacePresenter | None = None,
        platform_audit: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.reservations"
        )
        self._reservations_workspace_presenter = (
            reservations_workspace_presenter
            or InventoryReservationsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._status_options: list[dict[str, str]] = []
        self._item_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._selected_item_filter = "all"
        self._selected_storeroom_filter = "all"
        self._search_text = ""
        self._reservations_table_model = DynamicTableModel(self)
        self._reservations: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_reservation: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "linkedDocuments": [],
            "state": {},
        }
        self._selected_reservation_id = ""
        self._reservation_page = 1
        self._reservation_page_size = 25
        self._selected_reservation_ids: list[str] = []
        self._platform_audit = platform_audit
        self._detail_activity_items: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=itemOptionsChanged)
    def itemOptions(self) -> list[dict[str, str]]:
        return self._item_options

    @Property("QVariantList", notify=storeroomOptionsChanged)
    def storeroomOptions(self) -> list[dict[str, str]]:
        return self._storeroom_options

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=selectedItemFilterChanged)
    def selectedItemFilter(self) -> str:
        return self._selected_item_filter

    @Property(str, notify=selectedStoreroomFilterChanged)
    def selectedStoreroomFilter(self) -> str:
        return self._selected_storeroom_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=reservationsChanged)
    def reservations(self) -> dict[str, object]:
        return self._reservations

    @Property(QObject, constant=True)
    def reservationsTableModel(self) -> DynamicTableModel:
        return self._reservations_table_model

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTable(self, columns: list, file_path: str) -> dict[str, object]:
        from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file
        return export_to_file(list(self._reservations_table_model._rows), list(columns), (file_path or "").strip())

    @Property("QVariantMap", notify=selectedReservationChanged)
    def selectedReservation(self) -> dict[str, object]:
        return self._selected_reservation

    @Property(str, notify=selectedReservationIdChanged)
    def selectedReservationId(self) -> str:
        return self._selected_reservation_id

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._reservations_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                item_filter=self._selected_item_filter,
                storeroom_filter=self._selected_storeroom_filter,
                selected_reservation_id=self._selected_reservation_id or None,
            )
            self._set_overview(
                serialize_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_item_options(
                serialize_selector_options(workspace_state.item_options)
            )
            self._set_storeroom_options(
                serialize_selector_options(workspace_state.storeroom_options)
            )
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_selected_item_filter(workspace_state.selected_item_filter)
            self._set_selected_storeroom_filter(
                workspace_state.selected_storeroom_filter
            )
            self._set_search_text(workspace_state.search_text)
            self._set_reservations(
                {
                    "title": "Reservations",
                    "subtitle": "Manage stock holds, issuing, release, and cancellation flows against real upstream demand.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.reservations),
                }
            )
            self._set_selected_reservation_id(
                workspace_state.selected_reservation_id
            )
            self._set_selected_reservation(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_reservation_detail
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status: str) -> None:
        normalized = (status or "").strip() or "all"
        if normalized == self._selected_status_filter:
            return
        self._set_selected_status_filter(normalized)
        self.refresh()

    @Slot(str)
    def setItemFilter(self, item_id: str) -> None:
        normalized = (item_id or "").strip() or "all"
        if normalized == self._selected_item_filter:
            return
        self._set_selected_item_filter(normalized)
        self.refresh()

    @Slot(str)
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        normalized = (storeroom_id or "").strip() or "all"
        if normalized == self._selected_storeroom_filter:
            return
        self._set_selected_storeroom_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectReservation(self, reservation_id: str) -> None:
        normalized = (reservation_id or "").strip()
        if normalized == self._selected_reservation_id:
            return
        self._set_selected_reservation_id(normalized)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createReservation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._reservations_workspace_presenter.create_reservation(
                dict(payload)
            ),
            success_message="Reservation created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def issueReservation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._reservations_workspace_presenter.issue_reservation(
                dict(payload)
            ),
            success_message="Reserved stock issued.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def releaseReservation(self, reservation_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._reservations_workspace_presenter.release_reservation(
                reservation_id
            ),
            success_message="Reservation released.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def cancelReservation(self, reservation_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._reservations_workspace_presenter.cancel_reservation(
                reservation_id
            ),
            success_message="Reservation cancelled.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── pagination + bulk ────────────────────────────────────────────

    @Property(int, notify=reservationPageChanged)
    def reservationPage(self) -> int:
        return self._reservation_page

    @Property(int, notify=reservationPageSizeChanged)
    def reservationPageSize(self) -> int:
        return self._reservation_page_size

    @Property(int, notify=reservationsChanged)
    def reservationTotalCount(self) -> int:
        return len(self._reservations.get("items", []))

    @Property("QVariantList", notify=selectedReservationIdsChanged)
    def selectedReservationIds(self) -> list[str]:
        return self._selected_reservation_ids

    @Property(int, notify=selectedReservationIdsChanged)
    def selectedReservationCount(self) -> int:
        return len(self._selected_reservation_ids)

    @Slot(str)
    def activateReservation(self, reservation_id: str) -> None:
        self.selectReservation(reservation_id)

    @Slot(int)
    def setReservationPage(self, page: int) -> None:
        self._reservation_page = max(1, int(page))
        self.reservationPageChanged.emit()

    @Slot(int)
    def setReservationPageSize(self, size: int) -> None:
        self._reservation_page_size = max(10, min(200, int(size)))
        self._reservation_page = 1
        self.reservationPageSizeChanged.emit()
        self.reservationPageChanged.emit()

    @Slot(str, bool)
    def setReservationBulkSelection(self, row_id: str, selected: bool) -> None:
        ids = list(self._selected_reservation_ids)
        if selected and row_id not in ids:
            ids.append(row_id)
        elif not selected and row_id in ids:
            ids.remove(row_id)
        self._set_selected_reservation_ids(ids)

    @Slot()
    def clearReservationBulkSelection(self) -> None:
        self._set_selected_reservation_ids([])

    @Slot()
    def selectVisibleReservations(self) -> None:
        all_ids = [
            str(r.get("id", ""))
            for r in self._reservations.get("items", [])
            if r.get("id")
        ]
        self._set_selected_reservation_ids(all_ids)

    @Slot()
    def clearFilters(self) -> None:
        self._set_selected_status_filter("all")
        self._set_selected_item_filter("all")
        self._set_selected_storeroom_filter("all")
        self._set_search_text("")
        self.refresh()

    def _set_selected_reservation_ids(self, ids: list[str]) -> None:
        if ids == self._selected_reservation_ids:
            return
        self._selected_reservation_ids = ids
        self.selectedReservationIdsChanged.emit()

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        if self._platform_audit is None or not entity_id:
            self._set_detail_activity_items([])
            return
        try:
            result = self._platform_audit.list_recent(entity_type=entity_type, limit=200)
            items = (
                serialize_audit_entries_for_activity(result.data, entity_id)
                if result.ok and result.data is not None
                else []
            )
        except Exception:  # pragma: no cover - defensive fallback
            items = []
        self._set_detail_activity_items(items)

    def _set_detail_activity_items(self, items: list[dict[str, object]]) -> None:
        if items == self._detail_activity_items:
            return
        self._detail_activity_items = items
        self.detailActivityItemsChanged.emit()

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="inventory_procurement")
        self._subscribe_domain_change("site", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_status_options(self, status_options: list[dict[str, str]]) -> None:
        if status_options == self._status_options:
            return
        self._status_options = status_options
        self.statusOptionsChanged.emit()

    def _set_item_options(self, item_options: list[dict[str, str]]) -> None:
        if item_options == self._item_options:
            return
        self._item_options = item_options
        self.itemOptionsChanged.emit()

    def _set_storeroom_options(
        self,
        storeroom_options: list[dict[str, str]],
    ) -> None:
        if storeroom_options == self._storeroom_options:
            return
        self._storeroom_options = storeroom_options
        self.storeroomOptionsChanged.emit()

    def _set_selected_status_filter(self, selected_status_filter: str) -> None:
        if selected_status_filter == self._selected_status_filter:
            return
        self._selected_status_filter = selected_status_filter
        self.selectedStatusFilterChanged.emit()

    def _set_selected_item_filter(self, selected_item_filter: str) -> None:
        if selected_item_filter == self._selected_item_filter:
            return
        self._selected_item_filter = selected_item_filter
        self.selectedItemFilterChanged.emit()

    def _set_selected_storeroom_filter(
        self,
        selected_storeroom_filter: str,
    ) -> None:
        if selected_storeroom_filter == self._selected_storeroom_filter:
            return
        self._selected_storeroom_filter = selected_storeroom_filter
        self.selectedStoreroomFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_reservations(self, reservations: dict[str, object]) -> None:
        if reservations == self._reservations:
            return
        self._reservations = reservations
        self._reservations_table_model.set_rows(reservations.get("items", []))
        self.reservationsChanged.emit()

    def _set_selected_reservation(
        self,
        selected_reservation: dict[str, object],
    ) -> None:
        if selected_reservation == self._selected_reservation:
            return
        self._selected_reservation = selected_reservation
        self.selectedReservationChanged.emit()

    def _set_selected_reservation_id(self, selected_reservation_id: str) -> None:
        if selected_reservation_id == self._selected_reservation_id:
            return
        self._selected_reservation_id = selected_reservation_id
        self.selectedReservationIdChanged.emit()


__all__ = ["InventoryProcurementReservationsWorkspaceController"]
