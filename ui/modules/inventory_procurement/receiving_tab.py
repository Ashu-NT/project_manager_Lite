from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.platform import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryService,
    ItemMasterService,
    PurchasingService,
)
from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseOrderStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.procurement_dialogs import ReceiptPostDialog
from ui.modules.inventory_procurement.procurement_support import (
    build_item_lookup,
    build_storeroom_lookup,
    format_date,
    format_datetime,
    format_item_label,
    format_quantity,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.inventory_procurement.reference_support import (
    build_option_rows,
    build_party_lookup,
    build_site_lookup,
    format_party_label,
    format_site_label,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class ReceivingTab(QWidget):
    def __init__(
        self,
        *,
        purchasing_service: PurchasingService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchasing_service = purchasing_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[PurchaseOrder] = []
        self._selected_lines = []
        self._selected_receipts = []
        self._site_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._item_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_receiving()
        domain_events.inventory_purchase_orders_changed.connect(self._on_inventory_changed)
        domain_events.inventory_receipts_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.sites_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryReceivingHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryReceivingHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("RECEIVING CONTROL")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Receiving")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Receive against approved purchase orders, separate accepted and rejected quantities, and keep receipt posting tied to the stock ledger."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 orders")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.outstanding_badge = QLabel("0 outstanding lines")
        self.outstanding_badge.setStyleSheet(dashboard_meta_chip_style())
        self.receipt_badge = QLabel("0 receipts")
        self.receipt_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: None")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.count_badge,
            self.outstanding_badge,
            self.receipt_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryReceivingControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryReceivingControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search PO number, supplier, or delivery status")
        self.mode_filter = QComboBox()
        self.mode_filter.addItem("Open for receiving", "OPEN")
        self.mode_filter.addItem("All purchase orders", "ALL")
        self.mode_filter.addItem("Fully received", "FULLY_RECEIVED")
        self.site_filter = QComboBox()
        self.site_filter.addItem("All sites", None)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.mode_filter)
        filter_row.addWidget(self.site_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_post_receipt = QPushButton("Post Receipt")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_post_receipt, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_post_receipt.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_post_receipt)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PO Number", "Supplier", "Site", "Status", "Expected", "Open Qty"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.Stretch)
        table_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryReceivingDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryReceivingDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Receiving Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a purchase order")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        self.detail_supplier = QLabel("-")
        self.detail_site = QLabel("-")
        self.detail_delivery = QLabel("-")
        detail_grid.addWidget(QLabel("Supplier"), 0, 0)
        detail_grid.addWidget(self.detail_supplier, 0, 1)
        detail_grid.addWidget(QLabel("Site"), 1, 0)
        detail_grid.addWidget(self.detail_site, 1, 1)
        detail_grid.addWidget(QLabel("Delivery"), 2, 0)
        detail_grid.addWidget(self.detail_delivery, 2, 1)
        detail_layout.addLayout(detail_grid)

        self.work_tabs = QTabWidget()
        self.work_tabs.setObjectName("inventoryReceivingWorkTabs")

        lines_page = QWidget()
        lines_layout = QVBoxLayout(lines_page)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        self.lines_table = QTableWidget(0, 6)
        self.lines_table.setHorizontalHeaderLabels(
            ["Line", "Item", "Storeroom", "Outstanding", "Received", "Status"]
        )
        style_table(self.lines_table)
        self.lines_table.setSelectionMode(QTableWidget.NoSelection)
        self.lines_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lines_header = self.lines_table.horizontalHeader()
        lines_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        lines_header.setSectionResizeMode(1, QHeaderView.Stretch)
        lines_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        lines_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        lines_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        lines_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        lines_layout.addWidget(self.lines_table)

        receipts_page = QWidget()
        receipts_layout = QVBoxLayout(receipts_page)
        receipts_layout.setContentsMargins(0, 0, 0, 0)
        self.receipts_table = QTableWidget(0, 5)
        self.receipts_table.setHorizontalHeaderLabels(
            ["Receipt", "Posted", "Delivery Ref", "Accepted", "Rejected"]
        )
        style_table(self.receipts_table)
        self.receipts_table.setSelectionMode(QTableWidget.NoSelection)
        self.receipts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        receipts_header = self.receipts_table.horizontalHeader()
        receipts_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        receipts_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        receipts_header.setSectionResizeMode(2, QHeaderView.Stretch)
        receipts_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        receipts_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        receipts_layout.addWidget(self.receipts_table)

        self.work_tabs.addTab(lines_page, "Outstanding Lines")
        self.work_tabs.addTab(receipts_page, "Receipt History")
        detail_layout.addWidget(self.work_tabs, 1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.search_edit.textChanged.connect(lambda _text: self.reload_receiving())
        self.mode_filter.currentIndexChanged.connect(lambda _index: self.reload_receiving())
        self.site_filter.currentIndexChanged.connect(lambda _index: self.reload_receiving())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Receiving", callback=self.reload_receiving))
        self.btn_post_receipt.clicked.connect(make_guarded_slot(self, title="Receiving", callback=self.post_receipt))
        apply_permission_hint(self.btn_post_receipt, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_receiving(self) -> None:
        selected_id = self._selected_purchase_order_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            items = self._item_service.list_items(active_only=None)
            parties = self._reference_service.list_business_parties(active_only=None)
            self._site_lookup = build_site_lookup(sites)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._item_lookup = build_item_lookup(items)
            self._party_lookup = build_party_lookup(parties)
            self._reload_site_filter()
            rows = self._purchasing_service.list_purchase_orders(site_id=self._selected_site_filter())
            self._rows = self._apply_filters(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Receiving", str(exc))
            self._rows = []
            self._selected_lines = []
            self._selected_receipts = []
        except Exception as exc:
            QMessageBox.critical(self, "Receiving", f"Failed to load receiving worklist: {exc}")
            self._rows = []
            self._selected_lines = []
            self._selected_receipts = []
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def post_receipt(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        line_rows = self._receipt_dialog_rows()
        if not line_rows:
            QMessageBox.information(self, "Receiving", "The selected purchase order has no outstanding lines.")
            return
        dialog = ReceiptPostDialog(
            purchase_order_number=purchase_order.po_number,
            line_rows=line_rows,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        if not dialog.receipt_lines:
            QMessageBox.warning(self, "Receiving", "Enter at least one accepted or rejected quantity.")
            return
        try:
            self._purchasing_service.post_receipt(
                purchase_order.id,
                receipt_lines=dialog.receipt_lines,
                supplier_delivery_reference=dialog.supplier_delivery_reference,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Receiving", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Receiving", f"Failed to post receipt: {exc}")
            return
        self.reload_receiving()
        self._select_purchase_order(purchase_order.id)

    def _apply_filters(self, rows: list[PurchaseOrder]) -> list[PurchaseOrder]:
        mode = str(self.mode_filter.currentData() or "OPEN")
        needle = self.search_text
        filtered: list[PurchaseOrder] = []
        for row in rows:
            if mode == "OPEN" and row.status not in {
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
            }:
                continue
            if mode == "FULLY_RECEIVED" and row.status != PurchaseOrderStatus.FULLY_RECEIVED:
                continue
            if needle:
                haystacks = (
                    row.po_number,
                    row.status.value,
                    format_party_label(row.supplier_party_id, self._party_lookup),
                )
                if not any(needle in str(value or "").lower() for value in haystacks):
                    continue
            filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, purchase_order in enumerate(self._rows):
            open_qty = format_quantity(self._open_quantity(purchase_order))
            values = (
                purchase_order.po_number,
                format_party_label(purchase_order.supplier_party_id, self._party_lookup),
                format_site_label(purchase_order.site_id, self._site_lookup),
                humanize_status(purchase_order.status.value),
                format_date(purchase_order.expected_delivery_date),
                open_qty,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, purchase_order.id)
                self.table.setItem(row_index, column, item)
            if purchase_order.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._selected_lines = []
            self._selected_receipts = []
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None:
            self._selected_lines = []
            self._selected_receipts = []
            self._update_detail(None)
            self._sync_actions()
            return
        try:
            self._selected_lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
            self._selected_receipts = self._purchasing_service.list_receipts(purchase_order_id=purchase_order.id)
        except Exception:
            self._selected_lines = []
            self._selected_receipts = []
        self._update_detail(purchase_order)
        self._sync_actions()

    def _update_detail(self, purchase_order: PurchaseOrder | None) -> None:
        if purchase_order is None:
            self.detail_name.setText("Select a purchase order")
            self.detail_status.setText("-")
            self.detail_supplier.setText("-")
            self.detail_site.setText("-")
            self.detail_delivery.setText("-")
            self.lines_table.setRowCount(0)
            self.receipts_table.setRowCount(0)
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(purchase_order.po_number)
        self.detail_status.setText(humanize_status(purchase_order.status.value))
        self.detail_supplier.setText(format_party_label(purchase_order.supplier_party_id, self._party_lookup))
        self.detail_site.setText(format_site_label(purchase_order.site_id, self._site_lookup))
        self.detail_delivery.setText(f"Expected {format_date(purchase_order.expected_delivery_date)}")
        self.selection_badge.setText(f"Selection: {purchase_order.po_number}")

        self.lines_table.setRowCount(len(self._selected_lines))
        for row_index, line in enumerate(self._selected_lines):
            outstanding = max(
                0.0,
                float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0),
            )
            values = (
                line.line_number,
                format_item_label(line.stock_item_id, self._item_lookup),
                format_storeroom_label(line.destination_storeroom_id, self._storeroom_lookup),
                format_quantity(outstanding),
                format_quantity(line.quantity_received),
                humanize_status(line.status.value),
            )
            for column, value in enumerate(values):
                self.lines_table.setItem(row_index, column, QTableWidgetItem(str(value)))

        self.receipts_table.setRowCount(len(self._selected_receipts))
        for row_index, receipt in enumerate(self._selected_receipts):
            accepted = 0.0
            rejected = 0.0
            try:
                receipt_lines = self._purchasing_service.list_receipt_lines(receipt.id)
                accepted = sum(float(line.quantity_accepted or 0.0) for line in receipt_lines)
                rejected = sum(float(line.quantity_rejected or 0.0) for line in receipt_lines)
            except Exception:
                pass
            values = (
                receipt.receipt_number,
                format_datetime(receipt.receipt_date),
                receipt.supplier_delivery_reference or "-",
                format_quantity(accepted),
                format_quantity(rejected),
            )
            for column, value in enumerate(values):
                self.receipts_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _update_badges(self) -> None:
        outstanding_lines = 0
        for purchase_order in self._rows:
            try:
                lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
            except Exception:
                continue
            outstanding_lines += sum(
                1
                for line in lines
                if (float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0)) > 0
            )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} orders")
        self.outstanding_badge.setText(f"{outstanding_lines} outstanding lines")
        self.receipt_badge.setText(f"{len(self._selected_receipts)} receipts")

    def _reload_site_filter(self) -> None:
        current = self._selected_site_filter()
        self.site_filter.blockSignals(True)
        self.site_filter.clear()
        self.site_filter.addItem("All sites", None)
        for label, row_id in build_option_rows(
            {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
        ):
            self.site_filter.addItem(label, row_id)
        _set_combo_to_data(self.site_filter, current or "")
        self.site_filter.blockSignals(False)

    def _receipt_dialog_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for line in self._selected_lines:
            outstanding = max(
                0.0,
                float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0),
            )
            if outstanding <= 0:
                continue
            rows.append(
                {
                    "purchase_order_line_id": line.id,
                    "item_label": format_item_label(line.stock_item_id, self._item_lookup),
                    "storeroom_label": format_storeroom_label(line.destination_storeroom_id, self._storeroom_lookup),
                    "outstanding_qty": outstanding,
                    "uom": line.uom,
                    "unit_price": line.unit_price,
                }
            )
        return rows

    def _open_quantity(self, purchase_order: PurchaseOrder) -> float:
        try:
            lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
        except Exception:
            return 0.0
        return sum(
            max(
                0.0,
                float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0),
            )
            for line in lines
        )

    def _selected_purchase_order_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_purchase_order(self) -> PurchaseOrder | None:
        selected_id = self._selected_purchase_order_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    def _select_purchase_order(self, purchase_order_id: str) -> None:
        for row_index, row in enumerate(self._rows):
            if row.id == purchase_order_id:
                self.table.selectRow(row_index)
                return

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    def _selected_site_filter(self) -> str | None:
        value = self.site_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        purchase_order = self._selected_purchase_order()
        can_receive = bool(
            purchase_order is not None
            and purchase_order.status in {
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
            }
            and self._receipt_dialog_rows()
        )
        self.btn_post_receipt.setEnabled(self._can_manage and can_receive)

    def _context_label(self) -> str:
        site_label = "All sites"
        site_id = self._selected_site_filter()
        if site_id:
            site_label = format_site_label(site_id, self._site_lookup)
        return f"{site_label} | {self.mode_filter.currentText()}"

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_receiving()


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


__all__ = ["ReceivingTab"]
