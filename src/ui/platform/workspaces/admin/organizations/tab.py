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

from src.api.desktop.platform import (
    DesktopApiError,
    ModuleDto,
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
    PlatformRuntimeDesktopApi,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.notifications.domain_events import domain_events
from src.ui.platform.dialogs.admin.organizations.dialogs import OrganizationEditDialog
from src.ui.platform.widgets.admin_header import build_admin_header
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class OrganizationAdminTab(QWidget):
    def __init__(
        self,
        *,
        platform_runtime_api: PlatformRuntimeDesktopApi,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._platform_runtime_api = platform_runtime_api
        self._user_session = user_session
        self._can_manage_organizations = has_permission(self._user_session, "settings.manage")
        self._rows: list[OrganizationDto] = []
        self._setup_ui()
        self.reload_organizations()
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        access_label = "Manage Enabled" if self._can_manage_organizations else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="organizationAdminHeaderCard",
            eyebrow_text="ORGANIZATION",
            title_text="Organizations",
            subtitle_text="Maintain the current install organization profile and future hosting boundary.",
            badge_specs=(
                ("organization_scope_badge", "Install Profile", "accent"),
                ("organization_count_badge", "0 organizations", "meta"),
                ("organization_active_badge", "No active", "meta"),
                ("organization_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="organizationAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_organization", "New Organization", "primary"),
                ToolbarButtonSpec("btn_edit_organization", "Edit Organization"),
                ToolbarButtonSpec("btn_set_active", "Set Active"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Code", "Display Name", "Timezone", "Currency", "Active"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
            ),
        )
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
            result = self._platform_runtime_api.list_organizations(active_only=None)
        except Exception as exc:
            QMessageBox.critical(self, "Organizations", f"Failed to load organizations: {exc}")
            self._rows = []
        else:
            if result.ok and result.data is not None:
                self._rows = list(result.data)
            else:
                self._show_api_error(result.error)
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
        dlg = OrganizationEditDialog(
            parent=self,
            available_modules=self._available_modules_for_create(),
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                error = self._create_organization_from_dialog(dlg)
            except Exception as exc:
                QMessageBox.critical(self, "Organizations", f"Failed to create organization: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category in {"validation", "conflict"}:
                    continue
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
                error = self._update_organization(
                    organization.id,
                    organization_code=dlg.organization_code,
                    display_name=dlg.display_name,
                    timezone_name=dlg.timezone_name,
                    base_currency=dlg.base_currency,
                    is_active=dlg.is_active,
                    expected_version=organization.version,
                )
            except Exception as exc:
                QMessageBox.critical(self, "Organizations", f"Failed to update organization: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category == "conflict":
                    self.reload_organizations()
                    return
                if error.category == "validation":
                    continue
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
            error = self._set_active_organization(organization.id)
        except Exception as exc:
            QMessageBox.critical(self, "Organizations", f"Failed to set active organization: {exc}")
            return
        if error is not None:
            self._show_api_error(error)
            return
        self.reload_organizations()

    def _selected_organization(self) -> OrganizationDto | None:
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

    def _update_header_badges(self, rows: list[OrganizationDto]) -> None:
        active = next((row.display_name for row in rows if row.is_active), "No active")
        self.organization_count_badge.setText(f"{len(rows)} organizations")
        self.organization_active_badge.setText(active)

    def _create_organization_from_dialog(self, dlg: OrganizationEditDialog) -> DesktopApiError | None:
        result = self._platform_runtime_api.provision_organization(
            OrganizationProvisionCommand(
                organization_code=dlg.organization_code,
                display_name=dlg.display_name,
                timezone_name=dlg.timezone_name,
                base_currency=dlg.base_currency,
                is_active=dlg.is_active,
                initial_module_codes=tuple(dlg.initial_module_codes),
            )
        )
        return None if result.ok else result.error

    def _update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> DesktopApiError | None:
        result = self._platform_runtime_api.update_organization(
            OrganizationUpdateCommand(
                organization_id=organization_id,
                organization_code=organization_code,
                display_name=display_name,
                timezone_name=timezone_name,
                base_currency=base_currency,
                is_active=is_active,
                expected_version=expected_version,
            )
        )
        return None if result.ok else result.error

    def _set_active_organization(self, organization_id: str) -> DesktopApiError | None:
        result = self._platform_runtime_api.set_active_organization(organization_id)
        return None if result.ok else result.error

    def _available_modules_for_create(self) -> tuple[ModuleDto, ...]:
        result = self._platform_runtime_api.list_modules()
        if result.ok and result.data is not None:
            return result.data
        self._show_api_error(result.error)
        return ()

    def _show_api_error(self, error: DesktopApiError | None) -> None:
        message = error.message if error is not None else "The platform runtime API did not return a result."
        QMessageBox.warning(self, "Organizations", message)


__all__ = ["OrganizationAdminTab"]
