from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryInventoryWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .inventory_activity_handler import load_detail_activity
from .inventory_bulk_handler import (
    clear_balance_bulk_selection,
    select_visible_balances,
    set_balance_bulk_selection,
)
from .inventory_domain_event_binder import bind_domain_events
from .inventory_export_handler import export_table, is_balances_view
from .inventory_filter_handler import (
    clear_filters,
    set_active_filter,
    set_item_filter,
    set_search_text,
    set_site_filter,
    set_storeroom_filter,
    set_transaction_type_filter,
)
from .inventory_foundation_handler import (
    complete_cycle_count,
    create_location,
    schedule_cycle_count,
    update_location,
    upsert_reorder_policy,
)
from .inventory_mutation_handler import (
    create_storeroom,
    generate_entity_code,
    toggle_storeroom_active,
    update_storeroom,
)
from .inventory_refresh_service import refresh as _do_refresh
from .inventory_selection_handler import (
    select_balance,
    select_location,
    select_storeroom,
    set_active_view,
    set_balance_page,
    set_balance_page_size,
    set_location_page,
    set_location_page_size,
    set_movement_page,
    set_movement_page_size,
    set_storeroom_page,
    set_storeroom_page_size,
)
from .inventory_state import (
    default_collection,
    default_detail,
    default_foundation,
    default_overview,
)
from .inventory_state_setters import (
    set_active_options,
    set_balances,
    set_detail_activity_items,
    set_foundation,
    set_item_options,
    set_manager_party_options,
    set_overview,
    set_search_text as _set_search_text_setter,
    set_selected_active_filter,
    set_selected_balance,
    set_selected_balance_id,
    set_selected_balance_ids,
    set_selected_item_filter,
    set_selected_location_id,
    set_selected_site_filter,
    set_selected_storeroom,
    set_selected_storeroom_filter,
    set_selected_storeroom_id,
    set_selected_storeroom_ids,
    set_selected_transaction_type_filter,
    set_site_options,
    set_storeroom_options,
    set_storeroom_status_options,
    set_storerooms,
    set_transaction_type_options,
    set_transactions,
)
from .inventory_stock_movement_handler import (
    issue_stock,
    post_adjustment,
    post_opening_balance,
    return_stock,
    transfer_stock,
)
from .inventory_table_models import create_inventory_table_models

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementInventoryWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    activeOptionsChanged = Signal()
    storeroomStatusOptionsChanged = Signal()
    transactionTypeOptionsChanged = Signal()
    storeroomOptionsChanged = Signal()
    itemOptionsChanged = Signal()
    managerPartyOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedActiveFilterChanged = Signal()
    selectedStoreroomFilterChanged = Signal()
    selectedItemFilterChanged = Signal()
    selectedTransactionTypeFilterChanged = Signal()
    searchTextChanged = Signal()
    storeroomsChanged = Signal()
    selectedStoreroomChanged = Signal()
    selectedStoreroomIdChanged = Signal()
    balancesChanged = Signal()
    selectedBalanceChanged = Signal()
    selectedBalanceIdChanged = Signal()
    transactionsChanged = Signal()
    foundationChanged = Signal()
    balancePageChanged = Signal()
    balancePageSizeChanged = Signal()
    selectedBalanceIdsChanged = Signal()
    storeroomPageChanged = Signal()
    storeroomPageSizeChanged = Signal()
    selectedStoreroomIdsChanged = Signal()
    activeViewChanged = Signal()
    movementPageChanged = Signal()
    movementPageSizeChanged = Signal()
    locationPageChanged = Signal()
    locationPageSizeChanged = Signal()
    selectedLocationIdChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        inventory_workspace_presenter: InventoryInventoryWorkspacePresenter | None = None,
        activity_api: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = (
            workspace_presenter
            or InventoryProcurementWorkspacePresenter("inventory_procurement.inventory")
        )
        self._inventory_workspace_presenter = (
            inventory_workspace_presenter or InventoryInventoryWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
        self._site_options: list[dict[str, str]] = []
        self._active_options: list[dict[str, str]] = []
        self._storeroom_status_options: list[dict[str, str]] = []
        self._transaction_type_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._item_options: list[dict[str, str]] = []
        self._manager_party_options: list[dict[str, str]] = []
        self._selected_site_filter = "all"
        self._selected_active_filter = "all"
        self._selected_storeroom_filter = "all"
        self._selected_item_filter = "all"
        self._selected_transaction_type_filter = "all"
        self._search_text = ""
        (
            self._storerooms_table_model,
            self._balances_table_model,
            self._transactions_table_model,
            self._foundation_table_model,
        ) = create_inventory_table_models(self)
        self._storerooms: dict[str, object] = default_collection()
        self._selected_storeroom: dict[str, object] = default_detail()
        self._selected_storeroom_id = ""
        self._balances: dict[str, object] = default_collection()
        self._selected_balance: dict[str, object] = default_detail()
        self._selected_balance_id = ""
        self._transactions: dict[str, object] = default_collection()
        self._foundation: dict[str, object] = default_foundation()
        self._balance_page = 1
        self._balance_page_size = 25
        self._selected_balance_ids: list[str] = []
        self._storeroom_page = 1
        self._storeroom_page_size = 25
        self._selected_storeroom_ids: list[str] = []
        self._active_view = "balances"
        self._movement_page = 1
        self._movement_page_size = 25
        self._location_page = 1
        self._location_page_size = 25
        self._selected_location_id = ""
        self._activity_api = activity_api
        self._detail_activity_items: list[dict[str, object]] = []
        bind_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, str]]:
        return self._site_options

    @Property("QVariantList", notify=activeOptionsChanged)
    def activeOptions(self) -> list[dict[str, str]]:
        return self._active_options

    @Property("QVariantList", notify=storeroomStatusOptionsChanged)
    def storeroomStatusOptions(self) -> list[dict[str, str]]:
        return self._storeroom_status_options

    @Property("QVariantList", notify=transactionTypeOptionsChanged)
    def transactionTypeOptions(self) -> list[dict[str, str]]:
        return self._transaction_type_options

    @Property("QVariantList", notify=storeroomOptionsChanged)
    def storeroomOptions(self) -> list[dict[str, str]]:
        return self._storeroom_options

    @Property("QVariantList", notify=itemOptionsChanged)
    def itemOptions(self) -> list[dict[str, str]]:
        return self._item_options

    @Property("QVariantList", notify=managerPartyOptionsChanged)
    def managerPartyOptions(self) -> list[dict[str, str]]:
        return self._manager_party_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=selectedStoreroomFilterChanged)
    def selectedStoreroomFilter(self) -> str:
        return self._selected_storeroom_filter

    @Property(str, notify=selectedItemFilterChanged)
    def selectedItemFilter(self) -> str:
        return self._selected_item_filter

    @Property(str, notify=selectedTransactionTypeFilterChanged)
    def selectedTransactionTypeFilter(self) -> str:
        return self._selected_transaction_type_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=storeroomsChanged)
    def storerooms(self) -> dict[str, object]:
        return self._storerooms

    @Property(QObject, constant=True)
    def storeroomsTableModel(self) -> DynamicTableModel:
        return self._storerooms_table_model

    @Property("QVariantMap", notify=selectedStoreroomChanged)
    def selectedStoreroom(self) -> dict[str, object]:
        return self._selected_storeroom

    @Property(str, notify=selectedStoreroomIdChanged)
    def selectedStoreroomId(self) -> str:
        return self._selected_storeroom_id

    @Property("QVariantMap", notify=balancesChanged)
    def balances(self) -> dict[str, object]:
        return self._balances

    @Property(QObject, constant=True)
    def balancesTableModel(self) -> DynamicTableModel:
        return self._balances_table_model

    @Property("QVariantMap", notify=selectedBalanceChanged)
    def selectedBalance(self) -> dict[str, object]:
        return self._selected_balance

    @Property(str, notify=selectedBalanceIdChanged)
    def selectedBalanceId(self) -> str:
        return self._selected_balance_id

    @Property("QVariantMap", notify=transactionsChanged)
    def transactions(self) -> dict[str, object]:
        return self._transactions

    @Property(QObject, constant=True)
    def transactionsTableModel(self) -> DynamicTableModel:
        return self._transactions_table_model

    @Property("QVariantMap", notify=foundationChanged)
    def foundation(self) -> dict[str, object]:
        return self._foundation

    @Property(QObject, constant=True)
    def foundationTableModel(self) -> DynamicTableModel:
        return self._foundation_table_model

    @Property(int, notify=balancePageChanged)
    def balancePage(self) -> int:
        return self._balance_page

    @Property(int, notify=balancePageSizeChanged)
    def balancePageSize(self) -> int:
        return self._balance_page_size

    @Property(int, notify=balancesChanged)
    def balanceTotalCount(self) -> int:
        return len(self._balances.get("items", []))

    @Property("QVariantList", notify=selectedBalanceIdsChanged)
    def selectedBalanceIds(self) -> list[str]:
        return self._selected_balance_ids

    @Property(int, notify=selectedBalanceIdsChanged)
    def selectedBalanceCount(self) -> int:
        return len(self._selected_balance_ids)

    @Property(int, notify=storeroomPageChanged)
    def storeroomPage(self) -> int:
        return self._storeroom_page

    @Property(int, notify=storeroomPageSizeChanged)
    def storeroomPageSize(self) -> int:
        return self._storeroom_page_size

    @Property(int, notify=storeroomsChanged)
    def storeroomTotalCount(self) -> int:
        return len(self._storerooms.get("items", []))

    @Property("QVariantList", notify=selectedStoreroomIdsChanged)
    def selectedStoreroomIds(self) -> list[str]:
        return self._selected_storeroom_ids

    @Property(int, notify=selectedStoreroomIdsChanged)
    def selectedStoreroomCount(self) -> int:
        return len(self._selected_storeroom_ids)

    @Property(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @Property(int, notify=movementPageChanged)
    def movementPage(self) -> int:
        return self._movement_page

    @Property(int, notify=movementPageSizeChanged)
    def movementPageSize(self) -> int:
        return self._movement_page_size

    @Property(int, notify=transactionsChanged)
    def movementTotalCount(self) -> int:
        return len(self._transactions.get("items", []))

    @Property(int, notify=locationPageChanged)
    def locationPage(self) -> int:
        return self._location_page

    @Property(int, notify=locationPageSizeChanged)
    def locationPageSize(self) -> int:
        return self._location_page_size

    @Property(int, notify=foundationChanged)
    def locationTotalCount(self) -> int:
        return len(self._foundation.get("locations", []))

    @Property(str, notify=selectedLocationIdChanged)
    def selectedLocationId(self) -> str:
        return self._selected_location_id

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    # ── Internal view helper ──────────────────────────────────────────

    @property
    def _is_balances_view(self) -> bool:
        return is_balances_view(self)

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        _do_refresh(self)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        set_search_text(self, search_text)

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        set_site_filter(self, site_id)

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        set_active_filter(self, active_filter)

    @Slot(str)
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        set_storeroom_filter(self, storeroom_id)

    @Slot(str)
    def setItemFilter(self, item_id: str) -> None:
        set_item_filter(self, item_id)

    @Slot(str)
    def setTransactionTypeFilter(self, transaction_type: str) -> None:
        set_transaction_type_filter(self, transaction_type)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def selectStoreroom(self, storeroom_id: str) -> None:
        select_storeroom(self, storeroom_id)

    @Slot(str)
    def activateStoreroom(self, storeroom_id: str) -> None:
        select_storeroom(self, storeroom_id)

    @Slot(str)
    def selectBalance(self, balance_id: str) -> None:
        select_balance(self, balance_id)

    @Slot(str)
    def activateBalance(self, balance_id: str) -> None:
        select_balance(self, balance_id)

    @Slot(str)
    def selectLocation(self, location_id: str) -> None:
        select_location(self, location_id)

    @Slot(str)
    def activateLocation(self, location_id: str) -> None:
        select_location(self, location_id)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        set_active_view(self, view)

    @Slot(int)
    def setBalancePage(self, page: int) -> None:
        set_balance_page(self, page)

    @Slot(int)
    def setBalancePageSize(self, size: int) -> None:
        set_balance_page_size(self, size)

    @Slot(int)
    def setStoreroomPage(self, page: int) -> None:
        set_storeroom_page(self, page)

    @Slot(int)
    def setStoreroomPageSize(self, size: int) -> None:
        set_storeroom_page_size(self, size)

    @Slot(int)
    def setMovementPage(self, page: int) -> None:
        set_movement_page(self, page)

    @Slot(int)
    def setMovementPageSize(self, size: int) -> None:
        set_movement_page_size(self, size)

    @Slot(int)
    def setLocationPage(self, page: int) -> None:
        set_location_page(self, page)

    @Slot(int)
    def setLocationPageSize(self, size: int) -> None:
        set_location_page_size(self, size)

    @Slot(str, bool)
    def setBalanceBulkSelection(self, row_id: str, selected: bool) -> None:
        set_balance_bulk_selection(self, row_id, selected)

    @Slot()
    def clearBalanceBulkSelection(self) -> None:
        clear_balance_bulk_selection(self)

    @Slot()
    def selectVisibleBalances(self) -> None:
        select_visible_balances(self)

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def createStoreroom(self, payload: dict[str, object]) -> dict[str, object]:
        return create_storeroom(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updateStoreroom(self, payload: dict[str, object]) -> dict[str, object]:
        return update_storeroom(self, dict(payload))

    @Slot(str, int, result="QVariantMap")
    def toggleStoreroomActive(
        self, storeroom_id: str, expected_version: int = 0
    ) -> dict[str, object]:
        return toggle_storeroom_active(self, storeroom_id, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def postOpeningBalance(self, payload: dict[str, object]) -> dict[str, object]:
        return post_opening_balance(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def postAdjustment(self, payload: dict[str, object]) -> dict[str, object]:
        return post_adjustment(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def issueStock(self, payload: dict[str, object]) -> dict[str, object]:
        return issue_stock(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def returnStock(self, payload: dict[str, object]) -> dict[str, object]:
        return return_stock(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def transferStock(self, payload: dict[str, object]) -> dict[str, object]:
        return transfer_stock(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def createLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return create_location(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updateLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return update_location(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def upsertReorderPolicy(self, payload: dict[str, object]) -> dict[str, object]:
        return upsert_reorder_policy(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def scheduleCycleCount(self, payload: dict[str, object]) -> dict[str, object]:
        return schedule_cycle_count(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def completeCycleCount(self, payload: dict[str, object]) -> dict[str, object]:
        return complete_cycle_count(self, dict(payload))

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTable(self, columns: list, file_path: str) -> dict[str, object]:
        return export_table(self, columns, file_path)

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        load_detail_activity(self, entity_id, entity_type)

    # ── Private state setters (called by handlers and refresh service) ─

    def _set_overview(self, v: dict[str, object]) -> None:
        set_overview(self, v)

    def _set_site_options(self, v: list[dict[str, str]]) -> None:
        set_site_options(self, v)

    def _set_active_options(self, v: list[dict[str, str]]) -> None:
        set_active_options(self, v)

    def _set_storeroom_status_options(self, v: list[dict[str, str]]) -> None:
        set_storeroom_status_options(self, v)

    def _set_transaction_type_options(self, v: list[dict[str, str]]) -> None:
        set_transaction_type_options(self, v)

    def _set_storeroom_options(self, v: list[dict[str, str]]) -> None:
        set_storeroom_options(self, v)

    def _set_item_options(self, v: list[dict[str, str]]) -> None:
        set_item_options(self, v)

    def _set_manager_party_options(self, v: list[dict[str, str]]) -> None:
        set_manager_party_options(self, v)

    def _set_selected_site_filter(self, v: str) -> None:
        set_selected_site_filter(self, v)

    def _set_selected_active_filter(self, v: str) -> None:
        set_selected_active_filter(self, v)

    def _set_selected_storeroom_filter(self, v: str) -> None:
        set_selected_storeroom_filter(self, v)

    def _set_selected_item_filter(self, v: str) -> None:
        set_selected_item_filter(self, v)

    def _set_selected_transaction_type_filter(self, v: str) -> None:
        set_selected_transaction_type_filter(self, v)

    def _set_search_text(self, v: str) -> None:
        _set_search_text_setter(self, v)

    def _set_storerooms(self, v: dict[str, object]) -> None:
        set_storerooms(self, v)

    def _set_selected_storeroom(self, v: dict[str, object]) -> None:
        set_selected_storeroom(self, v)

    def _set_selected_storeroom_id(self, v: str) -> None:
        set_selected_storeroom_id(self, v)

    def _set_balances(self, v: dict[str, object]) -> None:
        set_balances(self, v)

    def _set_selected_balance(self, v: dict[str, object]) -> None:
        set_selected_balance(self, v)

    def _set_selected_balance_id(self, v: str) -> None:
        set_selected_balance_id(self, v)

    def _set_selected_location_id(self, v: str) -> None:
        set_selected_location_id(self, v)

    def _set_transactions(self, v: dict[str, object]) -> None:
        set_transactions(self, v)

    def _set_foundation(self, v: dict[str, object]) -> None:
        set_foundation(self, v)

    def _set_selected_balance_ids(self, v: list[str]) -> None:
        set_selected_balance_ids(self, v)

    def _set_selected_storeroom_ids(self, v: list[str]) -> None:
        set_selected_storeroom_ids(self, v)

    def _set_detail_activity_items(self, v: list[dict[str, object]]) -> None:
        set_detail_activity_items(self, v)


__all__ = ["InventoryProcurementInventoryWorkspaceController"]
