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
from core.modules.inventory_procurement import InventoryService, ItemMasterService, ReservationService
from core.modules.inventory_procurement.domain import StockReservation, StockReservationStatus
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.reservation.reservation_dialogs import (
    ReservationCreateDialog,
    ReservationIssueDialog,
)
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.procurement_support import (
    build_item_lookup,
    build_storeroom_lookup,
    format_date,
    format_item_label,
    format_quantity,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class ReservationsTab(QWidget):
    def __init__(
        self,
        *,
        reservation_service: ReservationService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._reservation_service = reservation_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[StockReservation] = []
        self._item_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_reservations()
        domain_events.inventory_reservations_changed.connect(self._on_inventory_changed)
        domain_events.inventory_balances_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryReservationsHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryReservationsHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("SUPPLY COMMITMENT")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Reservations")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Reserve stock against upstream demand references, then issue, release, or cancel from one operational queue."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 reservations")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.active_badge = QLabel("0 active")
        self.active_badge.setStyleSheet(dashboard_meta_chip_style())
        self.issued_badge = QLabel("0 issued")
        self.issued_badge.setStyleSheet(dashboard_meta_chip_style())
        self.selection_badge = QLabel("Selection: None")
        self.selection_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.count_badge,
            self.active_badge,
            self.issued_badge,
            self.selection_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryReservationControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryReservationControlSurface {{
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
        self.search_edit.setPlaceholderText("Search reservation number, source, or requester")
        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses", None)
        for status in ("ACTIVE", "PARTIALLY_ISSUED", "FULLY_ISSUED", "RELEASED", "CANCELLED"):
            self.status_filter.addItem(humanize_status(status), status)
        self.item_filter = QComboBox()
        self.item_filter.addItem("All items", None)
        self.storeroom_filter = QComboBox()
        self.storeroom_filter.addItem("All storerooms", None)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.item_filter)
        filter_row.addWidget(self.storeroom_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Reservation")
        self.btn_issue = QPushButton("Issue Reserved")
        self.btn_release = QPushButton("Release")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_issue, self.btn_release, self.btn_cancel, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_issue.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_release.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_cancel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_issue)
        action_row.addWidget(self.btn_release)
        action_row.addWidget(self.btn_cancel)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Reservation", "Status", "Item", "Storeroom", "Reserved", "Remaining", "Need By"]
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
        detail_card.setObjectName("inventoryReservationDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryReservationDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Reservation Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a reservation")
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
        self.detail_source = QLabel("-")
        self.detail_quantities = QLabel("-")
        self.detail_need_by = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Item"), 0, 0)
        detail_grid.addWidget(self.detail_item, 0, 1)
        detail_grid.addWidget(QLabel("Storeroom"), 1, 0)
        detail_grid.addWidget(self.detail_storeroom, 1, 1)
        detail_grid.addWidget(QLabel("Source"), 2, 0)
        detail_grid.addWidget(self.detail_source, 2, 1)
        detail_grid.addWidget(QLabel("Quantities"), 3, 0)
        detail_grid.addWidget(self.detail_quantities, 3, 1)
        detail_grid.addWidget(QLabel("Need By"), 4, 0)
        detail_grid.addWidget(self.detail_need_by, 4, 1)
        detail_grid.addWidget(QLabel("Notes"), 5, 0)
        detail_grid.addWidget(self.detail_notes, 5, 1)
        detail_layout.addLayout(detail_grid)
        detail_layout.addStretch(1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.search_edit.textChanged.connect(lambda _text: self.reload_reservations())
        self.status_filter.currentIndexChanged.connect(lambda _index: self.reload_reservations())
        self.item_filter.currentIndexChanged.connect(lambda _index: self.reload_reservations())
        self.storeroom_filter.currentIndexChanged.connect(lambda _index: self.reload_reservations())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Reservations", callback=self.reload_reservations))
        self.btn_new.clicked.connect(make_guarded_slot(self, title="Reservations", callback=self.create_reservation))
        self.btn_issue.clicked.connect(make_guarded_slot(self, title="Reservations", callback=self.issue_reservation))
        self.btn_release.clicked.connect(make_guarded_slot(self, title="Reservations", callback=self.release_reservation))
        self.btn_cancel.clicked.connect(make_guarded_slot(self, title="Reservations", callback=self.cancel_reservation))
        for button in (self.btn_new, self.btn_issue, self.btn_release, self.btn_cancel):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_reservations(self) -> None:
        selected_id = self._selected_reservation_id()
        try:
            items = self._item_service.list_items(active_only=None)
            storerooms = self._inventory_service.list_storerooms(active_only=None)
            self._item_lookup = build_item_lookup(items)
            self._storeroom_lookup = build_storeroom_lookup(storerooms)
            self._reload_filters()
            rows = self._reservation_service.list_reservations(
                stock_item_id=self._selected_item_filter(),
                storeroom_id=self._selected_storeroom_filter(),
                status=self._selected_status_filter(),
            )
            self._rows = self._apply_search_filter(rows)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Reservations", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Reservations", f"Failed to load reservations: {exc}")
            self._rows = []
        self._populate_table(selected_id=selected_id)
        self._update_badges()
        self._sync_actions()

    def create_reservation(self) -> None:
        if not self._can_manage:
            return
        dialog = ReservationCreateDialog(
            item_options=self._active_item_options(),
            storeroom_options=self._active_storeroom_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            reservation = self._reservation_service.create_reservation(
                stock_item_id=dialog.stock_item_id,
                storeroom_id=dialog.storeroom_id,
                reserved_qty=dialog.reserved_qty,
                need_by_date=dialog.need_by_date,
                source_reference_type=dialog.source_reference_type,
                source_reference_id=dialog.source_reference_id,
                notes=dialog.notes,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Reservations", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Reservations", f"Failed to create reservation: {exc}")
            return
        self.reload_reservations()
        self._select_reservation(reservation.id)

    def issue_reservation(self) -> None:
        reservation = self._selected_reservation()
        if reservation is None or not self._can_manage:
            return
        dialog = ReservationIssueDialog(
            reservation_number=reservation.reservation_number,
            remaining_qty=reservation.remaining_qty,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._reservation_service.issue_reserved_stock(
                reservation.id,
                quantity=dialog.quantity,
                note=dialog.note,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Reservations", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Reservations", f"Failed to issue reserved stock: {exc}")
            return
        self.reload_reservations()
        self._select_reservation(reservation.id)

    def release_reservation(self) -> None:
        reservation = self._selected_reservation()
        if reservation is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Release Reservation",
            f"Release remaining quantity on {reservation.reservation_number}?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._reservation_service.release_reservation(reservation.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Reservations", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Reservations", f"Failed to release reservation: {exc}")
            return
        self.reload_reservations()
        self._select_reservation(reservation.id)

    def cancel_reservation(self) -> None:
        reservation = self._selected_reservation()
        if reservation is None or not self._can_manage:
            return
        answer = QMessageBox.question(
            self,
            "Cancel Reservation",
            f"Cancel {reservation.reservation_number} and return remaining quantity to availability?",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self._reservation_service.cancel_reservation(reservation.id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Reservations", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Reservations", f"Failed to cancel reservation: {exc}")
            return
        self.reload_reservations()
        self._select_reservation(reservation.id)

    def _apply_search_filter(self, rows: list[StockReservation]) -> list[StockReservation]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[StockReservation] = []
        for row in rows:
            haystacks = (
                row.reservation_number,
                row.source_reference_type,
                row.source_reference_id,
                row.requested_by_username,
                row.status.value,
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, reservation in enumerate(self._rows):
            values = (
                reservation.reservation_number,
                humanize_status(reservation.status.value),
                format_item_label(reservation.stock_item_id, self._item_lookup),
                format_storeroom_label(reservation.storeroom_id, self._storeroom_lookup),
                format_quantity(reservation.reserved_qty),
                format_quantity(reservation.remaining_qty),
                format_date(reservation.need_by_date),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, reservation.id)
                self.table.setItem(row_index, column, item)
            if reservation.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        self._update_detail(self._selected_reservation())
        self._sync_actions()

    def _update_detail(self, reservation: StockReservation | None) -> None:
        if reservation is None:
            self.detail_name.setText("Select a reservation")
            self.detail_status.setText("-")
            self.detail_item.setText("-")
            self.detail_storeroom.setText("-")
            self.detail_source.setText("-")
            self.detail_quantities.setText("-")
            self.detail_need_by.setText("-")
            self.detail_notes.setText("-")
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(reservation.reservation_number)
        self.detail_status.setText(
            f"{humanize_status(reservation.status.value)} | Requester: {reservation.requested_by_username or '-'}"
        )
        self.detail_item.setText(format_item_label(reservation.stock_item_id, self._item_lookup))
        self.detail_storeroom.setText(format_storeroom_label(reservation.storeroom_id, self._storeroom_lookup))
        self.detail_source.setText(f"{reservation.source_reference_type}: {reservation.source_reference_id}")
        self.detail_quantities.setText(
            f"Reserved {format_quantity(reservation.reserved_qty)} | "
            f"Issued {format_quantity(reservation.issued_qty)} | "
            f"Remaining {format_quantity(reservation.remaining_qty)}"
        )
        self.detail_need_by.setText(format_date(reservation.need_by_date))
        self.detail_notes.setText(reservation.notes or "-")
        self.selection_badge.setText(f"Selection: {reservation.reservation_number}")

    def _update_badges(self) -> None:
        active = sum(
            1
            for row in self._rows
            if row.status in {StockReservationStatus.ACTIVE, StockReservationStatus.PARTIALLY_ISSUED}
        )
        issued = sum(
            1
            for row in self._rows
            if row.status in {StockReservationStatus.PARTIALLY_ISSUED, StockReservationStatus.FULLY_ISSUED}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} reservations")
        self.active_badge.setText(f"{active} active")
        self.issued_badge.setText(f"{issued} issued")

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

    def _selected_reservation_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_reservation(self) -> StockReservation | None:
        selected_id = self._selected_reservation_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    def _select_reservation(self, reservation_id: str) -> None:
        for row_index, row in enumerate(self._rows):
            if row.id == reservation_id:
                self.table.selectRow(row_index)
                return

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    def _selected_status_filter(self) -> str | None:
        value = self.status_filter.currentData()
        return str(value).strip() if value else None

    def _selected_item_filter(self) -> str | None:
        value = self.item_filter.currentData()
        return str(value).strip() if value else None

    def _selected_storeroom_filter(self) -> str | None:
        value = self.storeroom_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        reservation = self._selected_reservation()
        can_operate = bool(
            reservation is not None
            and reservation.status in {StockReservationStatus.ACTIVE, StockReservationStatus.PARTIALLY_ISSUED}
            and float(reservation.remaining_qty or 0.0) > 0
        )
        self.btn_issue.setEnabled(self._can_manage and can_operate)
        self.btn_release.setEnabled(self._can_manage and can_operate)
        self.btn_cancel.setEnabled(self._can_manage and can_operate)

    def _context_label(self) -> str:
        parts = [humanize_status(self._selected_status_filter() or "all")]
        item_id = self._selected_item_filter()
        if item_id:
            parts.append(format_item_label(item_id, self._item_lookup))
        return " | ".join(parts)

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_reservations()


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


__all__ = ["ReservationsTab"]
