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
    ProcurementService,
    PurchasingService,
)
from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseOrderStatus, PurchaseRequisitionStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.procurement.procurement_dialogs import (
    PurchaseOrderEditDialog,
    PurchaseOrderLineDialog,
)
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.procurement_support import (
    build_item_lookup,
    build_requisition_lookup,
    build_storeroom_lookup,
    format_date,
    format_item_label,
    format_quantity,
    format_requisition_label,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.inventory_procurement.shared.reference_support import (
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


class PurchaseOrdersTab(QWidget):
    def __init__(
        self,
        *,
        purchasing_service: PurchasingService,
        procurement_service: ProcurementService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchasing_service = purchasing_service
        self._procurement_service = procurement_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[PurchaseOrder] = []
        self._selected_lines = []
        self._site_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._item_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._requisition_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_purchase_orders()
        domain_events.inventory_purchase_orders_changed.connect(self._on_inventory_changed)
        domain_events.inventory_requisitions_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.sites_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.approvals_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryPurchaseOrdersHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryPurchaseOrdersHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("EXTERNAL PROCUREMENT")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Purchase Orders")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Commit approved demand to suppliers with explicit site scope, receiving destinations, and approval-backed control."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 purchase orders")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.awaiting_badge = QLabel("0 awaiting approval")
        self.awaiting_badge.setStyleSheet(dashboard_meta_chip_style())
        self.receiving_badge = QLabel("0 open for receiving")
        self.receiving_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: None")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.count_badge,
            self.awaiting_badge,
            self.receiving_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryPurchaseOrderControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryPurchaseOrderControlSurface {{
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
        self.search_edit.setPlaceholderText("Search PO number, supplier reference, supplier, or currency")
        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses", None)
        for status in (
            "DRAFT",
            "SUBMITTED",
            "UNDER_REVIEW",
            "APPROVED",
            "SENT",
            "PARTIALLY_RECEIVED",
            "FULLY_RECEIVED",
            "REJECTED",
            "CANCELLED",
            "CLOSED",
        ):
            self.status_filter.addItem(humanize_status(status), status)
        self.site_filter = QComboBox()
        self.site_filter.addItem("All sites", None)
        self.supplier_filter = QComboBox()
        self.supplier_filter.addItem("All suppliers", None)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.site_filter)
        filter_row.addWidget(self.supplier_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Purchase Order")
        self.btn_edit = QPushButton("Edit")
        self.btn_add_line = QPushButton("Add Line")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_submit = QPushButton("Submit")
        self.btn_send = QPushButton("Send")
        self.btn_close = QPushButton("Close")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (
            self.btn_new,
            self.btn_edit,
            self.btn_add_line,
            self.btn_cancel,
            self.btn_submit,
            self.btn_send,
            self.btn_close,
            self.btn_refresh,
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_add_line.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_cancel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_submit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_send.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_close.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_edit)
        action_row.addWidget(self.btn_add_line)
        action_row.addWidget(self.btn_cancel)
        action_row.addWidget(self.btn_submit)
        action_row.addWidget(self.btn_send)
        action_row.addWidget(self.btn_close)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["PO Number", "Status", "Site", "Supplier", "Currency", "Expected", "Source Req."]
        )
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(3, QHeaderView.Stretch)
        table_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryPurchaseOrderDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryPurchaseOrderDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Purchase Order Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a purchase order")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(CFG.SPACING_MD)
        detail_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.detail_site = QLabel("-")
        self.detail_supplier = QLabel("-")
        self.detail_currency = QLabel("-")
        self.detail_delivery = QLabel("-")
        self.detail_source = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Site"), 0, 0)
        detail_grid.addWidget(self.detail_site, 0, 1)
        detail_grid.addWidget(QLabel("Supplier"), 1, 0)
        detail_grid.addWidget(self.detail_supplier, 1, 1)
        detail_grid.addWidget(QLabel("Currency"), 2, 0)
        detail_grid.addWidget(self.detail_currency, 2, 1)
        detail_grid.addWidget(QLabel("Delivery"), 3, 0)
        detail_grid.addWidget(self.detail_delivery, 3, 1)
        detail_grid.addWidget(QLabel("Source Requisition"), 4, 0)
        detail_grid.addWidget(self.detail_source, 4, 1)
        detail_grid.addWidget(QLabel("Notes"), 5, 0)
        detail_grid.addWidget(self.detail_notes, 5, 1)
        detail_layout.addLayout(detail_grid)

        lines_title = QLabel("PO Lines")
        lines_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(lines_title)
        self.lines_table = QTableWidget(0, 7)
        self.lines_table.setHorizontalHeaderLabels(
            ["Line", "Item", "Storeroom", "Ordered", "Received", "Rejected", "Status"]
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
        lines_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        detail_layout.addWidget(self.lines_table, 1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.search_edit.textChanged.connect(lambda _text: self.reload_purchase_orders())
        self.status_filter.currentIndexChanged.connect(lambda _index: self.reload_purchase_orders())
        self.site_filter.currentIndexChanged.connect(lambda _index: self.reload_purchase_orders())
        self.supplier_filter.currentIndexChanged.connect(lambda _index: self.reload_purchase_orders())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.reload_purchase_orders))
        self.btn_new.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.create_purchase_order))
        self.btn_edit.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.edit_purchase_order))
        self.btn_add_line.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.add_line))
        self.btn_cancel.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.cancel_purchase_order))
        self.btn_submit.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.submit_purchase_order))
        self.btn_send.clicked.connect(make_guarded_slot(self, title="Purchase Orders", callback=self.send_purchase_order))
        self.btn_close.clicked.connect(
            make_guarded_slot(self, title="Purchase Orders", callback=self.close_purchase_order)
        )
        for button in (
            self.btn_new,
            self.btn_edit,
            self.btn_add_line,
            self.btn_cancel,
            self.btn_submit,
            self.btn_send,
            self.btn_close,
        ):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_purchase_orders(self) -> None:
        selected_id = self._selected_purchase_order_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            items = self._item_service.list_items(active_only=None)
            parties = self._reference_service.list_business_parties(active_only=None)
            requisitions = self._procurement_service.list_requisitions()
            self._site_lookup = build_site_lookup(sites)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._item_lookup = build_item_lookup(items)
            self._party_lookup = build_party_lookup(parties)
            self._requisition_lookup = build_requisition_lookup(requisitions)
            self._reload_site_filter()
            self._reload_supplier_filter()
            rows = self._purchasing_service.list_purchase_orders(
                status=self._selected_status_filter(),
                site_id=self._selected_site_filter(),
                supplier_party_id=self._selected_supplier_filter(),
            )
            self._rows = self._apply_search_filter(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            self._rows = []
            self._selected_lines = []
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to load purchase orders: {exc}")
            self._rows = []
            self._selected_lines = []
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def create_purchase_order(self) -> None:
        if not self._can_manage:
            return
        dialog = PurchaseOrderEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
            ),
            requisition_options=self._requisition_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            purchase_order = self._purchasing_service.create_purchase_order(
                site_id=dialog.site_id,
                supplier_party_id=dialog.supplier_party_id,
                currency_code=dialog.currency_code or None,
                source_requisition_id=dialog.source_requisition_id,
                expected_delivery_date=dialog.expected_delivery_date,
                supplier_reference=dialog.supplier_reference,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to create purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def edit_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        dialog = PurchaseOrderEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
            ),
            requisition_options=self._requisition_options(),
            purchase_order=purchase_order,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._purchasing_service.update_purchase_order(
                purchase_order.id,
                site_id=dialog.site_id,
                supplier_party_id=dialog.supplier_party_id,
                currency_code=dialog.currency_code or None,
                source_requisition_id=dialog.source_requisition_id,
                expected_delivery_date=dialog.expected_delivery_date,
                supplier_reference=dialog.supplier_reference,
                notes=dialog.notes,
                expected_version=purchase_order.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to update purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def add_line(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        dialog = PurchaseOrderLineDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._storeroom_options_for_site(purchase_order.site_id),
            requisition_line_options=self._requisition_line_options(purchase_order.source_requisition_id),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._purchasing_service.add_purchase_order_line(
                purchase_order.id,
                stock_item_id=dialog.stock_item_id,
                destination_storeroom_id=dialog.destination_storeroom_id,
                quantity_ordered=dialog.quantity_ordered,
                unit_price=dialog.unit_price,
                expected_delivery_date=dialog.expected_delivery_date,
                description=dialog.description,
                source_requisition_line_id=dialog.source_requisition_line_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to add purchase-order line: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def submit_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Submit Purchase Order",
            f"Submit {purchase_order.po_number} for approval?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.submit_purchase_order(purchase_order.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to submit purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def cancel_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Cancel Purchase Order",
            f"Cancel draft purchase order {purchase_order.po_number}?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.cancel_purchase_order(
                purchase_order.id,
                expected_version=purchase_order.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to cancel purchase order: {exc}")
            return
        self.reload_purchase_orders()

    def send_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Send Purchase Order",
            f"Mark purchase order {purchase_order.po_number} as sent to the supplier?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.send_purchase_order(purchase_order.id)
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to send purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def close_purchase_order(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Close Purchase Order",
            f"Close purchase order {purchase_order.po_number}? This is only allowed once all line quantities are fully processed.",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._purchasing_service.close_purchase_order(purchase_order.id)
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Purchase Orders", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_purchase_orders()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Purchase Orders", f"Failed to close purchase order: {exc}")
            return
        self.reload_purchase_orders()
        self._select_purchase_order(purchase_order.id)

    def _apply_search_filter(self, rows: list[PurchaseOrder]) -> list[PurchaseOrder]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[PurchaseOrder] = []
        for row in rows:
            haystacks = (
                row.po_number,
                row.currency_code,
                row.supplier_reference,
                row.status.value,
                format_party_label(row.supplier_party_id, self._party_lookup),
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, purchase_order in enumerate(self._rows):
            values = (
                purchase_order.po_number,
                humanize_status(purchase_order.status.value),
                format_site_label(purchase_order.site_id, self._site_lookup),
                format_party_label(purchase_order.supplier_party_id, self._party_lookup),
                purchase_order.currency_code or "-",
                format_date(purchase_order.expected_delivery_date),
                format_requisition_label(purchase_order.source_requisition_id, self._requisition_lookup),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, purchase_order.id)
                self.table.setItem(row_index, column, item)
            if purchase_order.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
            self._on_selection_changed()
        elif self._rows:
            self.table.selectRow(0)
            self._on_selection_changed()
        else:
            self._selected_lines = []
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None:
            self._selected_lines = []
            self._update_detail(None)
            self._sync_actions()
            return
        try:
            self._selected_lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
        except Exception:
            self._selected_lines = []
        self._update_detail(purchase_order)
        self._sync_actions()

    def _update_detail(self, purchase_order: PurchaseOrder | None) -> None:
        if purchase_order is None:
            self.detail_name.setText("Select a purchase order")
            self.detail_status.setText("-")
            self.detail_site.setText("-")
            self.detail_supplier.setText("-")
            self.detail_currency.setText("-")
            self.detail_delivery.setText("-")
            self.detail_source.setText("-")
            self.detail_notes.setText("-")
            self.lines_table.setRowCount(0)
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(purchase_order.po_number)
        self.detail_status.setText(
            f"{humanize_status(purchase_order.status.value)} | Supplier Ref: {purchase_order.supplier_reference or '-'}"
        )
        self.detail_site.setText(format_site_label(purchase_order.site_id, self._site_lookup))
        self.detail_supplier.setText(format_party_label(purchase_order.supplier_party_id, self._party_lookup))
        self.detail_currency.setText(purchase_order.currency_code or "-")
        delivery_text = f"Expected {format_date(purchase_order.expected_delivery_date)}"
        if purchase_order.order_date:
            delivery_text = f"Ordered {format_date(purchase_order.order_date)} | {delivery_text}"
        self.detail_delivery.setText(delivery_text)
        self.detail_source.setText(format_requisition_label(purchase_order.source_requisition_id, self._requisition_lookup))
        self.detail_notes.setText(purchase_order.notes or "-")
        self.selection_badge.setText(f"Selection: {purchase_order.po_number}")
        self.lines_table.setRowCount(len(self._selected_lines))
        for row_index, line in enumerate(self._selected_lines):
            values = (
                line.line_number,
                format_item_label(line.stock_item_id, self._item_lookup),
                format_storeroom_label(line.destination_storeroom_id, self._storeroom_lookup),
                format_quantity(line.quantity_ordered),
                format_quantity(line.quantity_received),
                format_quantity(line.quantity_rejected),
                humanize_status(line.status.value),
            )
            for column, value in enumerate(values):
                self.lines_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _update_badges(self) -> None:
        awaiting = sum(
            1
            for row in self._rows
            if row.status in {PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.UNDER_REVIEW}
        )
        open_receiving = sum(
            1
            for row in self._rows
            if row.status in {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.SENT, PurchaseOrderStatus.PARTIALLY_RECEIVED}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} purchase orders")
        self.awaiting_badge.setText(f"{awaiting} awaiting approval")
        self.receiving_badge.setText(f"{open_receiving} open for receiving")

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

    def _reload_supplier_filter(self) -> None:
        current = self._selected_supplier_filter()
        self.supplier_filter.blockSignals(True)
        self.supplier_filter.clear()
        self.supplier_filter.addItem("All suppliers", None)
        for label, row_id in build_option_rows(
            {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
        ):
            self.supplier_filter.addItem(label, row_id)
        _set_combo_to_data(self.supplier_filter, current or "")
        self.supplier_filter.blockSignals(False)

    def _requisition_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for requisition_id, requisition in self._requisition_lookup.items():
            if requisition.status not in {
                PurchaseRequisitionStatus.APPROVED,
                PurchaseRequisitionStatus.PARTIALLY_SOURCED,
            }:
                continue
            label = (
                f"{requisition.requisition_number} | "
                f"{format_site_label(requisition.requesting_site_id, self._site_lookup)} | "
                f"{humanize_status(requisition.status.value)}"
            )
            options.append((label, requisition_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _requisition_line_options(self, requisition_id: str | None) -> list[tuple[str, str]]:
        if not requisition_id:
            return []
        try:
            lines = self._procurement_service.list_requisition_lines(requisition_id)
        except Exception:
            return []
        options: list[tuple[str, str]] = []
        for line in lines:
            remaining = max(0.0, float(line.quantity_requested or 0.0) - float(line.quantity_sourced or 0.0))
            if remaining <= 0:
                continue
            label = (
                f"L{line.line_number} | {format_item_label(line.stock_item_id, self._item_lookup)} | "
                f"Remaining {format_quantity(remaining)}"
            )
            options.append((label, line.id))
        return sorted(options, key=lambda row: row[0].lower())

    def _storeroom_options_for_site(self, site_id: str) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for storeroom_id, storeroom in self._storeroom_lookup.items():
            if storeroom.site_id != site_id:
                continue
            options.append((format_storeroom_label(storeroom_id, self._storeroom_lookup), storeroom_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _active_item_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item_id, item in self._item_lookup.items():
            if not item.is_active or not item.is_purchase_allowed:
                continue
            options.append((format_item_label(item_id, self._item_lookup), item_id))
        return sorted(options, key=lambda row: row[0].lower())

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
                try:
                    self._selected_lines = self._purchasing_service.list_purchase_order_lines(row.id)
                except Exception:
                    self._selected_lines = []
                self._update_detail(row)
                self._sync_actions()
                return

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    def _selected_status_filter(self) -> str | None:
        value = self.status_filter.currentData()
        return str(value).strip() if value else None

    def _selected_site_filter(self) -> str | None:
        value = self.site_filter.currentData()
        return str(value).strip() if value else None

    def _selected_supplier_filter(self) -> str | None:
        value = self.supplier_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        purchase_order = self._selected_purchase_order()
        is_draft = bool(purchase_order is not None and purchase_order.status == PurchaseOrderStatus.DRAFT)
        can_send = bool(purchase_order is not None and purchase_order.status == PurchaseOrderStatus.APPROVED)
        can_close = bool(
            purchase_order is not None
            and purchase_order.status
            in {
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
                PurchaseOrderStatus.FULLY_RECEIVED,
            }
            and _is_fully_processed(self._selected_lines)
        )
        self.btn_edit.setEnabled(self._can_manage and is_draft)
        self.btn_add_line.setEnabled(self._can_manage and is_draft)
        self.btn_cancel.setEnabled(self._can_manage and is_draft)
        self.btn_submit.setEnabled(self._can_manage and is_draft and bool(self._selected_lines))
        self.btn_send.setEnabled(self._can_manage and can_send)
        self.btn_close.setEnabled(self._can_manage and can_close)

    def _context_label(self) -> str:
        site_label = "All sites"
        site_id = self._selected_site_filter()
        if site_id:
            site_label = format_site_label(site_id, self._site_lookup)
        status_label = humanize_status(self._selected_status_filter() or "all")
        return f"{site_label} | {status_label}"

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_purchase_orders()


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


def _is_fully_processed(lines) -> bool:
    return bool(lines) and all(
        max(0.0, float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0)) <= 0
        for line in lines
    )


__all__ = ["PurchaseOrdersTab"]
