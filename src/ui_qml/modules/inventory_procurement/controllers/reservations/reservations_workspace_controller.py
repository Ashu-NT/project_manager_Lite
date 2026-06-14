from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryProcurementWorkspacePresenter,
    InventoryReservationsWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .reservations_activity_handler import load_detail_activity
from .reservations_bulk_handler import (
    clear_reservation_bulk_selection,
    select_visible_reservations,
    set_reservation_bulk_selection,
)
from .reservations_domain_event_binder import bind_domain_events
from .reservations_export_handler import export_table
from .reservations_filter_handler import (
    clear_filters,
    set_item_filter,
    set_search_text as _set_search_text_filter,
    set_status_filter,
    set_storeroom_filter,
)
from .reservations_mutation_handler import (
    cancel_reservation,
    create_reservation,
    issue_reservation,
    release_reservation,
)
from .reservations_refresh_service import refresh as _do_refresh
from .reservations_selection_handler import (
    select_reservation,
    set_reservation_page,
    set_reservation_page_size,
)
from .reservations_state import default_collection, default_detail, default_overview
from .reservations_state_setters import (
    set_detail_activity_items,
    set_item_options,
    set_overview,
    set_reservations,
    set_search_text,
    set_selected_item_filter,
    set_selected_reservation,
    set_selected_reservation_id,
    set_selected_reservation_ids,
    set_selected_status_filter,
    set_selected_storeroom_filter,
    set_status_options,
    set_storeroom_options,
)
from .reservations_table_models import create_reservations_table_models

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
    reservationPageChanged = Signal()
    reservationPageSizeChanged = Signal()
    selectedReservationIdsChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        reservations_workspace_presenter: InventoryReservationsWorkspacePresenter | None = None,
        activity_api: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = (
            workspace_presenter
            or InventoryProcurementWorkspacePresenter("inventory_procurement.reservations")
        )
        self._reservations_workspace_presenter = (
            reservations_workspace_presenter or InventoryReservationsWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
        self._status_options: list[dict[str, str]] = []
        self._item_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._selected_item_filter = "all"
        self._selected_storeroom_filter = "all"
        self._search_text = ""
        self._reservations_table_model = create_reservations_table_models(self)
        self._reservations: dict[str, object] = default_collection()
        self._selected_reservation: dict[str, object] = default_detail()
        self._selected_reservation_id = ""
        self._reservation_page = 1
        self._reservation_page_size = 25
        self._selected_reservation_ids: list[str] = []
        self._activity_api = activity_api
        self._detail_activity_items: list[dict[str, object]] = []
        bind_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────

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

    @Property("QVariantMap", notify=selectedReservationChanged)
    def selectedReservation(self) -> dict[str, object]:
        return self._selected_reservation

    @Property(str, notify=selectedReservationIdChanged)
    def selectedReservationId(self) -> str:
        return self._selected_reservation_id

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

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        _do_refresh(self)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        _set_search_text_filter(self, search_text)

    @Slot(str)
    def setStatusFilter(self, status: str) -> None:
        set_status_filter(self, status)

    @Slot(str)
    def setItemFilter(self, item_id: str) -> None:
        set_item_filter(self, item_id)

    @Slot(str)
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        set_storeroom_filter(self, storeroom_id)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def selectReservation(self, reservation_id: str) -> None:
        select_reservation(self, reservation_id)

    @Slot(str)
    def activateReservation(self, reservation_id: str) -> None:
        select_reservation(self, reservation_id)

    @Slot(int)
    def setReservationPage(self, page: int) -> None:
        set_reservation_page(self, page)

    @Slot(int)
    def setReservationPageSize(self, size: int) -> None:
        set_reservation_page_size(self, size)

    @Slot(str, bool)
    def setReservationBulkSelection(self, row_id: str, selected: bool) -> None:
        set_reservation_bulk_selection(self, row_id, selected)

    @Slot()
    def clearReservationBulkSelection(self) -> None:
        clear_reservation_bulk_selection(self)

    @Slot()
    def selectVisibleReservations(self) -> None:
        select_visible_reservations(self)

    @Slot("QVariantMap", result="QVariantMap")
    def createReservation(self, payload: dict[str, object]) -> dict[str, object]:
        return create_reservation(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def issueReservation(self, payload: dict[str, object]) -> dict[str, object]:
        return issue_reservation(self, payload)

    @Slot(str, result="QVariantMap")
    def releaseReservation(self, reservation_id: str) -> dict[str, object]:
        return release_reservation(self, reservation_id)

    @Slot(str, result="QVariantMap")
    def cancelReservation(self, reservation_id: str) -> dict[str, object]:
        return cancel_reservation(self, reservation_id)

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTable(self, columns: list, file_path: str) -> dict[str, object]:
        return export_table(self, columns, file_path)

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        load_detail_activity(self, entity_id, entity_type)

    # ── Private state setters (called by handlers and refresh service) ─

    def _set_overview(self, v: dict[str, object]) -> None:
        set_overview(self, v)

    def _set_status_options(self, v: list[dict[str, str]]) -> None:
        set_status_options(self, v)

    def _set_item_options(self, v: list[dict[str, str]]) -> None:
        set_item_options(self, v)

    def _set_storeroom_options(self, v: list[dict[str, str]]) -> None:
        set_storeroom_options(self, v)

    def _set_selected_status_filter(self, v: str) -> None:
        set_selected_status_filter(self, v)

    def _set_selected_item_filter(self, v: str) -> None:
        set_selected_item_filter(self, v)

    def _set_selected_storeroom_filter(self, v: str) -> None:
        set_selected_storeroom_filter(self, v)

    def _set_search_text(self, v: str) -> None:
        set_search_text(self, v)

    def _set_reservations(self, v: dict[str, object]) -> None:
        set_reservations(self, v)

    def _set_selected_reservation(self, v: dict[str, object]) -> None:
        set_selected_reservation(self, v)

    def _set_selected_reservation_id(self, v: str) -> None:
        set_selected_reservation_id(self, v)

    def _set_selected_reservation_ids(self, ids: list[str]) -> None:
        set_selected_reservation_ids(self, ids)

    def _set_detail_activity_items(self, v: list[dict[str, object]]) -> None:
        set_detail_activity_items(self, v)


__all__ = ["InventoryProcurementReservationsWorkspaceController"]
