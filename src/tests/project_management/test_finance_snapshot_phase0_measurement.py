"""Phase 0 measurement harness for the Finance Snapshot CQRS pilot.

Test-only instrumentation (docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md,
§18 Phase 0). No production code is modified by this file — every hook below wraps a bound method
on an already-constructed instance for the duration of one measurement, then restores it.

Measures, at three fixture sizes, the exact dimensions Phase 0 requires: SQL statement count
(grouped by table), database execution time, python-side time, wall-clock total, session
identity-map growth (an ORM-object-construction proxy), and the repeated-call counts the audit
document's canonical table (§7) originally predicted from the source
(``FinanceService.get_finance_snapshot`` / ``CostPolicyEngine`` / ``LaborCostEngine``).

The historical Phase 0 baseline remains in the audit. These assertions now enforce the accepted
Phase 1 budget and one-call orchestration contract across all three fixture sizes.
"""

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

from src.core.modules.project_management.domain.enums import CostType

_TABLE_NAME_RE = re.compile(r'(?:FROM|INTO|UPDATE|JOIN)\s+"?(\w+)"?', re.IGNORECASE)


# ---------------------------------------------------------------------------
# SQL-level instrumentation (engine events only — no repository access)
# ---------------------------------------------------------------------------


@dataclass
class SqlStats:
    total_statements: int = 0
    total_db_time_s: float = 0.0
    by_table: Counter = field(default_factory=Counter)
    by_exact_statement: Counter = field(default_factory=Counter)


@contextmanager
def measure_sql(session):
    engine = session.get_bind()
    stats = SqlStats()
    starts: list[float] = []

    def _before(_conn, _cursor, _statement, _parameters, _context, _executemany):
        starts.append(time.perf_counter())

    def _after(_conn, _cursor, statement, _parameters, _context, _executemany):
        elapsed = time.perf_counter() - starts.pop()
        stats.total_statements += 1
        stats.total_db_time_s += elapsed
        for table in set(_TABLE_NAME_RE.findall(statement)):
            stats.by_table[table] += 1
        stats.by_exact_statement[" ".join(statement.split())] += 1

    event.listen(engine, "before_cursor_execute", _before)
    event.listen(engine, "after_cursor_execute", _after)
    try:
        yield stats
    finally:
        event.remove(engine, "before_cursor_execute", _before)
        event.remove(engine, "after_cursor_execute", _after)


# ---------------------------------------------------------------------------
# Named-call instrumentation (wraps specific bound methods on the already-
# constructed FinanceService/CostPolicyEngine/LaborCostEngine instances for
# the duration of one measurement, then restores the originals)
# ---------------------------------------------------------------------------


class CallLog:
    def __init__(self) -> None:
        self.entries: list[tuple[str, float, int | None]] = []

    def count(self, label: str) -> int:
        return sum(1 for entry_label, _, _ in self.entries if entry_label == label)

    def rows(self, label: str) -> int:
        return sum(
            size for entry_label, _, size in self.entries if entry_label == label and size is not None
        )


@contextmanager
def count_calls(targets: list[tuple[object, str, str]]):
    """``targets``: (instance, method_name, label) triples. Restores originals on exit."""
    log = CallLog()
    saved: list[tuple[object, str, object]] = []
    for instance, method_name, label in targets:
        original = getattr(instance, method_name)
        saved.append((instance, method_name, original))

        def _make_wrapper(original=original, label=label):
            @functools.wraps(original)
            def _wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = original(*args, **kwargs)
                elapsed = time.perf_counter() - start
                try:
                    size = len(result)
                except TypeError:
                    size = None
                log.entries.append((label, elapsed, size))
                return result

            return _wrapper

        setattr(instance, method_name, _make_wrapper())
    try:
        yield log
    finally:
        for instance, method_name, original in saved:
            setattr(instance, method_name, original)


# ---------------------------------------------------------------------------
# Fixture seeding at 3 sizes
# ---------------------------------------------------------------------------

_SIZES = {
    "small": {"resources": 1, "tasks": 2, "cost_items": 2},
    "medium": {"resources": 10, "tasks": 15, "cost_items": 30},
    "large": {"resources": 50, "tasks": 60, "cost_items": 150},
}


