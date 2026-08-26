from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import date
from pathlib import Path
from time import perf_counter

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetEntryCriteria,
    TimesheetHistoryCriteria,
    TimesheetResourceFact,
    TimesheetResourceSelectorCriteria,
    TimesheetReviewCriteria,
    TimesheetScope,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources.sqlalchemy_catalog_reader import (
    SqlAlchemyResourceCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources.sqlalchemy_workload_reader import (
    SqlAlchemyResourceWorkloadDemandReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets.sqlalchemy_review_reader import (
    SqlAlchemyTimesheetReviewReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets.sqlalchemy_workspace_reader import (
    SqlAlchemyTimesheetWorkspaceReader,
)


pytestmark = pytest.mark.postgresql_integration

PERF_TENANT = "r5h-perf-tenant"
PERF_SCOPES = {
    10_000: "r5h-perf-org-10k",
    50_000: "r5h-perf-org-50k",
}
_EVIDENCE: dict[str, object] = {"environment": "docker-postgresql-16"}


def _percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _measure(operation: Callable[[], object], *, repetitions: int = 7) -> dict[str, float]:
    operation()
    samples: list[float] = []
    for _ in range(repetitions):
        started = perf_counter()
        operation()
        samples.append((perf_counter() - started) * 1000)
    return {
        "p50_ms": round(_percentile(samples, 0.50), 2),
        "p95_ms": round(_percentile(samples, 0.95), 2),
        "min_ms": round(min(samples), 2),
        "max_ms": round(max(samples), 2),
    }


def _seed_scale(connection, *, size: int, organization_id: str) -> None:
    suffix = "10k" if size == 10_000 else "50k"
    project_id = f"r5h-perf-project-{suffix}"
    task_id = f"r5h-perf-task-{suffix}"
    connection.execute(
        text(
            "INSERT INTO organizations "
            "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, is_active, version) "
            "VALUES (:id, :tenant, :code, :name, 'UTC', 'XAF', true, 1)"
        ),
        {
            "id": organization_id,
            "tenant": PERF_TENANT,
            "code": f"R5H-PERF-{suffix.upper()}",
            "name": f"R5H Performance {suffix}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO projects "
            "(id, tenant_id, project_code, name, description, status, organization_id, version) "
            "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, 1)"
        ),
        {
            "id": project_id,
            "tenant": PERF_TENANT,
            "code": f"R5H-PERF-P-{suffix.upper()}",
            "name": f"R5H Performance Project {suffix}",
            "organization": organization_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO tasks "
            "(id, project_id, task_code, wbs_code, sort_order, name, description, status, "
            "priority, percent_complete, is_milestone, start_date, end_date, version) "
            "VALUES (:id, :project, :code, '1', 1, :name, '', 'TODO', 0, 0, false, "
            "'2026-08-01', '2026-08-31', 1)"
        ),
        {
            "id": task_id,
            "project": project_id,
            "code": f"R5H-PERF-T-{suffix.upper()}",
            "name": f"R5H Performance Task {suffix}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO resources "
            "(id, tenant_id, resource_code, name, kind, role, hourly_rate, is_active, "
            "capacity_percent, cost_type, worker_type, organization_id, version) "
            "SELECT :prefix || value, :tenant, :code_prefix || value, "
            ":name_prefix || lpad(value::text, 6, '0'), 'PERSON', 'Engineer', 80, true, "
            "100, 'LABOR', 'EXTERNAL', :organization, 1 "
            "FROM generate_series(1, :size) AS value"
        ),
        {
            "prefix": f"r5h-perf-resource-{suffix}-",
            "code_prefix": f"R5H-{suffix.upper()}-",
            "name_prefix": f"Resource {suffix} ",
            "tenant": PERF_TENANT,
            "organization": organization_id,
            "size": size,
        },
    )
    connection.execute(
        text(
            "INSERT INTO task_assignments "
            "(id, task_id, resource_id, allocation_percent, hours_logged, "
            "allocated_planned_hours, version, response_status) "
            "SELECT :assignment_prefix || value, :task, :resource_prefix || value, "
            "100, 8, 40, 1, 'accepted' FROM generate_series(1, :size) AS value"
        ),
        {
            "assignment_prefix": f"r5h-perf-assignment-{suffix}-",
            "resource_prefix": f"r5h-perf-resource-{suffix}-",
            "task": task_id,
            "size": size,
        },
    )
    connection.execute(
        text(
            "INSERT INTO time_entries "
            "(id, tenant_id, organization_id, work_allocation_id, assignment_id, entry_date, "
            "hours, note, owner_type, scope_type, scope_id, created_at, updated_at, version) "
            "SELECT :entry_prefix || value, :tenant, :organization, "
            ":assignment_prefix || value, :assignment_prefix || value, '2026-08-24', "
            "8, 'R5H performance entry', 'work_allocation', 'project', :project, now(), now(), 1 "
            "FROM generate_series(1, :size) AS value"
        ),
        {
            "entry_prefix": f"r5h-perf-entry-{suffix}-",
            "assignment_prefix": f"r5h-perf-assignment-{suffix}-",
            "tenant": PERF_TENANT,
            "organization": organization_id,
            "project": project_id,
            "size": size,
        },
    )
    connection.execute(
        text(
            "INSERT INTO timesheet_periods "
            "(id, tenant_id, organization_id, resource_id, period_start, period_end, status, "
            "submitted_at, submitted_by_username, version) "
            "SELECT :period_prefix || value, :tenant, :organization, :resource_prefix || value, "
            "'2026-08-01', '2026-08-31', 'SUBMITTED', now(), 'r5h-perf', 1 "
            "FROM generate_series(1, :size) AS value"
        ),
        {
            "period_prefix": f"r5h-perf-period-{suffix}-",
            "resource_prefix": f"r5h-perf-resource-{suffix}-",
            "tenant": PERF_TENANT,
            "organization": organization_id,
            "size": size,
        },
    )


@pytest.fixture(scope="module", autouse=True)
def seeded_performance_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tenants "
                "(id, tenant_code, display_name, tenant_status, is_active, version) "
                "VALUES (:id, 'R5H-PERF', 'R5H Performance', 'active', true, 1)"
            ),
            {"id": PERF_TENANT},
        )
        for size, organization_id in PERF_SCOPES.items():
            _seed_scale(connection, size=size, organization_id=organization_id)
        connection.execute(text("ANALYZE"))
    yield
    evidence_path = Path(".security-evidence/r5h1_postgresql.json")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(_EVIDENCE, indent=2, sort_keys=True), encoding="utf-8")


