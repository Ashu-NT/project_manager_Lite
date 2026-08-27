from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import MagicMock, call

from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationWorkspaceDto,
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
