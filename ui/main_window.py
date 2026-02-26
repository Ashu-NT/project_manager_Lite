# ui/main_window.py
from __future__ import annotations

import os

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.services.auth import UserSessionContext
from infra.update import check_for_updates, default_update_manifest_source
from infra.version import get_app_version
from ui.admin.audit_tab import AuditLogTab
from ui.admin.users_tab import UserAdminTab
from ui.calendar.tab import CalendarTab
from ui.cost.tab import CostTab
from ui.dashboard.tab import DashboardTab
from ui.governance.tab import GovernanceTab
from ui.project.tab import ProjectTab
from ui.report.tab import ReportTab
from ui.resource.tab import ResourceTab
from ui.settings import MainWindowSettingsStore
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.styles.theme import apply_app_style
from ui.styles.ui_config import UIConfig as CFG
from ui.support.tab import SupportTab
from ui.task.tab import TaskTab


class MainWindow(QMainWindow):
    def __init__(self, services: dict[str, object], parent: QWidget | None = None):
        super().__init__(parent)
        self.services: dict[str, object] = services
        self._user_session: UserSessionContext | None = services.get("user_session")  # type: ignore[assignment]
        self._settings_store = MainWindowSettingsStore()
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

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._build_tabs()
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(central)
        self._restore_persisted_state()
        self._run_startup_update_check()

    def _build_tabs(self) -> None:
        if self._has_permission("project.read") or self._has_permission("report.view"):
            dashboard_tab = DashboardTab(
                dashboard_service=self.services["dashboard_service"],
                project_service=self.services["project_service"],
                baseline_service=self.services["baseline_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(dashboard_tab, "Dashboard")

        if self._has_permission("task.read"):
            calendar_tab = CalendarTab(
                work_calendar_service=self.services["work_calendar_service"],
                work_calendar_engine=self.services["work_calendar_engine"],
                scheduling_engine=self.services["scheduling_engine"],
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(calendar_tab, "Calendar")

        if self._has_permission("resource.read"):
            resource_tab = ResourceTab(
                resource_service=self.services["resource_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(resource_tab, "Resources")

        if self._has_permission("project.read"):
            project_tab = ProjectTab(
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                reporting_service=self.services["reporting_service"],
                project_resource_service=self.services["project_resource_service"],
                resource_service=self.services["resource_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(project_tab, "Projects")

        if self._has_permission("task.read"):
            task_tab = TaskTab(
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                resource_service=self.services["resource_service"],
                project_resource_service=self.services["project_resource_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(task_tab, "Tasks")

        if self._has_permission("cost.read"):
            cost_tab = CostTab(
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                cost_service=self.services["cost_service"],
                reporting_service=self.services["reporting_service"],
                resource_service=self.services["resource_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(cost_tab, "Costs")

        if self._has_permission("report.view"):
            report_tab = ReportTab(
                project_service=self.services["project_service"],
                reporting_service=self.services["reporting_service"],
                finance_service=self.services.get("finance_service"),
                user_session=self._user_session,
            )
            self.tabs.addTab(report_tab, "Reports")

        if self._has_permission("auth.manage"):
            users_tab = UserAdminTab(
                auth_service=self.services["auth_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(users_tab, "Users")

        if self._has_permission("auth.manage"):
            audit_tab = AuditLogTab(
                audit_service=self.services["audit_service"],
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                resource_service=self.services["resource_service"],
                cost_service=self.services["cost_service"],
                baseline_service=self.services["baseline_service"],
            )
            self.tabs.addTab(audit_tab, "Audit")

        if self._has_permission("auth.manage"):
            support_tab = SupportTab(
                settings_store=self._settings_store,
                user_session=self._user_session,
            )
            self.tabs.addTab(support_tab, "Support")

        if self._has_permission("approval.request") or self._has_permission("approval.decide"):
            governance_tab = GovernanceTab(
                approval_service=self.services["approval_service"],
                project_service=self.services["project_service"],
                task_service=self.services["task_service"],
                cost_service=self.services["cost_service"],
                user_session=self._user_session,
            )
            self.tabs.addTab(governance_tab, "Governance")

    def _has_permission(self, permission_code: str) -> bool:
        if self._user_session is None:
            return True
        return self._user_session.has_permission(permission_code)

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
            self._settings_store.save_tab_index(index)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings_store.save_theme_mode(self._theme_mode)
        self._settings_store.save_tab_index(self.tabs.currentIndex())
        self._settings_store.save_geometry(self.saveGeometry())
        super().closeEvent(event)

