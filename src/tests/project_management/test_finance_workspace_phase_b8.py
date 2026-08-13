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


def test_workspace_query_reconciles_canonical_finance_views(services) -> None:
    project = _seed_workspace(services)

    result = services["finance_workspace_query"].get(project.id)

    assert result.profile is not None
    assert result.profile.currency_code == "USD"
    assert result.default_cost_code == "LABOR - Project Labor"
    assert len(result.budget_versions) == 1
    assert result.budget_versions[0].total_amount == Decimal("1250")
    assert result.budget_versions[0].line_count == 2
    assert result.budget_lines[0].task_name == "Engineering"
    assert result.budget_lines[0].wbs_code == "1.1"

    scopes = {card.scope for card in result.rate_cards}
    assert scopes == {"organization", "project"}
    assert any(line.rate_amount == Decimal("60") for line in result.rate_lines)

    current = result.planned_cost_versions[0]
    assert current.status == "current"
    assert current.total_hours == Decimal("10")
    assert current.total_amount == Decimal("600")
    assert result.planned_cost_lines[0].resource_name == "Lead Engineer"
    assert result.planned_cost_lines[0].cost_code == "LABOR"


def test_workspace_query_has_bounded_statement_shape(services) -> None:
    project = _seed_workspace(services)
    query = services["finance_workspace_query"]
    query.get(project.id)  # warm the validated-principal lease

    with _statement_count(services["session"]) as statements:
        query.get(project.id)

    assert len(statements) <= 14


def test_workspace_query_paginates_lines_without_corrupting_version_totals(services) -> None:
    project = _seed_workspace(services)

    result = services["finance_workspace_query"].get(
        project.id,
        budget_line_page=2,
        rate_line_page=1,
        planned_cost_line_page=1,
        page_size=1,
    )

    assert len(result.budget_lines) == 1
    assert result.budget_line_page == 2
    assert result.budget_line_page_size == 1
    assert result.budget_line_total == 2
    assert result.budget_versions[0].line_count == 2
    assert result.budget_versions[0].total_amount == Decimal("1250")
    assert len(result.rate_lines) == 1
    assert result.rate_line_total >= 2


def test_desktop_projection_formats_canonical_workspace_without_recalculation(services) -> None:
    project = _seed_workspace(services)
    api = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    result = api.get_configuration_workspace(project.id)

    assert result.profile.status_label == "Active"
    assert result.budget_versions[0].supporting_text == "Authorized total USD 1,250.00"
    assert any(card.subtitle == "Organization scope" for card in result.rate_cards)
    assert result.planned_cost_versions[0].supporting_text == "USD 600.00 | 10.0 h"
    assert "Lead Engineer" in result.planned_cost_lines[0].subtitle


def test_workspace_query_fails_closed_after_organization_switch(services) -> None:
    project = _seed_workspace(services)
    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="PF-WORKSPACE-ISOLATION",
        display_name="Finance Workspace Isolation",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(other.id)
    try:
        with pytest.raises(NotFoundError) as exc:
            services["finance_workspace_query"].get(project.id)
        assert exc.value.code == "FINANCIAL_PROFILE_NOT_FOUND"
    finally:
        organization_service.set_active_organization(original.id)


def test_qml_uses_five_project_level_finance_views_and_deletes_false_budget_view() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/financials")
    page = (root / "FinancialsWorkspacePage.qml").read_text(encoding="utf-8")
    panel = (root / "panels/FinancialsDetailPanel.qml").read_text(encoding="utf-8")
    section_registry = (root / "sections/qmldir").read_text(encoding="utf-8")

    for section in (
        "Profile",
        "Budget Versions",
        "Budget Lines",
        "Rate Cards",
        "Planned Costs",
    ):
        assert f'"{section}"' in page
        assert f'"{section}"' in panel
    assert "FinancialsBudgetSection" not in section_registry
    assert not (root / "sections/FinancialsBudgetSection.qml").exists()
    assert "FinancialsDetailPanel" in page
    assert "FinancialsListPage" not in page


def test_financials_uses_grouped_scrollable_navigation_and_project_scope_selector() -> None:
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

    for group in ("Configuration", "Planning", "Cost Control", "Commercial", "Insights"):
        assert f'"group": "{group}"' in page

    assert "projectOptions" in page
    assert "selectedProjectId" in page
    assert "workspaceController.selectProject" in page
    assert "sectionGroupsCollapsedByDefault: true" in section_page
    assert "SectionNavigationRail" in section_page
    assert "GroupedNavigationRail" in navigation_rail
    assert "contentHeight: navColumn.implicitHeight" in grouped_rail
    assert "ScrollBar.vertical: ScrollBar" in grouped_rail
