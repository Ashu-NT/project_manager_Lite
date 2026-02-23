# ui/main_window.py
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.calendar.tab import CalendarTab
from ui.cost.tab import CostTab
from ui.dashboard.tab import DashboardTab
from ui.project.tab import ProjectTab
from ui.report.tab import ReportTab
from ui.resource.tab import ResourceTab
from ui.styles.theme import apply_app_style
from ui.styles.ui_config import UIConfig as CFG
from ui.task.tab import TaskTab


class MainWindow(QMainWindow):
    def __init__(self, services: dict[str, object], parent: QWidget | None = None):
        super().__init__(parent)
        self.services: dict[str, object] = services
        self._theme_mode: str = os.getenv("PM_THEME", "light").strip().lower()
        if self._theme_mode not in {"light", "dark"}:
            self._theme_mode = "light"

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
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._build_tabs()

        self.setCentralWidget(central)

    def _build_tabs(self) -> None:
        dashboard_tab = DashboardTab(
            dashboard_service=self.services["dashboard_service"],
            project_service=self.services["project_service"],
            baseline_service=self.services["baseline_service"],
        )
        self.tabs.addTab(dashboard_tab, "Dashboard")

        calendar_tab = CalendarTab(
            work_calendar_service=self.services["work_calendar_service"],
            work_calendar_engine=self.services["work_calendar_engine"],
            scheduling_engine=self.services["scheduling_engine"],
            project_service=self.services["project_service"],
            task_service=self.services["task_service"],
        )
        self.tabs.addTab(calendar_tab, "Calendar")

        resource_tab = ResourceTab(resource_service=self.services["resource_service"])
        self.tabs.addTab(resource_tab, "Resources")

        project_tab = ProjectTab(
            project_service=self.services["project_service"],
            task_service=self.services["task_service"],
            reporting_service=self.services["reporting_service"],
            project_resource_service=self.services["project_resource_service"],
            resource_service=self.services["resource_service"],
        )
        self.tabs.addTab(project_tab, "Projects")

        task_tab = TaskTab(
            project_service=self.services["project_service"],
            task_service=self.services["task_service"],
            resource_service=self.services["resource_service"],
            project_resource_service=self.services["project_resource_service"],
        )
        self.tabs.addTab(task_tab, "Tasks")

        cost_tab = CostTab(
            project_service=self.services["project_service"],
            task_service=self.services["task_service"],
            cost_service=self.services["cost_service"],
            reporting_service=self.services["reporting_service"],
            resource_service=self.services["resource_service"],
        )
        self.tabs.addTab(cost_tab, "Costs")

        report_tab = ReportTab(
            project_service=self.services["project_service"],
            reporting_service=self.services["reporting_service"],
        )
        self.tabs.addTab(report_tab, "Reports")

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

        app = QApplication.instance()
        if app is not None:
            apply_app_style(app, mode=mode)

        self._rebuild_tabs(current_index=self.tabs.currentIndex())
