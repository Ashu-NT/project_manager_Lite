"""P3.4 -- regression guardrail for the confirmed N+1 in
TimesheetFinancialEventsMixin._enqueue_approved_time_events
(src/core/platform/application/time_management/time/timesheet_financial_events.py).

Before the fix, approving a timesheet period called
WorkAllocationRepository.get() once per time entry -- O(N) calls and O(N)
`task_assignments` SELECTs for N entries sharing the same work allocation.
The fix batches every distinct work_allocation_id into one
list_by_ids() call before the loop. These tests pin that behavior so it
cannot silently regress back to a per-entry loop.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import event

from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyAssignmentRepository,
)


def _setup(services, *, suffix: str):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        f"N+1 Guardrail {suffix}", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        f"N+1 Engineer {suffix}", hourly_rate=0, currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, f"N+1 Task {suffix}", start_date=date(2026, 5, 1), duration_days=60
    )
    assignment = services["task_service"].assign_resource(
        task.id, resource.id, allocation_percent=100
    )
    return project, resource, task, assignment


def _instrument(assignment_repo):
    """Wrap get()/list_by_ids() on this instance's class with counters.
    Returns (counts dict, restore callback)."""
    counts = {"get": 0, "list_by_ids": 0}
    cls = type(assignment_repo)
    real_get = cls.get
    real_list_by_ids = cls.list_by_ids

    def counting_get(self, *args, **kwargs):
        counts["get"] += 1
        return real_get(self, *args, **kwargs)

    def counting_list_by_ids(self, *args, **kwargs):
        counts["list_by_ids"] += 1
        return real_list_by_ids(self, *args, **kwargs)

    cls.get = counting_get
    cls.list_by_ids = counting_list_by_ids

    def restore():
        cls.get = real_get
        cls.list_by_ids = real_list_by_ids

    return counts, restore


def _count_allocation_selects(engine, fn):
    selects = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if "task_assignments" in statement:
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, len(selects)


def _approve_n_entries(services, session, *, entry_count: int, suffix: str):
    project, resource, task, assignment = _setup(services, suffix=suffix)
    for day in range(entry_count):
        services["task_service"].add_time_entry(
            assignment.id,
            entry_date=date(2026, 5, 1 + (day % 28)),
            hours=Decimal("1"),
            note=f"entry-{day}",
        )

    time_service = services["timesheet_service"]
    assignment_repo = time_service._work_allocation_repo
    assert isinstance(assignment_repo, SqlAlchemyAssignmentRepository)

    counts, restore = _instrument(assignment_repo)
    engine = session.get_bind()

    def do_approve():
        submitted = time_service.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))
        return time_service.approve_timesheet_period(
            submitted.period_id,
            expected_version=submitted.version,
            note="N+1 guardrail",
        )

    try:
        _, allocation_select_count = _count_allocation_selects(engine, do_approve)
    finally:
        restore()

    return counts, allocation_select_count


def test_approving_many_entries_issues_one_batch_allocation_call_not_one_per_entry(services, session):
    counts_1, selects_1 = _approve_n_entries(services, session, entry_count=1, suffix="one")
    counts_50, selects_50 = _approve_n_entries(services, session, entry_count=50, suffix="fifty")

    assert counts_1["get"] == 0, "expected _enqueue_approved_time_events to never call get() directly"
    assert counts_50["get"] == 0, "expected _enqueue_approved_time_events to never call get() directly"

    assert counts_1["list_by_ids"] == 1
    assert counts_50["list_by_ids"] == 1, (
        f"approving 50 entries issued {counts_50['list_by_ids']} list_by_ids() calls, expected "
        "exactly 1 -- the per-entry N+1 may have regressed."
    )

    # The work-allocation SELECT count must not scale with entry count -- it
    # should be the same small constant for 1 entry and for 50.
    assert selects_50 == selects_1, (
        f"work-allocation SELECT count grew from {selects_1} (1 entry) to {selects_50} "
        "(50 entries) -- expected a constant, entry-count-independent number of SELECTs."
    )


def test_batch_allocation_call_scales_with_distinct_allocations_not_entries(services, session):
    """50 entries against ONE shared assignment must not cost more
    allocation SELECTs than 1 entry against that same assignment -- the
    batch call is keyed by distinct work_allocation_ids, not by entry
    count."""
    _, selects_1 = _approve_n_entries(services, session, entry_count=1, suffix="single")
    _, selects_10 = _approve_n_entries(services, session, entry_count=10, suffix="ten")

    assert selects_1 == selects_10
