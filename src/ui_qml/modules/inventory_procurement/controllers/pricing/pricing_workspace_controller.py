from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    serialize_audit_entries_for_activity,
    serialize_catalog_overview_view_model,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryPricingWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)

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
    # pagination
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
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.pricing"
        )
        self._pricing_workspace_presenter = (
            pricing_workspace_presenter or InventoryPricingWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._context_label = ""
        self._site_options: list[dict[str, str]] = []
        self._storeroom_options: list[dict[str, str]] = []
        self._supplier_options: list[dict[str, str]] = []
        self._limit_options: list[dict[str, str]] = []
        self._selected_site_filter = "all"
        self._selected_storeroom_filter = "all"
        self._selected_supplier_filter = "all"
        self._selected_limit_filter = "200"
        self._stock_signals: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._supplier_pricing: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._can_export = False
        # pagination + view state
        self._stock_signal_page = 1
        self._stock_signal_page_size = 25
        self._supplier_pricing_page = 1
        self._supplier_pricing_page_size = 25
        self._active_view = "stock"
        self._selected_stock_signal_id = ""
        self._selected_supplier_pricing_id = ""
        self._platform_audit = platform_audit
        self._detail_activity_items: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

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

    @Property("QVariantMap", notify=supplierPricingChanged)
    def supplierPricing(self) -> dict[str, object]:
        return self._supplier_pricing

    @Property(bool, notify=canExportChanged)
    def canExport(self) -> bool:
        return self._can_export

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
            workspace_state = self._pricing_workspace_presenter.build_workspace_state(
                site_filter=self._selected_site_filter,
                storeroom_filter=self._selected_storeroom_filter,
                supplier_filter=self._selected_supplier_filter,
                limit_filter=self._selected_limit_filter,
            )
            self._set_overview(
                serialize_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_context_label(workspace_state.context_label)
            self._set_site_options(serialize_selector_options(workspace_state.site_options))
            self._set_storeroom_options(
                serialize_selector_options(workspace_state.storeroom_options)
            )
            self._set_supplier_options(
                serialize_selector_options(workspace_state.supplier_options)
            )
            self._set_limit_options(serialize_selector_options(workspace_state.limit_options))
            self._set_selected_site_filter(workspace_state.selected_site_filter)
            self._set_selected_storeroom_filter(
                workspace_state.selected_storeroom_filter
            )
            self._set_selected_supplier_filter(
                workspace_state.selected_supplier_filter
            )
            self._set_selected_limit_filter(workspace_state.selected_limit_filter)
            self._set_stock_signals(
                {
                    "title": "Stock Status Signals",
                    "subtitle": (
                        "Filtered stock rows that matter for replenishment, reserved "
                        "demand, and inbound supply planning."
                    ),
                    "emptyState": workspace_state.stock_empty_state,
                    "items": serialize_record_view_models(workspace_state.stock_rows),
                }
            )
            self._set_supplier_pricing(
                {
                    "title": "Supplier Price Lines",
                    "subtitle": (
                        "Recent purchase-order lines with unit prices, outstanding "
                        "quantities, and expected delivery context."
                    ),
                    "emptyState": workspace_state.supplier_price_empty_state,
                    "items": serialize_record_view_models(
                        workspace_state.supplier_price_rows
                    ),
                }
            )
            self._set_can_export(workspace_state.can_export)
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

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
    def setLimitFilter(self, limit_value: str) -> None:
        normalized = (limit_value or "").strip() or "200"
        if normalized == self._selected_limit_filter:
            return
        self._set_selected_limit_filter(normalized)
        self.refresh()

    @Slot(str, result="QVariantMap")
    def exportStockStatusCsv(self, output_path: str) -> dict[str, object]:
        return self._run_export_action(
            lambda: self._pricing_workspace_presenter.export_stock_status_csv(
                output_path,
                site_filter=self._selected_site_filter,
                storeroom_filter=self._selected_storeroom_filter,
            ),
            success_prefix="Stock CSV exported to",
        )

    @Slot(str, result="QVariantMap")
    def exportStockStatusExcel(self, output_path: str) -> dict[str, object]:
        return self._run_export_action(
            lambda: self._pricing_workspace_presenter.export_stock_status_excel(
                output_path,
                site_filter=self._selected_site_filter,
                storeroom_filter=self._selected_storeroom_filter,
            ),
            success_prefix="Stock Excel exported to",
        )

    @Slot(str, result="QVariantMap")
    def exportProcurementOverviewCsv(self, output_path: str) -> dict[str, object]:
        return self._run_export_action(
            lambda: self._pricing_workspace_presenter.export_procurement_overview_csv(
                output_path,
                site_filter=self._selected_site_filter,
                storeroom_filter=self._selected_storeroom_filter,
                supplier_filter=self._selected_supplier_filter,
                limit_filter=self._selected_limit_filter,
            ),
            success_prefix="Procurement CSV exported to",
        )

    @Slot(str, result="QVariantMap")
    def exportProcurementOverviewExcel(self, output_path: str) -> dict[str, object]:
        return self._run_export_action(
            lambda: self._pricing_workspace_presenter.export_procurement_overview_excel(
                output_path,
                site_filter=self._selected_site_filter,
                storeroom_filter=self._selected_storeroom_filter,
                supplier_filter=self._selected_supplier_filter,
                limit_filter=self._selected_limit_filter,
            ),
            success_prefix="Procurement Excel exported to",
        )

    def _run_export_action(self, operation, *, success_prefix: str) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            output_path = operation()
        except Exception as exc:
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            payload = {"ok": False, "message": str(exc)}
        else:
            message = f"{success_prefix} {output_path}"
            self._set_feedback_message(message)
            payload = {"ok": True, "message": message, "path": output_path}
        finally:
            self._set_is_busy(False)
        return payload

    # ── pagination + view ────────────────────────────────────────────

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

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        normalized = view if view in ("stock", "supplier") else "stock"
        if normalized == self._active_view:
            return
        self._active_view = normalized
        self.activeViewChanged.emit()

    @Slot(str)
    def selectStockSignal(self, row_id: str) -> None:
        normalized = (row_id or "").strip()
        if normalized == self._selected_stock_signal_id:
            return
        self._selected_stock_signal_id = normalized
        self.selectedStockSignalIdChanged.emit()

    @Slot(str)
    def selectSupplierPricing(self, row_id: str) -> None:
        normalized = (row_id or "").strip()
        if normalized == self._selected_supplier_pricing_id:
            return
        self._selected_supplier_pricing_id = normalized
        self.selectedSupplierPricingIdChanged.emit()

    @Slot(int)
    def setStockSignalPage(self, page: int) -> None:
        self._stock_signal_page = max(1, int(page))
        self.stockSignalPageChanged.emit()

    @Slot(int)
    def setStockSignalPageSize(self, size: int) -> None:
        self._stock_signal_page_size = max(10, min(200, int(size)))
        self._stock_signal_page = 1
        self.stockSignalPageSizeChanged.emit()
        self.stockSignalPageChanged.emit()

    @Slot(int)
    def setSupplierPricingPage(self, page: int) -> None:
        self._supplier_pricing_page = max(1, int(page))
        self.supplierPricingPageChanged.emit()

    @Slot(int)
    def setSupplierPricingPageSize(self, size: int) -> None:
        self._supplier_pricing_page_size = max(10, min(200, int(size)))
        self._supplier_pricing_page = 1
        self.supplierPricingPageSizeChanged.emit()
        self.supplierPricingPageChanged.emit()

    @Slot()
    def clearFilters(self) -> None:
        self._set_selected_site_filter("all")
        self._set_selected_storeroom_filter("all")
        self._set_selected_supplier_filter("all")
        self.refresh()

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
        self._subscribe_domain_change("party", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_context_label(self, context_label: str) -> None:
        if context_label == self._context_label:
            return
        self._context_label = context_label
        self.contextLabelChanged.emit()

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

    def _set_limit_options(self, limit_options: list[dict[str, str]]) -> None:
        if limit_options == self._limit_options:
            return
        self._limit_options = limit_options
        self.limitOptionsChanged.emit()

    def _set_selected_site_filter(self, selected_site_filter: str) -> None:
        if selected_site_filter == self._selected_site_filter:
            return
        self._selected_site_filter = selected_site_filter
        self.selectedSiteFilterChanged.emit()

    def _set_selected_storeroom_filter(self, selected_storeroom_filter: str) -> None:
        if selected_storeroom_filter == self._selected_storeroom_filter:
            return
        self._selected_storeroom_filter = selected_storeroom_filter
        self.selectedStoreroomFilterChanged.emit()

    def _set_selected_supplier_filter(self, selected_supplier_filter: str) -> None:
        if selected_supplier_filter == self._selected_supplier_filter:
            return
        self._selected_supplier_filter = selected_supplier_filter
        self.selectedSupplierFilterChanged.emit()

    def _set_selected_limit_filter(self, selected_limit_filter: str) -> None:
        if selected_limit_filter == self._selected_limit_filter:
            return
        self._selected_limit_filter = selected_limit_filter
        self.selectedLimitFilterChanged.emit()

    def _set_stock_signals(self, stock_signals: dict[str, object]) -> None:
        if stock_signals == self._stock_signals:
            return
        self._stock_signals = stock_signals
        self.stockSignalsChanged.emit()

    def _set_supplier_pricing(self, supplier_pricing: dict[str, object]) -> None:
        if supplier_pricing == self._supplier_pricing:
            return
        self._supplier_pricing = supplier_pricing
        self.supplierPricingChanged.emit()

    def _set_can_export(self, can_export: bool) -> None:
        normalized = bool(can_export)
        if normalized == self._can_export:
            return
        self._can_export = normalized
        self.canExportChanged.emit()


__all__ = ["InventoryProcurementPricingWorkspaceController"]
