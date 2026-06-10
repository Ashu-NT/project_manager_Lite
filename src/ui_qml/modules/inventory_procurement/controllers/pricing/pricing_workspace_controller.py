from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryPricingWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .pricing_activity_handler import load_detail_activity
from .pricing_domain_event_binder import bind_domain_events
from .pricing_export_handler import (
    export_procurement_overview_csv,
    export_procurement_overview_excel,
    export_stock_status_csv,
    export_stock_status_excel,
)
from .pricing_filter_handler import (
    clear_filters,
    set_limit_filter,
    set_site_filter,
    set_storeroom_filter,
    set_supplier_filter,
)
from .pricing_refresh_service import refresh as _do_refresh
from .pricing_selection_handler import (
    select_stock_signal,
    select_supplier_pricing,
    set_active_view,
    set_stock_signal_page,
    set_stock_signal_page_size,
    set_supplier_pricing_page,
    set_supplier_pricing_page_size,
)
from .pricing_state import default_collection, default_overview
from .pricing_state_setters import (
    set_can_export,
    set_context_label,
    set_detail_activity_items,
    set_limit_options,
    set_overview,
    set_selected_limit_filter,
    set_selected_site_filter,
    set_selected_storeroom_filter,
    set_selected_supplier_filter,
    set_site_options,
    set_stock_signals,
    set_storeroom_options,
    set_supplier_options,
    set_supplier_pricing,
)
from .pricing_table_models import create_pricing_table_models

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementPricingWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    contextLabelChanged = Signal()
    siteOptionsChanged = Signal()
    storeroomOptionsChanged = Signal()
    supplierOptionsChanged = Signal()
    limitOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedStoreroomFilterChanged = Signal()
    selectedSupplierFilterChanged = Signal()
    selectedLimitFilterChanged = Signal()
    stockSignalsChanged = Signal()
    supplierPricingChanged = Signal()
    canExportChanged = Signal()
    stockSignalPageChanged = Signal()
    stockSignalPageSizeChanged = Signal()
    supplierPricingPageChanged = Signal()
    supplierPricingPageSizeChanged = Signal()
    activeViewChanged = Signal()
    selectedStockSignalIdChanged = Signal()
    selectedSupplierPricingIdChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        pricing_workspace_presenter: InventoryPricingWorkspacePresenter | None = None,
        platform_audit: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = (
            workspace_presenter
            or InventoryProcurementWorkspacePresenter("inventory_procurement.pricing")
        )
        self._pricing_workspace_presenter = (
            pricing_workspace_presenter or InventoryPricingWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
        self._context_label = ""
        self._site_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._supplier_options: list[dict[str, str]] = []
        self._limit_options: list[dict[str, str]] = []
        self._selected_site_filter = "all"
        self._selected_storeroom_filter = "all"
        self._selected_supplier_filter = "all"
        self._selected_limit_filter = "200"
        self._stock_signals_table_model, self._supplier_pricing_table_model = (
            create_pricing_table_models(self)
        )
        self._stock_signals: dict[str, object] = default_collection()
        self._supplier_pricing: dict[str, object] = default_collection()
        self._can_export = False
        self._stock_signal_page = 1
        self._stock_signal_page_size = 25
        self._supplier_pricing_page = 1
        self._supplier_pricing_page_size = 25
        self._active_view = "stock"
        self._selected_stock_signal_id = ""
        self._selected_supplier_pricing_id = ""
        self._platform_audit = platform_audit
        self._detail_activity_items: list[dict[str, object]] = []
        bind_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property(str, notify=contextLabelChanged)
    def contextLabel(self) -> str:
        return self._context_label

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, str]]:
        return self._site_options

    @Property("QVariantList", notify=storeroomOptionsChanged)
    def storeroomOptions(self) -> list[dict[str, str]]:
        return self._storeroom_options

    @Property("QVariantList", notify=supplierOptionsChanged)
    def supplierOptions(self) -> list[dict[str, str]]:
        return self._supplier_options

    @Property("QVariantList", notify=limitOptionsChanged)
    def limitOptions(self) -> list[dict[str, str]]:
        return self._limit_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedStoreroomFilterChanged)
    def selectedStoreroomFilter(self) -> str:
        return self._selected_storeroom_filter

    @Property(str, notify=selectedSupplierFilterChanged)
    def selectedSupplierFilter(self) -> str:
        return self._selected_supplier_filter

    @Property(str, notify=selectedLimitFilterChanged)
    def selectedLimitFilter(self) -> str:
        return self._selected_limit_filter

    @Property("QVariantMap", notify=stockSignalsChanged)
    def stockSignals(self) -> dict[str, object]:
        return self._stock_signals

    @Property(QObject, constant=True)
    def stockSignalsTableModel(self) -> DynamicTableModel:
        return self._stock_signals_table_model

    @Property("QVariantMap", notify=supplierPricingChanged)
    def supplierPricing(self) -> dict[str, object]:
        return self._supplier_pricing

    @Property(QObject, constant=True)
    def supplierPricingTableModel(self) -> DynamicTableModel:
        return self._supplier_pricing_table_model

    @Property(bool, notify=canExportChanged)
    def canExport(self) -> bool:
        return self._can_export

    @Property(int, notify=stockSignalPageChanged)
    def stockSignalPage(self) -> int:
        return self._stock_signal_page

    @Property(int, notify=stockSignalPageSizeChanged)
    def stockSignalPageSize(self) -> int:
        return self._stock_signal_page_size

    @Property(int, notify=stockSignalsChanged)
    def stockSignalTotalCount(self) -> int:
        return len(self._stock_signals.get("items", []))

    @Property(int, notify=supplierPricingPageChanged)
    def supplierPricingPage(self) -> int:
        return self._supplier_pricing_page

    @Property(int, notify=supplierPricingPageSizeChanged)
    def supplierPricingPageSize(self) -> int:
        return self._supplier_pricing_page_size

    @Property(int, notify=supplierPricingChanged)
    def supplierPricingTotalCount(self) -> int:
        return len(self._supplier_pricing.get("items", []))

    @Property(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @Property(str, notify=selectedStockSignalIdChanged)
    def selectedStockSignalId(self) -> str:
        return self._selected_stock_signal_id

    @Property(str, notify=selectedSupplierPricingIdChanged)
    def selectedSupplierPricingId(self) -> str:
        return self._selected_supplier_pricing_id

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        _do_refresh(self)

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
    def setLimitFilter(self, limit_value: str) -> None:
        set_limit_filter(self, limit_value)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        set_active_view(self, view)

    @Slot(str)
    def selectStockSignal(self, row_id: str) -> None:
        select_stock_signal(self, row_id)

    @Slot(str)
    def selectSupplierPricing(self, row_id: str) -> None:
        select_supplier_pricing(self, row_id)

    @Slot(int)
    def setStockSignalPage(self, page: int) -> None:
        set_stock_signal_page(self, page)

    @Slot(int)
    def setStockSignalPageSize(self, size: int) -> None:
        set_stock_signal_page_size(self, size)

    @Slot(int)
    def setSupplierPricingPage(self, page: int) -> None:
        set_supplier_pricing_page(self, page)

    @Slot(int)
    def setSupplierPricingPageSize(self, size: int) -> None:
        set_supplier_pricing_page_size(self, size)

    @Slot(str, result="QVariantMap")
    def exportStockStatusCsv(self, output_path: str) -> dict[str, object]:
        return export_stock_status_csv(self, output_path)

    @Slot(str, result="QVariantMap")
    def exportStockStatusExcel(self, output_path: str) -> dict[str, object]:
        return export_stock_status_excel(self, output_path)

    @Slot(str, result="QVariantMap")
    def exportProcurementOverviewCsv(self, output_path: str) -> dict[str, object]:
        return export_procurement_overview_csv(self, output_path)

    @Slot(str, result="QVariantMap")
    def exportProcurementOverviewExcel(self, output_path: str) -> dict[str, object]:
        return export_procurement_overview_excel(self, output_path)

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        load_detail_activity(self, entity_id, entity_type)

    # ── Private state setters (called by handlers and refresh service) ─

    def _set_overview(self, v: dict[str, object]) -> None:
        set_overview(self, v)

    def _set_context_label(self, v: str) -> None:
        set_context_label(self, v)

    def _set_site_options(self, v: list[dict[str, str]]) -> None:
        set_site_options(self, v)

    def _set_storeroom_options(self, v: list[dict[str, str]]) -> None:
        set_storeroom_options(self, v)

    def _set_supplier_options(self, v: list[dict[str, str]]) -> None:
        set_supplier_options(self, v)

    def _set_limit_options(self, v: list[dict[str, str]]) -> None:
        set_limit_options(self, v)

    def _set_selected_site_filter(self, v: str) -> None:
        set_selected_site_filter(self, v)

    def _set_selected_storeroom_filter(self, v: str) -> None:
        set_selected_storeroom_filter(self, v)

    def _set_selected_supplier_filter(self, v: str) -> None:
        set_selected_supplier_filter(self, v)

    def _set_selected_limit_filter(self, v: str) -> None:
        set_selected_limit_filter(self, v)

    def _set_stock_signals(self, v: dict[str, object]) -> None:
        set_stock_signals(self, v)

    def _set_supplier_pricing(self, v: dict[str, object]) -> None:
        set_supplier_pricing(self, v)

    def _set_can_export(self, v: bool) -> None:
        set_can_export(self, v)

    def _set_detail_activity_items(self, v: list[dict[str, object]]) -> None:
        set_detail_activity_items(self, v)


__all__ = ["InventoryProcurementPricingWorkspaceController"]
