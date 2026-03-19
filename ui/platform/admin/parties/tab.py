from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
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

from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from core.platform.party import Party, PartyService
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.parties.dialogs import PartyEditDialog
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PartyAdminTab(QWidget):
    def __init__(
        self,
        party_service: PartyService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._party_service = party_service
        self._user_session = user_session
        self._can_manage_parties = has_permission(self._user_session, "settings.manage")
        self._rows: list[Party] = []
        self._setup_ui()
        self.reload_parties()
        domain_events.parties_changed.connect(self._on_parties_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("partyAdminHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#partyAdminHeaderCard {{
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
        eyebrow = QLabel("PARTY MASTER")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Parties")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel(
            "Manage shared supplier, manufacturer, vendor, contractor, and service-provider identities without duplicating master data across modules."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.party_context_badge = QLabel("Context: -")
        self.party_context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.party_count_badge = QLabel("0 parties")
        self.party_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.party_active_badge = QLabel("0 active")
        self.party_active_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_parties else "Read Only"
        self.party_access_badge = QLabel(access_label)
        self.party_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.party_context_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.party_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.party_active_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.party_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("partyAdminControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#partyAdminControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_party = QPushButton("New Party")
        self.btn_edit_party = QPushButton("Edit Party")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for btn in (self.btn_refresh, self.btn_new_party, self.btn_edit_party, self.btn_toggle_active):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new_party.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit_party.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar.addWidget(self.btn_new_party)
        toolbar.addWidget(self.btn_edit_party)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Type", "Country", "Active"])
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
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Parties", callback=self.reload_parties))
        self.btn_new_party.clicked.connect(make_guarded_slot(self, title="Parties", callback=self.create_party))
        self.btn_edit_party.clicked.connect(make_guarded_slot(self, title="Parties", callback=self.edit_party))
        self.btn_toggle_active.clicked.connect(make_guarded_slot(self, title="Parties", callback=self.toggle_active))
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_party, self.btn_edit_party, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage_parties, missing_permission="settings.manage")
        self._sync_actions()

    def reload_parties(self) -> None:
        try:
            context = self._party_service.get_context_organization()
            self._rows = self._party_service.list_parties()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Parties", str(exc))
            context_label = "-"
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Parties", f"Failed to load parties: {exc}")
            context_label = "-"
            self._rows = []
        else:
            context_label = context.display_name
        self.table.setRowCount(len(self._rows))
        for row, party in enumerate(self._rows):
            values = (
                party.party_code,
                party.party_name,
                party.party_type.value.replace("_", " ").title(),
                party.country or "-",
                "Yes" if party.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, party.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows, context_label=context_label)
        self._sync_actions()

    def create_party(self) -> None:
        dlg = PartyEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._party_service.create_party(
                    party_code=dlg.party_code,
                    party_name=dlg.party_name,
                    party_type=dlg.party_type,
                    legal_name=dlg.legal_name,
                    contact_name=dlg.contact_name,
                    country=dlg.country,
                    city=dlg.city,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Parties", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Parties", f"Failed to create party: {exc}")
                return
            break
        self.reload_parties()

    def edit_party(self) -> None:
        party = self._selected_party()
        if party is None:
            QMessageBox.information(self, "Parties", "Please select a party.")
            return
        dlg = PartyEditDialog(parent=self, party=party)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._party_service.update_party(
                    party.id,
                    party_code=dlg.party_code,
                    party_name=dlg.party_name,
                    party_type=dlg.party_type,
                    legal_name=dlg.legal_name,
                    contact_name=dlg.contact_name,
                    country=dlg.country,
                    city=dlg.city,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
                    expected_version=party.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Parties", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_parties()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Parties", f"Failed to update party: {exc}")
                return
            break
        self.reload_parties()

    def toggle_active(self) -> None:
        party = self._selected_party()
        if party is None:
            QMessageBox.information(self, "Parties", "Please select a party.")
            return
        try:
            self._party_service.update_party(
                party.id,
                is_active=not party.is_active,
                expected_version=party.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Parties", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Parties", f"Failed to update party: {exc}")
            return
        self.reload_parties()

    def _selected_party(self) -> Party | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        party_id = item.data(Qt.UserRole)
        for party in self._rows:
            if party.id == party_id:
                return party
        return None

    def _update_header_badges(self, rows: list[Party], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.party_context_badge.setText(f"Context: {context_label}")
        self.party_count_badge.setText(f"{len(rows)} parties")
        self.party_active_badge.setText(f"{active_count} active")

    def _on_parties_changed(self, _party_id: str) -> None:
        self.reload_parties()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_parties()

    def _sync_actions(self) -> None:
        has_party = self._selected_party() is not None
        self.btn_new_party.setEnabled(self._can_manage_parties)
        self.btn_edit_party.setEnabled(self._can_manage_parties and has_party)
        self.btn_toggle_active.setEnabled(self._can_manage_parties and has_party)


__all__ = ["PartyAdminTab"]
