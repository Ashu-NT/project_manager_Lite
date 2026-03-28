from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.procurement_support import humanize_status
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PurchaseOrdersSurfaceMixin:
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
