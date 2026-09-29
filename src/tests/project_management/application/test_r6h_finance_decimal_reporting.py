from decimal import Decimal
from types import SimpleNamespace

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
