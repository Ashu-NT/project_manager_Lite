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
    PlatformSiteDesktopApi,
    SiteCreateCommand,
    SiteDto,
    SiteUpdateCommand,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.notifications.domain_events import domain_events
from src.ui.platform.dialogs.admin.sites.dialogs import SiteEditDialog
from src.ui.platform.widgets.admin_header import build_admin_header
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class SiteAdminTab(QWidget):
    def __init__(
        self,
        *,
        platform_site_api: PlatformSiteDesktopApi,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._platform_site_api = platform_site_api
        self._user_session = user_session
        self._can_manage_sites = has_permission(self._user_session, "settings.manage")
        self._rows: list[SiteDto] = []
        self._setup_ui()
        self.reload_sites()
        domain_events.sites_changed.connect(self._on_sites_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        access_label = "Manage Enabled" if self._can_manage_sites else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="siteAdminHeaderCard",
            eyebrow_text="SITE MASTER",
            title_text="Sites",
            subtitle_text="Manage shared site records for organization structure, workforce context, and future module integrations.",
            badge_specs=(
                ("site_context_badge", "Context: -", "accent"),
                ("site_count_badge", "0 sites", "meta"),
                ("site_active_badge", "0 active", "meta"),
                ("site_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="siteAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_site", "New Site", "primary"),
                ToolbarButtonSpec("btn_edit_site", "Edit Site"),
                ToolbarButtonSpec("btn_toggle_active", "Toggle Active"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Code", "Name", "City", "Status", "Active"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
            ),
        )
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Sites", callback=self.reload_sites))
        self.btn_new_site.clicked.connect(make_guarded_slot(self, title="Sites", callback=self.create_site))
        self.btn_edit_site.clicked.connect(make_guarded_slot(self, title="Sites", callback=self.edit_site))
        self.btn_toggle_active.clicked.connect(make_guarded_slot(self, title="Sites", callback=self.toggle_active))
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_site, self.btn_edit_site, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage_sites, missing_permission="settings.manage")
        self._sync_actions()

    def reload_sites(self) -> None:
        try:
            context_result = self._platform_site_api.get_context()
            sites_result = self._platform_site_api.list_sites()
        except Exception as exc:
            QMessageBox.critical(self, "Sites", f"Failed to load sites: {exc}")
            context_label = "-"
            self._rows = []
        else:
            if context_result.ok and context_result.data is not None:
                context_label = context_result.data.display_name
            else:
                self._show_api_error(context_result.error)
                context_label = "-"
            if sites_result.ok and sites_result.data is not None:
                self._rows = list(sites_result.data)
            else:
                self._show_api_error(sites_result.error)
                self._rows = []
        self.table.setRowCount(len(self._rows))
        for row, site in enumerate(self._rows):
            values = (
                site.site_code,
                site.name,
                site.city or "-",
                site.status or "-",
                "Yes" if site.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, site.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows, context_label=context_label)
        self._sync_actions()

    def create_site(self) -> None:
        dlg = SiteEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                error = self._create_site_from_dialog(dlg)
            except Exception as exc:
                QMessageBox.critical(self, "Sites", f"Failed to create site: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category in {"validation", "conflict"}:
                    continue
                return
            break
        self.reload_sites()

    def edit_site(self) -> None:
        site = self._selected_site()
        if site is None:
            QMessageBox.information(self, "Sites", "Please select a site.")
            return
        dlg = SiteEditDialog(parent=self, site=site)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                error = self._update_site_from_dialog(site, dlg)
            except Exception as exc:
                QMessageBox.critical(self, "Sites", f"Failed to update site: {exc}")
                return
            if error is not None:
                self._show_api_error(error)
                if error.category == "conflict":
                    self.reload_sites()
                    return
                if error.category == "validation":
                    continue
                return
            break
        self.reload_sites()

    def toggle_active(self) -> None:
        site = self._selected_site()
        if site is None:
            QMessageBox.information(self, "Sites", "Please select a site.")
            return
        try:
            result = self._platform_site_api.update_site(
                SiteUpdateCommand(
                    site_id=site.id,
                    is_active=not site.is_active,
                    expected_version=site.version,
                )
            )
        except Exception as exc:
            QMessageBox.critical(self, "Sites", f"Failed to update site: {exc}")
            return
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_sites()

    def _selected_site(self) -> SiteDto | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        site_id = item.data(Qt.UserRole)
        for site in self._rows:
            if site.id == site_id:
                return site
        return None

    def _update_header_badges(self, rows: list[SiteDto], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.site_context_badge.setText(f"Context: {context_label}")
        self.site_count_badge.setText(f"{len(rows)} sites")
        self.site_active_badge.setText(f"{active_count} active")

    def _create_site_from_dialog(self, dlg: SiteEditDialog) -> DesktopApiError | None:
        result = self._platform_site_api.create_site(
            SiteCreateCommand(
                site_code=dlg.site_code,
                name=dlg.name,
                description=dlg.description,
                city=dlg.city,
                country=dlg.country,
                timezone_name=dlg.timezone_name,
                currency_code=dlg.currency_code,
                site_type=dlg.site_type,
                status=dlg.status,
                notes=dlg.notes,
                is_active=dlg.is_active,
            )
        )
        return None if result.ok else result.error

    def _update_site_from_dialog(self, site: SiteDto, dlg: SiteEditDialog) -> DesktopApiError | None:
        result = self._platform_site_api.update_site(
            SiteUpdateCommand(
                site_id=site.id,
                site_code=dlg.site_code,
                name=dlg.name,
                description=dlg.description,
                city=dlg.city,
                country=dlg.country,
                timezone_name=dlg.timezone_name,
                currency_code=dlg.currency_code,
                site_type=dlg.site_type,
                status=dlg.status,
                notes=dlg.notes,
                is_active=dlg.is_active,
                expected_version=site.version,
            )
        )
        return None if result.ok else result.error

    def _show_api_error(self, error: DesktopApiError | None) -> None:
        message = error.message if error is not None else "The platform site API did not return a result."
        QMessageBox.warning(self, "Sites", message)

    def _on_sites_changed(self, _site_id: str) -> None:
        self.reload_sites()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_sites()

    def _sync_actions(self) -> None:
        has_site = self._selected_site() is not None
        self.btn_new_site.setEnabled(self._can_manage_sites)
        self.btn_edit_site.setEnabled(self._can_manage_sites and has_site)
        self.btn_toggle_active.setEnabled(self._can_manage_sites and has_site)


__all__ = ["SiteAdminTab"]
