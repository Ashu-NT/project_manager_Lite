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
from core.modules.inventory_procurement import InventoryReferenceService, InventoryService
from core.modules.inventory_procurement.domain import Storeroom
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.reference_support import (
    build_option_rows,
    build_party_lookup,
    build_site_lookup,
    format_party_label,
    format_site_label,
)
from ui.modules.inventory_procurement.storeroom_dialogs import StoreroomEditDialog
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class StoreroomsTab(QWidget):
    def __init__(
        self,
        *,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[Storeroom] = []
        self._site_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_storerooms()
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.sites_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("storeroomsHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#storeroomsHeaderCard {{
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
        eyebrow = QLabel("STOREROOM CONTROL")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Storerooms")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Operate stockholding locations against shared site references while keeping issue, transfer, and receiving rules inside the inventory domain."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        badge_layout = QVBoxLayout()
        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 storerooms")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.active_badge = QLabel("0 active")
        self.active_badge.setStyleSheet(dashboard_meta_chip_style())
        self.receiving_badge = QLabel("0 receiving enabled")
        self.receiving_badge.setStyleSheet(dashboard_meta_chip_style())
        self.access_badge = QLabel("Manage Enabled" if self._can_manage else "Read Only")
        self.access_badge.setStyleSheet(dashboard_meta_chip_style())
        for badge in (
            self.context_badge,
            self.count_badge,
            self.active_badge,
            self.receiving_badge,
            self.access_badge,
        ):
            badge_layout.addWidget(badge, 0, Qt.AlignRight)
        badge_layout.addStretch(1)
        header_layout.addLayout(badge_layout)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("storeroomsControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#storeroomsControlSurface {{
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
        self.search_edit.setPlaceholderText("Search code, name, type, status, or currency")
        self.site_filter = QComboBox()
        self.site_filter.addItem("All sites", None)
        self.active_filter = QComboBox()
        self.active_filter.addItem("All statuses", None)
        self.active_filter.addItem("Active only", True)
        self.active_filter.addItem("Inactive only", False)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.site_filter)
        filter_row.addWidget(self.active_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Storeroom")
        self.btn_edit = QPushButton("Edit Storeroom")
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
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Site", "Type", "Status", "Active"])
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
        detail_card.setObjectName("storeroomDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#storeroomDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_title = QLabel("Storeroom Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a storeroom")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        self.detail_site = QLabel("-")
        self.detail_manager = QLabel("-")
        self.detail_controls = QLabel("-")
        self.detail_currency = QLabel("-")
        self.detail_notes = QLabel("-")
        detail_grid.addWidget(QLabel("Site"), 0, 0)
        detail_grid.addWidget(self.detail_site, 0, 1)
        detail_grid.addWidget(QLabel("Manager"), 1, 0)
        detail_grid.addWidget(self.detail_manager, 1, 1)
        detail_grid.addWidget(QLabel("Controls"), 2, 0)
        detail_grid.addWidget(self.detail_controls, 2, 1)
        detail_grid.addWidget(QLabel("Currency"), 3, 0)
        detail_grid.addWidget(self.detail_currency, 3, 1)
        detail_grid.addWidget(QLabel("Notes"), 4, 0)
        detail_grid.addWidget(self.detail_notes, 4, 1)
        detail_layout.addLayout(detail_grid)
        detail_layout.addStretch(1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Storerooms", callback=self.reload_storerooms))
        self.btn_new.clicked.connect(make_guarded_slot(self, title="Storerooms", callback=self.create_storeroom))
        self.btn_edit.clicked.connect(make_guarded_slot(self, title="Storerooms", callback=self.edit_storeroom))
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Storerooms", callback=self.toggle_active)
        )
        self.search_edit.textChanged.connect(lambda _text: self.reload_storerooms())
        self.site_filter.currentIndexChanged.connect(lambda _index: self.reload_storerooms())
        self.active_filter.currentIndexChanged.connect(lambda _index: self.reload_storerooms())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_storerooms(self) -> None:
        selected_id = self._selected_storeroom_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            parties = self._reference_service.list_business_parties(active_only=None)
            self._site_lookup = build_site_lookup(sites)
            self._party_lookup = build_party_lookup(parties)
            self._reload_site_filter()
            self._rows = self._inventory_service.search_storerooms(
                search_text=self.search_text,
                active_only=self._selected_active_filter(),
                site_id=self._selected_site_filter(),
            )
            context_label = self._context_label()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Storerooms", str(exc))
            self._rows = []
            self._site_lookup = {}
            self._party_lookup = {}
            context_label = "-"
        except Exception as exc:
            QMessageBox.critical(self, "Storerooms", f"Failed to load storerooms: {exc}")
            self._rows = []
            self._site_lookup = {}
            self._party_lookup = {}
            context_label = "-"
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row, storeroom in enumerate(self._rows):
            values = (
                storeroom.storeroom_code,
                storeroom.name,
                format_site_label(storeroom.site_id, self._site_lookup),
                storeroom.storeroom_type or "-",
                storeroom.status,
                "Yes" if storeroom.is_active else "No",
            )
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if col == 5:
                    table_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, table_item)
            self.table.item(row, 0).setData(Qt.UserRole, storeroom.id)
            if selected_id and storeroom.id == selected_id:
                selected_row = row
        self._update_badges(context_label=context_label)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
            self._populate_details(None)
        self._sync_actions()

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip()

    def create_storeroom(self) -> None:
        dialog = StoreroomEditDialog(
            site_options=self._site_options(),
            manager_options=self._party_options(),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._inventory_service.create_storeroom(
                    storeroom_code=dialog.storeroom_code,
                    name=dialog.name,
                    site_id=dialog.site_id,
                    status=dialog.status,
                    storeroom_type=dialog.storeroom_type,
                    default_currency_code=dialog.default_currency_code,
                    manager_party_id=dialog.manager_party_id,
                    is_internal_supplier=dialog.is_internal_supplier,
                    allows_issue=dialog.allows_issue,
                    allows_transfer=dialog.allows_transfer,
                    allows_receiving=dialog.allows_receiving,
                    notes=dialog.notes,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Storerooms", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Storerooms", f"Failed to create storeroom: {exc}")
                return
            break
        self.reload_storerooms()

    def edit_storeroom(self) -> None:
        storeroom = self._selected_storeroom()
        if storeroom is None:
            QMessageBox.information(self, "Storerooms", "Please select a storeroom.")
            return
        dialog = StoreroomEditDialog(
            storeroom=storeroom,
            site_options=self._site_options(),
            manager_options=self._party_options(),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._inventory_service.update_storeroom(
                    storeroom.id,
                    storeroom_code=dialog.storeroom_code,
                    name=dialog.name,
                    site_id=dialog.site_id,
                    status=dialog.status,
                    storeroom_type=dialog.storeroom_type,
                    default_currency_code=dialog.default_currency_code,
                    manager_party_id=dialog.manager_party_id,
                    is_internal_supplier=dialog.is_internal_supplier,
                    allows_issue=dialog.allows_issue,
                    allows_transfer=dialog.allows_transfer,
                    allows_receiving=dialog.allows_receiving,
                    notes=dialog.notes,
                    expected_version=storeroom.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Storerooms", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_storerooms()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Storerooms", f"Failed to update storeroom: {exc}")
                return
            break
        self.reload_storerooms()

    def toggle_active(self) -> None:
        storeroom = self._selected_storeroom()
        if storeroom is None:
            QMessageBox.information(self, "Storerooms", "Please select a storeroom.")
            return
        try:
            self._inventory_service.update_storeroom(
                storeroom.id,
                is_active=not storeroom.is_active,
                expected_version=storeroom.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Storerooms", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_storerooms()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Storerooms", f"Failed to update storeroom: {exc}")
            return
        self.reload_storerooms()

    def _selected_active_filter(self) -> bool | None:
        return self.active_filter.currentData()

    def _selected_site_filter(self) -> str | None:
        value = self.site_filter.currentData()
        if value is None:
            return None
        return str(value).strip() or None

    def _reload_site_filter(self) -> None:
        selected = self._selected_site_filter()
        self.site_filter.blockSignals(True)
        self.site_filter.clear()
        self.site_filter.addItem("All sites", None)
        for label, site_id in self._site_options():
            self.site_filter.addItem(label, site_id)
        if selected:
            index = self.site_filter.findData(selected)
            if index >= 0:
                self.site_filter.setCurrentIndex(index)
        self.site_filter.blockSignals(False)

    def _site_options(self) -> list[tuple[str, str]]:
        labels_by_id = {
            site_id: format_site_label(site_id, self._site_lookup)
            for site_id in self._site_lookup.keys()
        }
        return build_option_rows(labels_by_id, include_blank=False)

    def _party_options(self) -> list[tuple[str, str]]:
        labels_by_id = {
            party_id: format_party_label(party_id, self._party_lookup)
            for party_id in self._party_lookup.keys()
        }
        return build_option_rows(labels_by_id, include_blank=True)

    def _selected_storeroom_id(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return str(selected[0].data(Qt.UserRole) or "").strip() or None

    def _selected_storeroom(self) -> Storeroom | None:
        selected_id = self._selected_storeroom_id()
        if not selected_id:
            return None
        return next((row for row in self._rows if row.id == selected_id), None)

    def _sync_actions(self) -> None:
        has_selection = self._selected_storeroom() is not None
        self.btn_edit.setEnabled(self._can_manage and has_selection)
        self.btn_toggle_active.setEnabled(self._can_manage and has_selection)

    def _update_badges(self, *, context_label: str) -> None:
        active_count = sum(1 for row in self._rows if row.is_active)
        receiving_count = sum(1 for row in self._rows if row.allows_receiving)
        self.context_badge.setText(f"Context: {context_label}")
        self.count_badge.setText(f"{len(self._rows)} storerooms")
        self.active_badge.setText(f"{active_count} active")
        self.receiving_badge.setText(f"{receiving_count} receiving enabled")

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _on_inventory_changed(self, _entity_id: str) -> None:
        self.reload_storerooms()

    def _on_selection_changed(self) -> None:
        self._populate_details(self._selected_storeroom())
        self._sync_actions()

    def _populate_details(self, storeroom: Storeroom | None) -> None:
        if storeroom is None:
            self.detail_name.setText("Select a storeroom")
            self.detail_status.setText("-")
            self.detail_site.setText("-")
            self.detail_manager.setText("-")
            self.detail_controls.setText("-")
            self.detail_currency.setText("-")
            self.detail_notes.setText("-")
            return
        self.detail_name.setText(f"{storeroom.storeroom_code} - {storeroom.name}")
        self.detail_status.setText(f"{storeroom.status} | Type: {storeroom.storeroom_type or '-'}")
        self.detail_site.setText(format_site_label(storeroom.site_id, self._site_lookup))
        self.detail_manager.setText(format_party_label(storeroom.manager_party_id, self._party_lookup))
        controls = []
        if storeroom.allows_issue:
            controls.append("Issue")
        if storeroom.allows_transfer:
            controls.append("Transfer")
        if storeroom.allows_receiving:
            controls.append("Receiving")
        if storeroom.is_internal_supplier:
            controls.append("Internal supplier")
        self.detail_controls.setText(", ".join(controls) or "-")
        self.detail_currency.setText(storeroom.default_currency_code or "-")
        self.detail_notes.setText(storeroom.notes or "-")


__all__ = ["StoreroomsTab"]
