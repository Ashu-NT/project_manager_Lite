# ui/main_window.py
from __future__ import annotations
from PySide6.QtWidgets import QMainWindow, QWidget, QTabWidget, QVBoxLayout

from ui.project_tab import ProjectTab
from ui.report_tab import ReportTab
from ui.cost_tab import CostTab
from ui.task_tab import TaskTab
from ui.resource_tab import ResourceTab
from ui.calendar_tab import CalendarTab
from ui.dashboard_tab import DashboardTab
from ui.styles.ui_config import UIConfig as CFG


class MainWindow(QMainWindow):
    def __init__(self, services: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.services = services

        self.setWindowTitle("Project Management App")
        self.resize(CFG.DEFAULT_WINDOW_SIZE)
        self.setMinimumSize(CFG.MIN_WINDOW_SIZE)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        # Dashboard
        dashboard_tab = DashboardTab(
            dashboard_service=services["dashboard_service"],
            project_service=services["project_service"],
            baseline_service= services["baseline_service"]
        )
        self.tabs.addTab(dashboard_tab, "Dashboard")
        
        # calendar
        calendar_tab = CalendarTab(
            work_calendar_service=services["work_calendar_service"],
            work_calendar_engine=services["work_calendar_engine"],
            scheduling_engine=services["scheduling_engine"],
            project_service=services["project_service"],
            task_service=services["task_service"],
        )
        self.tabs.addTab(calendar_tab, "Calendar")
        
        #Resources
        resource_tab = ResourceTab(
            resource_service=services["resource_service"],
        )
        self.tabs.addTab(resource_tab, "Resources")
        
        # Projects
        project_tab = ProjectTab(
            project_service=services["project_service"],
            task_service=services["task_service"],
            reporting_service=services["reporting_service"],
            project_resource_service=services["project_resource_service"],
            resource_service=services["resource_service"],
        )
        self.tabs.addTab(project_tab, "Projects")

        # Tasks
        task_tab = TaskTab(
            project_service=services["project_service"],
            task_service=services["task_service"],
            resource_service=services["resource_service"],
            project_resource_service=services["project_resource_service"],
            
        )
        self.tabs.addTab(task_tab, "Tasks")
    

        # Costs
        cost_tab = CostTab(
            project_service=services["project_service"],
            task_service=services["task_service"],
            cost_service=services["cost_service"],
            reporting_service=services["reporting_service"],
            resource_service=services["resource_service"],
        )   
        self.tabs.addTab(cost_tab, "Costs")
        
        # Reports (project KPIs, Gantt, critical path, resources)
        report_tab = ReportTab(
            project_service=services["project_service"],
            reporting_service=services["reporting_service"],
        )
        self.tabs.addTab(report_tab, "Reports")

        self.setCentralWidget(central)
