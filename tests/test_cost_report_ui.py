from __future__ import annotations

from PySide6.QtWidgets import QSizePolicy

from ui.cost.tab import CostTab
from ui.report.tab import ReportTab


def test_cost_tab_runtime_uses_compact_header_and_badges(qapp, services):
    project = services["project_service"].create_project("Cost Header Project")

    tab = CostTab(
        project_service=services["project_service"],
        task_service=services["task_service"],
        cost_service=services["cost_service"],
        reporting_service=services["reporting_service"],
        resource_service=services["resource_service"],
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == project.id
    assert tab.cost_project_badge.text() == project.name
    assert tab.cost_count_badge.text() == "0 items"
    assert tab.cost_access_badge.text() == "Action Enabled"
    assert tab.cost_header_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    assert tab.cost_controls_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed


def test_report_tab_runtime_uses_compact_header_and_badges(qapp, services):
    project = services["project_service"].create_project("Report Header Project")
    can_export = services["user_session"].has_permission("report.export")
    finance_service = services.get("finance_service")

    tab = ReportTab(
        project_service=services["project_service"],
        reporting_service=services["reporting_service"],
        task_service=services["task_service"],
        finance_service=finance_service,
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == project.id
    assert tab.report_project_badge.text() == project.name
    assert tab.report_finance_badge.text() == ("Finance Ready" if finance_service is not None else "Finance Off")
    assert tab.report_export_badge.text() == ("Export Enabled" if can_export else "On-screen only")
    assert tab.report_header_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    assert tab.report_controls_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
