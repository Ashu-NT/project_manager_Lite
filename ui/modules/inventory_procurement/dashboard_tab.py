from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryService,
    ItemMasterService,
    ProcurementService,
    PurchasingService,
    ReservationService,
    StockControlService,
)
from core.modules.inventory_procurement.domain import PurchaseOrderStatus, PurchaseRequisitionStatus, StockReservationStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.procurement_support import format_date, humanize_status
from ui.modules.inventory_procurement.shared.reference_support import (
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
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class InventoryDashboardTab(QWidget):
    def __init__(
        self,
        *,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        stock_service: StockControlService,
        reservation_service: ReservationService,
        procurement_service: ProcurementService,
        purchasing_service: PurchasingService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._reservation_service = reservation_service
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._item_labels: dict[str, str] = {}
        self._storeroom_labels: dict[str, str] = {}
        self._setup_ui()
        self.reload_dashboard()
        for signal in (
            domain_events.inventory_items_changed,
            domain_events.inventory_storerooms_changed,
            domain_events.inventory_balances_changed,
            domain_events.inventory_reservations_changed,
            domain_events.inventory_requisitions_changed,
            domain_events.inventory_purchase_orders_changed,
            domain_events.inventory_receipts_changed,
            domain_events.sites_changed,
            domain_events.parties_changed,
            domain_events.organizations_changed,
        ):
            signal.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryDashboardHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryDashboardHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("INVENTORY CONTROL TOWER")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Inventory Dashboard")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "See stock pressure, open reservations, approval queues, and receiving workload in one place while shared sites and suppliers stay referenced from platform services."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.low_stock_badge = QLabel("0 low stock")
        self.low_stock_badge.setStyleSheet(dashboard_meta_chip_style())
        self.awaiting_badge = QLabel("0 awaiting approval")
        self.awaiting_badge.setStyleSheet(dashboard_meta_chip_style())
        self.receiving_badge = QLabel("0 open receiving")
        self.receiving_badge.setStyleSheet(dashboard_meta_chip_style())
        self.on_order_badge = QLabel("On order: 0.000")
        self.on_order_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.low_stock_badge,
            self.awaiting_badge,
            self.receiving_badge,
            self.on_order_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryDashboardControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryDashboardControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        controls_layout.addWidget(self.btn_refresh)
        controls_layout.addStretch(1)
        root.addWidget(controls)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(CFG.SPACING_MD)
        kpi_grid.setVerticalSpacing(CFG.SPACING_MD)
        self.kpi_items = KpiCard("Items", "0", "Active master records", CFG.COLOR_ACCENT)
        self.kpi_storerooms = KpiCard("Storerooms", "0", "Active stock locations", CFG.COLOR_SUCCESS)
        self.kpi_positions = KpiCard("Stock Positions", "0", "Ledger-backed balances", CFG.COLOR_ACCENT)
        self.kpi_reservations = KpiCard("Open Reservations", "0", "Committed demand holds", CFG.COLOR_WARNING)
        self.kpi_awaiting = KpiCard("Awaiting Approval", "0", "Requisitions and POs", CFG.COLOR_DANGER)
        self.kpi_receiving = KpiCard("Receiving Queue", "0", "POs open for receipt", CFG.COLOR_SUCCESS)
        self.kpi_low_stock = KpiCard("Low Stock", "0", "Reorder attention", CFG.COLOR_WARNING)
        self.kpi_on_order = KpiCard("On Order Qty", "0.000", "Approved external supply", CFG.COLOR_ACCENT)
        cards = (
            self.kpi_items,
            self.kpi_storerooms,
            self.kpi_positions,
            self.kpi_reservations,
            self.kpi_awaiting,
            self.kpi_receiving,
            self.kpi_low_stock,
            self.kpi_on_order,
        )
        for index, card in enumerate(cards):
            kpi_grid.addWidget(card, index // 4, index % 4)
        root.addLayout(kpi_grid)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_low_stock_panel(), 1)
        content_row.addWidget(self._build_queue_panel(), 1)
        root.addLayout(content_row, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Inventory Dashboard", callback=self.reload_dashboard)
        )

    def _build_low_stock_panel(self) -> QWidget:
        card = QWidget()
        card.setObjectName("inventoryDashboardLowStockCard")
        card.setStyleSheet(
            f"""
            QWidget#inventoryDashboardLowStockCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)
        title = QLabel("Low Stock Watch")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        subtitle = QLabel("Balances currently asking for replenishment based on the item policy.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.low_stock_table = QTableWidget(0, 5)
        self.low_stock_table.setHorizontalHeaderLabels(["Item", "Storeroom", "Available", "On Order", "Reorder"])
        style_table(self.low_stock_table)
        self.low_stock_table.setSelectionMode(QTableWidget.NoSelection)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.low_stock_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.low_stock_table, 1)
        return card

    def _build_queue_panel(self) -> QWidget:
        card = QWidget()
        card.setObjectName("inventoryDashboardQueueCard")
        card.setStyleSheet(
            f"""
            QWidget#inventoryDashboardQueueCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)
        title = QLabel("Operational Queue")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        subtitle = QLabel("The most actionable requisition and purchase-order work still moving through the module.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.queue_table = QTableWidget(0, 5)
        self.queue_table.setHorizontalHeaderLabels(["Type", "Number", "Status", "Site", "Target"])
        style_table(self.queue_table)
        self.queue_table.setSelectionMode(QTableWidget.NoSelection)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.queue_table, 1)
        return card

    def reload_dashboard(self) -> None:
        try:
            items = self._item_service.list_items(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            balances = self._stock_service.list_balances()
            reservations = self._reservation_service.list_reservations(limit=500)
            requisitions = self._procurement_service.list_requisitions(limit=500)
            purchase_orders = self._purchasing_service.list_purchase_orders(limit=500)
            self._site_lookup = build_site_lookup(self._reference_service.list_sites(active_only=None))
            self._party_lookup = build_party_lookup(self._reference_service.list_business_parties(active_only=None))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Dashboard", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Inventory Dashboard", f"Failed to load dashboard: {exc}")
            return

        self._item_labels = {item.id: f"{item.item_code} - {item.name}" for item in items}
        self._storeroom_labels = {
            storeroom.id: f"{storeroom.storeroom_code} - {storeroom.name}"
            for storeroom in storerooms
        }
        low_stock_rows = [
            balance
            for balance in balances
            if bool(balance.reorder_required)
        ]
        low_stock_rows.sort(key=lambda row: (float(row.available_qty or 0.0), -float(row.on_order_qty or 0.0)))
        open_reservations = [
            row
            for row in reservations
            if row.status in {StockReservationStatus.ACTIVE, StockReservationStatus.PARTIALLY_ISSUED}
        ]
        awaiting_approvals = [
            row
            for row in requisitions
            if row.status in {PurchaseRequisitionStatus.SUBMITTED, PurchaseRequisitionStatus.UNDER_REVIEW}
        ]
        awaiting_approvals.extend(
            row
            for row in purchase_orders
            if row.status in {PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.UNDER_REVIEW}
        )
        open_receiving = [
            row
            for row in purchase_orders
            if row.status in {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.SENT, PurchaseOrderStatus.PARTIALLY_RECEIVED}
        ]
        self._update_kpis(
            total_items=len(items),
            active_items=sum(1 for item in items if item.is_active),
            total_storerooms=len(storerooms),
            active_storerooms=sum(1 for storeroom in storerooms if storeroom.is_active),
            stock_positions=len(balances),
            low_stock=len(low_stock_rows),
            open_reservations=len(open_reservations),
            awaiting=len(awaiting_approvals),
            receiving=len(open_receiving),
            total_on_order=sum(float(balance.on_order_qty or 0.0) for balance in balances),
        )
        self._populate_low_stock_table(low_stock_rows)
        self._populate_queue_table(requisitions=requisitions, purchase_orders=purchase_orders)

    def _update_kpis(
        self,
        *,
        total_items: int,
        active_items: int,
        total_storerooms: int,
        active_storerooms: int,
        stock_positions: int,
        low_stock: int,
        open_reservations: int,
        awaiting: int,
        receiving: int,
        total_on_order: float,
    ) -> None:
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.low_stock_badge.setText(f"{low_stock} low stock")
        self.awaiting_badge.setText(f"{awaiting} awaiting approval")
        self.receiving_badge.setText(f"{receiving} open receiving")
        self.on_order_badge.setText(f"On order: {total_on_order:.3f}")
        self.kpi_items.set_value(str(total_items))
        self.kpi_items.set_subtitle(f"{active_items} active master records")
        self.kpi_storerooms.set_value(str(total_storerooms))
        self.kpi_storerooms.set_subtitle(f"{active_storerooms} active stock locations")
        self.kpi_positions.set_value(str(stock_positions))
        self.kpi_low_stock.set_value(str(low_stock))
        self.kpi_reservations.set_value(str(open_reservations))
        self.kpi_awaiting.set_value(str(awaiting))
        self.kpi_receiving.set_value(str(receiving))
        self.kpi_on_order.set_value(f"{total_on_order:.3f}")

    def _populate_low_stock_table(self, rows) -> None:
        self.low_stock_table.setRowCount(min(len(rows), 8))
        for row_index, balance in enumerate(rows[:8]):
            values = (
                self._item_labels.get(balance.stock_item_id, balance.stock_item_id),
                self._storeroom_labels.get(balance.storeroom_id, balance.storeroom_id),
                f"{float(balance.available_qty or 0.0):.3f}",
                f"{float(balance.on_order_qty or 0.0):.3f}",
                "Reorder Required" if balance.reorder_required else "Unavailable",
            )
            for column, value in enumerate(values):
                self.low_stock_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _populate_queue_table(self, *, requisitions, purchase_orders) -> None:
        queue_rows: list[tuple[str, str, str, str, str, str]] = []
        for requisition in requisitions:
            if requisition.status not in {
                PurchaseRequisitionStatus.SUBMITTED,
                PurchaseRequisitionStatus.UNDER_REVIEW,
                PurchaseRequisitionStatus.APPROVED,
                PurchaseRequisitionStatus.PARTIALLY_SOURCED,
            }:
                continue
            queue_rows.append(
                (
                    _sort_key_for_row(requisition.updated_at, requisition.created_at),
                    "Requisition",
                    requisition.requisition_number,
                    humanize_status(requisition.status.value),
                    format_site_label(requisition.requesting_site_id, self._site_lookup),
                    self._storeroom_labels.get(requisition.requesting_storeroom_id, requisition.requesting_storeroom_id),
                )
            )
        for purchase_order in purchase_orders:
            if purchase_order.status not in {
                PurchaseOrderStatus.SUBMITTED,
                PurchaseOrderStatus.UNDER_REVIEW,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
                PurchaseOrderStatus.FULLY_RECEIVED,
            }:
                continue
            queue_rows.append(
                (
                    _sort_key_for_row(purchase_order.updated_at, purchase_order.created_at),
                    "Purchase Order",
                    purchase_order.po_number,
                    humanize_status(purchase_order.status.value),
                    format_site_label(purchase_order.site_id, self._site_lookup),
                    format_party_label(purchase_order.supplier_party_id, self._party_lookup),
                )
            )
        queue_rows.sort(key=lambda row: row[0], reverse=True)
        self.queue_table.setRowCount(min(len(queue_rows), 10))
        for row_index, queue_row in enumerate(queue_rows[:10]):
            for column, value in enumerate(queue_row[1:]):
                self.queue_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_dashboard()


def _sort_key_for_row(primary, fallback) -> str:
    value = primary or fallback
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


__all__ = ["InventoryDashboardTab"]
