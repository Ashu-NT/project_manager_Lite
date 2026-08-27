from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.models.cost_entries import (
    FinancialCostEntryPageDto,
    FinancialManualActualOptionsDto,
)
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import (
    FinancialOverviewDto,
)
from src.ui_qml.modules.project_management.presenters.financials.destination_builder import (
    build_destination_state,
    build_shell_state,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.platform.api.desktop.history.audit.models.audit_entry import (
    AuditEntryDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.ui_qml.shell.qml_engine import create_qml_engine


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


def _overview() -> FinancialOverviewDto:
    return FinancialOverviewDto(
        project_id="project-1",
        project_currency="XAF",
        as_of=date(2026, 8, 27),
        budget="1000",
        budget_label="XAF 1,000.00",
        actual="200",
        actual_label="XAF 200.00",
        committed="100",
        committed_label="XAF 100.00",
        available="700",
        available_label="XAF 700.00",
        forecast_etc="500",
        forecast_etc_label="XAF 500.00",
        estimate_at_completion="700",
        estimate_at_completion_label="XAF 700.00",
        variance_at_completion="300",
        variance_at_completion_label="XAF 300.00",
    )


def test_shell_loads_only_project_selector_options() -> None:
    api = MagicMock()
    api.list_projects.return_value = (
        FinancialProjectOptionDescriptor("project-1", "Project One"),
    )

    state = build_shell_state(api)

    assert state.selected_project_id == "project-1"
    api.list_projects.assert_called_once_with()
    assert api.method_calls == [call.list_projects()]


def test_overview_uses_bounded_overview_contract_only() -> None:
    api = MagicMock()
    api.get_finance_overview.return_value = _overview()

    state = build_destination_state(
        api,
        destination="overview",
        subsection="summary",
        selected_project_id="project-1",
        selected_project_label="Project One",
    )

    assert len(state.overview.metrics) == 7
    api.get_finance_overview.assert_called_once_with("project-1")
    assert api.method_calls == [call.get_finance_overview("project-1")]


def test_planning_budget_tab_does_not_query_cost_or_performance_reads() -> None:
    api = MagicMock()
    api.get_budget_workspace.return_value = FinancialConfigurationWorkspaceDto()

    build_destination_state(
        api,
        destination="planning",
        subsection="budgets",
        selected_project_id="project-1",
    )

    api.get_budget_workspace.assert_called_once()
    kwargs = api.get_budget_workspace.call_args.kwargs
    assert kwargs["selected_budget_id"] == ""
    assert kwargs["version_page"] == 1
    assert kwargs["line_page"] == 1
    api.get_configuration_workspace.assert_not_called()
    api.get_finance_snapshot.assert_not_called()
    api.list_cost_entries.assert_not_called()
    api.get_billing_workspace.assert_not_called()


def test_planning_planned_cost_tab_uses_bounded_reader_facade_only() -> None:
    api = MagicMock()
    api.get_planned_cost_workspace.return_value = FinancialConfigurationWorkspaceDto()

    build_destination_state(
        api,
        destination="planning",
        subsection="planned_costs",
        selected_project_id="project-1",
        selected_planned_cost_version_id="snapshot-2",
        planned_cost_version_page=3,
        planned_cost_line_page=2,
        planned_cost_version_sort_key="metaText",
        planned_cost_version_sort_direction="asc",
        planned_cost_line_sort_key="supportingText",
        planned_cost_line_sort_direction="desc",
    )

    api.get_planned_cost_workspace.assert_called_once_with(
        "project-1",
        selected_version_id="snapshot-2",
        version_page=3,
        line_page=2,
        page_size=50,
        version_sort_key="metaText",
        version_sort_direction="asc",
        line_sort_key="supportingText",
        line_sort_direction="desc",
    )
    api.get_configuration_workspace.assert_not_called()
    api.get_finance_snapshot.assert_not_called()


def test_planning_forecast_tab_uses_bounded_reader_facade_only() -> None:
    api = MagicMock()
    from src.core.modules.project_management.api.desktop.financials.models.forecasts import (
        FinancialForecastWorkspaceDto,
    )

    api.get_forecast_workspace.return_value = FinancialForecastWorkspaceDto()
    build_destination_state(
        api,
        destination="planning",
        subsection="forecast",
        selected_project_id="project-1",
        selected_forecast_id="forecast-2",
        forecast_version_page=2,
        forecast_line_page=3,
        forecast_version_sort_key="metaText",
        forecast_version_sort_direction="asc",
        forecast_line_sort_key="supportingText",
        forecast_line_sort_direction="desc",
        forecast_version_search="approved",
        forecast_version_status="approved",
        forecast_generation_mode="manual",
        forecast_line_search="risk",
        forecast_line_source_type="risk",
    )

    api.get_forecast_workspace.assert_called_once_with(
        "project-1",
        selected_forecast_id="forecast-2",
        version_page=2,
        line_page=3,
        page_size=50,
        version_sort_key="metaText",
        version_sort_direction="asc",
        line_sort_key="supportingText",
        line_sort_direction="desc",
        version_search="approved",
        version_status="approved",
        generation_mode="manual",
        line_search="risk",
        line_source_type="risk",
    )
    api.get_cost_forecast.assert_not_called()
    api.list_forecast_versions.assert_not_called()
    api.list_forecast_lines.assert_not_called()


def test_budget_reader_pages_versions_and_selected_lines_authoritatively(services) -> None:
    project = services["project_service"].create_project(
        "R6B budget reader",
        financial_currency_code="USD",
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6B-BUDGET",
        name="R6B Budget",
    )
    budgets = services["budget_service"]

    first = budgets.create_budget(project.id, "Alpha", currency_code="USD")
    budgets.add_line(
        first.id,
        cost_code_id=cost_code.id,
        description="Alpha line",
        amount=Decimal("125"),
        expected_budget_version=first.row_version,
    )
    first = budgets.get_budget(first.id)
    first = budgets.submit_budget(
        first.id,
        submitted_by="admin",
        expected_version=first.row_version,
    )
    budgets.reject_budget(
        first.id,
        rejected_by="admin",
        expected_version=first.row_version,
    )

    second = budgets.create_budget(project.id, "Zulu", currency_code="USD")
    budgets.add_line(
        second.id,
        cost_code_id=cost_code.id,
        description="Zulu line",
        amount=Decimal("250"),
        expected_budget_version=second.row_version,
    )

    query = services["finance_workspace_query"]
    with _statement_count(services["session"]) as statements:
        first_page = query.get_budget_workspace(
            project.id,
            selected_budget_id=first.id,
            version_request=FinancePageRequest(
                page=1,
                page_size=1,
                sort_key="revision",
                sort_direction="asc",
            ),
            line_request=FinancePageRequest(
                page=1,
                page_size=1,
                sort_key="supportingText",
                sort_direction="asc",
            ),
        )

    # One module-entitlement authorization statement plus the Reader's
    # count/data pair for versions and count/data pair for selected lines.
    assert len(statements) <= 5
    assert first_page.versions.total == 2
    assert first_page.versions.items[0].id == first.id
    assert first_page.lines.total == 1
    assert first_page.lines.items[0].budget_id == first.id
    assert first_page.lines.items[0].amount == Decimal("125")

    second_page = query.get_budget_workspace(
        project.id,
        version_request=FinancePageRequest(
            page=2,
            page_size=1,
            sort_key="revision",
            sort_direction="asc",
        ),
    )
    assert second_page.versions.items[0].id == second.id
    assert second_page.lines.items == ()
    assert second_page.selected_budget_id == ""


def test_planned_cost_reader_pages_versions_and_selected_lines_authoritatively(
    services,
) -> None:
    project = services["project_service"].create_project(
        "R6B planned-cost reader",
        financial_currency_code="USD",
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6B-LABOR",
        name="R6B Labor",
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    task = services["task_service"].create_task(
        project.id,
        "R6B Engineering",
        wbs_code="1.1",
    )
    resource = services["resource_service"].create_resource(
        "R6B Engineer",
        hourly_rate=Decimal("50"),
        currency_code="USD",
    )
    project_resource = services["project_resource_service"].add_to_project(
        project.id,
        resource.id,
        hourly_rate=Decimal("50"),
        currency_code="USD",
        planned_hours=Decimal("20"),
    )
    assignment = services["task_service"].assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=100,
    )
    services["task_service"].update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=Decimal("10"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    rate_card = services["rate_card_service"].create_rate_card(
        name="R6B Rates",
        project_id=project.id,
    )
    services["rate_card_service"].create_line(
        rate_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("60"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=date(2026, 1, 1),
    )
    planned_costs = services["planned_cost_service"]
    first = planned_costs.calculate_snapshot(
        project.id,
        calculated_by="admin",
        as_of=date(2026, 8, 1),
    ).version
    second = planned_costs.calculate_snapshot(
        project.id,
        calculated_by="admin",
        as_of=date(2026, 8, 2),
    ).version

    query = services["finance_workspace_query"]
    with _statement_count(services["session"]) as statements:
        first_page = query.get_planned_cost_workspace(
            project.id,
            selected_version_id=first.id,
            version_request=FinancePageRequest(
                page=1,
                page_size=1,
                sort_key="revision",
                sort_direction="asc",
            ),
            line_request=FinancePageRequest(
                page=1,
                page_size=1,
                sort_key="title",
                sort_direction="asc",
            ),
        )

    assert len(statements) <= 5
    assert first_page.versions.total == 2
    assert first_page.versions.items[0].id == first.id
    assert first_page.lines.total == 1
    assert first_page.lines.items[0].version_id == first.id
    assert first_page.lines.items[0].task_name == "R6B Engineering"
    assert first_page.lines.items[0].resource_name == "R6B Engineer"
    assert first_page.lines.items[0].amount == Decimal("600")

    second_page = query.get_planned_cost_workspace(
        project.id,
        version_request=FinancePageRequest(
            page=2,
            page_size=1,
            sort_key="revision",
            sort_direction="asc",
        ),
    )
    assert second_page.versions.items[0].id == second.id
    assert second_page.lines.items == ()
    assert second_page.selected_version_id == ""


def _seed_forecast_reader(services):
    project = services["project_service"].create_project(
        "R6B forecast reader",
        financial_currency_code="USD",
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6B-ETC",
        name="R6B ETC",
    )
    task = services["task_service"].create_task(
        project.id,
        "R6B Forecast Task",
        wbs_code="2.1",
    )
    forecasts = services["forecast_version_service"]
    first = forecasts.create_forecast(
        project.id,
        name="Alpha Forecast",
        as_of_date=date(2026, 8, 1),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecasts.add_line(
        first.id,
        cost_code_id=cost_code.id,
        task_id=task.id,
        description="Manual replacement ETC",
        amount=Decimal("100.25"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=first.row_version,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
    )
    first = forecasts.get_forecast(first.id)
    forecasts.add_line(
        first.id,
        cost_code_id=cost_code.id,
        description="Risk contingency",
        amount=Decimal("50.10"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.RISK,
        source_reference_type="risk",
        source_reference_id="risk-1",
        source_snapshot_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        created_by="admin",
        expected_forecast_version=first.row_version,
    )
    first = forecasts.get_forecast(first.id)
    first = forecasts.submit_forecast(
        first.id,
        submitted_by="admin",
        expected_version=first.row_version,
    )
    first = forecasts.approve_forecast(
        first.id,
        approved_by="admin",
        expected_version=first.row_version,
    )

    second = forecasts.create_forecast(
        project.id,
        name="Zulu Forecast",
        as_of_date=date(2026, 8, 2),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecasts.add_line(
        second.id,
        cost_code_id=cost_code.id,
        description="Second manual ETC",
        amount=Decimal("200.05"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=second.row_version,
    )
    return project, first, second


def test_forecast_reader_is_bounded_filtered_and_parent_authoritative(services) -> None:
    project, first, second = _seed_forecast_reader(services)
    query = services["finance_workspace_query"]

    with _statement_count(services["session"]) as statements:
        selected = query.get_forecast_workspace(
            project.id,
            selected_forecast_id=first.id,
            version_request=ForecastVersionRequest(
                page=1,
                page_size=1,
                sort_key="revision",
                sort_direction="asc",
                status="approved",
                generation_mode="manual",
            ),
            line_request=ForecastLineRequest(
                page=1,
                page_size=1,
                sort_key="supportingText",
                sort_direction="desc",
                source_type="risk",
            ),
        )

    # Authorization plus version count/page, selected summary, and line count/page.
    assert len(statements) <= 6
    assert selected.versions.total == 1
    assert selected.versions.items[0].id == first.id
    assert selected.selected_forecast_id == first.id
    assert selected.selected_forecast is not None
    assert selected.selected_forecast.total_etc == Decimal("150.35")
    assert selected.selected_forecast.line_count == 2
    assert selected.lines.total == 1
    assert selected.lines.items[0].source_type == "risk"
    assert selected.lines.items[0].amount == Decimal("50.10")
    assert selected.lines.items[0].source_reference_id == "risk-1"

    second_page = query.get_forecast_workspace(
        project.id,
        version_request=ForecastVersionRequest(
            page=2,
            page_size=1,
            sort_key="revision",
            sort_direction="asc",
        ),
    )
    assert second_page.versions.items[0].id == second.id
    assert second_page.selected_forecast_id == ""
    assert second_page.lines.items == ()

    normalized = query.get_forecast_workspace(
        project.id,
        version_request=ForecastVersionRequest(sort_key="not-valid"),
        line_request=ForecastLineRequest(sort_key="not-valid"),
    )
    assert normalized.versions.sort_key == "revision"
    assert normalized.lines.sort_key == "title"

    invalid = query.get_forecast_workspace(
        project.id,
        selected_forecast_id="not-in-this-project",
    )
    assert invalid.selected_forecast_id == ""
    assert invalid.selected_forecast is None
    assert invalid.lines.items == ()


def test_forecast_reader_rejects_wrong_scope_and_serializes_decimal_strings(
    services,
) -> None:
    project, first, _second = _seed_forecast_reader(services)
    query = services["finance_workspace_query"]
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test forecast scope"
    )
    wrong_scope = query._forecast_reader.list_versions(
        tenant_id=scope.tenant_id,
        organization_id="wrong-organization",
        project_id=project.id,
        request=ForecastVersionRequest(),
    )
    assert wrong_scope.total == 0
    assert wrong_scope.items == ()

    desktop = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)
    dto = desktop.get_forecast_workspace(
        project.id,
        selected_forecast_id=first.id,
        line_page=1,
        page_size=1,
    )
    assert dto.selected_forecast_id == first.id
    assert isinstance(dto.versions[0].state["totalEtc"], str)
    assert dto.selected_forecast.fields[0][1] == "USD 150.35"
    assert Decimal(dto.lines[0].state["amount"]) in {
        Decimal("100.25"),
        Decimal("50.10"),
    }
    assert isinstance(dto.lines[0].state["amount"], str)


@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_forecast_master_detail_loads_at_supported_viewports(
    qapp, width: int, height: int
) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
import QtQuick
import workspaces.financials.sections 1.0
Window {
    visible: true
    FinancialsForecastSection {
        id: section
        objectName: "forecastSection"
        anchors.fill: parent
        forecastVersions: ({
            "items": [{"id": "forecast-1"}],
            "page": 1, "pageSize": 50, "total": 1
        })
        selectedForecastId: "forecast-1"
        selectedForecast: ({
            "id": "forecast-1", "title": "Forecast r1",
            "statusLabel": "Approved", "subtitle": "As of 2026-08-01",
            "fields": []
        })
        forecastLines: ({
            "items": [{"id": "line-1"}],
            "page": 1, "pageSize": 50, "total": 1
        })
    }
}
""",
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    root = component.create()
    assert root is not None
    root.setProperty("width", width)
    root.setProperty("height", height)
    root.show()
    qapp.processEvents()

    section = root.findChild(QObject, "forecastSection")
    versions_table = root.findChild(QObject, "forecastVersionsTable")
    lines_table = root.findChild(QObject, "forecastLinesTable")
    assert section is not None
    assert versions_table is not None
    assert lines_table is not None
    assert float(section.property("width")) == width
    assert float(versions_table.property("width")) >= width - 2
    assert float(lines_table.property("width")) >= width - 2
    root.deleteLater()


def test_financials_overview_loader_keeps_loaded_content_height(qapp) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
import QtQuick
import workspaces.financials.panels 1.0
Window {
    visible: true
    width: 1024
    height: 640
    FinancialsDetailPanel {
        id: panel
        objectName: "financialsDetailPanel"
        width: parent.width
        activeDestination: "overview"
        activeSubsection: "summary"
        overviewModel: ({
            "title": "Financials",
            "subtitle": "Overview regression",
            "metrics": [{
                "label": "Budget",
                "value": "XAF 1,000.00",
                "supportingText": "Approved revision 1"
            }]
        })
    }
}
""",
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    root = component.create()
    assert root is not None
    root.show()
    for _ in range(5):
        qapp.processEvents()

    panel = root.findChild(QObject, "financialsDetailPanel")
    loader = root.findChild(QObject, "financialsDestinationLoader")
    overview = root.findChild(QObject, "financialsOverviewSection")
    assert panel is not None
    assert loader is not None
    assert overview is not None
    assert float(loader.property("height")) > 0
    assert float(overview.property("height")) > 0
    assert float(panel.property("implicitHeight")) >= float(overview.property("height"))
    root.deleteLater()


def test_cost_actuals_tab_loads_only_paged_actual_dependencies() -> None:
    api = MagicMock()
    api.list_cost_entries.return_value = FinancialCostEntryPageDto()
    api.get_manual_actual_options.return_value = FinancialManualActualOptionsDto()
    api.list_tasks.return_value = ()

    build_destination_state(
        api,
        destination="costs",
        subsection="actuals",
        selected_project_id="project-1",
        actual_page=3,
        transaction_page_size=25,
    )

    api.list_cost_entries.assert_called_once_with(
        "project-1",
        offset=50,
        limit=25,
        sort_key="metaText",
        sort_direction="desc",
    )
    api.get_manual_actual_options.assert_called_once_with("project-1")
    api.list_tasks.assert_called_once_with("project-1")
    api.get_finance_snapshot.assert_not_called()
    api.get_configuration_workspace.assert_not_called()
    api.get_billing_workspace.assert_not_called()


def test_controls_activity_uses_project_scoped_enterprise_audit_only() -> None:
    finance_api = MagicMock()
    audit_api = MagicMock()
    audit_api.list_recent.return_value = DesktopApiResult(
        ok=True,
        data=(
            AuditEntryDto(
                id="audit-1",
                timestamp=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
                operation="project_budget.approve",
                entity_type="project_budget",
                entity_id="budget-1",
                module="project_management",
                actor_id="user-1",
                actor_username="Finance Manager",
                actor_type="user",
                source="desktop",
                severity="low",
                compliance_tag="financial_control",
            ),
        ),
    )

    state = build_destination_state(
        finance_api,
        audit_api=audit_api,
        destination="controls",
        subsection="activity",
        selected_project_id="project-1",
    )

    assert finance_api.method_calls == []
    audit_api.list_recent.assert_called_once()
    query = audit_api.list_recent.call_args.kwargs
    assert query["limit"] == 100
    assert query["module"] == "project_management"
    assert query["workspace_id"] == "project-1"
    assert "project_budget." in query["operation_prefixes"]
    assert state.activity.total == 1
    assert state.activity.items[0].title == "Finance Manager - Project Budget Approve"


def test_enterprise_audit_projection_filters_module_workspace_and_operation(services) -> None:
    audit = services["enterprise_audit_service"]
    target = audit.record(
        operation="project_budget.approve",
        entity_type="project_budget",
        entity_id="budget-target",
        module="project_management",
        workspace_id="project-r6b-audit",
    )
    audit.record(
        operation="task.update",
        entity_type="task",
        entity_id="task-other-operation",
        module="project_management",
        workspace_id="project-r6b-audit",
    )
    audit.record(
        operation="project_budget.approve",
        entity_type="project_budget",
        entity_id="budget-other-workspace",
        module="project_management",
        workspace_id="project-other",
    )
    audit.record(
        operation="project_budget.approve",
        entity_type="project_budget",
        entity_id="budget-other-module",
        module="inventory_procurement",
        workspace_id="project-r6b-audit",
    )
    services["session"].commit()

    rows = audit.list_recent(
        limit=100,
        module="project_management",
        workspace_id="project-r6b-audit",
        operation_prefixes=("project_budget.", "project_forecast."),
    )

    assert [row.id for row in rows] == [target.id]


def test_finance_overview_reader_is_bounded_and_uses_canonical_controls(services) -> None:
    project = services["project_service"].create_project(
        "R6B bounded overview",
        financial_currency_code="USD",
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6B-OVERVIEW",
        name="R6B Overview",
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved control", currency_code="USD")
    budgets.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Authorized scope",
        amount=Decimal("1000"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id,
        submitted_by="admin",
        expected_version=budget.row_version,
    )
    budgets.approve_budget(
        budget.id,
        approved_by="admin",
        expected_version=budget.row_version,
    )

    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id,
        name="Approved ETC",
        as_of_date=date(2026, 8, 1),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecasts.add_line(
        forecast.id,
        cost_code_id=cost_code.id,
        description="Remaining delivery",
        amount=Decimal("250"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast = forecasts.submit_forecast(
        forecast.id,
        submitted_by="admin",
        expected_version=forecast.row_version,
    )
    forecasts.approve_forecast(
        forecast.id,
        approved_by="admin",
        expected_version=forecast.row_version,
    )

    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test bounded finance overview"
    )
    reader = services["finance_service"]._finance_overview_reader
    with _statement_count(services["session"]) as statements:
        facts = reader.read_overview_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            as_of=date(2026, 8, 27),
        )

    assert len(statements) <= 5
    assert facts.approved_budget == Decimal("1000")
    assert facts.posted_actual == Decimal("0")
    assert facts.open_commitment == Decimal("0")
    assert facts.forecast_etc == Decimal("250")
    assert facts.estimate_at_completion == Decimal("250")
    assert facts.variance_at_completion == Decimal("750")
    assert facts.approved_budget_revision == 1
    assert facts.approved_forecast_revision == 1
