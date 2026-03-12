from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QSizePolicy

from ui.cost.tab import CostTab
from ui.report.dialog_finance import FinanceReportDialog
from ui.report.dialog_performance import PerformanceVarianceDialog
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


def test_performance_variance_dialog_uses_tabs_for_major_sections(qapp, services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Performance Variance Tabs")
    ts.create_task(
        project.id,
        "Variance Task",
        start_date=date(2026, 4, 1),
        duration_days=3,
    )

    dialog = PerformanceVarianceDialog(
        None,
        services["reporting_service"],
        project.id,
        project.name,
    )

    assert dialog.variance_tabs.count() == 3
    assert dialog.variance_tabs.tabText(0) == "Cost Sources"
    assert dialog.variance_tabs.tabText(1) == "Schedule Variance"
    assert dialog.variance_tabs.tabText(2) == "Cost Breakdown"


def test_finance_report_dialog_uses_tabs_for_major_sections(qapp, services):
    project = services["project_service"].create_project("Finance Tabs Project")

    dialog = FinanceReportDialog(
        None,
        services["finance_service"],
        project.id,
        project.name,
    )

    assert dialog.finance_tabs.count() == 3
    assert dialog.finance_tabs.tabText(0) == "Cashflow"
    assert dialog.finance_tabs.tabText(1) == "Analytics"
    assert dialog.finance_tabs.tabText(2) == "Ledger Trail"
