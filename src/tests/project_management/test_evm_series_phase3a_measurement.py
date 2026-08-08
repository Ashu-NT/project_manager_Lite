"""Phase 3A baseline and post-cutover guard for the monthly EVM series."""

from __future__ import annotations

import calendar
import functools
import re
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date

import pytest
from sqlalchemy import event

from src.core.modules.project_management.application.financials.earned_value.evm_calculator import (
    EarnedValueCalculator,
)
from src.core.modules.project_management.domain.enums import CostType


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
        context._phase3a_started = time.perf_counter()

    def _after(_conn, _cursor, statement, _parameters, context, _executemany):
        stats.total_statements += 1
        stats.total_db_time_s += time.perf_counter() - context._phase3a_started
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
def count_calculations():
    original = EarnedValueCalculator.calculate
    counts: Counter = Counter()

    @functools.wraps(original)
    def _wrapped(self, *args, **kwargs):
        counts["EarnedValueCalculator.calculate"] += 1
        return original(self, *args, **kwargs)

    EarnedValueCalculator.calculate = _wrapped
    try:
        yield counts
    finally:
        EarnedValueCalculator.calculate = original


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _month_end(value: date) -> date:
    return date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])


def _seed_series_project(services, *, periods: int, resources: int = 2) -> tuple[str, str, date]:
    start = date(2023, 1, 2)
    as_of = _month_end(_add_months(start, periods - 1))
    project = services["project_service"].create_project(
        f"Phase 3A EVM {periods}",
        start_date=start,
        end_date=_month_end(_add_months(start, periods + 1)),
        planned_budget=100000.0,
        currency="EUR",
    )
    task = services["task_service"].create_task(
        project.id,
        "Measured work package",
        start_date=start,
        duration_days=periods * 20,
    )
    for index in range(resources):
        resource = services["resource_service"].create_resource(
            f"EVM Resource {index}",
            "Engineer",
            hourly_rate=50.0 + index,
            currency_code="EUR",
            rate_effective_on=start,
        )
        project_resource = services["project_resource_service"].add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=40.0,
            hourly_rate=50.0 + index,
            currency_code="EUR",
        )
        assignment = services["task_service"].assign_project_resource(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=100.0 / resources,
        )
        services["task_service"].set_assignment_hours(assignment.id, 8.0)
    services["cost_service"].add_cost_item(
        project_id=project.id,
        task_id=task.id,
        description="Measured direct cost",
        planned_amount=5000.0,
        committed_amount=2500.0,
        actual_amount=2000.0,
        cost_type=CostType.MATERIAL,
        incurred_date=start,
        currency_code="EUR",
    )
    baseline = services["baseline_service"].create_baseline(
        project.id,
        "Phase 3A baseline",
        rate_as_of=start,
    )
    services["task_service"].update_progress(task.id, percent_complete=50.0)
    return project.id, baseline.id, as_of


@pytest.mark.parametrize("periods", [3, 12, 24])
def test_phase3a_measure_evm_series_growth(services, periods, capsys) -> None:
    project_id, baseline_id, as_of = _seed_series_project(services, periods=periods)
    reporting = services["reporting_service"]
    targets = [
        (reporting._evm_series_reader, "read_facts", "evm_series_reader.read_facts"),
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
            reporting._rate_resolver,
            "resolve_many_dates",
            "rate_resolver.resolve_many_dates",
        ),
        (
            reporting._rate_resolver._reader,
            "list_resource_contexts",
            "rate_reader.list_resource_contexts",
        ),
        (
            reporting._rate_resolver._reader,
            "list_candidates_for_range",
            "rate_reader.list_candidates_for_range",
        ),
        (
            reporting._calendar,
            "working_day_dates_between",
            "calendar.working_day_dates_between",
        ),
        (
            reporting,
            "calculate_project_labor_details",
            "ReportingService.calculate_project_labor_details",
        ),
    ]

    with (
        measure_sql(services["session"]) as sql_stats,
        count_calls(targets) as calls,
        count_calculations() as calculations,
    ):
        started = time.perf_counter()
        series = reporting.get_evm_series(
            project_id,
            baseline_id=baseline_id,
            as_of=as_of,
        )
        wall_time = time.perf_counter() - started

    report = "\n".join(
        (
            f"\n=== Phase 3A EVM post-cutover [periods={periods}] ===",
            f"wall_time_s={wall_time:.6f}",
            f"db_time_s={sql_stats.total_db_time_s:.6f}",
            f"sql_total_statements={sql_stats.total_statements}",
            f"sql_by_table={dict(sql_stats.by_table)}",
            f"call_counts={dict(calls | calculations)}",
        )
    )
    print(report)
    with capsys.disabled():
        print(report)

    assert len(series) == periods
    assert calculations["EarnedValueCalculator.calculate"] == periods
    assert sql_stats.total_statements == 50
    assert calls["evm_series_reader.read_facts"] == 1
    assert calls["rate_resolver.resolve_many_dates"] == 1
    assert calls["rate_reader.list_resource_contexts"] == 1
    assert calls["rate_reader.list_candidates_for_range"] == 1
    assert calls["calendar.working_day_dates_between"] == 1
    assert calls["baseline_repo.get_baseline"] == 0
    assert calls["baseline_repo.list_tasks"] == 0
    assert calls["task_repo.list_by_project"] == 0
    assert calls["cost_repo.list_by_project"] == 0
    assert calls["project_resource_repo.list_by_project"] == 0
    assert calls["assignment_repo.list_by_tasks"] == 0
    assert calls["resource_repo.get"] == 0
    assert calls["rate_resolver.resolve_many"] == 0
    assert calls["ReportingService.calculate_project_labor_details"] == 0
    assert calls["project_repo.get"] == 0
