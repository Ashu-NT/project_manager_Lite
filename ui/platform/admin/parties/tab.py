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

from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.party import Party, PartyService
from ui.platform.admin.parties.dialogs import PartyEditDialog
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.admin.shared_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
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

        access_label = "Manage Enabled" if self._can_manage_parties else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="partyAdminHeaderCard",
            eyebrow_text="PARTY MASTER",
            title_text="Parties",
            subtitle_text="Manage shared supplier, manufacturer, vendor, contractor, and service-provider identities without duplicating master data across modules.",
            badge_specs=(
                ("party_context_badge", "Context: -", "accent"),
                ("party_count_badge", "0 parties", "meta"),
                ("party_active_badge", "0 active", "meta"),
                ("party_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="partyAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_party", "New Party", "primary"),
                ToolbarButtonSpec("btn_edit_party", "Edit Party"),
                ToolbarButtonSpec("btn_toggle_active", "Toggle Active"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Code", "Name", "Type", "Country", "Active"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
            ),
        )
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
