from __future__ import annotations

import re
from pathlib import Path


PM_ROOT = Path("src/ui_qml/modules/project_management")
WORKSPACES = PM_ROOT / "qml/workspaces"
CONTROLLERS = PM_ROOT / "controllers"
PRESENTERS = PM_ROOT / "presenters"
TYPEINFO = PM_ROOT / "qml/ProjectManagement/Controllers/typeinfo"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _qml_sources() -> str:
    return "\n".join(_read(path) for path in WORKSPACES.rglob("*.qml"))


def test_active_pm_qml_has_no_empty_handlers_or_unsupported_export_calls() -> None:
    source = _qml_sources()

    assert not re.search(
        r"on[A-Za-z]+\s*:\s*(?:function\([^)]*\)\s*)?\{\s*\}",
        source,
    )
    for method_name in (
        "exportDashboard",
        "exportPortfolio",
        "exportRegister",
        "exportSchedule",
        "exportTimesheets",
    ):
        assert method_name not in source


def test_unsupported_export_adapters_and_fabricated_success_are_retired() -> None:
    production_source = "\n".join(
        _read(path)
        for root in (CONTROLLERS, PRESENTERS)
        for path in root.rglob("*.py")
    )
    typeinfo_source = "\n".join(
        _read(path)
        for path in TYPEINFO.iterdir()
        if path.suffix in {".fragment", ".qmltypes"}
    )

    for identifier in (
        "exportDashboard",
        "exportPortfolio",
        "exportRegister",
        "exportSchedule",
        "exportTimesheets",
        "export_schedule",
        "export_register",
    ):
        assert identifier not in production_source
        assert identifier not in typeinfo_source
    assert "Export is not available here" not in production_source


def test_real_file_export_surfaces_remain_available() -> None:
    assert "def export_projects(" in _read(CONTROLLERS / "projects/project_export_handler.py")
    assert "def export_tasks(" in _read(CONTROLLERS / "tasks/task_export_handler.py")
    assert "def export_resources(" in _read(CONTROLLERS / "resources/resource_export_handler.py")
    financials = _read(WORKSPACES / "financials/FinancialsWorkspacePage.qml")
    assert '"id": "export_excel"' in financials
    assert '"id": "export_pdf"' in financials


def test_portfolio_compare_presents_authoritative_analysis() -> None:
    # R3.4: the scenario selector/evaluate/compare toolbar and the heatmap
    # DataTable both moved off the shared workspace page into their own tabs
    # (Scenarios / Heatmap) as part of the six-tab Portfolio IA.
    page = _read(WORKSPACES / "portfolio/PortfolioWorkspacePage.qml")
    scenarios_tab = _read(WORKSPACES / "portfolio/tabs/ScenariosTab.qml")
    heatmap_tab = _read(WORKSPACES / "portfolio/tabs/HeatmapTab.qml")
    toolbar = _read(
        WORKSPACES / "portfolio/sections/PortfolioGovernanceToolbar.qml"
    )

    assert "evaluationModel: root.workspaceController" in scenarios_tab
    assert "comparisonModel: root.workspaceController" in scenarios_tab
    assert "onClicked: analysisPopup.open()" in toolbar
    assert toolbar.count("PortfolioSummaryCard {") == 2
    assert "bottomTab" not in page
    assert "Evaluate Scenario" not in page
    assert '"id": "evaluate"' not in page
    assert "multiSelect: false" in heatmap_tab


def test_scheduling_comparison_is_selector_driven_not_refresh_backed() -> None:
    baselines = _read(
        WORKSPACES / "scheduling/panels/SchedulingBaselinesPanel.qml"
    )

    assert "selectBaselineA" in baselines
    assert "selectBaselineB" in baselines
    assert '"id": "compare"' not in baselines
    assert 'actionId === "compare"' not in baselines
    assert "baselineCompareTableModel" in baselines


def test_future_purchase_order_placeholder_is_not_reachable() -> None:
    page = _read(WORKSPACES / "financials/FinancialsWorkspacePage.qml")
    panel = _read(WORKSPACES / "financials/panels/FinancialsDetailPanel.qml")
    qmldir = _read(WORKSPACES / "financials/sections/qmldir")
    placeholder = WORKSPACES / "financials/sections/FinancialsPurchaseOrdersSection.qml"

    assert "Purchase Orders" not in page
    assert "Purchase Orders" not in panel
    assert "FinancialsPurchaseOrdersSection" not in qmldir
    assert not placeholder.exists()


def test_lifecycle_and_capability_restrictions_remain_on_real_actions() -> None:
    baselines = _read(
        WORKSPACES / "scheduling/panels/SchedulingBaselinesPanel.qml"
    )
    timesheets = _read(WORKSPACES / "timesheets/TimesheetsWorkspaceState.qml")

    assert "pmCapabilityController.canApproveBaseline" in baselines
    assert "st.canApprove === true" in timesheets
    assert "st.canReject === true" in timesheets
    assert 'status === "SUBMITTED"' not in timesheets
    assert "st.canLock === true" in timesheets
    assert "st.canUnlock === true" in timesheets
    assert '"id": "export"' not in timesheets