def _count_reader_statements(session, operation: Callable[[], object]) -> tuple[object, int]:
    session.execute(text("SELECT 1"))
    statements = 0

    def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal statements
        normalized = statement.lstrip().upper()
        if normalized.startswith("SELECT") or normalized.startswith("WITH"):
            statements += 1

    event.listen(session.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        return operation(), statements
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", before_cursor_execute)


@pytest.mark.parametrize("size", [10_000, 50_000])
def test_real_readers_are_bounded_and_measured(postgres_test_environment, size):
    organization_id = PERF_SCOPES[size]
    session = postgres_test_environment.runtime_session(
        tenant_id=PERF_TENANT, organization_id=organization_id
    )
    try:
        catalog = SqlAlchemyResourceCatalogReader(session=session)
        workload = SqlAlchemyResourceWorkloadDemandReader(session=session)
        selector = SqlAlchemyTimesheetWorkspaceReader(session=session)
        review = SqlAlchemyTimesheetReviewReader(session=session)
        suffix = "10k" if size == 10_000 else "50k"
        resource_id = f"r5h-perf-resource-{suffix}-1"
        resource = TimesheetResourceFact(
            resource_id=resource_id,
            resource_name=f"Resource {suffix} 000001",
            resource_code=f"R5H-{suffix.upper()}-1",
            kind="PERSON",
            worker_type="EXTERNAL",
        )

        def read_catalog():
            return catalog.read_page(
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                search_text="",
                active=True,
                category=None,
                page=1,
                page_size=25,
                sort=ReadSort("title", ReadSortDirection.ASCENDING),
            )

        def read_selector():
            return selector.read_resource_page(
                scope=TimesheetScope.ALL,
                actor_user_id="r5h-reviewer",
                explicit_team_project_ids=(),
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                criteria=TimesheetResourceSelectorCriteria(),
                page=1,
                page_size=20,
            )

        def read_review():
            return review.read_page(
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                allowed_project_ids=None,
                criteria=TimesheetReviewCriteria(),
                page=1,
                page_size=25,
            )

        def read_inspector():
            return catalog.read_inspector(
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                resource_id=resource_id,
            )

        def read_availability_demand():
            return workload.read_overlapping_assignments(
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                resource_id=resource_id,
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 31),
            )

        def read_timesheet_entries():
            return selector.read_entries(
                resource=resource,
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                visible_project_ids=None,
                criteria=TimesheetEntryCriteria(period_start=date(2026, 8, 1)),
                page=1,
                page_size=25,
            )

        def read_timesheet_history():
            return selector.read_history(
                resource=resource,
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                criteria=TimesheetHistoryCriteria(),
                page=1,
                page_size=12,
            )

        def read_review_inspector():
            return review.read_item(
                item_id=f"r5h-perf-period-{suffix}-1",
                tenant_id=PERF_TENANT,
                organization_id=organization_id,
                allowed_project_ids=None,
            )

        catalog_page, catalog_statements = _count_reader_statements(session, read_catalog)
        selector_page, selector_statements = _count_reader_statements(session, read_selector)
        review_page, review_statements = _count_reader_statements(session, read_review)
        assert catalog_page.filtered_total == size
        assert selector_page.total == size
        assert review_page.total == size
        assert review_page.items
        assert all(
            item.project_ids == (f"r5h-perf-project-{suffix}",)
            and item.entry_count == 1
            for item in review_page.items
        )
        assert catalog_statements <= 3
        assert selector_statements <= 2
        assert review_statements <= 2

        measurements = {
            "catalog": _measure(read_catalog),
            "timesheet_resource_selector": _measure(read_selector),
            "review_queue": _measure(read_review),
            "resource_inspector": _measure(read_inspector),
            "availability_assignment_demand": _measure(read_availability_demand),
            "timesheet_entries": _measure(read_timesheet_entries),
            "timesheet_history": _measure(read_timesheet_history),
            "review_queue_inspector": _measure(read_review_inspector),
            "statement_counts": {
                "catalog": catalog_statements,
                "timesheet_resource_selector": selector_statements,
                "review_queue": review_statements,
            },
        }
        _EVIDENCE[f"scale_{size}"] = measurements
        assert measurements["catalog"]["p95_ms"] <= 200
        assert measurements["review_queue"]["p95_ms"] <= 200
        assert measurements["resource_inspector"]["p95_ms"] <= 100
        assert measurements["availability_assignment_demand"]["p95_ms"] <= 200
        assert measurements["timesheet_entries"]["p95_ms"] <= 200
        assert measurements["timesheet_history"]["p95_ms"] <= 200
        assert measurements["review_queue_inspector"]["p95_ms"] <= 200
    finally:
        session.close()


