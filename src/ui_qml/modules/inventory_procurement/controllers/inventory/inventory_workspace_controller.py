from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    run_mutation,
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_foundation_view_model,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryInventoryWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)

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
    # pagination + bulk + view
    balancePageChanged = Signal()
    balancePageSizeChanged = Signal()
    selectedBalanceIdsChanged = Signal()
    storeroomPageChanged = Signal()
    storeroomPageSizeChanged = Signal()
    selectedStoreroomIdsChanged = Signal()
    activeViewChanged = Signal()
    movementPageChanged = Signal()
    movementPageSizeChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        inventory_workspace_presenter: InventoryInventoryWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.inventory"
        )
        self._inventory_workspace_presenter = (
            inventory_workspace_presenter or InventoryInventoryWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
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
        self._storerooms: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_storeroom: dict[str, object] = {
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
        self._selected_storeroom_id = ""
        self._balances: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_balance: dict[str, object] = {
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
        self._selected_balance_id = ""
        self._transactions: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._foundation: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "metrics": [],
            "moduleLinks": [],
            "locationTypeOptions": [],
            "cycleCountStatusOptions": [],
            "locations": [],
            "reorderPolicies": [],
            "cycleCounts": [],
            "valuationSignals": [],
            "trackingSignals": [],
            "activitySignals": [],
        }
        # pagination + bulk + view state
        self._balance_page = 1
        self._balance_page_size = 25
        self._selected_balance_ids: list[str] = []
        self._storeroom_page = 1
        self._storeroom_page_size = 25
        self._selected_storeroom_ids: list[str] = []
        self._active_view = "balances"
        self._movement_page = 1
        self._movement_page_size = 25
        self._bind_domain_events()
        self.refresh()

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

    @Property("QVariantMap", notify=selectedStoreroomChanged)
    def selectedStoreroom(self) -> dict[str, object]:
        return self._selected_storeroom

    @Property(str, notify=selectedStoreroomIdChanged)
    def selectedStoreroomId(self) -> str:
        return self._selected_storeroom_id

    @Property("QVariantMap", notify=balancesChanged)
    def balances(self) -> dict[str, object]:
        return self._balances

    @Property("QVariantMap", notify=selectedBalanceChanged)
    def selectedBalance(self) -> dict[str, object]:
        return self._selected_balance

    @Property(str, notify=selectedBalanceIdChanged)
    def selectedBalanceId(self) -> str:
        return self._selected_balance_id

    @Property("QVariantMap", notify=transactionsChanged)
    def transactions(self) -> dict[str, object]:
        return self._transactions

    @Property("QVariantMap", notify=foundationChanged)
    def foundation(self) -> dict[str, object]:
        return self._foundation

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
            workspace_state = self._inventory_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                site_filter=self._selected_site_filter,
                active_filter=self._selected_active_filter,
                storeroom_filter=self._selected_storeroom_filter,
                item_filter=self._selected_item_filter,
                transaction_type_filter=self._selected_transaction_type_filter,
                selected_storeroom_id=self._selected_storeroom_id or None,
                selected_balance_id=self._selected_balance_id or None,
            )
            self._set_overview(
                serialize_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_site_options(serialize_selector_options(workspace_state.site_options))
            self._set_active_options(
                serialize_selector_options(workspace_state.active_options)
            )
            self._set_storeroom_status_options(
                serialize_selector_options(workspace_state.storeroom_status_options)
            )
            self._set_transaction_type_options(
                serialize_selector_options(workspace_state.transaction_type_options)
            )
            self._set_storeroom_options(
                serialize_selector_options(workspace_state.storeroom_options)
            )
            self._set_item_options(
                serialize_selector_options(workspace_state.item_options)
            )
            self._set_manager_party_options(
                serialize_selector_options(workspace_state.manager_party_options)
            )
            self._set_selected_site_filter(workspace_state.selected_site_filter)
            self._set_selected_active_filter(workspace_state.selected_active_filter)
            self._set_selected_storeroom_filter(
                workspace_state.selected_storeroom_filter
            )
            self._set_selected_item_filter(workspace_state.selected_item_filter)
            self._set_selected_transaction_type_filter(
                workspace_state.selected_transaction_type_filter
            )
            self._set_search_text(workspace_state.search_text)
            self._set_storerooms(
                {
                    "title": "Storerooms",
                    "subtitle": "Govern stock locations, operational permissions, and manager ownership.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.storerooms),
                }
            )
            self._set_selected_storeroom_id(workspace_state.selected_storeroom_id)
            self._set_selected_storeroom(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_storeroom_detail
                )
            )
            self._set_balances(
                {
                    "title": "Stock Balances",
                    "subtitle": "Inspect on-hand, reserved, available, and on-order positions by storeroom.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.balances),
                }
            )
            self._set_selected_balance_id(workspace_state.selected_balance_id)
            self._set_selected_balance(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_balance_detail
                )
            )
            self._set_transactions(
                {
                    "title": "Recent Movements",
                    "subtitle": "Opening balances, adjustments, issues, returns, and transfer history.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.transactions),
                }
            )
            self._set_foundation(
                serialize_foundation_view_model(workspace_state.foundation)
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
    def setSiteFilter(self, site_id: str) -> None:
        normalized = (site_id or "").strip() or "all"
        if normalized == self._selected_site_filter:
            return
        self._set_selected_site_filter(normalized)
        self.refresh()

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        normalized = (active_filter or "").strip().lower() or "all"
        if normalized == self._selected_active_filter:
            return
        self._set_selected_active_filter(normalized)
        self.refresh()

    @Slot(str)
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        normalized = (storeroom_id or "").strip() or "all"
        if normalized == self._selected_storeroom_filter:
            return
        self._set_selected_storeroom_filter(normalized)
        self.refresh()

    @Slot(str)
    def setItemFilter(self, item_id: str) -> None:
        normalized = (item_id or "").strip() or "all"
        if normalized == self._selected_item_filter:
            return
        self._set_selected_item_filter(normalized)
        self.refresh()

    @Slot(str)
    def setTransactionTypeFilter(self, transaction_type: str) -> None:
        normalized = (transaction_type or "").strip() or "all"
        if normalized == self._selected_transaction_type_filter:
            return
        self._set_selected_transaction_type_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectStoreroom(self, storeroom_id: str) -> None:
        normalized = (storeroom_id or "").strip()
        if normalized == self._selected_storeroom_id:
            return
        self._set_selected_storeroom_id(normalized)
        self.refresh()

    @Slot(str)
    def selectBalance(self, balance_id: str) -> None:
        normalized = (balance_id or "").strip()
        if normalized == self._selected_balance_id:
            return
        self._set_selected_balance_id(normalized)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createStoreroom(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.create_storeroom(
                dict(payload)
            ),
            success_message="Storeroom created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateStoreroom(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.update_storeroom(
                dict(payload)
            ),
            success_message="Storeroom updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleStoreroomActive(
        self,
        storeroom_id: str,
        expected_version: int = 0,
    ) -> dict[str, object]:
        resolved_version = expected_version or None
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.toggle_storeroom_active(
                storeroom_id,
                resolved_version,
            ),
            success_message="Storeroom availability updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def postOpeningBalance(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.post_opening_balance(
                dict(payload)
            ),
            success_message="Opening balance posted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def postAdjustment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.post_adjustment(
                dict(payload)
            ),
            success_message="Adjustment posted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def issueStock(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.issue_stock(
                dict(payload)
            ),
            success_message="Stock issued.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def returnStock(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.return_stock(
                dict(payload)
            ),
            success_message="Stock returned.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def transferStock(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.transfer_stock(
                dict(payload)
            ),
            success_message="Stock transfer posted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.create_location(
                dict(payload)
            ),
            success_message="Storage location created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.update_location(
                dict(payload)
            ),
            success_message="Storage location updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def upsertReorderPolicy(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.upsert_reorder_policy(
                dict(payload)
            ),
            success_message="Reorder policy saved.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def scheduleCycleCount(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.schedule_cycle_count(
                dict(payload)
            ),
            success_message="Cycle count scheduled.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def completeCycleCount(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._inventory_workspace_presenter.complete_cycle_count(
                dict(payload)
            ),
            success_message="Cycle count completed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── pagination + bulk + view ─────────────────────────────────────

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

    @Slot(str)
    def activateBalance(self, balance_id: str) -> None:
        self.selectBalance(balance_id)

    @Slot(str)
    def activateStoreroom(self, storeroom_id: str) -> None:
        self.selectStoreroom(storeroom_id)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        normalized = view if view in ("balances", "storerooms") else "balances"
        if normalized == self._active_view:
            return
        self._active_view = normalized
        self.activeViewChanged.emit()

    @Slot(int)
    def setBalancePage(self, page: int) -> None:
        self._balance_page = max(1, int(page))
        self.balancePageChanged.emit()

    @Slot(int)
    def setBalancePageSize(self, size: int) -> None:
        self._balance_page_size = max(10, min(200, int(size)))
        self._balance_page = 1
        self.balancePageSizeChanged.emit()
        self.balancePageChanged.emit()

    @Slot(int)
    def setStoreroomPage(self, page: int) -> None:
        self._storeroom_page = max(1, int(page))
        self.storeroomPageChanged.emit()

    @Slot(int)
    def setStoreroomPageSize(self, size: int) -> None:
        self._storeroom_page_size = max(10, min(200, int(size)))
        self._storeroom_page = 1
        self.storeroomPageSizeChanged.emit()
        self.storeroomPageChanged.emit()

    @Slot(int)
    def setMovementPage(self, page: int) -> None:
        self._movement_page = max(1, int(page))
        self.movementPageChanged.emit()

    @Slot(int)
    def setMovementPageSize(self, size: int) -> None:
        self._movement_page_size = max(10, min(200, int(size)))
        self._movement_page = 1
        self.movementPageSizeChanged.emit()
        self.movementPageChanged.emit()

    @Slot(str, bool)
    def setBalanceBulkSelection(self, row_id: str, selected: bool) -> None:
        ids = list(self._selected_balance_ids)
        if selected and row_id not in ids:
            ids.append(row_id)
        elif not selected and row_id in ids:
            ids.remove(row_id)
        self._set_selected_balance_ids(ids)

    @Slot()
    def clearBalanceBulkSelection(self) -> None:
        self._set_selected_balance_ids([])

    @Slot()
    def selectVisibleBalances(self) -> None:
        all_ids = [
            str(r.get("id", ""))
            for r in self._balances.get("items", [])
            if r.get("id")
        ]
        self._set_selected_balance_ids(all_ids)

    @Slot()
    def clearFilters(self) -> None:
        self._set_selected_site_filter("all")
        self._set_selected_active_filter("all")
        self._set_selected_storeroom_filter("all")
        self._set_selected_item_filter("all")
        self._set_selected_transaction_type_filter("all")
        self._set_search_text("")
        self.refresh()

    def _set_selected_balance_ids(self, ids: list[str]) -> None:
        if ids == self._selected_balance_ids:
            return
        self._selected_balance_ids = ids
        self.selectedBalanceIdsChanged.emit()

    def _set_selected_storeroom_ids(self, ids: list[str]) -> None:
        if ids == self._selected_storeroom_ids:
            return
        self._selected_storeroom_ids = ids
        self.selectedStoreroomIdsChanged.emit()

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="inventory_procurement")
        self._subscribe_domain_change("party", scope_code="platform")
        self._subscribe_domain_change("site", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_site_options(self, site_options: list[dict[str, str]]) -> None:
        if site_options == self._site_options:
            return
        self._site_options = site_options
        self.siteOptionsChanged.emit()

    def _set_active_options(self, active_options: list[dict[str, str]]) -> None:
        if active_options == self._active_options:
            return
        self._active_options = active_options
        self.activeOptionsChanged.emit()

    def _set_storeroom_status_options(
        self,
        storeroom_status_options: list[dict[str, str]],
    ) -> None:
        if storeroom_status_options == self._storeroom_status_options:
            return
        self._storeroom_status_options = storeroom_status_options
        self.storeroomStatusOptionsChanged.emit()

    def _set_transaction_type_options(
        self,
        transaction_type_options: list[dict[str, str]],
    ) -> None:
        if transaction_type_options == self._transaction_type_options:
            return
        self._transaction_type_options = transaction_type_options
        self.transactionTypeOptionsChanged.emit()

    def _set_storeroom_options(self, storeroom_options: list[dict[str, str]]) -> None:
        if storeroom_options == self._storeroom_options:
            return
        self._storeroom_options = storeroom_options
        self.storeroomOptionsChanged.emit()

    def _set_item_options(self, item_options: list[dict[str, str]]) -> None:
        if item_options == self._item_options:
            return
        self._item_options = item_options
        self.itemOptionsChanged.emit()

    def _set_manager_party_options(
        self,
        manager_party_options: list[dict[str, str]],
    ) -> None:
        if manager_party_options == self._manager_party_options:
            return
        self._manager_party_options = manager_party_options
        self.managerPartyOptionsChanged.emit()

    def _set_selected_site_filter(self, selected_site_filter: str) -> None:
        if selected_site_filter == self._selected_site_filter:
            return
        self._selected_site_filter = selected_site_filter
        self.selectedSiteFilterChanged.emit()

    def _set_selected_active_filter(self, selected_active_filter: str) -> None:
        if selected_active_filter == self._selected_active_filter:
            return
        self._selected_active_filter = selected_active_filter
        self.selectedActiveFilterChanged.emit()

    def _set_selected_storeroom_filter(self, selected_storeroom_filter: str) -> None:
        if selected_storeroom_filter == self._selected_storeroom_filter:
            return
        self._selected_storeroom_filter = selected_storeroom_filter
        self.selectedStoreroomFilterChanged.emit()

    def _set_selected_item_filter(self, selected_item_filter: str) -> None:
        if selected_item_filter == self._selected_item_filter:
            return
        self._selected_item_filter = selected_item_filter
        self.selectedItemFilterChanged.emit()

    def _set_selected_transaction_type_filter(
        self,
        selected_transaction_type_filter: str,
    ) -> None:
        if selected_transaction_type_filter == self._selected_transaction_type_filter:
            return
        self._selected_transaction_type_filter = selected_transaction_type_filter
        self.selectedTransactionTypeFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_storerooms(self, storerooms: dict[str, object]) -> None:
        if storerooms == self._storerooms:
            return
        self._storerooms = storerooms
        self.storeroomsChanged.emit()

    def _set_selected_storeroom(self, selected_storeroom: dict[str, object]) -> None:
        if selected_storeroom == self._selected_storeroom:
            return
        self._selected_storeroom = selected_storeroom
        self.selectedStoreroomChanged.emit()

    def _set_selected_storeroom_id(self, selected_storeroom_id: str) -> None:
        if selected_storeroom_id == self._selected_storeroom_id:
            return
        self._selected_storeroom_id = selected_storeroom_id
        self.selectedStoreroomIdChanged.emit()

    def _set_balances(self, balances: dict[str, object]) -> None:
        if balances == self._balances:
            return
        self._balances = balances
        self.balancesChanged.emit()

    def _set_selected_balance(self, selected_balance: dict[str, object]) -> None:
        if selected_balance == self._selected_balance:
            return
        self._selected_balance = selected_balance
        self.selectedBalanceChanged.emit()

    def _set_selected_balance_id(self, selected_balance_id: str) -> None:
        if selected_balance_id == self._selected_balance_id:
            return
        self._selected_balance_id = selected_balance_id
        self.selectedBalanceIdChanged.emit()

    def _set_transactions(self, transactions: dict[str, object]) -> None:
        if transactions == self._transactions:
            return
        self._transactions = transactions
        self.transactionsChanged.emit()

    def _set_foundation(self, foundation: dict[str, object]) -> None:
        if foundation == self._foundation:
            return
        self._foundation = foundation
        self.foundationChanged.emit()


__all__ = ["InventoryProcurementInventoryWorkspaceController"]
