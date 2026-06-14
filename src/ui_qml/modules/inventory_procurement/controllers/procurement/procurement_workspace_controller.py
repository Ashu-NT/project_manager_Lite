from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryProcurementProcurementWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .procurement_activity_handler import load_detail_activity
from .procurement_bulk_handler import (
    clear_purchase_order_bulk_selection,
    clear_requisition_bulk_selection,
    select_visible_purchase_orders,
    select_visible_requisitions,
    set_purchase_order_bulk_selection,
    set_requisition_bulk_selection,
)
from .procurement_domain_event_binder import bind_domain_events
from .procurement_export_handler import export_table, is_requisitions_view
from .procurement_filter_handler import (
    clear_filters,
    set_purchase_order_status_filter,
    set_requisition_status_filter,
    set_search_text,
    set_site_filter,
    set_storeroom_filter,
    set_supplier_filter,
)
from .procurement_purchase_order_handler import (
    add_purchase_order_line,
    cancel_purchase_order,
    close_purchase_order,
    create_purchase_order,
    send_purchase_order,
    submit_purchase_order,
    update_purchase_order,
)
from .procurement_receipt_handler import post_receipt
from .procurement_refresh_service import refresh as _do_refresh
from .procurement_requisition_handler import (
    add_requisition_line,
    cancel_requisition,
    create_requisition,
    submit_requisition,
    update_requisition,
)
from .procurement_selection_handler import (
    select_purchase_order,
    select_requisition,
    set_active_view,
    set_purchase_order_page,
    set_purchase_order_page_size,
    set_requisition_page,
    set_requisition_page_size,
)
from .procurement_state import default_collection, default_detail, default_overview
from .procurement_state_setters import (
    set_detail_activity_items,
    set_item_options,
    set_overview,
    set_purchase_order_lines,
    set_purchase_order_status_options,
    set_purchase_orders,
    set_receipts,
    set_requisition_line_options,
    set_requisition_lines,
    set_requisition_options,
    set_requisition_status_options,
    set_requisitions,
    set_search_text as _set_search_text_setter,
    set_selected_purchase_order,
    set_selected_purchase_order_id,
    set_selected_purchase_order_ids,
    set_selected_purchase_order_status_filter,
    set_selected_requisition,
    set_selected_requisition_id,
    set_selected_requisition_ids,
    set_selected_requisition_status_filter,
    set_selected_site_filter,
    set_selected_storeroom_filter,
    set_selected_supplier_filter,
    set_site_options,
    set_storeroom_options,
    set_supplier_options,
)
from .procurement_table_models import create_procurement_table_models

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
    requisitionPageChanged = Signal()
    requisitionPageSizeChanged = Signal()
    selectedRequisitionIdsChanged = Signal()
    purchaseOrderPageChanged = Signal()
    purchaseOrderPageSizeChanged = Signal()
    selectedPurchaseOrderIdsChanged = Signal()
    activeViewChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        procurement_workspace_presenter: InventoryProcurementProcurementWorkspacePresenter
        | None = None,
        activity_api: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = (
            workspace_presenter
            or InventoryProcurementWorkspacePresenter(
                "inventory_procurement.procurement"
            )
        )
        self._procurement_workspace_presenter = (
            procurement_workspace_presenter
            or InventoryProcurementProcurementWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
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
        (
            self._requisitions_table_model,
            self._purchase_orders_table_model,
            self._requisition_lines_table_model,
            self._purchase_order_lines_table_model,
            self._receipts_table_model,
        ) = create_procurement_table_models(self)
        self._requisitions: dict[str, object] = default_collection()
        self._selected_requisition: dict[str, object] = default_detail()
        self._selected_requisition_id = ""
        self._requisition_lines: dict[str, object] = default_collection()
        self._purchase_orders: dict[str, object] = default_collection()
        self._selected_purchase_order: dict[str, object] = default_detail()
        self._selected_purchase_order_id = ""
        self._purchase_order_lines: dict[str, object] = default_collection()
        self._receipts: dict[str, object] = default_collection()
        self._requisition_page = 1
        self._requisition_page_size = 25
        self._selected_requisition_ids: list[str] = []
        self._purchase_order_page = 1
        self._purchase_order_page_size = 25
        self._selected_purchase_order_ids: list[str] = []
        self._active_view = "requisitions"
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

    @Property(QObject, constant=True)
    def requisitionsTableModel(self) -> DynamicTableModel:
        return self._requisitions_table_model

    @Property("QVariantMap", notify=selectedRequisitionChanged)
    def selectedRequisition(self) -> dict[str, object]:
        return self._selected_requisition

    @Property(str, notify=selectedRequisitionIdChanged)
    def selectedRequisitionId(self) -> str:
        return self._selected_requisition_id

    @Property("QVariantMap", notify=requisitionLinesChanged)
    def requisitionLines(self) -> dict[str, object]:
        return self._requisition_lines

    @Property(QObject, constant=True)
    def requisitionLinesTableModel(self) -> DynamicTableModel:
        return self._requisition_lines_table_model

    @Property("QVariantMap", notify=purchaseOrdersChanged)
    def purchaseOrders(self) -> dict[str, object]:
        return self._purchase_orders

    @Property(QObject, constant=True)
    def purchaseOrdersTableModel(self) -> DynamicTableModel:
        return self._purchase_orders_table_model

    @Property("QVariantMap", notify=selectedPurchaseOrderChanged)
    def selectedPurchaseOrder(self) -> dict[str, object]:
        return self._selected_purchase_order

    @Property(str, notify=selectedPurchaseOrderIdChanged)
    def selectedPurchaseOrderId(self) -> str:
        return self._selected_purchase_order_id

    @Property("QVariantMap", notify=purchaseOrderLinesChanged)
    def purchaseOrderLines(self) -> dict[str, object]:
        return self._purchase_order_lines

    @Property(QObject, constant=True)
    def purchaseOrderLinesTableModel(self) -> DynamicTableModel:
        return self._purchase_order_lines_table_model

    @Property("QVariantMap", notify=receiptsChanged)
    def receipts(self) -> dict[str, object]:
        return self._receipts

    @Property(QObject, constant=True)
    def receiptsTableModel(self) -> DynamicTableModel:
        return self._receipts_table_model

    @Property(int, notify=requisitionPageChanged)
    def requisitionPage(self) -> int:
        return self._requisition_page

    @Property(int, notify=requisitionPageSizeChanged)
    def requisitionPageSize(self) -> int:
        return self._requisition_page_size

    @Property(int, notify=requisitionsChanged)
    def requisitionTotalCount(self) -> int:
        return len(self._requisitions.get("items", []))

    @Property("QVariantList", notify=selectedRequisitionIdsChanged)
    def selectedRequisitionIds(self) -> list[str]:
        return self._selected_requisition_ids

    @Property(int, notify=selectedRequisitionIdsChanged)
    def selectedRequisitionCount(self) -> int:
        return len(self._selected_requisition_ids)

    @Property(int, notify=purchaseOrderPageChanged)
    def purchaseOrderPage(self) -> int:
        return self._purchase_order_page

    @Property(int, notify=purchaseOrderPageSizeChanged)
    def purchaseOrderPageSize(self) -> int:
        return self._purchase_order_page_size

    @Property(int, notify=purchaseOrdersChanged)
    def purchaseOrderTotalCount(self) -> int:
        return len(self._purchase_orders.get("items", []))

    @Property("QVariantList", notify=selectedPurchaseOrderIdsChanged)
    def selectedPurchaseOrderIds(self) -> list[str]:
        return self._selected_purchase_order_ids

    @Property(int, notify=selectedPurchaseOrderIdsChanged)
    def selectedPurchaseOrderCount(self) -> int:
        return len(self._selected_purchase_order_ids)

    @Property(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    # ── Internal view helper ──────────────────────────────────────────

    @property
    def _is_requisitions_view(self) -> bool:
        return is_requisitions_view(self)

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
    def setStoreroomFilter(self, storeroom_id: str) -> None:
        set_storeroom_filter(self, storeroom_id)

    @Slot(str)
    def setSupplierFilter(self, supplier_id: str) -> None:
        set_supplier_filter(self, supplier_id)

    @Slot(str)
    def setRequisitionStatusFilter(self, status: str) -> None:
        set_requisition_status_filter(self, status)

    @Slot(str)
    def setPurchaseOrderStatusFilter(self, status: str) -> None:
        set_purchase_order_status_filter(self, status)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def selectRequisition(self, requisition_id: str) -> None:
        select_requisition(self, requisition_id)

    @Slot(str)
    def activateRequisition(self, req_id: str) -> None:
        select_requisition(self, req_id)

    @Slot(str)
    def selectPurchaseOrder(self, purchase_order_id: str) -> None:
        select_purchase_order(self, purchase_order_id)

    @Slot(str)
    def activatePurchaseOrder(self, po_id: str) -> None:
        select_purchase_order(self, po_id)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        set_active_view(self, view)

    @Slot(int)
    def setRequisitionPage(self, page: int) -> None:
        set_requisition_page(self, page)

    @Slot(int)
    def setRequisitionPageSize(self, size: int) -> None:
        set_requisition_page_size(self, size)

    @Slot(int)
    def setPurchaseOrderPage(self, page: int) -> None:
        set_purchase_order_page(self, page)

    @Slot(int)
    def setPurchaseOrderPageSize(self, size: int) -> None:
        set_purchase_order_page_size(self, size)

    @Slot(str, bool)
    def setRequisitionBulkSelection(self, row_id: str, selected: bool) -> None:
        set_requisition_bulk_selection(self, row_id, selected)

    @Slot()
    def clearRequisitionBulkSelection(self) -> None:
        clear_requisition_bulk_selection(self)

    @Slot()
    def selectVisibleRequisitions(self) -> None:
        select_visible_requisitions(self)

    @Slot(str, bool)
    def setPurchaseOrderBulkSelection(self, row_id: str, selected: bool) -> None:
        set_purchase_order_bulk_selection(self, row_id, selected)

    @Slot()
    def clearPurchaseOrderBulkSelection(self) -> None:
        clear_purchase_order_bulk_selection(self)

    @Slot()
    def selectVisiblePurchaseOrders(self) -> None:
        select_visible_purchase_orders(self)

    @Slot("QVariantMap", result="QVariantMap")
    def createRequisition(self, payload: dict[str, object]) -> dict[str, object]:
        return create_requisition(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updateRequisition(self, payload: dict[str, object]) -> dict[str, object]:
        return update_requisition(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def addRequisitionLine(self, payload: dict[str, object]) -> dict[str, object]:
        return add_requisition_line(self, dict(payload))

    @Slot(str, result="QVariantMap")
    def submitRequisition(self, requisition_id: str) -> dict[str, object]:
        return submit_requisition(self, requisition_id)

    @Slot(str, result="QVariantMap")
    def cancelRequisition(self, requisition_id: str) -> dict[str, object]:
        return cancel_requisition(self, requisition_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createPurchaseOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return create_purchase_order(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updatePurchaseOrder(self, payload: dict[str, object]) -> dict[str, object]:
        return update_purchase_order(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def addPurchaseOrderLine(self, payload: dict[str, object]) -> dict[str, object]:
        return add_purchase_order_line(self, dict(payload))

    @Slot(str, result="QVariantMap")
    def submitPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return submit_purchase_order(self, purchase_order_id)

    @Slot(str, result="QVariantMap")
    def sendPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return send_purchase_order(self, purchase_order_id)

    @Slot(str, result="QVariantMap")
    def cancelPurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return cancel_purchase_order(self, purchase_order_id)

    @Slot(str, result="QVariantMap")
    def closePurchaseOrder(self, purchase_order_id: str) -> dict[str, object]:
        return close_purchase_order(self, purchase_order_id)

    @Slot("QVariantMap", result="QVariantMap")
    def postReceipt(self, payload: dict[str, object]) -> dict[str, object]:
        return post_receipt(self, dict(payload))

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

    def _set_storeroom_options(self, v: list[dict[str, str]]) -> None:
        set_storeroom_options(self, v)

    def _set_supplier_options(self, v: list[dict[str, str]]) -> None:
        set_supplier_options(self, v)

    def _set_requisition_status_options(self, v: list[dict[str, str]]) -> None:
        set_requisition_status_options(self, v)

    def _set_purchase_order_status_options(self, v: list[dict[str, str]]) -> None:
        set_purchase_order_status_options(self, v)

    def _set_item_options(self, v: list[dict[str, str]]) -> None:
        set_item_options(self, v)

    def _set_requisition_options(self, v: list[dict[str, str]]) -> None:
        set_requisition_options(self, v)

    def _set_requisition_line_options(self, v: list[dict[str, str]]) -> None:
        set_requisition_line_options(self, v)

    def _set_selected_site_filter(self, v: str) -> None:
        set_selected_site_filter(self, v)

    def _set_selected_storeroom_filter(self, v: str) -> None:
        set_selected_storeroom_filter(self, v)

    def _set_selected_supplier_filter(self, v: str) -> None:
        set_selected_supplier_filter(self, v)

    def _set_selected_requisition_status_filter(self, v: str) -> None:
        set_selected_requisition_status_filter(self, v)

    def _set_selected_purchase_order_status_filter(self, v: str) -> None:
        set_selected_purchase_order_status_filter(self, v)

    def _set_search_text(self, v: str) -> None:
        _set_search_text_setter(self, v)

    def _set_requisitions(self, v: dict[str, object]) -> None:
        set_requisitions(self, v)

    def _set_selected_requisition(self, v: dict[str, object]) -> None:
        set_selected_requisition(self, v)

    def _set_selected_requisition_id(self, v: str) -> None:
        set_selected_requisition_id(self, v)

    def _set_requisition_lines(self, v: dict[str, object]) -> None:
        set_requisition_lines(self, v)

    def _set_purchase_orders(self, v: dict[str, object]) -> None:
        set_purchase_orders(self, v)

    def _set_selected_purchase_order(self, v: dict[str, object]) -> None:
        set_selected_purchase_order(self, v)

    def _set_selected_purchase_order_id(self, v: str) -> None:
        set_selected_purchase_order_id(self, v)

    def _set_purchase_order_lines(self, v: dict[str, object]) -> None:
        set_purchase_order_lines(self, v)

    def _set_receipts(self, v: dict[str, object]) -> None:
        set_receipts(self, v)

    def _set_selected_requisition_ids(self, v: list[str]) -> None:
        set_selected_requisition_ids(self, v)

    def _set_selected_purchase_order_ids(self, v: list[str]) -> None:
        set_selected_purchase_order_ids(self, v)

    def _set_detail_activity_items(self, v: list[dict[str, object]]) -> None:
        set_detail_activity_items(self, v)


__all__ = ["InventoryProcurementProcurementWorkspaceController"]
