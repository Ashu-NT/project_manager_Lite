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
from core.modules.inventory_procurement import InventoryReferenceService, ItemMasterService
from core.modules.inventory_procurement.domain import StockItem
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.item_dialogs import InventoryItemEditDialog
from ui.modules.inventory_procurement.reference_support import (
    build_option_rows,
    build_party_lookup,
    format_party_label,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class InventoryItemsTab(QWidget):
    def __init__(
        self,
        *,
        item_service: ItemMasterService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._item_service = item_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[StockItem] = []
        self._party_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_items()
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.documents_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryItemsHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryItemsHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)

        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("ITEM MASTER")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Items")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Maintain reusable stock items with operational fields first, while supplier identity and documents stay shared by platform reference."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        badge_layout = QVBoxLayout()
        badge_layout.setSpacing(CFG.SPACING_SM)
        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 items")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.active_badge = QLabel("0 active")
        self.active_badge.setStyleSheet(dashboard_meta_chip_style())
        self.stocked_badge = QLabel("0 stocked")
        self.stocked_badge.setStyleSheet(dashboard_meta_chip_style())
        self.access_badge = QLabel("Manage Enabled" if self._can_manage else "Read Only")
        self.access_badge.setStyleSheet(dashboard_meta_chip_style())
        for badge in (
            self.context_badge,
            self.count_badge,
            self.active_badge,
            self.stocked_badge,
            self.access_badge,
        ):
            badge_layout.addWidget(badge, 0, Qt.AlignRight)
        badge_layout.addStretch(1)
        header_layout.addLayout(badge_layout)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryItemsControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryItemsControlSurface {{
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
        self.search_edit.setPlaceholderText("Search code, name, type, category, or UOM")
        self.active_filter = QComboBox()
        self.active_filter.addItem("All statuses", None)
        self.active_filter.addItem("Active only", True)
        self.active_filter.addItem("Inactive only", False)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.active_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Item")
        self.btn_edit = QPushButton("Edit Item")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_edit)
        action_row.addWidget(self.btn_toggle_active)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Type", "Status", "Stock UOM", "Preferred Party"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header_widget = self.table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryItemDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryItemDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Item Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select an item")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(CFG.SPACING_MD)
        detail_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.detail_type = QLabel("-")
        self.detail_category = QLabel("-")
        self.detail_reorder = QLabel("-")
        self.detail_flags = QLabel("-")
        self.detail_documents = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Type"), 0, 0)
        detail_grid.addWidget(self.detail_type, 0, 1)
        detail_grid.addWidget(QLabel("Category"), 1, 0)
        detail_grid.addWidget(self.detail_category, 1, 1)
        detail_grid.addWidget(QLabel("Reorder"), 2, 0)
        detail_grid.addWidget(self.detail_reorder, 2, 1)
        detail_grid.addWidget(QLabel("Flags"), 3, 0)
        detail_grid.addWidget(self.detail_flags, 3, 1)
        detail_grid.addWidget(QLabel("Documents"), 4, 0)
        detail_grid.addWidget(self.detail_documents, 4, 1)
        detail_grid.addWidget(QLabel("Notes"), 5, 0)
        detail_grid.addWidget(self.detail_notes, 5, 1)
        detail_layout.addLayout(detail_grid)
        detail_layout.addStretch(1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Inventory Items", callback=self.reload_items))
        self.btn_new.clicked.connect(make_guarded_slot(self, title="Inventory Items", callback=self.create_item))
        self.btn_edit.clicked.connect(make_guarded_slot(self, title="Inventory Items", callback=self.edit_item))
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Inventory Items", callback=self.toggle_active)
        )
        self.search_edit.textChanged.connect(lambda _text: self.reload_items())
        self.active_filter.currentIndexChanged.connect(lambda _index: self.reload_items())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_items(self) -> None:
        selected_id = self._selected_item_id()
        try:
            self._party_lookup = build_party_lookup(self._reference_service.list_business_parties(active_only=None))
            self._rows = self._item_service.search_items(
                search_text=self.search_text,
                active_only=self._selected_active_filter(),
            )
            context_label = self._context_label()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Items", str(exc))
            self._rows = []
            self._party_lookup = {}
            context_label = "-"
        except Exception as exc:
            QMessageBox.critical(self, "Inventory Items", f"Failed to load items: {exc}")
            self._rows = []
            self._party_lookup = {}
            context_label = "-"
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row, item in enumerate(self._rows):
            values = (
                item.item_code,
                item.name,
                item.item_type or "-",
                item.status,
                item.stock_uom,
                format_party_label(item.preferred_party_id, self._party_lookup),
            )
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                self.table.setItem(row, col, table_item)
            self.table.item(row, 0).setData(Qt.UserRole, item.id)
            if selected_id and item.id == selected_id:
                selected_row = row
        self._update_badges(context_label=context_label)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
            self._populate_details(None)
        self._sync_actions()

    def create_item(self) -> None:
        dialog = InventoryItemEditDialog(
            party_options=self._party_options(include_blank=True),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._item_service.create_item(
                    item_code=dialog.item_code,
                    name=dialog.name,
                    status=dialog.status,
                    item_type=dialog.item_type,
                    stock_uom=dialog.stock_uom,
                    order_uom=dialog.order_uom,
                    issue_uom=dialog.issue_uom,
                    category_code=dialog.category_code,
                    reorder_point=dialog.reorder_point,
                    reorder_qty=dialog.reorder_qty,
                    preferred_party_id=dialog.preferred_party_id,
                    is_stocked=dialog.is_stocked,
                    is_purchase_allowed=dialog.is_purchase_allowed,
                    notes=dialog.notes,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Inventory Items", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Inventory Items", f"Failed to create item: {exc}")
                return
            break
        self.reload_items()

    def edit_item(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Inventory Items", "Please select an item.")
            return
        dialog = InventoryItemEditDialog(
            item=item,
            party_options=self._party_options(include_blank=True),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._item_service.update_item(
                    item.id,
                    item_code=dialog.item_code,
                    name=dialog.name,
                    status=dialog.status,
                    item_type=dialog.item_type,
                    stock_uom=dialog.stock_uom,
                    order_uom=dialog.order_uom,
                    issue_uom=dialog.issue_uom,
                    category_code=dialog.category_code,
                    reorder_point=dialog.reorder_point,
                    reorder_qty=dialog.reorder_qty,
                    preferred_party_id=dialog.preferred_party_id,
                    is_stocked=dialog.is_stocked,
                    is_purchase_allowed=dialog.is_purchase_allowed,
                    notes=dialog.notes,
                    expected_version=item.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Inventory Items", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_items()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Inventory Items", f"Failed to update item: {exc}")
                return
            break
        self.reload_items()

    def toggle_active(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Inventory Items", "Please select an item.")
            return
        try:
            self._item_service.update_item(
                item.id,
                is_active=not item.is_active,
                expected_version=item.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Inventory Items", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_items()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Inventory Items", f"Failed to update item: {exc}")
            return
        self.reload_items()

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip()

    def _selected_active_filter(self) -> bool | None:
        return self.active_filter.currentData()

    def _party_options(self, *, include_blank: bool) -> list[tuple[str, str]]:
        labels_by_id = {
            party_id: format_party_label(party_id, self._party_lookup)
            for party_id in self._party_lookup.keys()
        }
        return build_option_rows(labels_by_id, include_blank=include_blank)

    def _selected_item_id(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return str(selected[0].data(Qt.UserRole) or "").strip() or None

    def _selected_item(self) -> StockItem | None:
        selected_id = self._selected_item_id()
        if not selected_id:
            return None
        return next((row for row in self._rows if row.id == selected_id), None)

    def _sync_actions(self) -> None:
        has_selection = self._selected_item() is not None
        self.btn_edit.setEnabled(self._can_manage and has_selection)
        self.btn_toggle_active.setEnabled(self._can_manage and has_selection)

    def _update_badges(self, *, context_label: str) -> None:
        active_count = sum(1 for item in self._rows if item.is_active)
        stocked_count = sum(1 for item in self._rows if item.is_stocked)
        self.context_badge.setText(f"Context: {context_label}")
        self.count_badge.setText(f"{len(self._rows)} items")
        self.active_badge.setText(f"{active_count} active")
        self.stocked_badge.setText(f"{stocked_count} stocked")

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_items()

    def _on_selection_changed(self) -> None:
        self._populate_details(self._selected_item())
        self._sync_actions()

    def _populate_details(self, item: StockItem | None) -> None:
        if item is None:
            self.detail_name.setText("Select an item")
            self.detail_status.setText("-")
            self.detail_type.setText("-")
            self.detail_category.setText("-")
            self.detail_reorder.setText("-")
            self.detail_flags.setText("-")
            self.detail_documents.setText("-")
            self.detail_notes.setText("-")
            return
        self.detail_name.setText(f"{item.item_code} - {item.name}")
        self.detail_status.setText(
            f"{item.status} | Preferred party: {format_party_label(item.preferred_party_id, self._party_lookup)}"
        )
        self.detail_type.setText(item.item_type or "-")
        self.detail_category.setText(item.category_code or "-")
        self.detail_reorder.setText(
            f"Point {item.reorder_point:.3f} / Qty {item.reorder_qty:.3f} / UOM {item.stock_uom}"
        )
        flags = []
        if item.is_stocked:
            flags.append("Stocked")
        if item.is_purchase_allowed:
            flags.append("Purchasable")
        if item.is_lot_tracked:
            flags.append("Lot tracked")
        if item.is_serial_tracked:
            flags.append("Serial tracked")
        self.detail_flags.setText(", ".join(flags) or "-")
        try:
            documents = self._item_service.list_linked_documents(item.id)
        except Exception:
            documents = []
        document_summary = ", ".join(document.title for document in documents[:3]) or "No linked documents"
        if len(documents) > 3:
            document_summary = f"{document_summary} (+{len(documents) - 3} more)"
        self.detail_documents.setText(document_summary)
        self.detail_notes.setText(item.notes or "-")


__all__ = ["InventoryItemsTab"]
