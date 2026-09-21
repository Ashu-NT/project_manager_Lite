from __future__ import annotations

from pathlib import Path


def test_qml_uses_six_intent_destinations_and_secondary_finance_views() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    page = (root / "FinancialsWorkspacePage.qml").read_text(encoding="utf-8")
    panel = (root / "shared/panels/FinancialsDetailPanel.qml").read_text(encoding="utf-8")
    section_registry = (root / "budgets/sections/qmldir").read_text(encoding="utf-8")

    for section in (
        "Overview",
        "Planning",
        "Costs",
        "Performance",
        "Commercial",
        "Controls",
    ):
        assert f'"{section}"' in page
    for subsection in (
        "Budgets",
        "Planned Costs",
        "Forecast",
        "Actuals",
        "Commitments",
        "Rate Cards",
        "Variance",
        "Cost Phasing",
        "Reports",
        "Billing Preparation",
        "Projected Profitability",
        "Accounting Status",
        "Financial Setup",
        "Change Control",
        "Activity",
    ):
        assert f'"label": "{subsection}"' in panel
    assert "Cashflow" not in panel
    assert "FinancialsBudgetSection" not in section_registry
    assert not list(root.rglob("FinancialsBudgetSection.qml"))
    assert "FinancialsDetailPanel" in page
    assert "FinancialsListPage" not in page


def test_budget_create_action_stays_visible_when_open_version_blocks_creation() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    section = (root / "budgets/sections/FinancialsBudgetVersionsSection.qml").read_text(
        encoding="utf-8"
    )

    assert "visible: root.showCreateVersion" in section
    assert "enabled: root.canCreateVersion && !root.busy" in section
    assert "AppWidgets.InfoTip" in section
    assert 'title: "Create Version unavailable"' in section
    assert "accessibleLabel: \"Why Create Version is unavailable\"" in section
    assert "root.createVersionDisabledReason" in section


def test_financials_uses_flat_scrollable_navigation_and_project_scope_selector() -> None:
    financials_root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    page = (financials_root / "FinancialsWorkspacePage.qml").read_text(encoding="utf-8")
    section_page = Path(
        "src/ui_qml/shared/qml/App/Widgets/SectionDetailPage.qml"
    ).read_text(encoding="utf-8")
    navigation_rail = Path(
        "src/ui_qml/shared/qml/App/Widgets/SectionNavigationRail.qml"
    ).read_text(encoding="utf-8")
    # R1.4 re-implemented SectionNavigationRail on top of the shared
    # GroupedNavigationRail primitive (R0.1 D7); the scrollable-content
    # implementation now lives there, not in SectionNavigationRail.qml
    # itself, which is now a thin wrapper.
    grouped_rail = Path(
        "src/ui_qml/shared/qml/App/Widgets/GroupedNavigationRail.qml"
    ).read_text(encoding="utf-8")

    assert '"group": "Finance"' not in page
    for destination in (
        "Overview",
        "Planning",
        "Costs",
        "Performance",
        "Commercial",
        "Controls",
    ):
        assert f'            "{destination}",' in page or f'            "{destination}"' in page

    assert "projectOptions" in page
    assert "selectedProjectId" in page
    assert "workspaceController.selectProject" in page
    assert "sectionGroupsCollapsedByDefault: true" in section_page
    assert "SectionNavigationRail" in section_page
    assert "GroupedNavigationRail" in navigation_rail
    assert "contentHeight: navColumn.implicitHeight" in grouped_rail
    assert "ScrollBar.vertical: ScrollBar" in grouped_rail


def test_financials_uses_only_shared_selector_controls() -> None:
    financials_root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    sources = tuple(financials_root.rglob("*.qml"))

    combo_count = 0
    paged_selector_count = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        combo_count += text.count("AppControls.ComboBox {")
        paged_selector_count += text.count("AppControls.SearchablePagedSelector {")
        assert "\nComboBox {" not in text, source
        assert "\nSearchablePagedSelector {" not in text, source

    # Finite lists use the same shared ComboBox as Projects/Tasks. Large lookup
    # datasets keep the shared server-paged selector rather than loading all rows.
    assert combo_count > 0
    assert paged_selector_count > 0
