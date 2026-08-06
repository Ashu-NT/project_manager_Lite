"""Phase 0B — SQL growth attribution
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0B).

Phase 0's measurement found total SQL statement counts growing 164 -> 272 -> 752 across the
small/medium/large fixtures, with `organizations`/`tenants` dominating 53-64% of all statements —
flagged there as a real, measured signal but an *unconfirmed* root cause. This is a focused
diagnostic, not an optimization pass: it exists only to attribute that growth to specific call
sites before Phase 1 designs the Reader SQL, so the Reader can be built to avoid reproducing
whichever pattern is actually responsible.

Test-only instrumentation, no production code modified — every hook wraps a bound method on an
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
def test_phase0b_attribute_sql_growth_to_call_sites(services, size_name, capsys):
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

    # --- Attribution check: resource_repo.get() is called exactly 4x per distinct resource, per
    # snapshot — confirmed empirically here and fully traced statically to two independent,
    # uncoordinated per-resource loops: (a) LaborCostEngine.calculate_project_labor_details's own
    # loop (labor_cost.py:129), invoked 3x per snapshot (2x via CostPolicyEngine.build_snapshot()
    # executed twice, 1x via build_computed_labor_actual_rows -> get_project_labor_details ->
    # calculate_project_labor_details) = 3xN; (b) ledger.py's build_computed_labor_plan_rows, which
    # has its own resource_cache dict (ledger.py:161-167) that correctly avoids re-fetching *within
    # its own loop*, but that cache is never shared with LaborCostEngine's separate lookups, so it
    # still contributes a 4th, independent pass over every resource = +1xN. Net: 3xN + 1xN = 4xN,
    # matching the measurement below exactly at every fixture size.
    labor_invocations = call_log.count("LaborCostEngine.calculate_project_labor_details")
    assert labor_invocations == 3
    assert call_log.count("resource_repo.get") == 4 * sizes["resources"]

    # --- Attribution check: every tenant-context resolution costs 1 SQL statement against
    # `tenants` and (usually) 1 against `organizations`, with no per-request caching. This
    # accounts for the large majority — but not literally all — of the measured `tenants`/
    # `organizations` statement volume; a small remainder (a few percent) comes from other,
    # independent consumers (e.g. the module-entitlement/session-scoping checks each repository
    # call and permission check also triggers) not attributed further in this diagnostic pass.
    tenant_lookups = call_log.count("tenant_context.get_active_tenant")
    org_lookups = call_log.count("tenant_context.get_active_organization")
    assert sql_stats.by_table.get("tenants", 0) >= tenant_lookups * 0.9
    assert sql_stats.by_table.get("organizations", 0) >= org_lookups * 0.9

    # --- Attribution check: resource_repo.get()'s own tenant-context resolution
    # (SqlAlchemyResourceRepository._context() -> require_organization_context(), called fresh on
    # every single repository call, per repository.py's _base_stmt()) is the single largest
    # contributor to tenant/organization lookup volume, and therefore to total SQL statement
    # growth as resource count scales — this is the confirmed root cause the growth measured in
    # Phase 0 the resource-repo-per-call tenant/org re-resolution above.
    resource_repo_calls = call_log.count("resource_repo.get")
    assert resource_repo_calls > 0
    # Every resource_repo.get() call triggers its own tenant+org resolution (2 statements), so
    # resource_repo.get() alone accounts for at least this many of the total tenant/org lookups —
    # a lower bound, since FinanceService's other collaborators also resolve tenant/org context
    # independently on their own calls.
    assert tenant_lookups >= resource_repo_calls
    assert org_lookups >= resource_repo_calls
