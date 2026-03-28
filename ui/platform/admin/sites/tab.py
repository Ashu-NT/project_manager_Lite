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
from core.platform.org.domain import Site
from core.platform.notifications.domain_events import domain_events
from core.platform.org import SiteService
from ui.platform.admin.sites.dialogs import SiteEditDialog
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.admin.shared_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class SiteAdminTab(QWidget):
    def __init__(
        self,
        site_service: SiteService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._site_service = site_service
        self._user_session = user_session
        self._can_manage_sites = has_permission(self._user_session, "settings.manage")
        self._rows: list[Site] = []
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
            context = self._site_service.get_context_organization()
            self._rows = self._site_service.list_sites()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Sites", str(exc))
            context_label = "-"
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Sites", f"Failed to load sites: {exc}")
            context_label = "-"
            self._rows = []
        else:
            context_label = context.display_name
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
                self._site_service.create_site(
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
            except ValidationError as exc:
                QMessageBox.warning(self, "Sites", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Sites", f"Failed to create site: {exc}")
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
                self._site_service.update_site(
                    site.id,
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
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Sites", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_sites()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Sites", f"Failed to update site: {exc}")
                return
            break
        self.reload_sites()

    def toggle_active(self) -> None:
        site = self._selected_site()
        if site is None:
            QMessageBox.information(self, "Sites", "Please select a site.")
            return
        try:
            self._site_service.update_site(
                site.id,
                is_active=not site.is_active,
                expected_version=site.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Sites", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Sites", f"Failed to update site: {exc}")
            return
        self.reload_sites()

    def _selected_site(self) -> Site | None:
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

    def _update_header_badges(self, rows: list[Site], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.site_context_badge.setText(f"Context: {context_label}")
        self.site_count_badge.setText(f"{len(rows)} sites")
        self.site_active_badge.setText(f"{active_count} active")

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
