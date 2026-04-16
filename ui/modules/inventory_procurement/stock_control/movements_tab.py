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

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import InventoryService, ItemMasterService, StockControlService
from core.modules.inventory_procurement.domain import StockTransaction, StockTransactionType
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.procurement_support import (
    build_item_lookup,
    build_storeroom_lookup,
    format_datetime,
    format_item_label,
    format_quantity,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.inventory_procurement.stock_control.movement_dialogs import (
    StockMovementDialog,
    StockTransferDialog,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG

_MOVEMENT_TRANSACTION_TYPES = {
    StockTransactionType.ISSUE,
    StockTransactionType.RETURN,
    StockTransactionType.TRANSFER_OUT,
    StockTransactionType.TRANSFER_IN,
}


class MovementsTab(QWidget):
    def __init__(
        self,
        *,
        stock_service: StockControlService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stock_service = stock_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[StockTransaction] = []
        self._item_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_movements()
        domain_events.inventory_balances_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryMovementsHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryMovementsHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("WAREHOUSE EXECUTION")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Movements")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Execute issue, return, and transfer actions against the stock ledger without editing balances directly."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 movements")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.issue_badge = QLabel("0 issues")
        self.issue_badge.setStyleSheet(dashboard_meta_chip_style())
        self.transfer_badge = QLabel("0 transfers")
        self.transfer_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: None")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.count_badge,
            self.issue_badge,
            self.transfer_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryMovementControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryMovementControlSurface {{
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
        self.search_edit.setPlaceholderText("Search reference, type, item, or storeroom")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All movement types", None)
        self.type_filter.addItem("Issue", StockTransactionType.ISSUE.value)
        self.type_filter.addItem("Return", StockTransactionType.RETURN.value)
        self.type_filter.addItem("Transfer Out", StockTransactionType.TRANSFER_OUT.value)
        self.type_filter.addItem("Transfer In", StockTransactionType.TRANSFER_IN.value)
        self.item_filter = QComboBox()
        self.item_filter.addItem("All items", None)
        self.storeroom_filter = QComboBox()
        self.storeroom_filter.addItem("All storerooms", None)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(self.item_filter)
        filter_row.addWidget(self.storeroom_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_issue = QPushButton("Issue")
        self.btn_return = QPushButton("Return")
        self.btn_transfer = QPushButton("Transfer")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_issue, self.btn_return, self.btn_transfer, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_issue.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_return.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_transfer.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_issue)
        action_row.addWidget(self.btn_return)
        action_row.addWidget(self.btn_transfer)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["When", "Type", "Item", "Storeroom", "Qty", "Reference", "On Hand"]
        )
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(2, QHeaderView.Stretch)
        table_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryMovementDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryMovementDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Movement Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a movement")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(CFG.SPACING_MD)
        detail_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.detail_item = QLabel("-")
        self.detail_storeroom = QLabel("-")
        self.detail_reference = QLabel("-")
        self.detail_result = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Item"), 0, 0)
        detail_grid.addWidget(self.detail_item, 0, 1)
        detail_grid.addWidget(QLabel("Storeroom"), 1, 0)
        detail_grid.addWidget(self.detail_storeroom, 1, 1)
        detail_grid.addWidget(QLabel("Reference"), 2, 0)
        detail_grid.addWidget(self.detail_reference, 2, 1)
        detail_grid.addWidget(QLabel("Result"), 3, 0)
        detail_grid.addWidget(self.detail_result, 3, 1)
        detail_grid.addWidget(QLabel("Notes"), 4, 0)
        detail_grid.addWidget(self.detail_notes, 4, 1)
        detail_layout.addLayout(detail_grid)
        detail_layout.addStretch(1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.search_edit.textChanged.connect(lambda _text: self.reload_movements())
        self.type_filter.currentIndexChanged.connect(lambda _index: self.reload_movements())
        self.item_filter.currentIndexChanged.connect(lambda _index: self.reload_movements())
        self.storeroom_filter.currentIndexChanged.connect(lambda _index: self.reload_movements())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Movements", callback=self.reload_movements))
        self.btn_issue.clicked.connect(make_guarded_slot(self, title="Movements", callback=self.issue_stock))
        self.btn_return.clicked.connect(make_guarded_slot(self, title="Movements", callback=self.return_stock))
        self.btn_transfer.clicked.connect(make_guarded_slot(self, title="Movements", callback=self.transfer_stock))
        for button in (self.btn_issue, self.btn_return, self.btn_transfer):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")

    def reload_movements(self) -> None:
        selected_id = self._selected_transaction_id()
        try:
            items = self._item_service.list_items(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            self._item_lookup = build_item_lookup(items)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._reload_filters()
            rows = self._stock_service.list_transactions(
                stock_item_id=self._selected_item_filter(),
                storeroom_id=self._selected_storeroom_filter(),
            )
            movement_rows = [row for row in rows if row.transaction_type in _MOVEMENT_TRANSACTION_TYPES]
            type_code = self._selected_type_filter()
            if type_code:
                movement_rows = [row for row in movement_rows if row.transaction_type.value == type_code]
            self._rows = self._apply_search_filter(movement_rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Movements", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Movements", f"Failed to load movement history: {exc}")
            self._rows = []
        self._populate_table(selected_id=selected_id)
        self._update_badges()

    def issue_stock(self) -> None:
        if not self._can_manage:
            return
        dialog = StockMovementDialog(
            title="Issue Stock",
            intro_text="Issue available stock for operational consumption or execution demand.",
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            reference_type_placeholder="task_issue, work_order_issue, project_issue, ...",
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._stock_service.issue_stock(
                stock_item_id=dialog.stock_item_id,
                storeroom_id=dialog.storeroom_id,
                quantity=dialog.quantity,
                reference_type=dialog.reference_type or "issue",
                reference_id=dialog.reference_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Movements", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Movements", f"Failed to issue stock: {exc}")
            return
        self.reload_movements()

    def return_stock(self) -> None:
        if not self._can_manage:
            return
        dialog = StockMovementDialog(
            title="Return Stock",
            intro_text="Return stock back into a storeroom after unused or reversed operational consumption.",
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            reference_type_placeholder="task_return, work_order_return, project_return, ...",
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._stock_service.return_stock(
                stock_item_id=dialog.stock_item_id,
                storeroom_id=dialog.storeroom_id,
                quantity=dialog.quantity,
                reference_type=dialog.reference_type or "return",
                reference_id=dialog.reference_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Movements", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Movements", f"Failed to return stock: {exc}")
            return
        self.reload_movements()

    def transfer_stock(self) -> None:
        if not self._can_manage:
            return
        dialog = StockTransferDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._stock_service.transfer_stock(
                stock_item_id=dialog.stock_item_id,
                source_storeroom_id=dialog.source_storeroom_id,
                destination_storeroom_id=dialog.destination_storeroom_id,
                quantity=dialog.quantity,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Movements", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Movements", f"Failed to transfer stock: {exc}")
            return
        self.reload_movements()

    def _apply_search_filter(self, rows: list[StockTransaction]) -> list[StockTransaction]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[StockTransaction] = []
        for row in rows:
            haystacks = (
                row.reference_type,
                row.reference_id,
                row.transaction_type.value,
                format_item_label(row.stock_item_id, self._item_lookup),
                format_storeroom_label(row.storeroom_id, self._storeroom_lookup),
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return rows if not filtered and not needle else filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, transaction in enumerate(self._rows):
            reference = transaction.reference_type or "-"
            if transaction.reference_id:
                reference = f"{reference}: {transaction.reference_id}"
            values = (
                format_datetime(transaction.transaction_at),
                humanize_status(transaction.transaction_type.value),
                format_item_label(transaction.stock_item_id, self._item_lookup),
                format_storeroom_label(transaction.storeroom_id, self._storeroom_lookup),
                format_quantity(transaction.quantity),
                reference,
                format_quantity(transaction.resulting_on_hand_qty),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, transaction.id)
                self.table.setItem(row_index, column, item)
            if transaction.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        self._update_detail(self._selected_transaction())

    def _update_detail(self, transaction: StockTransaction | None) -> None:
        if transaction is None:
            self.detail_name.setText("Select a movement")
            self.detail_status.setText("-")
            self.detail_item.setText("-")
            self.detail_storeroom.setText("-")
            self.detail_reference.setText("-")
            self.detail_result.setText("-")
            self.detail_notes.setText("-")
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(humanize_status(transaction.transaction_type.value))
        self.detail_status.setText(format_datetime(transaction.transaction_at))
        self.detail_item.setText(format_item_label(transaction.stock_item_id, self._item_lookup))
        self.detail_storeroom.setText(format_storeroom_label(transaction.storeroom_id, self._storeroom_lookup))
        reference = transaction.reference_type or "-"
        if transaction.reference_id:
            reference = f"{reference}: {transaction.reference_id}"
        self.detail_reference.setText(reference)
        self.detail_result.setText(
            f"Qty {format_quantity(transaction.quantity)} | "
            f"On hand {format_quantity(transaction.resulting_on_hand_qty)} | "
            f"Available {format_quantity(transaction.resulting_available_qty)}"
        )
        self.detail_notes.setText(transaction.notes or "-")
        self.selection_badge.setText(f"Selection: {humanize_status(transaction.transaction_type.value)}")

    def _update_badges(self) -> None:
        issue_count = sum(1 for row in self._rows if row.transaction_type == StockTransactionType.ISSUE)
        transfer_count = sum(
            1
            for row in self._rows
            if row.transaction_type in {StockTransactionType.TRANSFER_OUT, StockTransactionType.TRANSFER_IN}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} movements")
        self.issue_badge.setText(f"{issue_count} issues")
        self.transfer_badge.setText(f"{transfer_count} transfers")

    def _reload_filters(self) -> None:
        current_item = self._selected_item_filter()
        current_storeroom = self._selected_storeroom_filter()
        self.item_filter.blockSignals(True)
        self.item_filter.clear()
        self.item_filter.addItem("All items", None)
        for label, row_id in self._active_item_options():
            self.item_filter.addItem(label, row_id)
        _set_combo_to_data(self.item_filter, current_item or "")
        self.item_filter.blockSignals(False)

        self.storeroom_filter.blockSignals(True)
        self.storeroom_filter.clear()
        self.storeroom_filter.addItem("All storerooms", None)
        for label, row_id in self._active_storeroom_options():
            self.storeroom_filter.addItem(label, row_id)
        _set_combo_to_data(self.storeroom_filter, current_storeroom or "")
        self.storeroom_filter.blockSignals(False)

    def _active_item_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item_id, item in self._item_lookup.items():
            if not item.is_active or not item.is_stocked:
                continue
            options.append((format_item_label(item_id, self._item_lookup), item_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _active_storeroom_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for storeroom_id, storeroom in self._storeroom_lookup.items():
            if not storeroom.is_active:
                continue
            options.append((format_storeroom_label(storeroom_id, self._storeroom_lookup), storeroom_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _selected_transaction_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_transaction(self) -> StockTransaction | None:
        selected_id = self._selected_transaction_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    def _selected_type_filter(self) -> str | None:
        value = self.type_filter.currentData()
        return str(value).strip() if value else None

    def _selected_item_filter(self) -> str | None:
        value = self.item_filter.currentData()
        return str(value).strip() if value else None

    def _selected_storeroom_filter(self) -> str | None:
        value = self.storeroom_filter.currentData()
        return str(value).strip() if value else None

    def _context_label(self) -> str:
        type_label = self.type_filter.currentText()
        storeroom_id = self._selected_storeroom_filter()
        if storeroom_id:
            return f"{type_label} | {format_storeroom_label(storeroom_id, self._storeroom_lookup)}"
        return type_label

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_movements()


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


__all__ = ["MovementsTab"]
