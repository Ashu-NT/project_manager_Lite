"""Task-scoped (never resource-wide, never period-bound) Time summary + resource
breakdown + paginated Time Entries listing, against the real backend.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)


def _setup_project_resource(services, *, planned_hours: float = 100.0):
    ps = services['project_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]
    project = services['project_create'].create_project("Time Redesign Backend Project")
    resource = services["resource_master_commands"].create_resource("Alice Brown", hourly_rate=50.0)
    project_resource = services["project_resource_commands"].add_to_project(project.id, resource.id, planned_hours=planned_hours)
    return ps, rs, prs, project, resource, project_resource


def test_task_time_summary_aggregates_across_all_assignments_on_the_task(services):
    ps, rs, prs, project, alice, pr_alice = _setup_project_resource(services)
    services['task_lookup_query']
    bob = services["resource_master_commands"].create_resource("Bob Smith", hourly_rate=60.0)
    pr_bob = services["project_resource_commands"].add_to_project(project.id, bob.id, planned_hours=100.0)
    task = services['task_lifecycle_commands'].create_task(project.id, "Electrical Design")

    a1 = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_alice.id,
        allocation_percent=50.0, allocated_planned_hours=Decimal(32),
    )
    a2 = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_bob.id,
        allocation_percent=40.0, allocated_planned_hours=Decimal(24),
    )
    services["time_entry_commands"].add_time_entry(a1.id, entry_date=date(2026, 8, 16), hours=18.0, note="Wiring")
    services["time_entry_commands"].add_time_entry(a2.id, entry_date=date(2026, 8, 17), hours=20.0, note="Docs")

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )
    summary = api.get_task_time_summary(task.id)

    assert summary.planned_hours_label == "56.0 h"
    assert summary.actual_hours_label == "38.0 h"
    assert summary.remaining_hours_label == "18.0 h"
    assert summary.has_overrun is False
    assert summary.assignment_count == 2
    breakdown_by_resource = {row.resource_name: row for row in summary.resource_breakdown}
    assert breakdown_by_resource["Alice Brown"].actual_hours_label == "18.0 h"
    assert breakdown_by_resource["Bob Smith"].actual_hours_label == "20.0 h"


def test_task_time_summary_reports_overrun_when_actual_exceeds_planned(services):
    ps, rs, prs, project, alice, pr_alice = _setup_project_resource(services, planned_hours=10.0)
    services['task_lookup_query']
    task = services['task_lifecycle_commands'].create_task(project.id, "Overrun Task")
    assignment = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_alice.id,
        allocation_percent=100.0, allocated_planned_hours=Decimal(8),
    )
    services["time_entry_commands"].add_time_entry(assignment.id, entry_date=date(2026, 8, 16), hours=6.0, note="Work")
    services["time_entry_commands"].add_time_entry(assignment.id, entry_date=date(2026, 8, 17), hours=6.0, note="More work")

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )
    summary = api.get_task_time_summary(task.id)

    assert summary.planned_hours_label == "8.0 h"
    assert summary.actual_hours_label == "12.0 h"
    assert summary.has_overrun is True
    assert summary.overrun_hours_label == "4.0 h"
    assert summary.remaining_hours_label == "0.0 h"
    assert summary.burn_status == "OVERRUN"
    row = summary.resource_breakdown[0]
    assert row.has_overrun is True
    assert row.overrun_hours_label == "4.0 h"


def test_task_time_summary_and_entries_are_task_scoped_not_resource_wide(services):
    """The same resource logs time against two different tasks -- Task A's figures must
    reflect only Task A's hours, never the resource's combined total."""
    ps, rs, prs, project, alice, pr_alice = _setup_project_resource(services, planned_hours=100.0)
    services['task_lookup_query']
    task_a = services['task_lifecycle_commands'].create_task(project.id, "Task A")
    task_b = services['task_lifecycle_commands'].create_task(project.id, "Task B")

    assignment_a = services['task_assignment_commands'].assign_project_resource(
        task_id=task_a.id, project_resource_id=pr_alice.id,
        allocation_percent=50.0, allocated_planned_hours=Decimal(20),
    )
    assignment_b = services['task_assignment_commands'].assign_project_resource(
        task_id=task_b.id, project_resource_id=pr_alice.id,
        allocation_percent=50.0, allocated_planned_hours=Decimal(50),
    )
    services["time_entry_commands"].add_time_entry(assignment_a.id, entry_date=date(2026, 8, 16), hours=18.0, note="Task A work")
    services["time_entry_commands"].add_time_entry(assignment_b.id, entry_date=date(2026, 8, 16), hours=42.0, note="Task B work")

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )

    summary_a = api.get_task_time_summary(task_a.id)
    summary_b = api.get_task_time_summary(task_b.id)

    assert summary_a.actual_hours_label == "18.0 h"
    assert summary_b.actual_hours_label == "42.0 h"

    entries_a = api.list_task_time_entries(task_a.id, page=1, page_size=25)
    entries_b = api.list_task_time_entries(task_b.id, page=1, page_size=25)

    assert entries_a.total == 1
    assert entries_a.items[0].hours == 18.0
    assert entries_b.total == 1
    assert entries_b.items[0].hours == 42.0


def test_list_task_time_entries_paginates_authoritatively(services):
    ps, rs, prs, project, alice, pr_alice = _setup_project_resource(services, planned_hours=1000.0)
    services['task_lookup_query']
    task = services['task_lifecycle_commands'].create_task(project.id, "Many Entries Task")
    assignment = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_alice.id,
        allocation_percent=100.0, allocated_planned_hours=Decimal(500),
    )
    base_date = date(2026, 8, 1)
    for i in range(7):
        services["time_entry_commands"].add_time_entry(
            assignment.id, entry_date=base_date + timedelta(days=i), hours=1.0 + i, note=f"Entry {i}"
        )

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )

    page1 = api.list_task_time_entries(task.id, page=1, page_size=3)
    page2 = api.list_task_time_entries(task.id, page=2, page_size=3)
    page3 = api.list_task_time_entries(task.id, page=3, page_size=3)

    assert page1.total == 7
    assert len(page1.items) == 3
    assert len(page2.items) == 3
    assert len(page3.items) == 1
    # Newest-first: page 1's first row is the latest date (day 6).
    assert page1.items[0].entry_date_label == (base_date + timedelta(days=6)).isoformat()
    all_ids = {item.entry_id for item in page1.items + page2.items + page3.items}
    assert len(all_ids) == 7


def test_list_task_time_entries_filters_by_resource(services):
    ps, rs, prs, project, alice, pr_alice = _setup_project_resource(services, planned_hours=100.0)
    services['task_lookup_query']
    bob = services["resource_master_commands"].create_resource("Bob Smith", hourly_rate=55.0)
    pr_bob = services["project_resource_commands"].add_to_project(project.id, bob.id, planned_hours=100.0)
    task = services['task_lifecycle_commands'].create_task(project.id, "Filter Task")

    a1 = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_alice.id, allocation_percent=50.0
    )
    a2 = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=pr_bob.id, allocation_percent=50.0
    )
    services["time_entry_commands"].add_time_entry(a1.id, entry_date=date(2026, 8, 16), hours=3.0, note="Alice work")
    services["time_entry_commands"].add_time_entry(a2.id, entry_date=date(2026, 8, 16), hours=4.0, note="Bob work")

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )

    alice_only = api.list_task_time_entries(task.id, resource_id=alice.id, page=1, page_size=25)
    assert alice_only.total == 1
    assert alice_only.items[0].resource_name == "Alice Brown"

    unfiltered = api.list_task_time_entries(task.id, page=1, page_size=25)
    assert unfiltered.total == 2


def test_get_task_time_summary_returns_none_for_blank_task_id(services):
    ps = services['project_query']
    services['task_lookup_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], resource_query=rs, project_resource_query=prs,
        task_assignment_commands=services["task_assignment_commands"],
        task_time_entries=services["task_time_entries"],
    )
    assert api.get_task_time_summary("") is None
    assert api.list_task_time_entries("") is None
