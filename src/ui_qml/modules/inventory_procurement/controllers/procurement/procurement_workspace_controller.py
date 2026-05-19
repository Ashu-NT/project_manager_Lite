from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    run_mutation,
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryProcurementProcurementWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementProcurementWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    storeroomOptionsChanged = Signal()
    supplierOptionsChanged = Signal()
    requisitionStatusOptionsChanged = Signal()
    purchaseOrderStatusOptionsChanged = Signal()
    itemOptionsChanged = Signal()
    requisitionOptionsChanged = Signal()
    requisitionLineOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedStoreroomFilterChanged = Signal()
    selectedSupplierFilterChanged = Signal()
    selectedRequisitionStatusFilterChanged = Signal()
    selectedPurchaseOrderStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    requisitionsChanged = Signal()
    selectedRequisitionChanged = Signal()
    selectedRequisitionIdChanged = Signal()
    requisitionLinesChanged = Signal()
    purchaseOrdersChanged = Signal()
    selectedPurchaseOrderChanged = Signal()
    selectedPurchaseOrderIdChanged = Signal()
    purchaseOrderLinesChanged = Signal()
    receiptsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        procurement_workspace_presenter: InventoryProcurementProcurementWorkspacePresenter
        | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.procurement"
        )
        self._procurement_workspace_presenter = (
            procurement_workspace_presenter
            or InventoryProcurementProcurementWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._supplier_options: list[dict[str, str]] = []
        self._requisition_status_options: list[dict[str, str]] = []
        self._purchase_order_status_options: list[dict[str, str]] = []
        self._item_options: list[dict[str, str]] = []
        self._requisition_options: list[dict[str, str]] = []
        self._requisition_line_options: list[dict[str, str]] = []
        self._selected_site_filter = "all"
        self._selected_storeroom_filter = "all"
        self._selected_supplier_filter = "all"
        self._selected_requisition_status_filter = "all"
        self._selected_purchase_order_status_filter = "all"
        self._search_text = ""
        self._requisitions: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_requisition: dict[str, object] = {
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
        self._selected_requisition_id = ""
        self._requisition_lines: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._purchase_orders: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_purchase_order: dict[str, object] = {
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
        self._selected_purchase_order_id = ""
        self._purchase_order_lines: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._receipts: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, str]]:
        return self._site_options

    @Property("QVariantList", notify=storeroomOptionsChanged)
    def storeroomOptions(self) -> list[dict[str, str]]:
        return self._storeroom_options

    @Property("QVariantList", notify=supplierOptionsChanged)
    def supplierOptions(self) -> list[dict[str, str]]:
        return self._supplier_options

    @Property("QVariantList", notify=requisitionStatusOptionsChanged)
    def requisitionStatusOptions(self) -> list[dict[str, str]]:
        return self._requisition_status_options

    @Property("QVariantList", notify=purchaseOrderStatusOptionsChanged)
    def purchaseOrderStatusOptions(self) -> list[dict[str, str]]:
        return self._purchase_order_status_options

    @Property("QVariantList", notify=itemOptionsChanged)
    def itemOptions(self) -> list[dict[str, str]]:
        return self._item_options

    @Property("QVariantList", notify=requisitionOptionsChanged)
    def requisitionOptions(self) -> list[dict[str, str]]:
        return self._requisition_options

    @Property("QVariantList", notify=requisitionLineOptionsChanged)
    def requisitionLineOptions(self) -> list[dict[str, str]]:
        return self._requisition_line_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedStoreroomFilterChanged)
    def selectedStoreroomFilter(self) -> str:
        return self._selected_storeroom_filter

    @Property(str, notify=selectedSupplierFilterChanged)
    def selectedSupplierFilter(self) -> str:
        return self._selected_supplier_filter

    @Property(str, notify=selectedRequisitionStatusFilterChanged)
    def selectedRequisitionStatusFilter(self) -> str:
        return self._selected_requisition_status_filter

    @Property(str, notify=selectedPurchaseOrderStatusFilterChanged)
    def selectedPurchaseOrderStatusFilter(self) -> str:
        return self._selected_purchase_order_status_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=requisitionsChanged)
    def requisitions(self) -> dict[str, object]:
        return self._requisitions

    @Property("QVariantMap", notify=selectedRequisitionChanged)
    def selectedRequisition(self) -> dict[str, object]:
        return self._selected_requisition

    @Property(str, notify=selectedRequisitionIdChanged)
    def selectedRequisitionId(self) -> str:
        return self._selected_requisition_id

    @Property("QVariantMap", notify=requisitionLinesChanged)
    def requisitionLines(self) -> dict[str, object]:
        return self._requisition_lines

    @Property("QVariantMap", notify=purchaseOrdersChanged)
    def purchaseOrders(self) -> dict[str, object]:
        return self._purchase_orders

    @Property("QVariantMap", notify=selectedPurchaseOrderChanged)
    def selectedPurchaseOrder(self) -> dict[str, object]:
        return self._selected_purchase_order

    @Property(str, notify=selectedPurchaseOrderIdChanged)
    def selectedPurchaseOrderId(self) -> str:
        return self._selected_purchase_order_id

    @Property("QVariantMap", notify=purchaseOrderLinesChanged)
    def purchaseOrderLines(self) -> dict[str, object]:
        return self._purchase_order_lines

    @Property("QVariantMap", notify=receiptsChanged)
    def receipts(self) -> dict[str, object]:
        return self._receipts

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
            workspace_state = (
                self._procurement_workspace_presenter.build_workspace_state(
                    search_text=self._search_text,
                    site_filter=self._selected_site_filter,
                    storeroom_filter=self._selected_storeroom_filter,
                    supplier_filter=self._selected_supplier_filter,
                    requisition_status_filter=self._selected_requisition_status_filter,
                    purchase_order_status_filter=self._selected_purchase_order_status_filter,
                    selected_requisition_id=self._selected_requisition_id or None,
                    selected_purchase_order_id=self._selected_purchase_order_id or None,
                )
            )
            self._set_overview(
                serialize_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_site_options(
                serialize_selector_options(workspace_state.site_options)
            )
            self._set_storeroom_options(
                serialize_selector_options(workspace_state.storeroom_options)
            )
            self._set_supplier_options(
                serialize_selector_options(workspace_state.supplier_options)
            )
            self._set_requisition_status_options(
                serialize_selector_options(workspace_state.requisition_status_options)
            )
            self._set_purchase_order_status_options(
                serialize_selector_options(
                    workspace_state.purchase_order_status_options
                )
            )
            self._set_item_options(
                serialize_selector_options(workspace_state.item_options)
            )
            self._set_requisition_options(
                serialize_selector_options(workspace_state.requisition_options)
            )
            self._set_requisition_line_options(
                serialize_selector_options(workspace_state.requisition_line_options)
            )
            self._set_selected_site_filter(workspace_state.selected_site_filter)
            self._set_selected_storeroom_filter(
                workspace_state.selected_storeroom_filter
            )
            self._set_selected_supplier_filter(
                workspace_state.selected_supplier_filter
            )
            self._set_selected_requisition_status_filter(
                workspace_state.selected_requisition_status_filter
            )
            self._set_selected_purchase_order_status_filter(
                workspace_state.selected_purchase_order_status_filter
            )
            self._set_search_text(workspace_state.search_text)
            self._set_requisitions(
                {
                    "title": "Requisitions",
                    "subtitle": (
                        "Capture internal supply demand, add line-level item needs, "
                        "and move draft demand into approvals."
                    ),
                    "emptyState": workspace_state.requisitions_empty_state,
                    "items": serialize_record_view_models(workspace_state.requisitions),
                }
            )
            self._set_selected_requisition_id(
                workspace_state.selected_requisition_id
            )
            self._set_selected_requisition(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_requisition_detail
                )
            )
            self._set_requisition_lines(
                {
                    "title": "Requisition Lines",
                    "subtitle": (
                        "Demand lines that will later be converted into supplier-facing "
                        "procurement commitments."
                    ),
                    "emptyState": workspace_state.requisition_lines_empty_state,
                    "items": serialize_record_view_models(
                        workspace_state.requisition_lines
                    ),
                }
            )
            self._set_purchase_orders(
                {
                    "title": "Purchase Orders",
                    "subtitle": (
                        "Commit approved demand to suppliers, track approval state, and "
                        "prepare orders for receiving."
                    ),
                    "emptyState": workspace_state.purchase_orders_empty_state,
                    "items": serialize_record_view_models(
                        workspace_state.purchase_orders
                    ),
                }
            )
            self._set_selected_purchase_order_id(
                workspace_state.selected_purchase_order_id
            )
            self._set_selected_purchase_order(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_purchase_order_detail
                )
            )
            self._set_purchase_order_lines(
                {
                    "title": "Purchase-Order Lines",
                    "subtitle": (
                        "Receiving destinations, ordered quantities, and outstanding "
                        "supplier commitments on the selected order."
                    ),
                    "emptyState": workspace_state.purchase_order_lines_empty_state,
                    "items": serialize_record_view_models(
                        workspace_state.purchase_order_lines
                    ),
                }
            )
            self._set_receipts(
                {
                    "title": "Receipt History",
                    "subtitle": (
                        "Posted receiving transactions for the selected purchase order, "
                        "including accepted and rejected quantities."
                    ),
                    "emptyState": workspace_state.receipts_empty_state,
                    "items": serialize_record_view_models(workspace_state.receipts),
                }
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
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        normalized = (storeroom_id or "").strip() or "all"
        if normalized == self._selected_storeroom_filter:
            return
        self._set_selected_storeroom_filter(normalized)
        self.refresh()

    @Slot(str)
    def setSupplierFilter(self, supplier_id: str) -> None:
        normalized = (supplier_id or "").strip() or "all"
        if normalized == self._selected_supplier_filter:
            return
        self._set_selected_supplier_filter(normalized)
        self.refresh()

    @Slot(str)
    def setRequisitionStatusFilter(self, status: str) -> None:
        normalized = (status or "").strip() or "all"
        if normalized == self._selected_requisition_status_filter:
            return
        self._set_selected_requisition_status_filter(normalized)
        self.refresh()

    @Slot(str)
    def setPurchaseOrderStatusFilter(self, status: str) -> None:
        normalized = (status or "").strip() or "all"
        if normalized == self._selected_purchase_order_status_filter:
            return
        self._set_selected_purchase_order_status_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectRequisition(self, requisition_id: str) -> None:
        normalized = (requisition_id or "").strip()
        if normalized == self._selected_requisition_id:
            return
        self._set_selected_requisition_id(normalized)
        self.refresh()

    @Slot(str)
    def selectPurchaseOrder(self, purchase_order_id: str) -> None:
        normalized = (purchase_order_id or "").strip()
        if normalized == self._selected_purchase_order_id:
            return
        self._set_selected_purchase_order_id(normalized)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createRequisition(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.create_requisition(
                dict(payload)
            ),
            success_message="Requisition created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateRequisition(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.update_requisition(
                dict(payload)
            ),
            success_message="Requisition updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addRequisitionLine(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.add_requisition_line(
                dict(payload)
            ),
            success_message="Requisition line added.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def submitRequisition(self, requisition_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.submit_requisition(
                requisition_id
            ),
            success_message="Requisition submitted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def cancelRequisition(self, requisition_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.cancel_requisition(
                requisition_id
            ),
            success_message="Requisition cancelled.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createPurchaseOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.create_purchase_order(
                dict(payload)
            ),
            success_message="Purchase order created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updatePurchaseOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.update_purchase_order(
                dict(payload)
            ),
            success_message="Purchase order updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addPurchaseOrderLine(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.add_purchase_order_line(
                dict(payload)
            ),
            success_message="Purchase-order line added.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def submitPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.submit_purchase_order(
                purchase_order_id
            ),
            success_message="Purchase order submitted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def sendPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.send_purchase_order(
                purchase_order_id
            ),
            success_message="Purchase order sent.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def cancelPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.cancel_purchase_order(
                purchase_order_id
            ),
            success_message="Purchase order cancelled.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def closePurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.close_purchase_order(
                purchase_order_id
            ),
            success_message="Purchase order closed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def postReceipt(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._procurement_workspace_presenter.post_receipt(
                dict(payload)
            ),
            success_message="Receipt posted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="inventory_procurement")
        self._subscribe_domain_change("site", scope_code="platform")
        self._subscribe_domain_change("party", scope_code="platform")

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

    def _set_storeroom_options(self, storeroom_options: list[dict[str, str]]) -> None:
        if storeroom_options == self._storeroom_options:
            return
        self._storeroom_options = storeroom_options
        self.storeroomOptionsChanged.emit()

    def _set_supplier_options(self, supplier_options: list[dict[str, str]]) -> None:
        if supplier_options == self._supplier_options:
            return
        self._supplier_options = supplier_options
        self.supplierOptionsChanged.emit()

    def _set_requisition_status_options(
        self,
        status_options: list[dict[str, str]],
    ) -> None:
        if status_options == self._requisition_status_options:
            return
        self._requisition_status_options = status_options
        self.requisitionStatusOptionsChanged.emit()

    def _set_purchase_order_status_options(
        self,
        status_options: list[dict[str, str]],
    ) -> None:
        if status_options == self._purchase_order_status_options:
            return
        self._purchase_order_status_options = status_options
        self.purchaseOrderStatusOptionsChanged.emit()

    def _set_item_options(self, item_options: list[dict[str, str]]) -> None:
        if item_options == self._item_options:
            return
        self._item_options = item_options
        self.itemOptionsChanged.emit()

    def _set_requisition_options(
        self,
        requisition_options: list[dict[str, str]],
    ) -> None:
        if requisition_options == self._requisition_options:
            return
        self._requisition_options = requisition_options
        self.requisitionOptionsChanged.emit()

    def _set_requisition_line_options(
        self,
        requisition_line_options: list[dict[str, str]],
    ) -> None:
        if requisition_line_options == self._requisition_line_options:
            return
        self._requisition_line_options = requisition_line_options
        self.requisitionLineOptionsChanged.emit()

    def _set_selected_site_filter(self, selected_site_filter: str) -> None:
        if selected_site_filter == self._selected_site_filter:
            return
        self._selected_site_filter = selected_site_filter
        self.selectedSiteFilterChanged.emit()

    def _set_selected_storeroom_filter(
        self,
        selected_storeroom_filter: str,
    ) -> None:
        if selected_storeroom_filter == self._selected_storeroom_filter:
            return
        self._selected_storeroom_filter = selected_storeroom_filter
        self.selectedStoreroomFilterChanged.emit()

    def _set_selected_supplier_filter(self, selected_supplier_filter: str) -> None:
        if selected_supplier_filter == self._selected_supplier_filter:
            return
        self._selected_supplier_filter = selected_supplier_filter
        self.selectedSupplierFilterChanged.emit()

    def _set_selected_requisition_status_filter(
        self,
        selected_requisition_status_filter: str,
    ) -> None:
        if selected_requisition_status_filter == self._selected_requisition_status_filter:
            return
        self._selected_requisition_status_filter = selected_requisition_status_filter
        self.selectedRequisitionStatusFilterChanged.emit()

    def _set_selected_purchase_order_status_filter(
        self,
        selected_purchase_order_status_filter: str,
    ) -> None:
        if (
            selected_purchase_order_status_filter
            == self._selected_purchase_order_status_filter
        ):
            return
        self._selected_purchase_order_status_filter = (
            selected_purchase_order_status_filter
        )
        self.selectedPurchaseOrderStatusFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_requisitions(self, requisitions: dict[str, object]) -> None:
        if requisitions == self._requisitions:
            return
        self._requisitions = requisitions
        self.requisitionsChanged.emit()

    def _set_selected_requisition(
        self,
        selected_requisition: dict[str, object],
    ) -> None:
        if selected_requisition == self._selected_requisition:
            return
        self._selected_requisition = selected_requisition
        self.selectedRequisitionChanged.emit()

    def _set_selected_requisition_id(self, selected_requisition_id: str) -> None:
        if selected_requisition_id == self._selected_requisition_id:
            return
        self._selected_requisition_id = selected_requisition_id
        self.selectedRequisitionIdChanged.emit()

    def _set_requisition_lines(self, requisition_lines: dict[str, object]) -> None:
        if requisition_lines == self._requisition_lines:
            return
        self._requisition_lines = requisition_lines
        self.requisitionLinesChanged.emit()

    def _set_purchase_orders(self, purchase_orders: dict[str, object]) -> None:
        if purchase_orders == self._purchase_orders:
            return
        self._purchase_orders = purchase_orders
        self.purchaseOrdersChanged.emit()

    def _set_selected_purchase_order(
        self,
        selected_purchase_order: dict[str, object],
    ) -> None:
        if selected_purchase_order == self._selected_purchase_order:
            return
        self._selected_purchase_order = selected_purchase_order
        self.selectedPurchaseOrderChanged.emit()

    def _set_selected_purchase_order_id(
        self,
        selected_purchase_order_id: str,
    ) -> None:
        if selected_purchase_order_id == self._selected_purchase_order_id:
            return
        self._selected_purchase_order_id = selected_purchase_order_id
        self.selectedPurchaseOrderIdChanged.emit()

    def _set_purchase_order_lines(
        self,
        purchase_order_lines: dict[str, object],
    ) -> None:
        if purchase_order_lines == self._purchase_order_lines:
            return
        self._purchase_order_lines = purchase_order_lines
        self.purchaseOrderLinesChanged.emit()

    def _set_receipts(self, receipts: dict[str, object]) -> None:
        if receipts == self._receipts:
            return
        self._receipts = receipts
        self.receiptsChanged.emit()


__all__ = ["InventoryProcurementProcurementWorkspaceController"]
