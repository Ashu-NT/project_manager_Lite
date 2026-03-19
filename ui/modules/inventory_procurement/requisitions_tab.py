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
)
from core.modules.inventory_procurement.domain import PurchaseRequisition, PurchaseRequisitionStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.procurement_dialogs import (
    RequisitionEditDialog,
    RequisitionLineDialog,
)
from ui.modules.inventory_procurement.procurement_support import (
    build_item_lookup,
    build_storeroom_lookup,
    format_date,
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


class RequisitionsTab(QWidget):
    def __init__(
        self,
        *,
        procurement_service: ProcurementService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._procurement_service = procurement_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[PurchaseRequisition] = []
        self._selected_lines = []
        self._site_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._item_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_requisitions()
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
        self.btn_add_line = QPushButton("Add Line")
        self.btn_submit = QPushButton("Submit")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_add_line, self.btn_submit, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_add_line.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_submit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_add_line)
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
        self.btn_add_line.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.add_line))
        self.btn_submit.clicked.connect(make_guarded_slot(self, title="Requisitions", callback=self.submit_requisition))
        for button in (self.btn_new, self.btn_add_line, self.btn_submit):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_requisitions(self) -> None:
        selected_id = self._selected_requisition_id()
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
            self._reload_storeroom_filter()
            rows = self._procurement_service.list_requisitions(
                status=self._selected_status_filter(),
                site_id=self._selected_site_filter(),
                storeroom_id=self._selected_storeroom_filter(),
            )
            self._rows = self._apply_search_filter(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            self._rows = []
            self._selected_lines = []
            self._site_lookup = {}
            self._storeroom_lookup = {}
            self._item_lookup = {}
            self._party_lookup = {}
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to load requisitions: {exc}")
            self._rows = []
            self._selected_lines = []
            self._site_lookup = {}
            self._storeroom_lookup = {}
            self._item_lookup = {}
            self._party_lookup = {}
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def create_requisition(self) -> None:
        if not self._can_manage:
            return
        dialog = RequisitionEditDialog(
            site_options=build_option_rows(
                {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
            ),
            storeroom_options=self._storeroom_option_rows(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            requisition = self._procurement_service.create_requisition(
                requesting_site_id=dialog.site_id,
                requesting_storeroom_id=dialog.storeroom_id,
                purpose=dialog.purpose,
                needed_by_date=dialog.needed_by_date,
                priority=dialog.priority,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to create requisition: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def add_line(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        dialog = RequisitionLineDialog(
            item_options=self._active_item_options(),
            supplier_options=build_option_rows(
                {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup},
                include_blank=False,
            ),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._procurement_service.add_requisition_line(
                requisition.id,
                stock_item_id=dialog.stock_item_id,
                quantity_requested=dialog.quantity_requested,
                description=dialog.description,
                needed_by_date=dialog.needed_by_date,
                estimated_unit_cost=dialog.estimated_unit_cost,
                suggested_supplier_party_id=dialog.suggested_supplier_party_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to add requisition line: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def submit_requisition(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Submit Requisition",
            f"Submit {requisition.requisition_number} for approval?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._procurement_service.submit_requisition(requisition.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Requisitions", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Requisitions", f"Failed to submit requisition: {exc}")
            return
        self.reload_requisitions()
        self._select_requisition(requisition.id)

    def _apply_search_filter(self, rows: list[PurchaseRequisition]) -> list[PurchaseRequisition]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[PurchaseRequisition] = []
        for row in rows:
            haystacks = (
                row.requisition_number,
                row.purpose,
                row.priority,
                row.requester_username,
                row.status.value,
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, requisition in enumerate(self._rows):
            values = (
                requisition.requisition_number,
                humanize_status(requisition.status.value),
                format_site_label(requisition.requesting_site_id, self._site_lookup),
                format_storeroom_label(requisition.requesting_storeroom_id, self._storeroom_lookup),
                humanize_status(requisition.priority),
                format_date(requisition.needed_by_date),
                requisition.requester_username or "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, requisition.id)
                self.table.setItem(row_index, column, item)
            if requisition.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._selected_lines = []
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None:
            self._selected_lines = []
            self._update_detail(None)
            self._sync_actions()
            return
        try:
            self._selected_lines = self._procurement_service.list_requisition_lines(requisition.id)
        except Exception:
            self._selected_lines = []
        self._update_detail(requisition)
        self._sync_actions()

    def _update_detail(self, requisition: PurchaseRequisition | None) -> None:
        if requisition is None:
            self.detail_name.setText("Select a requisition")
            self.detail_status.setText("-")
            self.detail_site.setText("-")
            self.detail_storeroom.setText("-")
            self.detail_purpose.setText("-")
            self.detail_needed_by.setText("-")
            self.detail_source.setText("-")
            self.detail_notes.setText("-")
            self.lines_table.setRowCount(0)
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(requisition.requisition_number)
        self.detail_status.setText(
            f"{humanize_status(requisition.status.value)} | Requester: {requisition.requester_username or '-'}"
        )
        self.detail_site.setText(format_site_label(requisition.requesting_site_id, self._site_lookup))
        self.detail_storeroom.setText(
            format_storeroom_label(requisition.requesting_storeroom_id, self._storeroom_lookup)
        )
        self.detail_purpose.setText(requisition.purpose or "-")
        self.detail_needed_by.setText(format_date(requisition.needed_by_date))
        source_text = requisition.source_reference_type or "-"
        if requisition.source_reference_id:
            source_text = f"{source_text}: {requisition.source_reference_id}"
        self.detail_source.setText(source_text)
        self.detail_notes.setText(requisition.notes or "-")
        self.selection_badge.setText(f"Selection: {requisition.requisition_number}")
        self.lines_table.setRowCount(len(self._selected_lines))
        for row_index, line in enumerate(self._selected_lines):
            values = (
                line.line_number,
                format_item_label(line.stock_item_id, self._item_lookup),
                format_quantity(line.quantity_requested),
                format_quantity(line.quantity_sourced),
                format_party_label(line.suggested_supplier_party_id, self._party_lookup),
                humanize_status(line.status.value),
            )
            for column, value in enumerate(values):
                self.lines_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _update_badges(self) -> None:
        awaiting = sum(
            1
            for row in self._rows
            if row.status in {PurchaseRequisitionStatus.SUBMITTED, PurchaseRequisitionStatus.UNDER_REVIEW}
        )
        sourced = sum(
            1
            for row in self._rows
            if row.status in {PurchaseRequisitionStatus.PARTIALLY_SOURCED, PurchaseRequisitionStatus.FULLY_SOURCED}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} requisitions")
        self.awaiting_badge.setText(f"{awaiting} awaiting approval")
        self.sourced_badge.setText(f"{sourced} sourced")

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

    def _reload_storeroom_filter(self) -> None:
        current = self._selected_storeroom_filter()
        self.storeroom_filter.blockSignals(True)
        self.storeroom_filter.clear()
        self.storeroom_filter.addItem("All storerooms", None)
        for label, row_id, _site_id in self._storeroom_option_rows():
            self.storeroom_filter.addItem(label, row_id)
        _set_combo_to_data(self.storeroom_filter, current or "")
        self.storeroom_filter.blockSignals(False)

    def _storeroom_option_rows(self) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for storeroom_id, storeroom in self._storeroom_lookup.items():
            label = (
                f"{format_storeroom_label(storeroom_id, self._storeroom_lookup)}"
                f" ({format_site_label(storeroom.site_id, self._site_lookup)})"
            )
            rows.append((label, storeroom_id, storeroom.site_id))
        return sorted(rows, key=lambda row: row[0].lower())

    def _active_item_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item_id, item in self._item_lookup.items():
            if not item.is_active or not item.is_purchase_allowed:
                continue
            options.append((format_item_label(item_id, self._item_lookup), item_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _selected_requisition_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_requisition(self) -> PurchaseRequisition | None:
        selected_id = self._selected_requisition_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    def _select_requisition(self, requisition_id: str) -> None:
        for row_index, row in enumerate(self._rows):
            if row.id == requisition_id:
                self.table.selectRow(row_index)
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

    def _selected_storeroom_filter(self) -> str | None:
        value = self.storeroom_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        requisition = self._selected_requisition()
        is_draft = bool(requisition is not None and requisition.status == PurchaseRequisitionStatus.DRAFT)
        self.btn_add_line.setEnabled(self._can_manage and is_draft)
        self.btn_submit.setEnabled(self._can_manage and is_draft and bool(self._selected_lines))

    def _context_label(self) -> str:
        site_label = "All sites"
        site_id = self._selected_site_filter()
        if site_id:
            site_label = format_site_label(site_id, self._site_lookup)
        status_label = humanize_status(self._selected_status_filter() or "all")
        return f"{site_label} | {status_label}"

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_requisitions()


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


__all__ = ["RequisitionsTab"]
