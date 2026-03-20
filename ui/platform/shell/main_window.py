# ui/platform/shell/main_window.py
from __future__ import annotations

import os

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from application.platform import resolve_platform_runtime_application_service
from core.platform.auth import UserSessionContext
from core.platform.notifications.domain_events import domain_events
from infra.platform.update import check_for_updates, default_update_manifest_source
from infra.platform.version import get_app_version
from ui.platform.shell import NavigationEntry, NavigationModule, ShellNavigation, build_workspace_definitions
from ui.platform.settings import MainWindowSettingsStore
from ui.platform.shared.async_job import JobUiConfig, start_async_job
from ui.platform.shared.styles.theme import apply_app_style
from ui.platform.shared.styles.theme_refresh import refresh_widget_theme
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MainWindow(QMainWindow):
    _NAVIGATION_AUTO_HIDE_WIDTH = 1000

    def __init__(self, services: dict[str, object], parent: QWidget | None = None):
        super().__init__(parent)
        self.services: dict[str, object] = services
        self._user_session: UserSessionContext | None = services.get("user_session")  # type: ignore[assignment]
        self._platform_runtime_application_service = resolve_platform_runtime_application_service(
            platform_runtime_application_service=services.get("platform_runtime_application_service"),
            module_runtime_service=services.get("module_runtime_service"),
            module_catalog_service=services.get("module_catalog_service"),
            organization_service=services.get("organization_service"),
        )
        self._settings_store = MainWindowSettingsStore()
        self._navigation_auto_hidden = False
        self._navigation_preferred_visible = True
        self._module_refresh_pending = False
        default_theme = os.getenv("PM_THEME", "light").strip().lower()
        self._theme_mode: str = self._settings_store.load_theme_mode(default_mode=default_theme)
        os.environ["PM_THEME"] = self._theme_mode

        self.setWindowTitle("TECHASH Enterprise")
        self.resize(CFG.DEFAULT_WINDOW_SIZE)
        self.setMinimumSize(CFG.MIN_WINDOW_SIZE)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        header = QWidget()
        header.setObjectName("shellHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(CFG.SPACING_SM)
        self.btn_toggle_navigation = QPushButton("Hide Menu")
        self.btn_toggle_navigation.clicked.connect(self._toggle_navigation_visibility)
        header_layout.addWidget(self.btn_toggle_navigation)
        self.app_label = QLabel("TECHASH Enterprise")
        self.app_label.setObjectName("shellHeaderTitle")
        header_layout.addWidget(self.app_label)
        header_layout.addStretch()
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeSwitch")
        self.theme_combo.setEditable(False)
        self.theme_combo.addItem("Dark", userData="dark")
        self.theme_combo.addItem("Light", userData="light")
        idx = self.theme_combo.findData(self._theme_mode)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        header_layout.addWidget(self.theme_combo)
        principal = self._user_session.principal if self._user_session else None
        if principal is not None:
            label = principal.display_name or principal.username
            self.user_label = QLabel(label)
            self.user_label.setObjectName("shellUserLabel")
            header_layout.addWidget(self.user_label)
        header.setStyleSheet(
            f"""
            QWidget#shellHeader {{
                background: transparent;
            }}
            QLabel#shellHeaderTitle {{
                color: {CFG.COLOR_TEXT_PRIMARY};
                font-size: 11pt;
                font-weight: 700;
            }}
            QLabel#shellUserLabel {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 9pt;
                font-weight: 600;
            }}
            """
        )
        layout.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(CFG.SPACING_MD)

        self.shell_navigation = ShellNavigation(parent=self)
        self.shell_navigation.workspace_selected.connect(self._on_navigation_selected)
        body_layout.addWidget(self.shell_navigation)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("workspaceStack")
        self.tabs.tabBar().hide()
        self.tabs.setStyleSheet("QTabWidget#workspaceStack::pane { border: 0; }")
        body_layout.addWidget(self.tabs, 1)

        layout.addWidget(body, 1)
        self._build_tabs()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.shell_navigation.set_current_index(self.tabs.currentIndex())
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

        self.setCentralWidget(central)
        self._restore_persisted_state()
        self._sync_navigation_responsiveness()
        self._run_startup_update_check()

    def _build_tabs(self) -> None:
        navigation_entries: list[NavigationEntry] = []
        for workspace in build_workspace_definitions(
            services=self.services,
            settings_store=self._settings_store,
            user_session=self._user_session,
            parent=self,
        ):
            tab_index = self.tabs.addTab(workspace.widget, workspace.label)
            navigation_entries.append(
                NavigationEntry(
                    module_code=workspace.module_code,
                    module_label=workspace.module_label,
                    group_label=workspace.group_label,
                    label=workspace.label,
                    tab_index=tab_index,
                )
            )

        self.shell_navigation.set_entries(
            navigation_entries,
            modules=self._build_navigation_modules(),
        )
        self.shell_navigation.set_current_index(self.tabs.currentIndex())
        self._sync_shell_context()
        has_navigation = self.tabs.count() > 0
        self.btn_toggle_navigation.setVisible(has_navigation)
        self._set_navigation_visible(
            has_navigation and self._navigation_preferred_visible and not self._navigation_auto_hidden
        )

    def _rebuild_tabs(self, current_index: int) -> None:
        updates_enabled = self.updatesEnabled()
        tab_updates_enabled = self.tabs.updatesEnabled()
        navigation_updates_enabled = self.shell_navigation.updatesEnabled()
        orphaned_widgets: list[QWidget] = []
        self.setUpdatesEnabled(False)
        self.tabs.setUpdatesEnabled(False)
        self.shell_navigation.setUpdatesEnabled(False)
        tabs_blocker = QSignalBlocker(self.tabs)
        try:
            while self.tabs.count() > 0:
                widget = self.tabs.widget(0)
                self.tabs.removeTab(0)
                if widget is not None:
                    orphaned_widgets.append(widget)
            self._build_tabs()
            if self.tabs.count():
                safe_index = max(0, min(current_index, self.tabs.count() - 1))
                self.tabs.setCurrentIndex(safe_index)
                self.shell_navigation.set_current_index(self.tabs.currentIndex())
            self._sync_navigation_responsiveness()
        finally:
            for widget in orphaned_widgets:
                widget.deleteLater()
            del tabs_blocker
            self.shell_navigation.setUpdatesEnabled(navigation_updates_enabled)
            self.tabs.setUpdatesEnabled(tab_updates_enabled)
            self.setUpdatesEnabled(updates_enabled)
            self.update()

    def _on_theme_changed(self, _index: int) -> None:
        mode = self.theme_combo.currentData()
        if not mode or mode == self._theme_mode:
            return

        previous_mode = self._theme_mode
        self._theme_mode = mode
        os.environ["PM_THEME"] = mode
        self._settings_store.save_theme_mode(mode)

        app = QApplication.instance()
        self.setUpdatesEnabled(False)
        try:
            if app is not None:
                apply_app_style(app, mode=mode)
            refresh_widget_theme(
                self,
                previous_mode=previous_mode,
                next_mode=mode,
            )
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def _restore_persisted_state(self) -> None:
        geometry = self._settings_store.load_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        if self.tabs.count():
            saved_index = self._settings_store.load_tab_index(default_index=0)
            safe_index = max(0, min(saved_index, self.tabs.count() - 1))
            self.tabs.setCurrentIndex(safe_index)

    def _run_startup_update_check(self) -> None:
        if not self._settings_store.load_update_auto_check(default_enabled=False):
            return
        manifest = self._settings_store.load_update_manifest_url(
            default_url=default_update_manifest_source()
        )
        if not manifest:
            return
        channel = self._settings_store.load_update_channel(default_channel="stable")

        def _work(token, progress):
            token.raise_if_cancelled()
            return check_for_updates(
                current_version=get_app_version(),
                channel=channel,
                manifest_source=manifest,
            )

        def _on_success(result) -> None:
            if not getattr(result, "update_available", False):
                return
            latest = getattr(result, "latest", None)
            QMessageBox.information(
                self,
                "Update Available",
                (
                    f"{result.message}\n\n"
                    f"Channel: {result.channel}\n"
                    f"Download: {getattr(latest, 'url', None) or 'N/A'}"
                ),
            )

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Update Check",
                label="Checking for updates...",
                show_progress=False,
            ),
            work=_work,
            on_success=_on_success,
        )

    def _on_tab_changed(self, index: int) -> None:
        if index >= 0:
            self.shell_navigation.set_current_index(index)
            self._settings_store.save_tab_index(index)

    def _on_navigation_selected(self, index: int) -> None:
        if 0 <= index < self.tabs.count() and index != self.tabs.currentIndex():
            self.tabs.setCurrentIndex(index)

    def focus_workspace(self, label: str) -> bool:
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == label:
                self.tabs.setCurrentIndex(index)
                self.shell_navigation.set_current_index(index)
                return True
        return False

    def _toggle_navigation_visibility(self) -> None:
        self._navigation_auto_hidden = False
        self._navigation_preferred_visible = not self.shell_navigation.isVisible()
        self._set_navigation_visible(self._navigation_preferred_visible)

    def _sync_shell_context(self) -> None:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "shell_summary"):
            self.shell_navigation.set_module_summary(None)
            return
        self.shell_navigation.set_module_summary(service.shell_summary())

    def _build_navigation_modules(self) -> list[NavigationModule]:
        modules = [NavigationModule(code="platform", label="Platform", enabled=True)]
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "list_modules") or not hasattr(service, "is_enabled"):
            modules.append(
                NavigationModule(code="project_management", label="Project Management", enabled=True)
            )
            return modules

        for module in service.list_modules():
            modules.append(
                NavigationModule(
                    code=module.code,
                    label=module.label,
                    enabled=bool(service.is_enabled(module.code)),
                )
            )
        return modules

    def _set_navigation_visible(self, visible: bool) -> None:
        can_show_navigation = self.tabs.count() > 0
        should_show = bool(visible and can_show_navigation)
        self.shell_navigation.setVisible(should_show)
        self.btn_toggle_navigation.setVisible(can_show_navigation)
        self.btn_toggle_navigation.setText("Hide Menu" if should_show else "Show Menu")

    def _sync_navigation_responsiveness(self) -> None:
        if self.tabs.count() == 0:
            self._navigation_auto_hidden = False
            self._set_navigation_visible(False)
            return

        should_auto_hide = self.width() < self._NAVIGATION_AUTO_HIDE_WIDTH
        if should_auto_hide and self.shell_navigation.isVisible():
            self._navigation_auto_hidden = True
            self._set_navigation_visible(False)
        elif not should_auto_hide and self._navigation_auto_hidden:
            self._navigation_auto_hidden = False
            self._set_navigation_visible(self._navigation_preferred_visible)

    def _on_modules_changed(self, _module_code: str) -> None:
        self._schedule_module_refresh(immediate=True)

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self._schedule_module_refresh(immediate=True)

    def _schedule_module_refresh(self, *, immediate: bool) -> None:
        if immediate:
            self._module_refresh_pending = False
            self._apply_module_refresh()
            return
        if self._module_refresh_pending:
            return
        self._module_refresh_pending = True
        QTimer.singleShot(0, self._apply_module_refresh)

    def _apply_module_refresh(self) -> None:
        self._module_refresh_pending = False
        self._rebuild_tabs(current_index=self.tabs.currentIndex())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_navigation_responsiveness()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings_store.save_theme_mode(self._theme_mode)
        self._settings_store.save_tab_index(self.tabs.currentIndex())
        self._settings_store.save_geometry(self.saveGeometry())
        super().closeEvent(event)