def _seed_finance_project(services, *, resources: int, tasks: int, cost_items: int) -> str:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    cs = services["cost_service"]

    project = ps.create_project(
        "Phase 0 Measurement",
        start_date=date(2024, 1, 8),
        end_date=date(2024, 12, 29),
        planned_budget=500000.0,
        currency="EUR",
    )
    pid = project.id

    task_ids: list[str] = []
    for i in range(tasks):
        task = ts.create_task(
            pid,
            f"Task {i}",
            start_date=date(2024, 1, 8),
            duration_days=5,
        )
        task_ids.append(task.id)

    resource_ids: list[str] = []
    for i in range(resources):
        resource = rs.create_resource(
            f"Resource {i}",
            "Developer",
            hourly_rate=50.0 + i,
            currency_code="EUR",
            rate_effective_on=date(2024, 1, 8),
        )
        pr = prs.add_to_project(
            project_id=pid,
            resource_id=resource.id,
            planned_hours=20.0,
            hourly_rate=50.0 + i,
            currency_code="EUR",
        )
        assignment = ts.assign_project_resource(
            task_id=task_ids[i % tasks],
            project_resource_id=pr.id,
            allocation_percent=50.0,
        )
        ts.set_assignment_hours(assignment.id, 6.0)
        resource_ids.append(resource.id)

    cost_type_cycle = [CostType.MATERIAL, CostType.OVERHEAD, CostType.LABOR]
    for i in range(cost_items):
        cs.add_cost_item(
            project_id=pid,
            task_id=task_ids[i % tasks] if tasks else None,
            description=f"Cost item {i}",
            planned_amount=100.0 + i,
            committed_amount=80.0 + i,
            actual_amount=60.0 + i,
            cost_type=cost_type_cycle[i % len(cost_type_cycle)],
            incurred_date=date(2024, 1, 20),
            currency_code="EUR",
        )
    return pid


# ---------------------------------------------------------------------------
# The measurement test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase0_measure_get_finance_snapshot(services, size_name, capsys):
    sizes = _SIZES[size_name]
    pid = _seed_finance_project(
        services,
        resources=sizes["resources"],
        tasks=sizes["tasks"],
        cost_items=sizes["cost_items"],
    )

    finance = services["finance_service"]
    session = services["session"]
    as_of = date(2024, 6, 1)

    call_targets = [
        (finance._finance_snapshot_reader, "read_facts", "FinanceSnapshotReader.read_facts"),
        (finance._cost_repo, "list_by_project", "cost_repo.list_by_project"),
        (finance._project_resource_repo, "list_by_project", "project_resource_repo.list_by_project"),
        (finance._task_repo, "list_by_project", "task_repo.list_by_project"),
        (finance._rate_resolver, "resolve_many", "rate_resolver.resolve_many"),
        (finance._labor, "calculate_project_labor_details", "LaborCostEngine.calculate_project_labor_details"),
        (finance._project_repo, "get", "project_repo.get"),
    ]

    identity_before = len(session.identity_map)
    with measure_sql(session) as sql_stats, count_calls(call_targets) as call_log:
        t0 = time.perf_counter()
        snapshot = finance.get_finance_snapshot(pid, as_of=as_of)
        wall_time = time.perf_counter() - t0
    identity_after = len(session.identity_map)

    db_time = sql_stats.total_db_time_s
    python_time = max(0.0, wall_time - db_time)

    report_lines = [
        f"\n=== Phase 0 measurement: get_finance_snapshot [{size_name}] "
        f"(resources={sizes['resources']}, tasks={sizes['tasks']}, cost_items={sizes['cost_items']}) ===",
        f"wall_time_s={wall_time:.6f} db_time_s={db_time:.6f} python_time_s={python_time:.6f}",
        f"sql_total_statements={sql_stats.total_statements}",
        f"sql_by_table={dict(sql_stats.by_table)}",
        f"identity_map_delta={identity_after - identity_before}",
        f"named_call_counts: "
        f"FinanceSnapshotReader.read_facts={call_log.count('FinanceSnapshotReader.read_facts')} "
        f"cost_repo.list_by_project={call_log.count('cost_repo.list_by_project')} "
        f"project_resource_repo.list_by_project={call_log.count('project_resource_repo.list_by_project')} "
        f"task_repo.list_by_project={call_log.count('task_repo.list_by_project')} "
        f"rate_resolver.resolve_many={call_log.count('rate_resolver.resolve_many')} "
        f"LaborCostEngine.calculate_project_labor_details={call_log.count('LaborCostEngine.calculate_project_labor_details')} "
        f"project_repo.get={call_log.count('project_repo.get')}",
        f"named_call_rows_returned: "
        f"cost_repo.list_by_project={call_log.rows('cost_repo.list_by_project')} "
        f"project_resource_repo.list_by_project={call_log.rows('project_resource_repo.list_by_project')} "
        f"task_repo.list_by_project={call_log.rows('task_repo.list_by_project')}",
        f"snapshot_ledger_rows={len(snapshot.ledger)}",
    ]
    report = "\n".join(report_lines)
    print(report)
    with capsys.disabled():
        print(report)

    assert call_log.count("FinanceSnapshotReader.read_facts") == 1
    assert call_log.count("cost_repo.list_by_project") == 0
    assert call_log.count("project_resource_repo.list_by_project") == 0
    assert call_log.count("task_repo.list_by_project") == 0
    assert call_log.count("project_repo.get") == 0
    assert call_log.count("rate_resolver.resolve_many") == 1
    assert call_log.count("LaborCostEngine.calculate_project_labor_details") == 1
    assert sql_stats.total_statements <= 70
