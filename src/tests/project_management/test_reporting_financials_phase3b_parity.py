from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.financials.costs.cost_breakdown_engine import (
    CostBreakdownEngine,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyFinanceSnapshotReader,
)
from src.tests.project_management.test_finance_snapshot_phase0_measurement import (
    _seed_finance_project,
)


def test_reporting_financial_reads_match_repository_backed_engines(services) -> None:
    project_id = _seed_finance_project(
        services,
        resources=3,
        tasks=4,
        cost_items=9,
    )
    as_of = date(2024, 6, 1)
    services["cost_service"].add_cost_item(
        project_id=project_id,
        description="Future direct cost",
        planned_amount=0.0,
        committed_amount=0.0,
        actual_amount=700.0,
        cost_type=CostType.OVERHEAD,
        incurred_date=date(2025, 1, 1),
        currency_code="EUR",
    )
    services["cost_service"].add_cost_item(
        project_id=project_id,
        description="Out-of-scope currency",
        planned_amount=900.0,
        committed_amount=800.0,
        actual_amount=700.0,
        cost_type=CostType.MATERIAL,
        incurred_date=date(2024, 2, 1),
        currency_code="USD",
    )
    baseline = services["baseline_service"].create_baseline(
        project_id,
        "Phase 3B parity baseline",
        rate_as_of=as_of,
    )
    reporting = services["reporting_service"]

    legacy_policy = reporting._make_cost_policy_engine()
    legacy_snapshot = legacy_policy.build_snapshot(project_id, as_of=as_of)
    expected_totals = legacy_policy._totals_from_snapshot(legacy_snapshot)
    manual_raw = {"planned": 0.0, "committed": 0.0, "actual": 0.0}
    for item in reporting._cost_repo.list_by_project(project_id):
        if item.cost_type != CostType.LABOR or item.currency_code != "EUR":
            continue
        manual_raw["planned"] += item.planned_amount
        manual_raw["committed"] += item.committed_amount
        if item.incurred_date is None or item.incurred_date <= as_of:
            manual_raw["actual"] += item.actual_amount
    expected_source = legacy_policy._source_breakdown_from_snapshot(
        legacy_snapshot,
        manual_raw=manual_raw,
    )
    baseline_tasks = reporting._baseline_repo.list_tasks(baseline.id)
    expected_breakdown = CostBreakdownEngine(
        cost_policy_engine=reporting._make_cost_policy_engine(),
    ).build_breakdown_from_snapshot(
        legacy_snapshot,
        baseline_tasks=baseline_tasks,
    )

    assert reporting.get_project_cost_control_totals(project_id, as_of=as_of) == expected_totals
    assert reporting.get_project_cost_source_breakdown(project_id, as_of=as_of) == expected_source
    assert reporting.get_cost_breakdown(
        project_id,
        as_of=as_of,
        baseline_id=baseline.id,
    ) == expected_breakdown

    explicit_evm = reporting.get_earned_value(
        project_id,
        as_of=as_of,
        baseline_id=baseline.id,
    )
    latest_evm = reporting.get_earned_value(
        project_id,
        as_of=as_of,
        baseline_id=None,
    )
    assert explicit_evm == latest_evm
    assert explicit_evm.AC == expected_totals.actual
    assert explicit_evm.BAC == sum(task.baseline_planned_cost for task in baseline_tasks)


def test_reporting_cost_runtime_uses_concrete_finance_reader(services, monkeypatch) -> None:
    project_id = _seed_finance_project(
        services,
        resources=1,
        tasks=2,
        cost_items=2,
    )
    reporting = services["reporting_service"]
    reader = reporting._finance_snapshot_reader
    assert isinstance(reader, SqlAlchemyFinanceSnapshotReader)

    calls = 0
    original = reader.read_facts

    def counted_read_facts(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(reader, "read_facts", counted_read_facts)
    totals = reporting.get_project_cost_control_totals(
        project_id,
        as_of=date(2024, 6, 1),
    )
    assert totals.project_id == project_id
    assert calls == 1
