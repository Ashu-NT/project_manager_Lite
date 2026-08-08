"""Phase 3B baseline for standalone Reporting cost and EVM reads."""

from __future__ import annotations

import functools
import re
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date

import pytest
from sqlalchemy import event

from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.application.financials.costs.labor_cost import (
    LaborCostEngine,
)
from src.tests.project_management.test_finance_snapshot_phase0_measurement import (
    _SIZES,
    _seed_finance_project,
)


_TABLE_NAME_RE = re.compile(r'(?:FROM|INTO|UPDATE|JOIN)\s+"?(\w+)"?', re.IGNORECASE)


@dataclass
class SqlStats:
    total_statements: int = 0
    total_db_time_s: float = 0.0
    by_table: Counter = field(default_factory=Counter)


@contextmanager
def measure_sql(session):
    engine = session.get_bind()
    stats = SqlStats()

    def _before(_conn, _cursor, _statement, _parameters, context, _executemany):
        context._phase3b_started = time.perf_counter()

    def _after(_conn, _cursor, statement, _parameters, context, _executemany):
        stats.total_statements += 1
        stats.total_db_time_s += time.perf_counter() - context._phase3b_started
        for table in set(_TABLE_NAME_RE.findall(statement)):
            stats.by_table[table] += 1

    event.listen(engine, "before_cursor_execute", _before)
    event.listen(engine, "after_cursor_execute", _after)
    try:
        yield stats
    finally:
        event.remove(engine, "before_cursor_execute", _before)
        event.remove(engine, "after_cursor_execute", _after)


@contextmanager
def count_calls(targets: list[tuple[object, str, str]]):
    counts: Counter = Counter()
    saved: list[tuple[object, str, object]] = []
    for instance, method_name, label in targets:
        original = getattr(instance, method_name)
        saved.append((instance, method_name, original))

        def _wrapper(*args, _original=original, _label=label, **kwargs):
            counts[_label] += 1
            return _original(*args, **kwargs)

        functools.update_wrapper(_wrapper, original)
        setattr(instance, method_name, _wrapper)
    try:
        yield counts
    finally:
        for instance, method_name, original in saved:
            setattr(instance, method_name, original)


@contextmanager
def count_policy_builds():
    original_build = CostPolicyEngine.build_snapshot
    original_compose = CostPolicyEngine.compose_from_facts
    original_labor = LaborCostEngine.calculate_project_labor_details
    counts: Counter = Counter()

    @functools.wraps(original_build)
    def _build(self, *args, **kwargs):
        counts["CostPolicyEngine.build_snapshot"] += 1
        return original_build(self, *args, **kwargs)

    @functools.wraps(original_compose)
    def _compose(self, *args, **kwargs):
        counts["CostPolicyEngine.compose_from_facts"] += 1
        return original_compose(self, *args, **kwargs)

    @functools.wraps(original_labor)
    def _labor(self, *args, **kwargs):
        counts["LaborCostEngine.calculate_project_labor_details"] += 1
        return original_labor(self, *args, **kwargs)

    CostPolicyEngine.build_snapshot = _build
    CostPolicyEngine.compose_from_facts = _compose
    LaborCostEngine.calculate_project_labor_details = _labor
    try:
        yield counts
    finally:
        CostPolicyEngine.build_snapshot = original_build
        CostPolicyEngine.compose_from_facts = original_compose
        LaborCostEngine.calculate_project_labor_details = original_labor


