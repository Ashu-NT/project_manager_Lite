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
from core.platform.common.models import Organization
from core.platform.notifications.domain_events import domain_events
from core.platform.org import OrganizationService
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.organizations.dialogs import OrganizationEditDialog
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class OrganizationAdminTab(QWidget):
    def __init__(
        self,
        organization_service: OrganizationService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._organization_service = organization_service
        self._user_session = user_session
        self._can_manage_organizations = has_permission(self._user_session, "settings.manage")
        self._rows: list[Organization] = []
        self._setup_ui()
        self.reload_organizations()
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("organizationAdminHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#organizationAdminHeaderCard {{
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
        eyebrow = QLabel("ORGANIZATION")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Organizations")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel("Maintain the current install organization profile and future hosting boundary.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.organization_scope_badge = QLabel("Install Profile")
        self.organization_scope_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.organization_count_badge = QLabel("0 organizations")
        self.organization_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.organization_active_badge = QLabel("No active")
        self.organization_active_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_organizations else "Read Only"
        self.organization_access_badge = QLabel(access_label)
        self.organization_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.organization_scope_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.organization_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.organization_active_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.organization_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("organizationAdminControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#organizationAdminControlSurface {{
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
        self.btn_new_organization = QPushButton("New Organization")
        self.btn_edit_organization = QPushButton("Edit Organization")
        self.btn_set_active = QPushButton("Set Active")
        for btn in (
            self.btn_refresh,
            self.btn_new_organization,
            self.btn_edit_organization,
            self.btn_set_active,
        ):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new_organization.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit_organization.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_set_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar.addWidget(self.btn_new_organization)
        toolbar.addWidget(self.btn_edit_organization)
        toolbar.addWidget(self.btn_set_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Code", "Display Name", "Timezone", "Currency", "Active"])
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

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Organizations", callback=self.reload_organizations))
        self.btn_new_organization.clicked.connect(
            make_guarded_slot(self, title="Organizations", callback=self.create_organization)
        )
        self.btn_edit_organization.clicked.connect(
            make_guarded_slot(self, title="Organizations", callback=self.edit_organization)
        )
        self.btn_set_active.clicked.connect(
            make_guarded_slot(self, title="Organizations", callback=self.set_active_organization)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        apply_permission_hint(
            self.btn_new_organization,
            allowed=self._can_manage_organizations,
            missing_permission="settings.manage",
        )
        apply_permission_hint(
            self.btn_edit_organization,
            allowed=self._can_manage_organizations,
            missing_permission="settings.manage",
        )
        apply_permission_hint(
            self.btn_set_active,
            allowed=self._can_manage_organizations,
            missing_permission="settings.manage",
        )
        self._sync_actions()

    def reload_organizations(self) -> None:
        try:
            self._rows = self._organization_service.list_organizations()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Organizations", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Organizations", f"Failed to load organizations: {exc}")
            self._rows = []
        self.table.setRowCount(len(self._rows))
        for row, organization in enumerate(self._rows):
            values = (
                organization.organization_code,
                organization.display_name,
                organization.timezone_name,
                organization.base_currency,
                "Yes" if organization.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, organization.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows)
        self._sync_actions()

    def create_organization(self) -> None:
        dlg = OrganizationEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._organization_service.create_organization(
                    organization_code=dlg.organization_code,
                    display_name=dlg.display_name,
                    timezone_name=dlg.timezone_name,
                    base_currency=dlg.base_currency,
                    is_active=dlg.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Organizations", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Organizations", f"Failed to create organization: {exc}")
                return
            break
        self.reload_organizations()

    def edit_organization(self) -> None:
        organization = self._selected_organization()
        if organization is None:
            QMessageBox.information(self, "Organizations", "Please select an organization.")
            return
        dlg = OrganizationEditDialog(parent=self, organization=organization)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._organization_service.update_organization(
                    organization.id,
                    organization_code=dlg.organization_code,
                    display_name=dlg.display_name,
                    timezone_name=dlg.timezone_name,
                    base_currency=dlg.base_currency,
                    is_active=dlg.is_active,
                    expected_version=organization.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Organizations", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_organizations()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Organizations", f"Failed to update organization: {exc}")
                return
            break
        self.reload_organizations()

    def set_active_organization(self) -> None:
        organization = self._selected_organization()
        if organization is None:
            QMessageBox.information(self, "Organizations", "Please select an organization.")
            return
        if organization.is_active:
            return
        try:
            self._organization_service.set_active_organization(organization.id)
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Organizations", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Organizations", f"Failed to set active organization: {exc}")
            return
        self.reload_organizations()

    def _selected_organization(self) -> Organization | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        organization_id = item.data(Qt.UserRole)
        for organization in self._rows:
            if organization.id == organization_id:
                return organization
        return None

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_organizations()

    def _sync_actions(self) -> None:
        organization = self._selected_organization()
        has_organization = organization is not None
        self.btn_new_organization.setEnabled(self._can_manage_organizations)
        self.btn_edit_organization.setEnabled(self._can_manage_organizations and has_organization)
        self.btn_set_active.setEnabled(
            self._can_manage_organizations
            and has_organization
            and organization is not None
            and not organization.is_active
        )

    def _update_header_badges(self, rows: list[Organization]) -> None:
        active = next((row.display_name for row in rows if row.is_active), "No active")
        self.organization_count_badge.setText(f"{len(rows)} organizations")
        self.organization_active_badge.setText(active)


__all__ = ["OrganizationAdminTab"]
