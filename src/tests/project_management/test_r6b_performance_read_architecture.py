from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials.models.performance import (
    FinancialCostPhasingDto,
    FinancialEvmDto,
)
from src.core.modules.project_management.application.financials.performance_query import (
    ProjectFinancePerformanceQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingPeriodFact,
    CostPhasingQuery,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.presenters.financials.destination_builder import (
    build_destination_state,
)


@contextmanager
def _statement_count(session):
    engine = session.get_bind()
    statements: list[str] = []

    def before_cursor(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)


def _basis(**overrides):
    values = {
        "currency_code": "XAF",
        "approved_budget_revision": 2,
        "approved_forecast_revision": 3,
        "approved_forecast_as_of": date(2026, 8, 1),
        "variance_at_completion": Decimal("125"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _query(monkeypatch, *, reader=None, evm=None, baseline=None):
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_permission",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_project_permission",
        lambda *_args, **_kwargs: None,
    )
    context = MagicMock()
    context.require_active_scope_ids.return_value = SimpleNamespace(
        tenant_id="tenant-1", organization_id="org-1"
    )
    overview = MagicMock()
    overview.read_overview_facts.return_value = _basis()
    return ProjectFinancePerformanceQuery(
        performance_reader=reader or MagicMock(),
        overview_reader=overview,
        earned_value_authority=evm or MagicMock(),
        baseline_variance_authority=baseline or MagicMock(
            list_baselines=MagicMock(return_value=[])
        ),
        tenant_context_service=context,
    )


def test_performance_destination_loads_only_requested_subsection() -> None:
    api = MagicMock()
    api.get_performance_evm.return_value = FinancialEvmDto(
        project_id="project-1",
        as_of_date=date(2026, 8, 28),
        availability="baseline_unavailable",
        unavailable_reason="No approved baseline.",
    )

    state = build_destination_state(
        api,
        destination="performance",
        subsection="evm",
        selected_project_id="project-1",
        performance_as_of_date=date(2026, 8, 28),
    )

    assert state.evm_basis.empty_state == "No approved baseline."
    assert api.method_calls == [
        call.get_performance_evm(
            "project-1", as_of_date=date(2026, 8, 28), baseline_id=None
        )
    ]


def test_cost_phasing_query_preserves_scope_range_and_decimal_facts(monkeypatch) -> None:
    reader = MagicMock()
    reader.read_cost_phasing.return_value = CostPhasingFacts(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        as_of_date=date(2026, 8, 28),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 8, 28),
        granularity="month",
        currency_code="XAF",
        periods=(
            CostPhasingPeriodFact(
                period_key="2026-08",
                period_start=date(2026, 8, 1),
                period_end=date(2026, 8, 31),
                planned_cost=Decimal("10.25"),
                open_commitment=Decimal("2.50"),
                posted_actual=Decimal("1.25"),
                forecast_cost=Decimal("4.00"),
                exposure=Decimal("7.75"),
                currency_code="XAF",
            ),
        ),
        approved_budget_id="budget-1",
        approved_budget_revision=2,
        approved_forecast_id="forecast-1",
        approved_forecast_revision=3,
        approved_forecast_as_of=date(2026, 8, 1),
    )
    query = _query(monkeypatch, reader=reader)

    result = query.get_cost_phasing(
        "project-1",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 8, 28),
    )

    assert result.periods[0].planned_cost == Decimal("10.25")
    reader.read_cost_phasing.assert_called_once_with(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        query=CostPhasingQuery(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 8, 28),
            granularity="month",
        ),
    )


def test_evm_calculator_failure_is_contained_but_permission_denial_is_not(monkeypatch) -> None:
    calculator = MagicMock()
    calculator.get_earned_value.side_effect = NameError("known calculator defect")
    query = _query(monkeypatch, evm=calculator)

    unavailable = query.get_evm("project-1", as_of_date=date(2026, 8, 28))

    assert unavailable.availability == "calculator_error"
    assert unavailable.unavailable_reason == "Earned value is temporarily unavailable."

    calculator.get_earned_value.side_effect = BusinessRuleError(
        "finance.read denied", code="PERMISSION_DENIED"
    )
    with pytest.raises(BusinessRuleError, match="finance.read denied"):
        query.get_evm("project-1", as_of_date=date(2026, 8, 28))


def test_variance_metrics_keep_vac_and_budget_pressure_distinct(monkeypatch) -> None:
    query = _query(monkeypatch)

    facts = query.get_variance("project-1", as_of_date=date(2026, 8, 28))
    metrics = {item.metric_code: item for item in facts.metrics}

    assert metrics["vac"].value == Decimal("125")
    assert metrics["budget_pressure"].value == Decimal("-125")
    assert "favorable" in metrics["vac"].sign_convention
    assert "overrun" in metrics["budget_pressure"].sign_convention
    assert metrics["period_actual_vs_planned"].availability == "period_required"


def test_sql_cost_phasing_reader_is_bounded_and_rejects_wrong_scope(services, session) -> None:
    project = services["project_service"].create_project(
        "R6B Performance reader", financial_currency_code="XAF"
    )
    query = services["finance_performance_query"]

    with _statement_count(session) as statements:
        facts = query.get_cost_phasing(
            project.id,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )

    assert facts.project_id == project.id
    assert facts.currency_code == "XAF"
    assert len(statements) <= 6

    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test Performance scope"
    )
    assert query._performance_reader.read_cost_phasing(
        tenant_id=scope.tenant_id,
        organization_id="wrong-organization",
        project_id=project.id,
        query=CostPhasingQuery(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        ),
    ) is None
