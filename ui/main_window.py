# ui/main_window.py
from __future__ import annotations

import os

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

from core.services.auth import UserSessionContext
from infra.update import check_for_updates, default_update_manifest_source
from infra.version import get_app_version
from ui.shell import NavigationEntry, ShellNavigation, build_workspace_definitions
from ui.settings import MainWindowSettingsStore
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.styles.theme import apply_app_style
from ui.styles.ui_config import UIConfig as CFG


class MainWindow(QMainWindow):
    _NAVIGATION_AUTO_HIDE_WIDTH = 1100

    def __init__(self, services: dict[str, object], parent: QWidget | None = None):
        super().__init__(parent)
        self.services: dict[str, object] = services
        self._user_session: UserSessionContext | None = services.get("user_session")  # type: ignore[assignment]
        self._settings_store = MainWindowSettingsStore()
        self._navigation_auto_hidden = False
        self._navigation_preferred_visible = True
        default_theme = os.getenv("PM_THEME", "light").strip().lower()
        self._theme_mode: str = self._settings_store.load_theme_mode(default_mode=default_theme)
        os.environ["PM_THEME"] = self._theme_mode

        self.setWindowTitle("Project Management App")
        self.resize(CFG.DEFAULT_WINDOW_SIZE)
        self.setMinimumSize(CFG.MIN_WINDOW_SIZE)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(CFG.SPACING_SM)
        self.btn_toggle_navigation = QPushButton("Hide Menu")
        self.btn_toggle_navigation.clicked.connect(self._toggle_navigation_visibility)
        header_layout.addWidget(self.btn_toggle_navigation)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Theme:"))
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
            self.user_label = QLabel(f"User: {label}")
            header_layout.addWidget(self.user_label)
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
                    section=workspace.section,
                    label=workspace.label,
                    tab_index=tab_index,
                )
            )

        self.shell_navigation.set_entries(navigation_entries)
        self.shell_navigation.set_current_index(self.tabs.currentIndex())
        has_navigation = self.tabs.count() > 0
        self.btn_toggle_navigation.setVisible(has_navigation)
        self._set_navigation_visible(
            has_navigation and self._navigation_preferred_visible and not self._navigation_auto_hidden
        )

    def _rebuild_tabs(self, current_index: int) -> None:
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if widget is not None:
                widget.deleteLater()
        self._build_tabs()
        if self.tabs.count():
            safe_index = max(0, min(current_index, self.tabs.count() - 1))
            self.tabs.setCurrentIndex(safe_index)
            self.shell_navigation.set_current_index(self.tabs.currentIndex())
        self._sync_navigation_responsiveness()

    def _on_theme_changed(self, _index: int) -> None:
        mode = self.theme_combo.currentData()
        if not mode or mode == self._theme_mode:
            return

        self._theme_mode = mode
        os.environ["PM_THEME"] = mode
        self._settings_store.save_theme_mode(mode)

        app = QApplication.instance()
        if app is not None:
            apply_app_style(app, mode=mode)

        self._rebuild_tabs(current_index=self.tabs.currentIndex())

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

    def _toggle_navigation_visibility(self) -> None:
        self._navigation_auto_hidden = False
        self._navigation_preferred_visible = not self.shell_navigation.isVisible()
        self._set_navigation_visible(self._navigation_preferred_visible)

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

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_navigation_responsiveness()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings_store.save_theme_mode(self._theme_mode)
        self._settings_store.save_tab_index(self.tabs.currentIndex())
        self._settings_store.save_geometry(self.saveGeometry())
        super().closeEvent(event)