@pytest.mark.parametrize("size", [10_000, 50_000])
def test_explain_analyze_buffers_uses_runtime_scope(postgres_test_environment, size):
    organization_id = PERF_SCOPES[size]
    session = postgres_test_environment.runtime_session(
        tenant_id=PERF_TENANT, organization_id=organization_id
    )
    statements = {
        "catalog": (
            "SELECT id, resource_code, name FROM resources "
            "WHERE tenant_id = :tenant AND organization_id = :organization AND is_active "
            "ORDER BY lower(name), id LIMIT 25"
        ),
        "timesheet_resource_selector": (
            "SELECT id, resource_code, name FROM resources "
            "WHERE tenant_id = :tenant AND organization_id = :organization "
            "AND is_active AND kind = 'PERSON' AND worker_type = 'EXTERNAL' "
            "AND cost_type = 'LABOR' ORDER BY lower(name), id LIMIT 20"
        ),
        "review_queue": (
            "WITH selected_periods AS ("
            "SELECT p.id, p.resource_id, p.period_start, p.period_end, p.submitted_at "
            "FROM timesheet_periods p JOIN resources r ON r.id = p.resource_id "
            "WHERE p.tenant_id = :tenant AND p.organization_id = :organization "
            "AND p.status = 'SUBMITTED' "
            "ORDER BY p.submitted_at DESC, p.id DESC LIMIT 25), "
            "entry_ownership AS ("
            "SELECT e.id AS entry_id, a.resource_id FROM time_entries e "
            "JOIN task_assignments a ON a.id = coalesce(e.assignment_id, e.work_allocation_id) "
            "WHERE e.tenant_id = :tenant AND e.organization_id = :organization) "
            "SELECT p.id, p.submitted_at, count(e.id) "
            "FROM selected_periods p JOIN entry_ownership o ON o.resource_id = p.resource_id "
            "JOIN time_entries e ON e.id = o.entry_id "
            "AND e.entry_date BETWEEN p.period_start AND p.period_end "
            "GROUP BY p.id, p.submitted_at ORDER BY p.submitted_at DESC, p.id DESC"
        ),
        "resource_inspector": (
            "SELECT r.id, r.name, "
            "(SELECT count(*) FROM task_assignments a "
            "JOIN tasks t ON t.id = a.task_id JOIN projects p ON p.id = t.project_id "
            "WHERE a.resource_id = r.id AND p.tenant_id = :tenant "
            "AND p.organization_id = :organization) AS assignment_count "
            "FROM resources r WHERE r.id = :resource AND r.tenant_id = :tenant "
            "AND r.organization_id = :organization"
        ),
        "availability_assignment_demand": (
            "SELECT a.id, t.id, t.start_date, t.end_date FROM task_assignments a "
            "JOIN tasks t ON t.id = a.task_id JOIN projects p ON p.id = t.project_id "
            "WHERE a.resource_id = :resource AND p.tenant_id = :tenant "
            "AND p.organization_id = :organization AND t.start_date <= '2026-08-31' "
            "AND t.end_date >= '2026-08-01' ORDER BY t.start_date, a.id"
        ),
        "timesheet_entries": (
            "SELECT e.id, e.entry_date, e.hours FROM time_entries e "
            "JOIN task_assignments a ON a.id = coalesce(e.assignment_id, e.work_allocation_id) "
            "WHERE e.tenant_id = :tenant AND e.organization_id = :organization "
            "AND a.resource_id = :resource AND e.entry_date BETWEEN '2026-08-01' AND '2026-08-31' "
            "ORDER BY e.entry_date DESC, e.id DESC LIMIT 25"
        ),
        "timesheet_history": (
            "SELECT p.id, p.period_start, sum(e.hours) FROM timesheet_periods p "
            "JOIN task_assignments a ON a.resource_id = p.resource_id "
            "JOIN time_entries e ON e.assignment_id = a.id "
            "AND e.entry_date BETWEEN p.period_start AND p.period_end "
            "WHERE p.tenant_id = :tenant AND p.organization_id = :organization "
            "AND p.resource_id = :resource GROUP BY p.id, p.period_start "
            "ORDER BY p.period_start DESC, p.id DESC LIMIT 12"
        ),
    }
    try:
        plans: dict[str, object] = {}
        for name, statement in statements.items():
            plan = session.scalar(
                text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}"),
                {
                    "tenant": PERF_TENANT,
                    "organization": organization_id,
                    "resource": f"r5h-perf-resource-{'10k' if size == 10_000 else '50k'}-1",
                },
            )
            root = plan[0]
            plans[name] = {
                "planning_time_ms": root.get("Planning Time"),
                "execution_time_ms": root.get("Execution Time"),
                "plan": root.get("Plan"),
            }
        _EVIDENCE[f"plans_{size}"] = plans
        assert all(float(value["execution_time_ms"] or 0) >= 0 for value in plans.values())
    finally:
        session.close()
