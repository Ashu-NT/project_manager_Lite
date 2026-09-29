from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
    empty_overview,
)
from src.core.modules.project_management.application.financials.cost.engines.cost_breakdown_engine import (
    CostBreakdownEngine,
)
from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostPolicySnapshot,
)
from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.domain.enums import CostType


def test_reporting_breakdown_keeps_exact_money_and_zero_without_baseline_substitution():
    snapshot = CostPolicySnapshot(
        project_id="project", project_currency="USD", budget=Decimal("100"),
        planned_map={(CostType.OTHER, "USD"): Decimal("9007199254740993.01")},
        actual_map={(CostType.OTHER, "USD"): Decimal("0.00")}, committed_map={},
    )
    engine = CostBreakdownEngine()
    row, = engine.build_breakdown_from_snapshot(snapshot)
    assert row.planned == Decimal("9007199254740993.01")
    assert row.actual == Decimal("0.00")
    assert isinstance(row.planned, Decimal)
    assert isinstance(row.actual, Decimal)
    snapshot.planned_map.clear()
    row, = engine.build_breakdown_from_snapshot(snapshot)
    assert row.planned == Decimal(0)
    snapshot.actual_map.clear()
    assert engine.build_breakdown_from_snapshot(snapshot) == []


def test_empty_overview_does_not_manufacture_financial_zero():
    overview = empty_overview(project_id="")
    for metric in ("budget", "actual", "committed", "available"):
        assert getattr(overview, metric) is None
        assert getattr(overview, f"{metric}_label") == "Not available"


def test_source_analytics_exposure_is_actual_plus_commitment_not_forecast():
    from src.core.modules.project_management.application.financials.models import (
        CostSourceRow,
    )
    from src.core.modules.project_management.application.financials.reporting.analytics import (
        build_source_analytics,
    )

    row = CostSourceRow(
        source_key="source", source_label="Source", planned=Decimal(100),
        actual=Decimal(30), committed=Decimal(70), forecast=Decimal(90),
    )
    result, = build_source_analytics([row])
    assert result.exposure == Decimal(100)
    assert result.forecast == Decimal(90)


@pytest.mark.parametrize("budget_id,expected", [(None, None), ("approved-zero", Decimal(0))])
def test_zero_budget_requires_approved_identity_for_headroom_and_availability(budget_id, expected):
    from datetime import date

    from src.core.modules.project_management.contracts.reads.financials.models.finance_overview_facts import (
        FinanceOverviewFacts,
    )
    from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
        FinanceControlFact,
    )

    facts = FinanceOverviewFacts(
        tenant_id="tenant", organization_id="org", project_id="project",
        as_of=date(2026, 9, 29), currency_code="USD",
        control=FinanceControlFact(Decimal(0), Decimal(0), Decimal(0), Decimal(0)),
        approved_budget_id=budget_id, approved_budget_revision=1 if budget_id else None,
        approved_budget_at=None, approved_forecast_id="forecast",
        approved_forecast_revision=1, approved_forecast_as_of=date(2026, 9, 1),
    )
    assert facts.available_after_commitment == expected
    assert facts.budget_headroom == expected


def test_labor_diagnostics_multiply_decimal_rate_and_hours_exactly():
    from datetime import date

    as_of = date(2026, 9, 29)
    facts = SimpleNamespace(
        project_id="project", as_of=as_of,
        tasks=(SimpleNamespace(task_id="task", name="Task"),),
        resources=(SimpleNamespace(resource_id="resource", name="Resource"),),
        assignments=(SimpleNamespace(
            assignment_id="assignment", task_id="task", resource_id="resource",
            hours_logged=0.1,
        ),),
        project_resources=(SimpleNamespace(
            project_resource_id="plan", resource_id="resource", is_active=True,
            planned_hours=0.3,
        ),),
    )
    snapshot = SimpleNamespace(monetary_rate=SimpleNamespace(money=SimpleNamespace(
        amount=Decimal("123456789.1234"), currency=SimpleNamespace(code="USD"),
    )))
    batch = SimpleNamespace(snapshot_for=lambda _: snapshot, unresolved=())
    engine = LaborCostEngine.for_facts(rate_resolver=None, tenant_context_service=None)
    result = engine._calculate_from_finance_facts(
        "project", as_of=as_of, facts=facts, rate_batch=batch,
    )
    row, = result.rows
    planned, = result.planned_rows
    assert row.total_cost == Decimal("12345678.91234")
    assert row.assignments[0].cost == row.total_cost
    assert planned.total_cost == Decimal("37037036.73702")
    assert isinstance(row.hourly_rate, Decimal)
    assert isinstance(planned.hourly_rate, Decimal)