def _operations(reporting, project_id: str, baseline_id: str):
    as_of = date(2024, 6, 1)
    return (
        (
            "cost_totals",
            lambda: reporting.get_project_cost_control_totals(project_id, as_of=as_of),
        ),
        (
            "cost_source",
            lambda: reporting.get_project_cost_source_breakdown(project_id, as_of=as_of),
        ),
        (
            "cost_breakdown",
            lambda: reporting.get_cost_breakdown(
                project_id,
                as_of=as_of,
                baseline_id=baseline_id,
            ),
        ),
        (
            "earned_value",
            lambda: reporting.get_earned_value(
                project_id,
                as_of=as_of,
                baseline_id=baseline_id,
            ),
        ),
    )


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase3b_measure_reporting_financial_reads(services, size_name, capsys) -> None:
    sizes = _SIZES[size_name]
    project_id = _seed_finance_project(services, **sizes)
    baseline = services["baseline_service"].create_baseline(
        project_id,
        "Phase 3B baseline",
        rate_as_of=date(2024, 6, 1),
    )
    reporting = services["reporting_service"]
    targets = [
        (
            reporting._finance_snapshot_reader,
            "read_facts",
            "FinanceSnapshotReader.read_facts",
        ),
        (reporting._evm_series_reader, "read_facts", "EvmSeriesReader.read_facts"),
        (reporting._project_repo, "get", "project_repo.get"),
        (reporting._baseline_repo, "get_baseline", "baseline_repo.get_baseline"),
        (reporting._baseline_repo, "list_tasks", "baseline_repo.list_tasks"),
        (reporting._task_repo, "list_by_project", "task_repo.list_by_project"),
        (reporting._cost_repo, "list_by_project", "cost_repo.list_by_project"),
        (
            reporting._project_resource_repo,
            "list_by_project",
            "project_resource_repo.list_by_project",
        ),
        (reporting._assignment_repo, "list_by_tasks", "assignment_repo.list_by_tasks"),
        (reporting._resource_repo, "get", "resource_repo.get"),
        (reporting._rate_resolver, "resolve_many", "rate_resolver.resolve_many"),
        (
            reporting,
            "calculate_project_labor_details",
            "ReportingService.calculate_project_labor_details",
        ),
    ]

    for operation_name, operation in _operations(reporting, project_id, baseline.id):
        identity_before = len(services["session"].identity_map)
        with (
            measure_sql(services["session"]) as sql_stats,
            count_calls(targets) as calls,
            count_policy_builds() as policy_builds,
        ):
            started = time.perf_counter()
            result = operation()
            wall_time = time.perf_counter() - started
        identity_delta = len(services["session"].identity_map) - identity_before
        report = "\n".join(
            (
                f"\n=== Phase 3B post-cutover [{size_name}:{operation_name}] ===",
                f"wall_time_s={wall_time:.6f}",
                f"db_time_s={sql_stats.total_db_time_s:.6f}",
                f"sql_total_statements={sql_stats.total_statements}",
                f"sql_by_table={dict(sql_stats.by_table)}",
                f"identity_map_delta={identity_delta}",
                f"call_counts={dict(calls | policy_builds)}",
            )
        )
        print(report)
        with capsys.disabled():
            print(report)

        assert result is not None
        uses_evm_reader = operation_name in {"cost_breakdown", "earned_value"}
        assert sql_stats.total_statements == (12 if uses_evm_reader else 10)
        assert calls["FinanceSnapshotReader.read_facts"] == (0 if uses_evm_reader else 1)
        assert calls["EvmSeriesReader.read_facts"] == (1 if uses_evm_reader else 0)
        assert policy_builds["CostPolicyEngine.build_snapshot"] == 0
        assert policy_builds["CostPolicyEngine.compose_from_facts"] == 1
        assert policy_builds["LaborCostEngine.calculate_project_labor_details"] == 1
        assert calls["project_resource_repo.list_by_project"] == 0
        assert calls["assignment_repo.list_by_tasks"] == 0
        assert calls["resource_repo.get"] == 0
        assert calls["rate_resolver.resolve_many"] == 1
        assert calls["ReportingService.calculate_project_labor_details"] == 0
        assert calls["cost_repo.list_by_project"] == 0
        assert calls["task_repo.list_by_project"] == 0
        assert calls["project_repo.get"] == 0
        assert calls["baseline_repo.get_baseline"] == 0
        assert calls["baseline_repo.list_tasks"] == 0
