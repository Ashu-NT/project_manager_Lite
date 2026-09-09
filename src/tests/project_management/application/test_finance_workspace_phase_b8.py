from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.common.exceptions import NotFoundError


@contextmanager
def _statement_count(session):
    engine = session.get_bind()
    statements: list[str] = []

    def _before(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _before)


def _seed_workspace(services):
    project = services["project_service"].create_project(
        "Finance Workspace", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="LABOR", name="Project Labor"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
        is_funded=True,
    )
    task = services["task_service"].create_task(
        project.id, "Engineering", wbs_code="1.1"
    )
    budget = services["budget_service"].create_budget(project.id, "Control Budget")
    services["budget_service"].add_line(
        budget.id,
        cost_code_id=cost_code.id,
        task_id=task.id,
        description="Engineering allocation",
        amount=Decimal("750"),
        currency_code="USD",
        expected_budget_version=budget.row_version,
    )
    budget = services["budget_service"].get_budget(budget.id)
    services["budget_service"].add_line(
        budget.id,
        cost_code_id=cost_code.id,
        task_id=task.id,
        description="Delivery allocation",
        amount=Decimal("500"),
        currency_code="USD",
        expected_budget_version=budget.row_version,
    )

    resource = services["resource_service"].create_resource(
        "Lead Engineer", hourly_rate=50.0, currency_code="USD"
    )
    project_resource = services["project_resource_service"].add_to_project(
        project.id,
        resource.id,
        hourly_rate=50.0,
        currency_code="USD",
        planned_hours=20.0,
    )
    assignment = services["task_service"].assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=100.0,
    )
    services["task_service"].update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=Decimal("10"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )

    project_card = services["rate_card_service"].create_rate_card(
        name="Project Rates", project_id=project.id
    )
    services["rate_card_service"].create_line(
        project_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("60"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=date(2026, 1, 1),
    )
    services["planned_cost_service"].calculate_snapshot(
        project.id, calculated_by="admin", as_of=date(2026, 8, 9)
    )
    return project


def test_qml_uses_six_intent_destinations_and_secondary_finance_views() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    page = (root / "FinancialsWorkspacePage.qml").read_text(encoding="utf-8")
    panel = (root / "panels/FinancialsDetailPanel.qml").read_text(encoding="utf-8")
    section_registry = (root / "sections/qmldir").read_text(encoding="utf-8")

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
    assert not (root / "sections/FinancialsBudgetSection.qml").exists()
    assert "FinancialsDetailPanel" in page
    assert "FinancialsListPage" not in page


def test_budget_create_action_stays_visible_when_open_version_blocks_creation() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    section = (root / "sections/FinancialsBudgetVersionsSection.qml").read_text(
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
