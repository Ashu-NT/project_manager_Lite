"""Phase 0B - SQL growth attribution
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0B).

Phase 0's measurement found total SQL statement counts growing 164 -> 272 -> 752 across the
small/medium/large fixtures, with `organizations`/`tenants` dominating 53-64% of all statements —
flagged there as a real, measured signal but an *unconfirmed* root cause. This is a focused
diagnostic, not an optimization pass: it exists only to attribute that growth to specific call
sites before Phase 1 designs the Reader SQL, so the Reader can be built to avoid reproducing
whichever pattern is actually responsible.

The Phase 0B tenant/organization diagnosis is retained in the audit as historical evidence. After
Phase 0C, this executable regression test continues to prove the still-unresolved 4 x N resource
lookup and 3 x labor-calculation findings without requiring the removed repository context defect.

Test-only instrumentation - every hook wraps a bound method on an
already-constructed instance for the duration of one measurement, then restores it (same technique
as the Phase 0 measurement harness).
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


@dataclass
class SqlStats:
    total_statements: int = 0
    by_table: Counter = field(default_factory=Counter)


@contextmanager
def measure_sql(session):
    engine = session.get_bind()
    stats = SqlStats()

    def _after(_conn, _cursor, statement, _parameters, _context, _executemany):
        stats.total_statements += 1
        for table in set(_TABLE_NAME_RE.findall(statement)):
            stats.by_table[table] += 1

    event.listen(engine, "after_cursor_execute", _after)
    try:
        yield stats
    finally:
        event.remove(engine, "after_cursor_execute", _after)


class CallLog:
    def __init__(self) -> None:
        self.counts: Counter = Counter()

    def count(self, label: str) -> int:
        return self.counts[label]


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
                log.counts[label] += 1
                return original(*args, **kwargs)

            return _wrapper

        setattr(instance, method_name, _make_wrapper())
    try:
        yield log
    finally:
        for instance, method_name, original in saved:
            setattr(instance, method_name, original)


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
        "Phase 0B Growth Attribution",
        start_date=date(2024, 1, 8),
        end_date=date(2024, 12, 29),
        planned_budget=500000.0,
        currency="EUR",
    )
    pid = project.id

    task_ids: list[str] = []
    for i in range(tasks):
        task = ts.create_task(pid, f"Task {i}", start_date=date(2024, 1, 8), duration_days=5)
        task_ids.append(task.id)

    for i in range(resources):
        resource = rs.create_resource(
            f"Resource {i}", "Developer", hourly_rate=50.0 + i,
            currency_code="EUR", rate_effective_on=date(2024, 1, 8),
        )
        pr = prs.add_to_project(
            project_id=pid, resource_id=resource.id, planned_hours=20.0,
            hourly_rate=50.0 + i, currency_code="EUR",
        )
        assignment = ts.assign_project_resource(
            task_id=task_ids[i % tasks], project_resource_id=pr.id, allocation_percent=50.0,
        )
        ts.set_assignment_hours(assignment.id, 6.0)

    cost_type_cycle = [CostType.MATERIAL, CostType.OVERHEAD, CostType.LABOR]
    for i in range(cost_items):
        cs.add_cost_item(
            project_id=pid,
            task_id=task_ids[i % tasks] if tasks else None,
            description=f"Cost item {i}",
            planned_amount=100.0 + i, committed_amount=80.0 + i, actual_amount=60.0 + i,
            cost_type=cost_type_cycle[i % len(cost_type_cycle)],
            incurred_date=date(2024, 1, 20), currency_code="EUR",
        )
    return pid


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase0b_preserves_resource_lookup_attribution_after_scope_remediation(
    services, size_name, capsys
):
    sizes = _SIZES[size_name]
    pid = _seed_finance_project(services, **sizes)

    finance = services["finance_service"]
    tenant_context = services["tenant_context_service"]
    resource_repo = finance._labor._resource_repo
    as_of = date(2024, 6, 1)

    call_targets = [
        (tenant_context, "get_active_tenant", "tenant_context.get_active_tenant"),
        (tenant_context, "get_active_organization", "tenant_context.get_active_organization"),
        (resource_repo, "get", "resource_repo.get"),
        (finance._rate_resolver, "resolve_many", "rate_resolver.resolve_many"),
        (finance._labor, "calculate_project_labor_details", "LaborCostEngine.calculate_project_labor_details"),
    ]

    with measure_sql(services["session"]) as sql_stats, count_calls(call_targets) as call_log:
        t0 = time.perf_counter()
        finance.get_finance_snapshot(pid, as_of=as_of)
        wall_time = time.perf_counter() - t0

    report = "\n".join([
        f"\n=== Phase 0B growth attribution [{size_name}] "
        f"(resources={sizes['resources']}, tasks={sizes['tasks']}, cost_items={sizes['cost_items']}) ===",
        f"wall_time_s={wall_time:.6f}",
        f"sql_total_statements={sql_stats.total_statements}",
        f"sql_by_table={dict(sql_stats.by_table)}",
        f"tenant_context.get_active_tenant_calls={call_log.count('tenant_context.get_active_tenant')}",
        f"tenant_context.get_active_organization_calls={call_log.count('tenant_context.get_active_organization')}",
        f"resource_repo.get_calls={call_log.count('resource_repo.get')}",
        f"rate_resolver.resolve_many_calls={call_log.count('rate_resolver.resolve_many')}",
        f"LaborCostEngine_invocations={call_log.count('LaborCostEngine.calculate_project_labor_details')}",
    ])
    print(report)
    with capsys.disabled():
        print(report)

    labor_invocations = call_log.count("LaborCostEngine.calculate_project_labor_details")
    assert labor_invocations == 3
    assert call_log.count("resource_repo.get") == 4 * sizes["resources"]

    # Full-context application flows still legitimately hydrate tenant/organization entities.
    # Phase 0C removes the repository-driven, size-dependent component; it does not remove those
    # entity-dependent calls.
    tenant_lookups = call_log.count("tenant_context.get_active_tenant")
    org_lookups = call_log.count("tenant_context.get_active_organization")
    assert sql_stats.by_table.get("tenants", 0) >= tenant_lookups * 0.9
    assert sql_stats.by_table.get("organizations", 0) >= org_lookups * 0.9

    # The resource lookup loop remains Phase 1 work. Phase 0C's dedicated contract and
    # architecture tests guarantee those calls no longer trigger full context hydration.
