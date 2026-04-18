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
from src.ui.shared.widgets.guards import apply_permission_hint, make_guarded_slot
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class RequisitionsSurfaceMixin:
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryRequisitionsHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryRequisitionsHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("PROCUREMENT DEMAND")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Requisitions")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Capture internal supply demand by site and storeroom, then move it through shared approvals before sourcing begins."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 requisitions")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.awaiting_badge = QLabel("0 awaiting approval")
        self.awaiting_badge.setStyleSheet(dashboard_meta_chip_style())
        self.sourced_badge = QLabel("0 sourced")
        self.sourced_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: None")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.count_badge,
            self.awaiting_badge,
            self.sourced_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryRequisitionControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryRequisitionControlSurface {{
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
        self.search_edit.setPlaceholderText("Search requisition number, purpose, requester, or priority")
        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses", None)
        for status in (
            "DRAFT",
            "SUBMITTED",
            "APPROVED",
            "PARTIALLY_SOURCED",
            "FULLY_SOURCED",
            "REJECTED",
        ):
            self.status_filter.addItem(humanize_status(status), status)
        self.site_filter = QComboBox()
        self.site_filter.addItem("All sites", None)
        self.storeroom_filter = QComboBox()
        self.storeroom_filter.addItem("All storerooms", None)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.site_filter)
        filter_row.addWidget(self.storeroom_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Requisition")
        self.btn_edit = QPushButton("Edit")
        self.btn_add_line = QPushButton("Add Line")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_submit = QPushButton("Submit")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_edit, self.btn_add_line, self.btn_cancel, self.btn_submit, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_add_line.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_cancel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_submit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_edit)
        action_row.addWidget(self.btn_add_line)
        action_row.addWidget(self.btn_cancel)
        action_row.addWidget(self.btn_submit)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Number", "Status", "Site", "Storeroom", "Priority", "Needed By", "Requester"]
        )
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(6, QHeaderView.Stretch)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryRequisitionDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryRequisitionDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Requisition Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a requisition")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(CFG.SPACING_MD)
        detail_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.detail_site = QLabel("-")
        self.detail_storeroom = QLabel("-")
        self.detail_purpose = QLabel("-")
        self.detail_needed_by = QLabel("-")
        self.detail_source = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Site"), 0, 0)
        detail_grid.addWidget(self.detail_site, 0, 1)
        detail_grid.addWidget(QLabel("Storeroom"), 1, 0)
        detail_grid.addWidget(self.detail_storeroom, 1, 1)
        detail_grid.addWidget(QLabel("Purpose"), 2, 0)
        detail_grid.addWidget(self.detail_purpose, 2, 1)
        detail_grid.addWidget(QLabel("Needed By"), 3, 0)
        detail_grid.addWidget(self.detail_needed_by, 3, 1)
        detail_grid.addWidget(QLabel("Source"), 4, 0)
        detail_grid.addWidget(self.detail_source, 4, 1)
        detail_grid.addWidget(QLabel("Notes"), 5, 0)
        detail_grid.addWidget(self.detail_notes, 5, 1)
        detail_layout.addLayout(detail_grid)

        lines_title = QLabel("Demand Lines")
        lines_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(lines_title)
        self.lines_table = QTableWidget(0, 6)
        self.lines_table.setHorizontalHeaderLabels(
            ["Line", "Item", "Requested", "Sourced", "Supplier", "Status"]
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
        detail_layout.addWidget(self.lines_table, 1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.search_edit.textChanged.connect(lambda _text: self.reload_requisitions())
        self.status_filter.currentIndexChanged.connect(lambda _index: self.reload_requisitions())
        self.site_filter.currentIndexChanged.connect(lambda _index: self.reload_requisitions())
        self.storeroom_filter.currentIndexChanged.connect(lambda _index: self.reload_requisitions())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.reload_requisitions))
        self.btn_new.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.create_requisition))
        self.btn_edit.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.edit_requisition))
        self.btn_add_line.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.add_line))
        self.btn_cancel.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.cancel_requisition))
        self.btn_submit.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.submit_requisition))
        for button in (self.btn_new, self.btn_edit, self.btn_add_line, self.btn_cancel, self.btn_submit):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()
