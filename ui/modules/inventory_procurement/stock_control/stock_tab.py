from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import InventoryService, ItemMasterService, StockControlService
from core.modules.inventory_procurement.domain import StockBalance
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.stock_control.stock_dialogs import (
    OpeningBalanceDialog,
    StockAdjustmentDialog,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class StockTab(QWidget):
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
        self._balances: list[StockBalance] = []
        self._item_name_by_id: dict[str, str] = {}
        self._storeroom_name_by_id: dict[str, str] = {}
        self._setup_ui()
        self.reload_stock()
        domain_events.inventory_balances_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.inventory_reservations_changed.connect(self._on_inventory_changed)
        domain_events.inventory_purchase_orders_changed.connect(self._on_inventory_changed)
        domain_events.inventory_receipts_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("stockTabHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#stockTabHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("STOCK CONTROL")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Stock")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Review stock positions and recent movement history from the ledger-backed balance model. Opening balances and adjustments stay controlled inside this workspace."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.balance_count_badge = QLabel("0 balances")
        self.balance_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.on_hand_badge = QLabel("On hand: 0.000")
        self.on_hand_badge.setStyleSheet(dashboard_meta_chip_style())
        self.available_badge = QLabel("Available: 0.000")
        self.available_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: All positions")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.balance_count_badge,
            self.on_hand_badge,
            self.available_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("stockControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#stockControlSurface {{
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
        self.item_filter = QComboBox()
        self.storeroom_filter = QComboBox()
        self.item_filter.addItem("All items", None)
        self.storeroom_filter.addItem("All storerooms", None)
        filter_row.addWidget(self.item_filter)
        filter_row.addWidget(self.storeroom_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_opening_balance = QPushButton("Opening Balance")
        self.btn_adjustment = QPushButton("Adjustment")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_opening_balance, self.btn_adjustment, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_opening_balance.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_adjustment.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_opening_balance)
        action_row.addWidget(self.btn_adjustment)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        self.work_tabs = QTabWidget()
        self.work_tabs.setObjectName("inventoryStockWorkTabs")

        positions_page = QWidget()
        positions_layout = QVBoxLayout(positions_page)
        positions_layout.setContentsMargins(0, 0, 0, 0)
        positions_layout.setSpacing(CFG.SPACING_SM)

        self.balance_table = QTableWidget(0, 8)
        self.balance_table.setHorizontalHeaderLabels(
            ["Item", "Storeroom", "On Hand", "Reserved", "Available", "On Order", "UOM", "Reorder"]
        )
        style_table(self.balance_table)
        self.balance_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.balance_table.setSelectionMode(QTableWidget.SingleSelection)
        self.balance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        balance_header = self.balance_table.horizontalHeader()
        balance_header.setSectionResizeMode(0, QHeaderView.Stretch)
        balance_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for index in range(2, 8):
            balance_header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        positions_layout.addWidget(self.balance_table, 1)

        transactions_page = QWidget()
        transactions_layout = QVBoxLayout(transactions_page)
        transactions_layout.setContentsMargins(0, 0, 0, 0)
        transactions_layout.setSpacing(CFG.SPACING_SM)

        self.transaction_table = QTableWidget(0, 7)
        self.transaction_table.setHorizontalHeaderLabels(
            ["When", "Type", "Qty", "UOM", "Reference", "On Hand", "Available"]
        )
        style_table(self.transaction_table)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transaction_table.setSelectionMode(QTableWidget.SingleSelection)
        self.transaction_table.setEditTriggers(QTableWidget.NoEditTriggers)
        txn_header = self.transaction_table.horizontalHeader()
        txn_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        txn_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        txn_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        txn_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        txn_header.setSectionResizeMode(4, QHeaderView.Stretch)
        txn_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        txn_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        transactions_layout.addWidget(self.transaction_table, 1)

        self.work_tabs.addTab(positions_page, "Stock Positions")
        self.work_tabs.addTab(transactions_page, "Transaction History")
        root.addWidget(self.work_tabs, 1)

        self.item_filter.currentIndexChanged.connect(lambda _index: self.reload_stock())
        self.storeroom_filter.currentIndexChanged.connect(lambda _index: self.reload_stock())
        self.balance_table.itemSelectionChanged.connect(self._reload_transactions)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Stock", callback=self.reload_stock))
        self.btn_opening_balance.clicked.connect(
            make_guarded_slot(self, title="Stock", callback=self.post_opening_balance)
        )
        self.btn_adjustment.clicked.connect(
            make_guarded_slot(self, title="Stock", callback=self.post_adjustment)
        )
        for button in (self.btn_opening_balance, self.btn_adjustment):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")

    def reload_stock(self) -> None:
        selected_balance_id = self._selected_balance_id()
        try:
            items = self._item_service.list_items(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            self._item_name_by_id = {item.id: f"{item.item_code} - {item.name}" for item in items}
            self._storeroom_name_by_id = {
                storeroom.id: f"{storeroom.storeroom_code} - {storeroom.name}" for storeroom in storerooms
            }
            self._reload_filter_options()
            self._balances = self._stock_service.list_balances(
                stock_item_id=self._selected_item_filter(),
                storeroom_id=self._selected_storeroom_filter(),
            )
            context_label = self._context_label()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Stock", str(exc))
            self._balances = []
            self._item_name_by_id = {}
            self._storeroom_name_by_id = {}
            context_label = "-"
        except Exception as exc:
            QMessageBox.critical(self, "Stock", f"Failed to load stock: {exc}")
            self._balances = []
            self._item_name_by_id = {}
            self._storeroom_name_by_id = {}
            context_label = "-"
        self.balance_table.setRowCount(len(self._balances))
        selected_row = -1
        for row, balance in enumerate(self._balances):
            values = (
                self._item_name_by_id.get(balance.stock_item_id, balance.stock_item_id),
                self._storeroom_name_by_id.get(balance.storeroom_id, balance.storeroom_id),
                f"{balance.on_hand_qty:.3f}",
                f"{balance.reserved_qty:.3f}",
                f"{balance.available_qty:.3f}",
                f"{balance.on_order_qty:.3f}",
                balance.uom,
                "Yes" if balance.reorder_required else "No",
            )
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if col >= 2:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.balance_table.setItem(row, col, table_item)
            self.balance_table.item(row, 0).setData(Qt.UserRole, balance.id)
            if selected_balance_id and balance.id == selected_balance_id:
                selected_row = row
        self._update_badges(context_label=context_label)
        if selected_row >= 0:
            self.balance_table.selectRow(selected_row)
        else:
            self.balance_table.clearSelection()
        self._reload_transactions()

    def post_opening_balance(self) -> None:
        dialog = OpeningBalanceDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._stock_service.post_opening_balance(
                    stock_item_id=dialog.stock_item_id,
                    storeroom_id=dialog.storeroom_id,
                    quantity=dialog.quantity,
                    unit_cost=dialog.unit_cost,
                    notes=dialog.notes,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Stock", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Stock", f"Failed to post opening balance: {exc}")
                return
            break
        self.reload_stock()

    def post_adjustment(self) -> None:
        dialog = StockAdjustmentDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._stock_service.post_adjustment(
                    stock_item_id=dialog.stock_item_id,
                    storeroom_id=dialog.storeroom_id,
                    quantity=dialog.quantity,
                    direction=dialog.direction,
                    unit_cost=dialog.unit_cost,
                    reference_id=dialog.reference_id,
                    notes=dialog.notes,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Stock", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Stock", f"Failed to post adjustment: {exc}")
                return
            break
        self.reload_stock()

    def _active_item_options(self) -> list[tuple[str, str]]:
        items = self._item_service.list_items(active_only=True)
        return [(f"{item.item_code} - {item.name}", item.id) for item in items]

    def _active_storeroom_options(self) -> list[tuple[str, str]]:
        storerooms = self._inventory_service.list_storerooms(active_only=True)
        return [(f"{row.storeroom_code} - {row.name}", row.id) for row in storerooms]

    def _selected_item_filter(self) -> str | None:
        value = self.item_filter.currentData()
        if value is None:
            return None
        return str(value).strip() or None

    def _selected_storeroom_filter(self) -> str | None:
        value = self.storeroom_filter.currentData()
        if value is None:
            return None
        return str(value).strip() or None

    def _reload_filter_options(self) -> None:
        selected_item = self._selected_item_filter()
        selected_storeroom = self._selected_storeroom_filter()
        self.item_filter.blockSignals(True)
        self.storeroom_filter.blockSignals(True)
        self.item_filter.clear()
        self.storeroom_filter.clear()
        self.item_filter.addItem("All items", None)
        self.storeroom_filter.addItem("All storerooms", None)
        for item_id, label in sorted(self._item_name_by_id.items(), key=lambda row: row[1].lower()):
            self.item_filter.addItem(label, item_id)
        for storeroom_id, label in sorted(self._storeroom_name_by_id.items(), key=lambda row: row[1].lower()):
            self.storeroom_filter.addItem(label, storeroom_id)
        if selected_item:
            index = self.item_filter.findData(selected_item)
            if index >= 0:
                self.item_filter.setCurrentIndex(index)
        if selected_storeroom:
            index = self.storeroom_filter.findData(selected_storeroom)
            if index >= 0:
                self.storeroom_filter.setCurrentIndex(index)
        self.item_filter.blockSignals(False)
        self.storeroom_filter.blockSignals(False)

    def _selected_balance_id(self) -> str | None:
        selected = self.balance_table.selectedItems()
        if not selected:
            return None
        return str(selected[0].data(Qt.UserRole) or "").strip() or None

    def _selected_balance(self) -> StockBalance | None:
        selected_id = self._selected_balance_id()
        if not selected_id:
            return None
        return next((row for row in self._balances if row.id == selected_id), None)

    def _reload_transactions(self) -> None:
        balance = self._selected_balance()
        try:
            if balance is None:
                self.selection_badge.setText("Selection: All positions")
                rows = self._stock_service.list_transactions(
                    stock_item_id=self._selected_item_filter(),
                    storeroom_id=self._selected_storeroom_filter(),
                    limit=120,
                )
            else:
                self.selection_badge.setText(
                    f"Selection: {self._item_name_by_id.get(balance.stock_item_id, 'Item')} @ "
                    f"{self._storeroom_name_by_id.get(balance.storeroom_id, 'Storeroom')}"
                )
                rows = self._stock_service.list_transactions(
                    stock_item_id=balance.stock_item_id,
                    storeroom_id=balance.storeroom_id,
                    limit=120,
                )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Stock", str(exc))
            rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Stock", f"Failed to load transactions: {exc}")
            rows = []
        self.transaction_table.setRowCount(len(rows))
        for row_index, transaction in enumerate(rows):
            ref_text = transaction.reference_type or "-"
            if transaction.reference_id:
                ref_text = f"{ref_text}: {transaction.reference_id}"
            values = (
                self._format_timestamp(transaction.transaction_at),
                transaction.transaction_type.value.replace("_", " ").title(),
                f"{transaction.quantity:.3f}",
                transaction.uom,
                ref_text,
                f"{transaction.resulting_on_hand_qty:.3f}",
                f"{transaction.resulting_available_qty:.3f}",
            )
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if col in {2, 5, 6}:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.transaction_table.setItem(row_index, col, table_item)

    def _update_badges(self, *, context_label: str) -> None:
        total_on_hand = sum(balance.on_hand_qty for balance in self._balances)
        total_available = sum(balance.available_qty for balance in self._balances)
        self.context_badge.setText(f"Context: {context_label}")
        self.balance_count_badge.setText(f"{len(self._balances)} balances")
        self.on_hand_badge.setText(f"On hand: {total_on_hand:.3f}")
        self.available_badge.setText(f"Available: {total_available:.3f}")

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.astimezone().strftime("%Y-%m-%d %H:%M")

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_stock()


__all__ = ["StockTab"]
