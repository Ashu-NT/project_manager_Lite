from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
    ModuleEntitlementDto,
    ModuleStatePatchCommand,
    PlatformRuntimeDesktopApi,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.notifications.domain_events import domain_events
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class ModuleLicensingTab(QWidget):
    def __init__(
        self,
        *,
        platform_runtime_api: PlatformRuntimeDesktopApi,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._platform_runtime_api = platform_runtime_api
        self._entitlements_by_code: dict[str, ModuleEntitlementDto] = {}
        self._user_session = user_session
        self._can_manage_modules = has_permission(self._user_session, "settings.manage")
        self._setup_ui()
        self.reload_modules()
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Module Setup")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Review licensed modules for this installation and control which business modules are enabled in the runtime."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        summary_row = QHBoxLayout()
        self.platform_base_badge = QLabel("Platform Base")
        self.context_badge = QLabel("Install Profile")
        self.licensed_badge = QLabel("0 licensed")
        self.runtime_badge = QLabel("0 runtime")
        self.lifecycle_badge = QLabel("0 alerts")
        self.planned_badge = QLabel("0 planned")
        for label in (
            self.platform_base_badge,
            self.context_badge,
            self.licensed_badge,
            self.runtime_badge,
            self.lifecycle_badge,
            self.planned_badge,
        ):
            label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
            summary_row.addWidget(label)
        summary_row.addStretch(1)
        root.addLayout(summary_row)

        build_admin_toolbar_surface(
            self,
            root,
            object_name="moduleAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_toggle_license", "Toggle License"),
                ToolbarButtonSpec("btn_toggle_enabled", "Toggle Enabled"),
                ToolbarButtonSpec("btn_change_status", "Change Status"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Module", "Stage", "Lifecycle", "Licensed", "Enabled", "Runtime", "Capabilities"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
            ),
        )
        root.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Modules", callback=self.reload_modules))
        self.btn_toggle_license.clicked.connect(
            make_guarded_slot(self, title="Modules", callback=self.toggle_license)
        )
        self.btn_toggle_enabled.clicked.connect(
            make_guarded_slot(self, title="Modules", callback=self.toggle_enabled)
        )
        self.btn_change_status.clicked.connect(
            make_guarded_slot(self, title="Modules", callback=self.change_status)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        apply_permission_hint(
            self.btn_toggle_license,
            allowed=self._can_manage_modules,
            missing_permission="settings.manage",
        )
        apply_permission_hint(
            self.btn_toggle_enabled,
            allowed=self._can_manage_modules,
            missing_permission="settings.manage",
        )
        apply_permission_hint(
            self.btn_change_status,
            allowed=self._can_manage_modules,
            missing_permission="settings.manage",
        )
        self._sync_actions()

    def reload_modules(self) -> None:
        result = self._platform_runtime_api.get_runtime_context()
        if not result.ok or result.data is None:
            self._show_api_error(result.error)
            entitlements: tuple[ModuleEntitlementDto, ...] = ()
            platform_capability_count = 0
            context_label = "Install Profile"
        else:
            context = result.data
            entitlements = context.entitlements
            platform_capability_count = len(context.platform_capabilities)
            context_label = context.context_label
        self._entitlements_by_code = {entitlement.module_code: entitlement for entitlement in entitlements}
        self.table.setRowCount(len(entitlements))
        for row_idx, entitlement in enumerate(entitlements):
            capabilities = ", ".join(entitlement.module.primary_capabilities) or "-"
            values = (
                entitlement.label,
                entitlement.stage.title(),
                entitlement.lifecycle_label,
                "Yes" if entitlement.licensed else "No",
                "Yes" if entitlement.enabled else "No",
                "Yes" if entitlement.runtime_enabled else "No",
                capabilities,
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, entitlement.module_code)
                self.table.setItem(row_idx, col, item)
        self.table.clearSelection()
        licensed_count = sum(1 for entitlement in entitlements if entitlement.licensed)
        runtime_count = sum(1 for entitlement in entitlements if entitlement.runtime_enabled)
        lifecycle_alert_count = sum(1 for entitlement in entitlements if entitlement.lifecycle_alert)
        planned_count = sum(1 for entitlement in entitlements if entitlement.planned)
        self.platform_base_badge.setText(f"Platform Base: {platform_capability_count} capabilities")
        self.context_badge.setText(f"Context: {context_label}")
        self.licensed_badge.setText(f"{licensed_count} licensed")
        self.runtime_badge.setText(f"{runtime_count} runtime")
        self.lifecycle_badge.setText(f"{lifecycle_alert_count} alerts")
        self.planned_badge.setText(f"{planned_count} planned")
        self._sync_actions()

    def toggle_license(self) -> None:
        entitlement = self._selected_entitlement()
        if entitlement is None:
            QMessageBox.information(self, "Modules", "Select a module first.")
            return
        if entitlement.planned:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} is still planned and cannot be licensed yet.",
            )
            return
        result = self._platform_runtime_api.patch_module_state(
            ModuleStatePatchCommand(
                module_code=entitlement.module_code,
                licensed=not entitlement.licensed,
                enabled=entitlement.enabled if entitlement.licensed else False,
            )
        )
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_modules()

    def toggle_enabled(self) -> None:
        entitlement = self._selected_entitlement()
        if entitlement is None:
            QMessageBox.information(self, "Modules", "Select a module first.")
            return
        if entitlement.planned:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} is still planned and cannot be enabled yet.",
            )
            return
        if not entitlement.licensed:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} must be licensed before it can be enabled.",
            )
            return
        if not entitlement.runtime_enabled and entitlement.lifecycle_status in {"suspended", "expired"}:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} is {entitlement.lifecycle_label.lower()}. Change its lifecycle status before enabling it.",
            )
            return
        result = self._platform_runtime_api.patch_module_state(
            ModuleStatePatchCommand(
                module_code=entitlement.module_code,
                enabled=not entitlement.enabled,
            )
        )
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_modules()

    def _selected_entitlement(self) -> ModuleEntitlementDto | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        module_code = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not module_code:
            return None
        return self._entitlements_by_code.get(module_code)

    def change_status(self) -> None:
        entitlement = self._selected_entitlement()
        if entitlement is None:
            QMessageBox.information(self, "Modules", "Select a module first.")
            return
        if entitlement.planned:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} is still planned and does not have an active lifecycle yet.",
            )
            return
        if not entitlement.licensed:
            QMessageBox.information(
                self,
                "Modules",
                f"{entitlement.label} must be licensed before its lifecycle can change.",
            )
            return

        options = ["Active", "Trial", "Suspended", "Expired"]
        current_label = entitlement.lifecycle_label
        try:
            current_index = options.index(current_label)
        except ValueError:
            current_index = 0
        selected, accepted = QInputDialog.getItem(
            self,
            "Module Lifecycle",
            f"Select lifecycle status for {entitlement.label}:",
            options,
            current_index,
            False,
        )
        if not accepted or not selected:
            return
        result = self._platform_runtime_api.patch_module_state(
            ModuleStatePatchCommand(
                module_code=entitlement.module_code,
                lifecycle_status=selected.strip().lower(),
            )
        )
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_modules()

    def _sync_actions(self) -> None:
        entitlement = self._selected_entitlement()
        actionable = bool(entitlement is not None and not entitlement.planned)
        self.btn_toggle_license.setEnabled(self._can_manage_modules and actionable)
        self.btn_toggle_enabled.setEnabled(
            self._can_manage_modules
            and actionable
            and entitlement is not None
            and entitlement.licensed
        )
        self.btn_change_status.setEnabled(
            self._can_manage_modules
            and actionable
            and entitlement is not None
            and entitlement.licensed
        )

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_modules()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_modules()

    def _show_api_error(self, error: DesktopApiError | None) -> None:
        message = error.message if error is not None else "The platform runtime API did not return a result."
        QMessageBox.warning(self, "Modules", message)


__all__ = ["ModuleLicensingTab"]
