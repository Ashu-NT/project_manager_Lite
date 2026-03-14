from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.modules.runtime import ModuleRuntimeService
from core.platform.notifications.domain_events import domain_events
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class ModuleLicensingTab(QWidget):
    def __init__(
        self,
        *,
        module_runtime_service: ModuleRuntimeService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._module_runtime_service = module_runtime_service
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
        self.enabled_badge = QLabel("0 enabled")
        self.planned_badge = QLabel("0 planned")
        for label in (
            self.platform_base_badge,
            self.context_badge,
            self.licensed_badge,
            self.enabled_badge,
            self.planned_badge,
        ):
            label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
            summary_row.addWidget(label)
        summary_row.addStretch(1)
        root.addLayout(summary_row)

        button_row = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_toggle_license = QPushButton("Toggle License")
        self.btn_toggle_enabled = QPushButton("Toggle Enabled")
        for button in (self.btn_refresh, self.btn_toggle_license, self.btn_toggle_enabled):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            button_row.addWidget(button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Module", "Stage", "Licensed", "Enabled", "Capabilities"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Modules", callback=self.reload_modules))
        self.btn_toggle_license.clicked.connect(
            make_guarded_slot(self, title="Modules", callback=self.toggle_license)
        )
        self.btn_toggle_enabled.clicked.connect(
            make_guarded_slot(self, title="Modules", callback=self.toggle_enabled)
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
        self._sync_actions()

    def reload_modules(self) -> None:
        entitlements = self._module_runtime_service.list_entitlements()
        self.table.setRowCount(len(entitlements))
        for row_idx, entitlement in enumerate(entitlements):
            capabilities = ", ".join(entitlement.module.primary_capabilities) or "-"
            values = (
                entitlement.label,
                entitlement.stage.title(),
                "Yes" if entitlement.licensed else "No",
                "Yes" if entitlement.enabled else "No",
                capabilities,
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, entitlement.code)
                self.table.setItem(row_idx, col, item)
        self.table.clearSelection()
        licensed_count = sum(1 for entitlement in entitlements if entitlement.licensed)
        enabled_count = sum(1 for entitlement in entitlements if entitlement.enabled)
        planned_count = sum(1 for entitlement in entitlements if entitlement.planned)
        self.platform_base_badge.setText(
            f"Platform Base: {len(self._module_runtime_service.list_platform_capabilities())} capabilities"
        )
        context_label = (
            self._module_runtime_service.current_context_label()
            if hasattr(self._module_runtime_service, "current_context_label")
            else "Install Profile"
        )
        self.context_badge.setText(f"Context: {context_label}")
        self.licensed_badge.setText(f"{licensed_count} licensed")
        self.enabled_badge.setText(f"{enabled_count} enabled")
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
        try:
            self._module_runtime_service.set_module_state(
                entitlement.code,
                licensed=not entitlement.licensed,
                enabled=entitlement.enabled if entitlement.licensed else False,
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Modules", str(exc))
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
        try:
            self._module_runtime_service.set_module_state(
                entitlement.code,
                enabled=not entitlement.enabled,
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Modules", str(exc))
            return
        self.reload_modules()

    def _selected_entitlement(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        module_code = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not module_code:
            return None
        return self._module_runtime_service.get_entitlement(module_code)

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

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_modules()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_modules()


__all__ = ["ModuleLicensingTab"]
